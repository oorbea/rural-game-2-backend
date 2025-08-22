from flask import current_app
from flask_socketio import Namespace

from controllers.GameController import GameController

class LobbyEvents(Namespace):
    """Namespace for handling game-related events."""

    def on_next_turn(self, data:dict):
        gc: GameController = current_app.extensions['game_controller']