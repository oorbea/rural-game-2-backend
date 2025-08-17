from controllers.GameController import ChallengeProvider
from models.Role import Role


class TurnManager(ChallengeProvider):
    _roles:list[Role] = []

    def __init__(self):
        def key_func(role: Role) -> tuple[int, int]:
            quantity = role.quantity_per_game if role.quantity_per_game is not None else -1
            return (role.priority, quantity)
        
        self._roles = sorted(Role.query.all(), key=key_func, reverse=True)

    def _get_random_player(self, players, *args, **kwargs) -> str:
        """Select a random player from the list."""
        from random import choice
        return choice(tuple(players))
    
    def _ponderate_roles(self, roles_priority:tuple[int], player_quantity: int) -> list[int]:
        total_priority = sum(roles_priority)
        raw = [(priority / total_priority) * player_quantity for priority in roles_priority]
        ponderated = [int(x) for x in raw]
        remainder = player_quantity - sum(ponderated)
        if remainder > 0:
            fractional = [(i, raw[i] - ponderated[i]) for i in range(len(raw))]
            fractional.sort(key=lambda x: x[1], reverse=True)
            for i in range(remainder):
                ponderated[fractional[i][0]] += 1
        return ponderated
    
    def get_next_challenge(self, lobby_code: str, game_state: dict) -> dict:
        return {}
    
    def get_player_roles(self, lobby_code: str, players: list[str]) -> dict[str, str]:
        if not players:
            raise ValueError("Cannot assign roles: no players or roles available")
        if not lobby_code:
            raise ValueError("Lobby code is required to assign roles")
        
        players_with_roles = {}
        
        remaining_roles:list[Role] = []
        for role in self._roles:
            if not players:
                break
            if role.quantity_per_game is not None:
                for i in range(role.quantity_per_game):
                    if players:
                        player = self._get_random_player(players)
                        players.remove(player)
                        players_with_roles[player] = role.title
                    else:
                        break
            else:
                remaining_roles.append(role)
        
        if remaining_roles and players:
            roles_priority = [role.priority for role in remaining_roles]
            ponderated = self._ponderate_roles(roles_priority, len(players))
            for i, role in enumerate(remaining_roles):
                for _ in range(ponderated[i]):
                    if players:
                        player = self._get_random_player(players)
                        players.remove(player)
                        players_with_roles[player] = role.title
                    else:
                        break
        
        for player in players:
            players_with_roles[player] = "default"
        
        return players_with_roles