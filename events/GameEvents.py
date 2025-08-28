import os
from flask import current_app
from flask_socketio import Namespace, join_room, leave_room
from marshmallow import ValidationError
from controllers.GameController import GameController
from enums.TurnType import TurnTypeEnum
from helpers.PlayerInfo import PlayerInfo
from schemas import CodeAndDescriptionSchema, CodeAndTurnTypeSchema, PlayerInfoSchema, CodeAndUsernameSchema, CodeAndPlayerSchema, SkipOrCompleteTurnSchema, UpdatePlayerSchema
import base64
import re
import time
from urllib.parse import quote_plus

class GameEvents(Namespace):
    """Namespace for handling lobby and game related events."""

    def __profile_pic_url(self, code: str, player_name: str) -> str:
        host = current_app.config.get('HOST_NAME', 'http://localhost:5000')
        api_prefix = current_app.config.get('API_PREFIX', '/api/v1')
        return f"{host}{api_prefix}/lobby/{code}/user/{player_name}/profile-picture"
    
    def _profile_pic_url(self, code: str, player_name: str) -> str:
        """Generate a profile picture URL with cache-busting."""
        url = self.__profile_pic_url(code, player_name)
        return f"{url}?t={int(time.time())}"
    
    def _challenge_pic_url(self, title:str, turn_type:TurnTypeEnum|str) -> str:
        host = current_app.config.get('HOST_NAME', 'http://localhost:5000')
        api_prefix = current_app.config.get('API_PREFIX', '/api/v1')
        turn_type = turn_type.value if hasattr(turn_type, 'value') else str(turn_type)
        title = quote_plus(title)
        return f"{host}{api_prefix}/{turn_type.replace('_type', '')}/icon?title={title}"
        
    def on_create_lobby(self, data: dict):
        try:
            player = data['player']
        except KeyError:
            return {'ok': False, 'error': 'Player information is required to create a lobby.'}

        schema = PlayerInfoSchema()
        try:
            player: dict = schema.load(player)
        except ValidationError as e:
            return {'ok': False, 'error': str(e)}

        gc: GameController = current_app.extensions['game_controller']
        try:
            code = gc.create_lobby(PlayerInfo(**player))
            join_room(code)

            self.emit('player_joined', {
                'player': player['username'],
                'profile_picture_url': self._profile_pic_url(code, player['username'])
            }, room=code, include_self=False)

            players = gc.redis.lrange(gc.PLAYERS_LIST_TEMPLATE.format(code=code), 0, -1)
            return {'ok': True, 'code': code, 'connected_players': [
                {'username': p, 'profile_picture_url': self._profile_pic_url(code, p)} for p in players
            ]}
        except ValueError as e:
            return {'ok': False, 'error': str(e)}
        except Exception as e:
            return {'ok': False, 'error': f'An error occurred while creating the lobby.\n{str(e)}'}



    def on_join_lobby(self, data: dict):
        try:
            code = data['code'] = str(data['code'])
            info = data['player']
        except KeyError:
            return {'ok': False, 'error': 'Lobby code and Player Information are required to join a lobby.'}

        schema = CodeAndPlayerSchema()
        try:
            data = schema.load(data)
        except ValidationError as e:
            return {'ok': False, 'error': str(e)}

        gc: GameController = current_app.extensions['game_controller']
        try:
            gc.join_lobby(code, PlayerInfo(**info))
            join_room(code)

            self.emit('player_joined', {
                'player': info['username'],
                'profile_picture_url': self._profile_pic_url(code, info['username']),
            }, room=code, include_self=False)

            players = gc.redis.lrange(gc.PLAYERS_LIST_TEMPLATE.format(code=code), 0, -1)
            return {'connected_players': [
                {'username': p, 'profile_picture_url': self._profile_pic_url(code, p)} for p in players
            ]}

        except ValueError as e:
            return {'ok': False, 'error': str(e)}
        except Exception as e:
            self.emit('error', {'message': f'An error occurred while joining the lobby.\n{str(e)}'}, room=code)
            return {'ok': False, 'error': f'An error occurred while joining the lobby.\n{str(e)}'}

    def on_leave_lobby(self, data: dict):
        try:
            code = data['code'] = str(data['code'])
            player = data['player_name']
        except KeyError:
            return {'ok': False, 'error': 'Lobby code and Player name are required to leave a lobby.'}

        schema = CodeAndUsernameSchema()
        try:
            data = schema.load(data)
        except ValidationError as e:
            return {'ok': False, 'error': str(e)}

        gc: GameController = current_app.extensions['game_controller']
        try:
            new_host = gc.player_manager.remove_player(code, player)
            leave_room(code)

            self.emit('player_left', {'player': player, 'host': new_host}, room=code, include_self=False)
            return {'ok': True, 'host': new_host}
        except ValueError as e:
            self.emit('error', {'message': str(e)}, room=code)
            return {'ok': False, 'error': str(e)}
        except Exception as e:
            self.emit('error', {'message': f'An error occurred while leaving the lobby.\n{str(e)}'}, room=code)
            return {'ok': False, 'error': f'An error occurred while leaving the lobby.\n{str(e)}'}

    
    def on_start_game(self, data:dict):
        try:
            code = data['code'] = str(data['code'])
            player = data['player_name']
        except KeyError:
            return {'ok': False, 'error': 'Lobby code and Player name are required to start a game.'}
        schema = CodeAndUsernameSchema()
        try:
            data = schema.load(data)
        except ValidationError as e:
            return {'ok': False, 'error': str(e)}
        gc:GameController = current_app.extensions['game_controller']
        try:
            gc.start_game(code, player)
            game_state = gc.get_lobby_state(code)
            self.emit('game_started', game_state, room=code)
            return {'ok': True}
        except ValueError as e:
            self.emit('error', {'message': str(e)}, room=code)
            return {'ok': False, 'error': str(e)}
        except Exception as e:
            self.emit('error', {'message': f'An error occurred while starting the game.\n{str(e)}'}, room=code)
            return {'ok': False, 'error': f'An error occurred while starting the game.\n{str(e)}'}
    
    def on_update_player(self, data: dict):
        try:
            code = data['code'] = str(data['code'])
            current_username = data['current_username']
        except KeyError:
            return {'ok': False, 'error': 'Lobby code and current username are required to update player information.'}

        schema = UpdatePlayerSchema()
        try:
            data = schema.load(data)
        except ValidationError as e:
            return {'ok': False, 'error': str(e)}

        data.pop('code', None)
        data.pop('current_username', None)

        gc: GameController = current_app.extensions['game_controller']
        try:
            new_username = data.pop('new_username', current_username)
            data['username'] = new_username
            gc.update_player_info(code, current_username, data)

            url = self._profile_pic_url(code, new_username)
            self.emit('player_updated', {
                'old_username': current_username,
                'new_username': new_username,
                'profile_picture_url': url
            }, room=code, include_self=False)
            return {'ok': True, 'player': new_username, 'profile_picture_url': url}

        except ValueError as e:
            return {'ok': False, 'error': str(e)}
        except Exception as e:
            return {'ok': False, 'error': f'An error occurred while updating player information.\n{str(e)}'}
    
    def on_get_user_info(self, data: dict):
        try:
            code = data['code'] = str(data['code'])
            username = data['player_name']
        except KeyError:
            return {'ok': False, 'error': 'Lobby code and player_name are required to get user information.'}

        schema = CodeAndUsernameSchema()
        try:
            data = schema.load(data)
        except ValidationError as e:
            return {'ok': False, 'error': str(e)}

        gc: GameController = current_app.extensions['game_controller']
        try:
            info = gc.get_player_info(code, username)
            return {'ok': True, 'player_info': {
                'username': info.username,
                'drinking': info.drinking,
                'smoking': info.smoking,
                'partnered': info.partnered,
                'virgin': info.virgin,
                'gender': info.gender.value if hasattr(info.gender, 'value') else str(info.gender),
                'profile_picture_url': self._profile_pic_url(code, username)
            }}

        except ValueError as e:
            return {'ok': False, 'error': str(e)}
        except Exception as e:
            return {'ok': False, 'error': f'An error occurred while retrieving user information.\n{str(e)}'}

    def on_update_profile_picture(self, data: dict):
        """Update the profile picture of a player in the lobby (per-lobby)."""
        try:
            code = data['code'] = str(data['code'])
            username = data['player_name']
        except KeyError:
            return {'ok': False, 'error': 'Lobby code and player_name are required.'}

        remove_only = bool(data.get('remove', False))

        raw_b64_or_dataurl: str | None = data.get('image_base64') or data.get('data_url')
        ext = (data.get('extension') or '').lower()
        filename_hint = data.get('filename')

        if not remove_only and not raw_b64_or_dataurl:
            return {'ok': False, 'error': 'Provide image_base64 or data_url or set remove=true.'}

        gc: GameController = current_app.extensions['game_controller']
        try:
            r = gc.redis
            if not r.sismember(gc.ACTIVE_LOBBIES_SET, code):
                return {'ok': False, 'error': 'Lobby not found or inactive.'}
            if username not in r.lrange(gc.PLAYERS_LIST_TEMPLATE.format(code=code), 0, -1):
                return {'ok': False, 'error': 'Player not in this lobby.'}

            content_b64 = None
            image_bytes = None
            if not remove_only:
                s = raw_b64_or_dataurl.strip()
                if ',' in s:
                    header, content_b64 = s.split(',', 1)
                    m = re.match(r'^data:(?P<mime>[^;]+);base64$', header.strip(), flags=re.IGNORECASE)
                    if m and not ext:
                        mime = m.group('mime').lower()
                        if '/' in mime:
                            ext = mime.rsplit('/', 1)[-1]
                else:
                    content_b64 = s

                if not ext and filename_hint and isinstance(filename_hint, str) and '.' in filename_hint:
                    ext = filename_hint.rsplit('.', 1)[-1].lower()

                if not ext:
                    return {'ok': False, 'error': 'Cannot infer image extension. Provide "extension", or "filename", or use a data URL header.'}

                allowed = set(current_app.config.get('ALLOWED_PICTURE_EXTENSIONS', {'png', 'jpg', 'jpeg', 'gif'}))
                if ext not in allowed:
                    return {'ok': False, 'error': f'Unsupported image extension: {ext}, allowed: {", ".join(allowed)}.'}

                try:
                    image_bytes = base64.b64decode(content_b64, validate=True)
                except Exception:
                    return {'ok': False, 'error': 'Invalid base64 image.'}

            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            pictures_dir = os.path.join(base_dir, current_app.config.get('PROFILE_PICTURES_DIR', 'public/ProfilePictures'))
            os.makedirs(pictures_dir, exist_ok=True)

            lobby_user_key = gc.player_manager.LOBBY_USER_TEMPLATE.format(code=code, username=username)
            old_path = r.hget(lobby_user_key, 'profile_pic')

            def resolve_fs(path: str | None) -> str | None:
                if not path:
                    return None
                if os.path.isabs(path):
                    return path
                return os.path.join(base_dir, path.lstrip('/'))

            new_rel_path = None
            if not remove_only:
                safe_username = re.sub(r'[^A-Za-z0-9_.-]', '_', username)
                new_filename = f"{code}_{safe_username}_{int(time.time())}.{ext}"
                fs_path = os.path.join(pictures_dir, new_filename)
                try:
                    with open(fs_path, 'wb') as f:
                        f.write(image_bytes)
                except Exception as e:
                    return {'ok': False, 'error': f'Error writing profile picture: {e}'}
                new_rel_path = os.path.relpath(fs_path, base_dir).replace(os.sep, '/')

            try:
                update_payload = {'profile_pic': None} if remove_only else {'profile_pic': new_rel_path}
                gc.update_player_info(code, username, update_payload)
            except Exception as e:
                if new_rel_path:
                    try:
                        new_fs = resolve_fs(new_rel_path)
                        if new_fs and os.path.exists(new_fs):
                            os.remove(new_fs)
                    except Exception:
                        pass
                return {'ok': False, 'error': f'Failed to update profile picture in store: {e}'}

            if old_path:
                try:
                    old_fs = resolve_fs(old_path)
                    if old_fs and os.path.exists(old_fs):
                        os.remove(old_fs)
                except Exception:
                    pass

            url = self._profile_pic_url(code, username)
            payload = {'player': username, 'profile_picture_url': url, 'removed': remove_only}
            self.emit('profile_picture_updated', payload, room=code, include_self=False)
            return {'ok': True, **payload}
        except Exception as e:
            return {'ok': False, 'error': f'An error occurred while updating profile picture.\n{str(e)}'}

    def on_next_turn(self, data:dict):
        """Proceed to the next turn in the game."""
        try:
            code = data['code'] = str(data['code'])
            turn_type = data['turn_type']
        except KeyError:
            return {'ok': False, 'error': 'Lobby code and turn type are required to proceed to the next turn.'}
        
        schema = CodeAndTurnTypeSchema()
        try:
            data = schema.load(data)
        except ValidationError as e:
            return {'ok': False, 'error': str(e)}
        
        gc: GameController = current_app.extensions['game_controller']

        try:
            self.emit('next_turn_type', {'turn_type': turn_type}, room=code)

            challenge, player = gc.next_turn(code, turn_type)

            challenge['icon'] = self._challenge_pic_url(challenge.get('title', 'unknown_title_error'), turn_type)
            
            if turn_type == TurnTypeEnum.SECRET_MISSION.value:
                self.emit('following_turn', {
                        'turn_type': turn_type,
                        'challenge': None,
                        'player': player
                    }, room=code)
                return {'ok': True, 'challenge': challenge, 'player': player, 'turn_type': turn_type}

            else:
                self.emit('following_turn', {
                    'turn_type': turn_type,
                    'challenge': challenge,
                    'player': player
                }, room=code)
                return {'ok': True}

        except ValueError as e:
            return {'ok': False, 'error': str(e)}
        except Exception as e:
            self.emit('error', {'message': f'An error occurred while proceeding to the next turn.\n{str(e)}'}, room=code)
            return {'ok': False, 'error': f'An error occurred while proceeding to the next turn.\n{str(e)}'}
        
    def on_choose_target(self, data:dict):
        """Choose the participants for a target challenge."""
        try:
            code = data['code'] = str(data['code'])
            description = data['description']
        except KeyError:
            return {'ok': False, 'error': 'Lobby code and description are required to choose a target.'}
        
        schema = CodeAndDescriptionSchema()
        try:
            data = schema.load(data)
        except ValidationError as e:
            return {'ok': False, 'error': str(e)}
        
        gc: GameController = current_app.extensions['game_controller']

        try:     
            player = gc.get_current_turn_player(code) 

            self.emit('target_chosen', {
                'turn_type': TurnTypeEnum.TARGET_CHALLENGE.value,
                'description': description,
                'player': player
            }, room=code)

            return {'ok': True}

        except ValueError as e:
            return {'ok': False, 'error': str(e)}
        except Exception as e:
            self.emit('error', {'message': f'An error occurred while choosing a target.\n{str(e)}'}, room=code)
            return {'ok': False, 'error': f'An error occurred while choosing a target.\n{str(e)}'}
        
    def on_skip_turn(self, data:dict):
        """Skip the current turn in the game."""
        try:
            code = data['code'] = str(data['code'])
            player = data['player_name']
            turn_type = data['turn_type']
            title = data['title']
        except KeyError:
            return {'ok': False, 'error': 'Lobby code, player username, turn type and title of the challenge are required to skip a turn.'}
        
        schema = SkipOrCompleteTurnSchema()
        try:
            data = schema.load(data)
        except ValidationError as e:
            return {'ok': False, 'error': str(e)}
        
        if turn_type == TurnTypeEnum.SECRET_MISSION.value:
            return {'ok': False, 'error': 'Cannot skip a Secret Mission turn.'}
        
        gc: GameController = current_app.extensions['game_controller']

        try:
            new_score = gc.skip_turn(code, player, turn_type, title)

            self.emit('turn_skipped', {
                'player': player,
                'turn_type': turn_type,
                'title': title,
                'new_score': new_score
            }, room=code)

            return {'ok': True}

        except ValueError as e:
            return {'ok': False, 'error': str(e)}
        except Exception as e:
            self.emit('error', {'message': f'An error occurred while skipping the turn.\n{str(e)}'}, room=code)
            return {'ok': False, 'error': f'An error occurred while skipping the turn.\n{str(e)}'}

    def on_complete_turn(self, data:dict):
        """The challenge for the current turn has been completed and the score should be updated."""
        try:
            code = data['code'] = str(data['code'])
            player = data['player_name']
            turn_type = data['turn_type']
            title = data['title']
        except KeyError:
            return {'ok': False, 'error': 'Lobby code, player username turn type and title of the challenge are required to skip a turn.'}

        schema = SkipOrCompleteTurnSchema()
        try:
            data = schema.load(data)
        except ValidationError as e:
            return {'ok': False, 'error': str(e)}

        gc: GameController = current_app.extensions['game_controller']

        try:
            score, voting = gc.complete_turn(code, player, turn_type, title)

            if voting:
                self.emit('turn_completed_needs_voting', {
                    'player': player,
                    'turn_type': turn_type,
                    'title': title,
                    'potential_prize': score
                }, room=code)

                return {'ok': True, 'potential_prize': score, 'voting': voting}

            self.emit('turn_completed', {
                'player': player,
                'turn_type': turn_type,
                'title': title,
                'new_score': score
            }, room=code)
            
            return {'ok': True}
        
        except ValueError as e:
            return {'ok': False, 'error': str(e)}
        except Exception as e:
            self.emit('error', {'message': f'An error occurred while completing the turn.\n{str(e)}'}, room=code)
            return {'ok': False, 'error': f'An error occurred while completing the turn.\n{str(e)}'}