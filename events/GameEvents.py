import json
import os
from flask import current_app
from flask_socketio import Namespace, join_room, leave_room
from marshmallow import ValidationError
from controllers.GameController import GameController
from enums.TurnType import TurnTypeEnum
from helpers.PlayerInfo import PlayerInfo
from schemas import CodeAndDescriptionSchema, CodeAndTurnTypeSchema, DetectiveGuessSchema, GivePointsSchema, JudgeSecretMissionSchema, PlayerInfoSchema, CodeAndUsernameSchema, CodeAndPlayerSchema, SkipOrCompleteTurnSchema, UpdatePlayerSchema, VoteSchema, VoteTeamSchema
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
    
    def _maybe_emit_game_finished(self, code: str):
        gc: GameController = current_app.extensions['game_controller']
        try:
            state = gc.get_lobby_state(code)
        except Exception:
            return

        lobby = state.get("lobby", {}) or {}
        winner = lobby.get("winner")
        if not winner:
            return

        try:
            ptw = int(lobby.get("points_to_win")) if lobby.get("points_to_win") is not None else None
        except Exception:
            ptw = None

        payload = {
            "winner": winner,
            "points_to_win": ptw,
            "ended_at": lobby.get("ended_at"),
            "closing": True,
        }
        self.emit('game_finished', payload, room=code)

        try:
            gc.end_lobby(code)
        except Exception:
            pass

        self.emit('lobby_closed', {'code': code}, room=code)
        
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

        points_to_win = data.get('points_to_win')
        try:
            if points_to_win is not None:
                points_to_win = int(points_to_win)
                if points_to_win <= 0:
                    points_to_win = None
        except Exception:
            points_to_win = None

        gc: GameController = current_app.extensions['game_controller']
        try:
            code = gc.create_lobby(PlayerInfo(**player), points_to_win=points_to_win)
            join_room(code)

            self.emit('player_joined', {
                'player': player['username'],
                'profile_picture_url': self._profile_pic_url(code, player['username'])
            }, room=code, include_self=False)

            players = gc.redis.lrange(gc.PLAYERS_LIST_TEMPLATE.format(code=code), 0, -1)
            resp = {'ok': True, 'code': code, 'connected_players': [
                {'username': p, 'profile_picture_url': self._profile_pic_url(code, p)} for p in players
            ]}
            if points_to_win is not None:
                resp['points_to_win'] = points_to_win
            return resp
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
            info_dict = info.to_dict()
            info_dict['profile_picture_url'] = self._profile_pic_url(code, username)
            info_dict.pop('profile_pic', None)

            return {'ok': True, 'player_info': info_dict}

        except ValueError as e:
            return {'ok': False, 'error': str(e)}
        except Exception as e:
            return {'ok': False, 'error': f'An error occurred while retrieving user information.\n{str(e)}'}
        
    def on_get_player_state(self, data: dict):
        try:
            code = data['code'] = str(data['code'])
            username = data['player_name']
        except KeyError:
            return {'ok': False, 'error': 'Lobby code and player_name are required to get player state.'}

        schema = CodeAndUsernameSchema()
        try:
            data = schema.load(data)
        except ValidationError as e:
            return {'ok': False, 'error': str(e)}

        gc: GameController = current_app.extensions['game_controller']
        try:
            state = gc.get_player_state(code, username)
            return {'ok': True, 'player_state': state.to_dict()}

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
            st = gc.get_lobby_state(code)
            lb = st.get("lobby", {}) or {}
            if lb.get("winner") or (str(lb.get("active", "true")).lower() in ("0","false","f","no","n")):
                w = lb.get("winner")
                if w:
                    return {'ok': False, 'error': f'The game has already finished. Winner: {w}.'}
                return {'ok': False, 'error': 'The game is not active.'}
        except Exception:
            pass

        try:
            self.emit('next_turn_type', {'turn_type': turn_type}, room=code)

            challenge, player = gc.next_turn(code, turn_type)

            challenge['icon'] = self._challenge_pic_url(challenge.get('title', 'unknown_title_error'), turn_type)

            meta = gc.get_current_challenge_meta(code)
            participants = []
            teams = []
            candidates_by_slot = None
            try:
                participants = json.loads(meta.get("participants", "[]"))
            except Exception:
                pass
            try:
                teams = json.loads(meta.get("teams", "[]"))
            except Exception:
                pass
            try:
                candidates_by_slot = json.loads(meta.get("candidates_by_slot", "null"))
            except Exception:
                candidates_by_slot = None

            if turn_type == TurnTypeEnum.SECRET_MISSION.value:
                self.emit('following_turn', {
                        'turn_type': turn_type,
                        'challenge': None,
                        'player': player,
                        'participants': participants
                    }, room=code)
                return {'ok': True, 'challenge': challenge, 'player': player, 'turn_type': turn_type}

            payload = {
                'turn_type': turn_type,
                'challenge': challenge,
                'player': player,
                'participants': participants
            }
            if teams:
                payload['teams'] = teams
            if candidates_by_slot is not None:
                payload['candidates_by_slot'] = candidates_by_slot

            self.emit('following_turn', payload, room=code)
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

            meta = gc.get_current_challenge_meta(code)
            slots = json.loads(meta.get("slots", "[]")) if meta.get("slots") else []
            team_by_slot = json.loads(meta.get("team_by_slot", "{}")) if meta.get("team_by_slot") else {}

            from helpers.RestrictionAdapter import RestrictionAdapter
            chosen = RestrictionAdapter.extract_chosen_from_description(description)
            assigned = {}
            for i, slot in enumerate(slots):
                if i < len(chosen):
                    assigned[slot] = chosen[i]

            teams_map: dict[str, list[str]] = {}
            for slot, username in assigned.items():
                team_name = team_by_slot.get(slot)
                if team_name:
                    teams_map.setdefault(team_name, []).append(username)

            teams = [{"name": name, "members": members} for name, members in sorted(teams_map.items(), key=lambda x: x[0])]
            participants = list(dict.fromkeys(chosen))
            if player not in participants:
                participants = [player] + participants

            new_meta = {
                "participants": json.dumps(participants),
                "teams": json.dumps(teams),
            }
            gc.set_current_challenge_meta(code, new_meta)

            self.emit('target_chosen', {
                'turn_type': TurnTypeEnum.TARGET_CHALLENGE.value,
                'description': description,
                'player': player,
                'participants': participants,
                'teams': teams
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
            meta = gc.get_current_challenge_meta(code)
            try:
                is_group = str(meta.get("group_challenge", "false")).lower() in ("1","true","t","yes","y")
                turn_now = meta.get("turn_type")
                if is_group and turn_now in (TurnTypeEnum.GROUP_CHALLENGE.value, TurnTypeEnum.TARGET_CHALLENGE.value):
                    participants = json.loads(meta.get("participants", "[]")) if meta.get("participants") else []
                    if player not in participants:
                        return {'ok': False, 'error': 'Only participants of this group challenge can skip it.'}
            except Exception:
                pass

            new_score = gc.skip_turn(code, player, turn_type, title)

            self.emit('turn_skipped', {
                'player': player,
                'turn_type': turn_type,
                'title': title,
                'new_score': new_score
            }, room=code)

            self._maybe_emit_game_finished(code)
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
            meta = gc.get_current_challenge_meta(code)
            is_group = str(meta.get("group_challenge", "false")).lower() in ("1","true","t","yes","y")
            turn_now = meta.get("turn_type")
            title_now = meta.get("title", title)
            prize = int(meta.get("prize", 0))
            voting_flag = bool(json.loads(meta.get("voting"))) if meta.get("voting") is not None else False
            participants = json.loads(meta.get("participants", "[]")) if meta.get("participants") else []
            teams = json.loads(meta.get("teams", "[]")) if meta.get("teams") else []

            if is_group and turn_now == TurnTypeEnum.GROUP_CHALLENGE.value and teams and len(teams) > 1:
                info = gc.begin_team_vote(code, teams=teams, participants=participants, title=title_now, turn_type=TurnTypeEnum.GROUP_CHALLENGE)
                self.emit('team_vote_started', {
                    'turn_type': TurnTypeEnum.GROUP_CHALLENGE.value,
                    'title': title_now,
                    'teams': teams,
                    'expected': info.get('expected', 0)
                }, room=code)
                return {'ok': True, 'team_vote': True}

            if is_group and turn_now == TurnTypeEnum.TARGET_CHALLENGE.value and teams and len(teams) > 1:
                info = gc.begin_team_vote(code, teams=teams, participants=participants, title=title_now, turn_type=TurnTypeEnum.TARGET_CHALLENGE)
                self.emit('team_vote_started', {
                    'turn_type': TurnTypeEnum.TARGET_CHALLENGE.value,
                    'title': title_now,
                    'teams': teams,
                    'expected': info.get('expected', 0)
                }, room=code)
                return {'ok': True, 'team_vote': True}

            if is_group and participants:
                if voting_flag:
                    gc.begin_vote_session(code,
                        performer_label=player,
                        turn_type=turn_now,
                        title=title_now,
                        potential_prize=prize,
                        awardees=participants
                    )
                    self.emit('turn_completed_needs_voting', {
                        'player': player,
                        'turn_type': turn_now,
                        'title': title_now,
                        'potential_prize': prize,
                        'participants': participants
                    }, room=code)
                    return {'ok': True, 'potential_prize': prize, 'voting': True}
                else:
                    totals = gc.award_points_to(code, participants, prize)
                    self.emit('turn_completed', {
                        'player': player,
                        'turn_type': turn_now,
                        'title': title_now,
                        'new_scores': totals
                    }, room=code)
                    gc.clear_current_challenge_meta(code)
                    self._maybe_emit_game_finished(code)
                    return {'ok': True}

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

            self._maybe_emit_game_finished(code)
            return {'ok': True}
        
        except ValueError as e:
            return {'ok': False, 'error': str(e)}
        except Exception as e:
            self.emit('error', {'message': f'An error occurred while completing the turn.\n{str(e)}'}, room=code)
            return {'ok': False, 'error': f'An error occurred while completing the turn.\n{str(e)}'}
        
    def on_vote(self, data: dict):
        """Vote for the performance of the last completed turn (0..10). Dictator counts as double."""
        try:
            code = data['code'] = str(data['code'])
            voter = data['player_name']
            vote = int(data['vote'])
        except KeyError:
            return {'ok': False, 'error': 'Lobby code, player username and vote are required to vote.'}
        except ValueError:
            return {'ok': False, 'error': 'Vote must be an integer.'}

        schema = VoteSchema()
        try:
            data = schema.load(data)
        except ValidationError as e:
            return {'ok': False, 'error': str(e)}

        gc: GameController = current_app.extensions['game_controller']
        r = gc.redis
        try:
            base = f"lobby:{code}:vote:performance"
            voted_set = f"{base}:voted"
            byuser_hash = f"{base}:byuser"

            if vote < 0 or vote > 10:
                return {'ok': False, 'error': 'Vote must be between 0 and 10.'}

            if r.sismember(voted_set, voter):
                return {'ok': False, 'error': 'You have already voted.'}

            r.hset(byuser_hash, voter, vote)
            r.sadd(voted_set, voter)

            voted = sorted(list(r.smembers(voted_set)))
            self.emit('vote_progress', {'voted': voted}, room=code)

            meta = getattr(gc, "get_current_challenge_meta", lambda c: {}) (code) or {}
            participants = []
            try:
                import json as _json
                participants = _json.loads(meta.get('participants', '[]')) if isinstance(meta.get('participants'), str) else (meta.get('participants') or [])
            except Exception:
                participants = []

            state = gc.get_lobby_state(code)
            lobby_players = state.get('order', []) or []
            if participants and len(participants) < len(lobby_players):
                eligible = [p for p in lobby_players if p not in participants]
            else:
                eligible = list(lobby_players)

            if len(voted) >= len(eligible) and len(eligible) > 0:
                all_votes = r.hgetall(byuser_hash)
                total_weight = 0
                weighted_sum = 0
                for user, vv in all_votes.items():
                    try:
                        v_int = int(vv)
                    except Exception:
                        continue
                    w = gc.get_vote_weight(code, user)
                    total_weight += w
                    weighted_sum += v_int * w

                avg = (weighted_sum / total_weight) if total_weight > 0 else 0.0

                potential_prize = int(meta.get('prize') or 0)
                award_points = int(round(potential_prize * (avg / 10.0)))

                performer = meta.get('performer')
                if performer:
                    new_score = gc.update_score(code, performer, award_points)
                else:
                    new_score = None

                self.emit('vote_finished', {
                    'average': avg,
                    'award_points': award_points,
                    'performer': performer,
                    'new_score': new_score
                }, room=code)

                self._maybe_emit_game_finished(code)
                return {'ok': True, 'average': avg, 'award_points': award_points, 'performer': performer, 'new_score': new_score}

            return {'ok': True}

        except ValueError as e:
            return {'ok': False, 'error': str(e)}
        except Exception as e:
            self.emit('error', {'message': f'An error occurred while voting.\n{str(e)}'}, room=code)
            return {'ok': False, 'error': f'An error occurred while voting.\n{str(e)}'}


    def on_team_vote(self, data: dict):
        """
        Vote to choose the winning team in a group/target challenge with teams>1.
        Dictator's vote counts as double (adds +2 to the chosen team).
        """
        try:
            code = data['code'] = str(data['code'])
            voter = data['player_name']
            team = data['team']
        except KeyError:
            return {'ok': False, 'error': 'Lobby code, player_name and team are required to vote the team.'}

        gc: GameController = current_app.extensions['game_controller']
        r = gc.redis

        try:
            # Keys
            base = f"lobby:{code}:vote:team"
            voted_set = f"{base}:voted"
            byuser_hash = f"{base}:byuser"
            counts_hash = f"{base}:counts"

            if r.sismember(voted_set, voter):
                return {'ok': False, 'error': 'You have already voted.'}

            if not isinstance(team, str) or not team.startswith("Team"):
                return {'ok': False, 'error': 'Invalid team value.'}

            r.hset(byuser_hash, voter, team)
            r.sadd(voted_set, voter)

            weight = gc.get_vote_weight(code, voter)
            r.hincrby(counts_hash, team, weight)

            voted = sorted(list(r.smembers(voted_set)))
            current_counts = {k: int(v) for k, v in r.hgetall(counts_hash).items()}
            self.emit('team_vote_progress', {'voted': voted, 'counts': current_counts}, room=code)

            meta = getattr(gc, "get_current_challenge_meta", lambda c: {}) (code) or {}
            participants = []
            try:
                import json as _json
                participants = _json.loads(meta.get('participants', '[]')) if isinstance(meta.get('participants'), str) else (meta.get('participants') or [])
            except Exception:
                participants = []

            state = gc.get_lobby_state(code)
            lobby_players = state.get('order', []) or []
            if participants and len(participants) < len(lobby_players):
                eligible = [p for p in lobby_players if p not in participants]
            else:
                eligible = list(lobby_players)

            if len(voted) >= len(eligible) and len(eligible) > 0:
                counts = {k: int(v) for k, v in r.hgetall(counts_hash).items()}
                if not counts:
                    return {'ok': True}

                max_count = max(counts.values())
                top = [team_name for team_name, c in counts.items() if c == max_count]

                if len(top) == 1:
                    winner = top[0]
                else:
                    import json as _json
                    teams_struct = []
                    try:
                        teams_struct = _json.loads(meta.get('teams', '[]')) if isinstance(meta.get('teams'), str) else (meta.get('teams') or [])
                    except Exception:
                        teams_struct = []

                    def avg_points(team_name: str) -> float:
                        members = []
                        for t in teams_struct:
                            if t.get("name") == team_name:
                                members = list(t.get("members") or [])
                                break
                        if not members:
                            return float('inf')
                        total = 0
                        for m in members:
                            try:
                                total += gc.get_player_state(code, m).points
                            except Exception:
                                pass
                        return total / max(1, len(members))

                    winner = min(top, key=lambda tn: avg_points(tn))

                self.emit('team_vote_finished', {
                    'winner_team': winner,
                    'counts': counts
                }, room=code)

                return {'ok': True, 'winner_team': winner, 'counts': counts}

            return {'ok': True}

        except ValueError as e:
            return {'ok': False, 'error': str(e)}
        except Exception as e:
            self.emit('error', {'message': f'An error occurred while team voting.\n{str(e)}'}, room=code)
            return {'ok': False, 'error': f'An error occurred while team voting.\n{str(e)}'}


    def on_give_points(self, data: dict):
        """Give points to a player."""
        try:
            code = data['code'] = str(data['code'])
            receiver = data['player_name']
            points = data['points'] = int(data['points'])
        except KeyError:
            return {'ok': False, 'error': 'Lobby code, receiver username and points are required to give points.'}

        schema = GivePointsSchema()
        try:
            data = schema.load(data)
        except ValidationError as e:
            return {'ok': False, 'error': str(e)}

        gc: GameController = current_app.extensions['game_controller']
        try:
            new_score = gc.update_score(code, receiver, points)

            self.emit('points_given', {
                'player': receiver,
                'points': points,
                'new_score': new_score
            }, room=code)

            self._maybe_emit_game_finished(code)
            return {'ok': True}

        except ValueError as e:
            return {'ok': False, 'error': str(e)}
        except Exception as e:
            self.emit('error', {'message': f'An error occurred while giving points.\n{str(e)}'}, room=code)
            return {'ok': False, 'error': f'An error occurred while giving points.\n{str(e)}'}
        
    def on_judge_secret_mission(self, data: dict):
        """
        Judge validates a player's secret mission (success/fail).
        Applies prize or punishment and removes the mission from the player's list.
        """
        try:
            code = data['code'] = str(data['code'])
            judge_name = data['judge_name']
            player_name = data['player_name']
            mission_title = data['mission_title']
            success = bool(data['success'])
        except KeyError:
            return {'ok': False, 'error': 'code, judge_name, player_name, mission_title and success are required.'}

        schema = JudgeSecretMissionSchema()
        try:
            data = schema.load(data)
        except ValidationError as e:
            return {'ok': False, 'error': str(e)}

        gc: GameController = current_app.extensions['game_controller']
        try:
            new_score, delta = gc.judge_secret_mission(code, judge_name, player_name, mission_title, success)
            payload = {
                'player': player_name,
                'mission_title': mission_title,
                'success': success,
                'points_applied': delta,
                'new_score': new_score,
                'judged_by': judge_name
            }
            self.emit('secret_mission_judged', payload, room=code)

            self._maybe_emit_game_finished(code)
            return {'ok': True, **payload}
        except ValueError as e:
            return {'ok': False, 'error': str(e)}
        except Exception as e:
            self.emit('error', {'message': f'An error occurred while judging secret mission.\n{str(e)}'}, room=code)
            return {'ok': False, 'error': f'An error occurred while judging secret mission.\n{str(e)}'}

    def on_detective_guess_role(self, data: dict):
        """
        Detective guesses someone else's role.
        +200 if correct, -200 and 60s cooldown if wrong.
        Broadcast does NOT reveal who the detective is.
        """
        try:
            code = data['code'] = str(data['code'])
            detective_name = data['detective_name']
            target_player = data['target_player']
            guessed_role = data['guessed_role']
        except KeyError:
            return {'ok': False, 'error': 'code, detective_name, target_player, guessed_role are required.'}

        schema = DetectiveGuessSchema()
        try:
            data = schema.load(data)
        except ValidationError as e:
            return {'ok': False, 'error': str(e)}

        gc: GameController = current_app.extensions['game_controller']
        try:
            correct, delta, new_score = gc.detective_guess_role(code, detective_name, target_player, guessed_role)
            self.emit('detective_guess_result', {
                'target_player': target_player,
                'guessed_role': guessed_role,
                'correct': correct
            }, room=code)

            self._maybe_emit_game_finished(code)
            return {
                'ok': True,
                'correct': correct,
                'points_delta': delta,
                'new_score': new_score
            }
        except ValueError as e:
            return {'ok': False, 'error': str(e)}
        except Exception as e:
            self.emit('error', {'message': f'An error occurred while guessing role.\n{str(e)}'}, room=code)
            return {'ok': False, 'error': f'An error occurred while guessing role.\n{str(e)}'}

    def on_get_role_info(self, data: dict):
        """Return role title + description (Tortolitos description rendered with partner)."""
        try:
            code = data['code'] = str(data['code'])
            username = data['player_name']
        except KeyError:
            return {'ok': False, 'error': 'Lobby code and player_name are required to get role info.'}

        gc: GameController = current_app.extensions['game_controller']
        try:
            info = gc.get_role_info(code, username)

            role_title = (info.get('title') or '')
            info['picture_url'] = self._challenge_pic_url(role_title, 'role')

            return {'ok': True, 'role': info}
        except ValueError as e:
            return {'ok': False, 'error': str(e)}
        except Exception as e:
            return {'ok': False, 'error': f'An error occurred while retrieving role info.\n{str(e)}'}

    def on_get_player_secret_missions(self, data: dict):
        """Return the pending secret missions for a player."""
        try:
            code = data['code'] = str(data['code'])
            username = data['player_name']
        except KeyError:
            return {'ok': False, 'error': 'Lobby code and player_name are required to get player secret missions.'}

        gc: GameController = current_app.extensions['game_controller']
        try:
            missions = gc.get_player_secret_missions(code, username)

            for m in missions:
                title = (m.get('title') or '')
                m['picture_url'] = self._challenge_pic_url(title, 'secret_mission')

            return {'ok': True, 'missions': missions}
        except ValueError as e:
            return {'ok': False, 'error': str(e)}
        except Exception as e:
            return {'ok': False, 'error': f'An error occurred while retrieving secret missions.\n{str(e)}'}
