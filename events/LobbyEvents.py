from flask import current_app
from flask_socketio import Namespace, join_room, leave_room
from marshmallow import ValidationError
from controllers.GameController import GameController
from helpers.PlayerInfo import PlayerInfo
from schemas import PlayerInfoSchema

class LobbyEvents(Namespace):
    """Namespace for handling lobby-related events."""
    def on_create_lobby(self, data):
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


    def on_join_lobby(self, data):
        try:
            code = str(data['code'])
        except KeyError:
            return {'ok': False, 'error': 'Lobby code is required to join a lobby.'}
        if len(code) != 4:
            return {'ok': False, 'error': 'Lobby code must be exactly 4 characters long.'}
        try:
            info = data['player']
        except KeyError:
            return {'ok': False, 'error': 'Player information is required to join a lobby.'}
        schema = PlayerInfoSchema()
        try:
            info:dict = schema.load(info)
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
    
    def on_leave_lobby(self, data):
        try:
            code = str(data['code'])
        except KeyError:
            return {'ok': False, 'error': 'Lobby code is required to leave a lobby.'}
        if len(code) != 4:
            return {'ok': False, 'error': 'Lobby code must be exactly 4 characters long.'}
        try:
            player = data['player_name']
        except KeyError:
            return {'ok': False, 'error': 'Player name is required to leave a lobby.'}
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
    
    def on_start_game(self, data):
        try:
            code = str(data['code'])
        except KeyError:
            return {'ok': False, 'error': 'Lobby code is required to start a game.'}
        if len(code) != 4:
            return {'ok': False, 'error': 'Lobby code must be exactly 4 characters long.'}
        try:
            player = data['player_name']
        except KeyError:
            return {'ok': False, 'error': 'Player name is required to start a game.'}
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