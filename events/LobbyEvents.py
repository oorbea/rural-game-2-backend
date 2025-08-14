from flask import current_app
from flask_socketio import Namespace, join_room, leave_room
from marshmallow import ValidationError
from controllers.GameController import GameController
from helpers.PlayerInfo import PlayerInfo
from schemas import PlayerInfoSchema, CodeAndUsernameSchema, CodeAndPlayerSchema, UpdatePlayerSchema

class LobbyEvents(Namespace):
    """Namespace for handling lobby-related events."""
    def on_create_lobby(self, data:dict):
        try:
            player = data['player']
        except KeyError:
            return {'ok': False, 'error': 'Player information is required to create a lobby.'}
        schema = PlayerInfoSchema()
        try:
            player:dict = schema.load(player)
        except ValidationError as e:
            return {'ok': False, 'error': str(e)}
        gc:GameController = current_app.extensions['game_controller']
        try:
            code = gc.create_lobby(PlayerInfo(**player))
            join_room(code)
            self.emit('player_joined', {'player': player['username']}, room=code)
            return {'ok': True, 'code': code, 'connected_players': gc.get_connected_players(code)}
        except ValueError as e:
            return {'ok': False, 'error': str(e)}
        except Exception as e:
            return {'ok': False, 'error': f'An error occurred while creating the lobby.\n{str(e)}'}


    def on_join_lobby(self, data:dict):
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
        gc:GameController = current_app.extensions['game_controller']
        try:
            gc.join_lobby(code, PlayerInfo(**info))
            join_room(code)
            self.emit('player_joined', {'player': info['username']}, room=code, include_self=False)
            return {'connected_players': gc.get_connected_players(code)}
        except ValueError as e:
            return {'ok': False, 'error': str(e)}
        except Exception as e:
            self.emit('error', {'message': f'An error occurred while joining the lobby.\n{str(e)}'}, room=code)
            return {'ok': False, 'error': f'An error occurred while joining the lobby.\n{str(e)}'}
    
    def on_leave_lobby(self, data:dict):
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
        gc:GameController = current_app.extensions['game_controller']
        try:
            new_host = gc.leave_lobby(code, player)
            leave_room(code)
            self.emit('player_left', {'player': player, 'host': new_host}, room=code, include_self=False)
            return {'ok': True}
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
    
    def on_update_player(self, data:dict):
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
        gc:GameController = current_app.extensions['game_controller']
        try:
            data['username'] = data.pop('new_username', current_username)
            gc.update_player_info(code, current_username, data)
            self.emit('player_updated', {'old_username': current_username, 'new_username': data['username']}, room=code, include_self=False)
            return {'ok': True, 'player': data['username']}
        except ValueError as e:
            return {'ok': False, 'error': str(e)}
        except Exception as e:
            return {'ok': False, 'error': f'An error occurred while updating player information.\n{str(e)}'}
    
    def on_get_user_info(self, data:dict):
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
        gc:GameController = current_app.extensions['game_controller']
        try:
            player_info = gc.get_player_info(code, username)
            return {'ok': True, 'player_info': player_info.to_dict()}
        except ValueError as e:
            return {'ok': False, 'error': str(e)}
        except Exception as e:
            return {'ok': False, 'error': f'An error occurred while retrieving user information.\n{str(e)}'}