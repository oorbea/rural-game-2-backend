from flask import current_app
from flask_socketio import Namespace, join_room, leave_room
from marshmallow import ValidationError
from controllers.GameController import GameController
from helpers.PlayerInfo import PlayerInfo
from schemas import PlayerInfoSchema

class LobbyEvents(Namespace):
    """Namespace for handling lobby-related events."""
    def on_join_lobby(self, data):
        code = str(data['code'])
        if len(code) != 4:
            return {'ok': False, 'error': 'Lobby code must be exactly 4 characters long.'}
        info = data['player']
        schema = PlayerInfoSchema()
        try:
            info:dict = schema.load(info)
        except ValidationError as e:
            return {'ok': False, 'error': str(e)}
        gc:GameController = current_app.extensions['game_controller']
        try:
            gc.join_lobby(code, PlayerInfo(**info))
            join_room(code)
            self.emit('player_joined', {'player': info['username']}, to=code, include_self=False)
            return {'connected_players': gc.get_connected_players(code)}
        except ValueError as e:
            return {'ok': False, 'error': str(e)}
        except Exception as e:
            self.emit('error', {'message': f'An error occurred while joining the lobby.\n{str(e)}'}, to=code)
            return {'ok': False, 'error': f'An error occurred while joining the lobby.\n{str(e)}'}
    
    def on_leave_lobby(self, data):
        code = str(data['code'])
        if len(code) != 4:
            return {'ok': False, 'error': 'Lobby code must be exactly 4 characters long.'}
        player = data['player_name']
        gc:GameController = current_app.extensions['game_controller']
        try:
            gc.leave_lobby(code, player)
            leave_room(code)
            self.emit('player_left', {'player': player}, to=code, include_self=False)
            return {'ok': True}
        except ValueError as e:
            self.emit('error', {'message': str(e)}, to=code)
            return {'ok': False, 'error': str(e)}
        except Exception as e:
            self.emit('error', {'message': f'An error occurred while leaving the lobby.\n{str(e)}'}, to=code)
            return {'ok': False, 'error': f'An error occurred while leaving the lobby.\n{str(e)}'}
    
    def on_start_game(self, data):
        code = str(data['code'])
        if len(code) != 4:
            return {'ok': False, 'error': 'Lobby code must be exactly 4 characters long.'}
        player = data['player_name']
        gc:GameController = current_app.extensions['game_controller']
        try:
            gc.start_game(code, player)
            game_state = gc.get_lobby_state(code)
            self.emit('game_started', game_state, to=code)
            return {'ok': True}
        except ValueError as e:
            self.emit('error', {'message': str(e)}, to=code)
            return {'ok': False, 'error': str(e)}
        except Exception as e:
            self.emit('error', {'message': f'An error occurred while starting the game.\n{str(e)}'}, to=code)
            return {'ok': False, 'error': f'An error occurred while starting the game.\n{str(e)}'}