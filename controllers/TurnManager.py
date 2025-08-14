from controllers.GameController import ChallengeProvider


class TurnManager(ChallengeProvider):
    def get_next_challenge(self, lobby_code: str, game_state: dict) -> dict:
        return {}
    
    def get_player_roles(self, lobby_code: str, players: list[str]) -> dict[str, str]:
        return {}