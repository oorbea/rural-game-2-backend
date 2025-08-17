from controllers.GameController import ChallengeProvider
from models.Role import Role


class TurnManager(ChallengeProvider):
    _roles:list[Role] = []

    def __init__(self):
        self._roles = Role.query.all()

    def _get_random_player(self, players: list[str]) -> str:
        """Select a random player from the list."""
        from random import choice
        return choice(players)
    
    def get_next_challenge(self, lobby_code: str, game_state: dict) -> dict:
        return {}
    
    def get_player_roles(self, lobby_code: str, players: list[str]) -> dict[str, str]:
        if not players or not self._roles:
            raise ValueError("Cannot assign roles: no players or roles available")
        if not lobby_code:
            raise ValueError("Lobby code is required to assign roles")
        
        return {}