from random import choice
from flask import current_app
from sqlalchemy import or_
from controllers.GameController import ChallengeProvider
from enums.TurnType import TurnTypeEnum
from helpers.PlayerInfo import PlayerInfo
from models.Challenge import Challenge
from models.GroupChallenge import GroupChallenge
from models.Role import Role
from models.SecretMission import SecretMission
from models.TargetChallenge import TargetChallenge

class TurnManager(ChallengeProvider):
    _roles:list[Role] = []

    def __init__(self):
        def key_func(role: Role) -> tuple[int, int]:
            quantity = role.quantity_per_game if role.quantity_per_game is not None else -1
            return (role.priority, quantity)
        
        self._roles = sorted(Role.query.all(), key=key_func, reverse=True)

    def _get_random_player(self, players, *args, **kwargs) -> str:
        """Select a random player from the list."""
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
    
    def _get_valid_challenges(self, code: str, challenge:type, restrictions: dict, player_name: str) -> list:
        """Get valid challenges based on lobby composition and player attributes."""
        gc = current_app.extensions['game_controller']
        player:PlayerInfo = gc.get_player_info(code, player_name)

        filters = []
        if restrictions:
            num_males = int(restrictions.get('males', 0))
            num_females = int(restrictions.get('females', 0))
            filters += [
                challenge.males <= num_males,
                challenge.females <= num_females,
            ]

        filters += [
            or_(challenge.drinking.is_(False), challenge.drinking == player.drinking),
            or_(challenge.smoking.is_(False), challenge.smoking == player.smoking),
            or_(challenge.partner_friendly.is_(True), challenge.partner_friendly == player.partnered),
        ]

        if challenge is not SecretMission:
            filters.append(or_(challenge.sex.is_(False), challenge.sex != player.virgin))

        return challenge.query.filter(*filters).all()
    
    def get_next_challenge(self, lobby_code: str, game_state: dict, type:TurnTypeEnum|str = TurnTypeEnum.CHALLENGE) -> dict:
        if not lobby_code:
            raise ValueError("Lobby code is required to get the next challenge")
        if not game_state:
            raise ValueError("Game state is required to get the next challenge")
        if not type:
            raise ValueError("Turn type is required to get the next challenge")
        
        if isinstance(type, str):
            type = TurnTypeEnum(type)

        player_name:str = game_state['order'][game_state['lobby']['current_turn']]

        match type:
            case TurnTypeEnum.CHALLENGE:
                challenges:list[Challenge] = self._get_valid_challenges(lobby_code, Challenge, game_state.get("restrictions", {"males": 0, "females": 0}), player_name)
                if not challenges:
                    raise ValueError("No valid challenges available for the current restrictions")
                chall = choice(challenges)
                return chall.to_dict()
            case TurnTypeEnum.GROUP_CHALLENGE:
                group_challenges:list[GroupChallenge] = self._get_valid_challenges(lobby_code, GroupChallenge, game_state.get("restrictions", {"males": 0, "females": 0}), player_name)
                if not group_challenges:
                    raise ValueError("No valid group challenges available for the current restrictions")
                gro = choice(group_challenges)
                return gro.to_dict()
            case TurnTypeEnum.SECRET_MISSION:
                secret_missions:list[SecretMission] = self._get_valid_challenges(lobby_code, SecretMission, game_state.get("restrictions", {"males": 0, "females": 0}), player_name)
                if not secret_missions:
                    raise ValueError("No valid secret missions available for the current restrictions")
                secr = choice(secret_missions)
                return secr.to_dict()
            case TurnTypeEnum.TARGET_CHALLENGE:
                target_challenges:list[TargetChallenge] = self._get_valid_challenges(lobby_code, TargetChallenge, game_state.get("restrictions", {"males": 0, "females": 0}), player_name)
                if not target_challenges:
                    raise ValueError("No valid target challenges available for the current restrictions")
                targ = choice(target_challenges)
                return targ.to_dict()
            case _:
                raise ValueError(f"Unsupported turn type: {type}")

    
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