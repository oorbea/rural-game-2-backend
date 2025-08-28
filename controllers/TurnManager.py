from random import choice, choices
from sqlalchemy import or_
from helpers.IChallengeProvider import ChallengeProvider
from enums.TurnType import TurnTypeEnum
from helpers.PlayerInfo import PlayerInfo
from helpers.RestrictionAdapter import RestrictionAdapter
from models.Challenge import Challenge
from models.GroupChallenge import GroupChallenge
from models.Role import Role
from models.SecretMission import SecretMission
from models.TargetChallenge import TargetChallenge
from random import shuffle

class TurnManager(ChallengeProvider):
    _roles:list[Role] = []
    gc = None

    def __init__(self):
        def key_func(role: Role) -> tuple[int, int]:
            quantity = role.quantity_per_game if role.quantity_per_game is not None else -1
            return (role.priority, quantity)
        
        self._roles = sorted(Role.query.all(), key=key_func, reverse=True)

    def _get_random_player(self, players, *args, **kwargs) -> str:
        """Select a random player from the list."""
        return choice(tuple(players))
    
    def _get_valid_players(self, players:list[PlayerInfo], challenge:Challenge|GroupChallenge|SecretMission|TargetChallenge) -> list[PlayerInfo]:
        valid_players = []
        for p in players:
            if self._valid_player(p, challenge):
                valid_players.append(p)
        return valid_players
    
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

    def _choice_with_probabilities(self, items: list[Challenge|GroupChallenge|SecretMission|TargetChallenge]) -> Challenge|GroupChallenge|SecretMission|TargetChallenge|None:
        if not items:
            return None
        
        weights:list[float] = [item.probability for item in items]
        return choices(items, weights=weights)[0]
    
    def _valid_player(self, p:PlayerInfo, challenge:Challenge|GroupChallenge|SecretMission|TargetChallenge) -> bool:
        return (challenge.drinking is False or p.drinking == challenge.drinking) and (challenge.smoking is False or p.smoking == challenge.smoking) and (challenge.partner_friendly is True or p.partnered == challenge.partner_friendly) and (not hasattr(challenge, 'sex') or challenge.sex is False or p.virgin != challenge.sex)
        
    def _get_valid_challenges(self, code: str, restrictions: dict, player_name: str) -> list[Challenge]:
        """Get valid challenges based on lobby composition and player attributes."""

        player:PlayerInfo = self.gc.get_player_info(code, player_name)

        filters = []
        if restrictions:
            num_males = int(restrictions.get('males', 0))
            num_females = int(restrictions.get('females', 0))
            filters += [
                Challenge.males <= num_males,
                Challenge.females <= num_females,
            ]

        filters += [
            or_(Challenge.drinking.is_(False), Challenge.drinking == player.drinking),
            or_(Challenge.smoking.is_(False), Challenge.smoking == player.smoking),
            or_(Challenge.partner_friendly.is_(True), Challenge.partner_friendly == player.partnered),
            or_(Challenge.sex.is_(False), Challenge.sex != player.virgin)
        ]

        return Challenge.query.filter(*filters).all()
    
    def _choose_challenge(self, player:str, challenges: list[Challenge], players_list: list[PlayerInfo]) -> Challenge|None:
        """
        Choose a challenge and select required players based on the challenge requirements.
        
        :param player: The player who will perform the challenge.
        :param challenges: List of valid challenges to choose from.
        :param players_list: List of all players in the lobby.
        :return: Selected challenge with players placed in the description, or None if no valid challenge found.
        """
        if not challenges:
            return None
        
        players_list.remove(next(filter(lambda x: hasattr(x, 'username') and x.username == player, players_list)))

        selected_players:list[PlayerInfo] = []

        challenge = self._choice_with_probabilities(challenges)
        if not challenge:
            return None
        
        needed_males = getattr(challenge, 'males', 0) or 0
        needed_females = getattr(challenge, 'females', 0) or 0

        shuffle(players_list)

        males_left = needed_males
        females_left = needed_females
        for p in players_list:

            gender = getattr(p, 'gender', None)
            gender_value = getattr(gender, 'value', gender)
            if not males_left and not females_left:
                if self._valid_player(p, challenge):
                    selected_players.append(p)
            elif males_left and (gender == 'male' or gender_value == 'male'):
                if self._valid_player(p, challenge):
                    selected_players.append(p)
                    males_left -= 1
            elif females_left and (gender == 'female' or gender_value == 'female'):
                if self._valid_player(p, challenge):
                    selected_players.append(p)
                    females_left -= 1
        
        shuffle(selected_players)
        challenge.description = RestrictionAdapter.place_players(challenge.description, selected_players, player)
        return challenge
    
    def _get_valid_group_challenges(self, code: str, restrictions: dict, player_name: str) -> list[GroupChallenge]:
        """Get valid group challenges based on lobby composition and player attributes."""

        player:PlayerInfo = self.gc.get_player_info(code, player_name)

        filters = []
        if restrictions:
            num_males = int(restrictions.get('males', 0))
            num_females = int(restrictions.get('females', 0))
            filters += [
                GroupChallenge.males <= num_males,
                GroupChallenge.females <= num_females,
                GroupChallenge.player_quantity <= num_males + num_females
            ]

        filters += [
            or_(GroupChallenge.drinking.is_(False), GroupChallenge.drinking == player.drinking),
            or_(GroupChallenge.smoking.is_(False), GroupChallenge.smoking == player.smoking),
            or_(GroupChallenge.partner_friendly.is_(True), GroupChallenge.partner_friendly == player.partnered),
            or_(GroupChallenge.sex.is_(False), GroupChallenge.sex != player.virgin)
        ]

        return GroupChallenge.query.filter(*filters).all()
    
    def _choose_group_challenge(self, player:str, challenges: list[GroupChallenge], players_list: list[PlayerInfo]) -> GroupChallenge|None:
        """
        Choose a group challenge and select required players based on the challenge requirements.

        :param player: The player who will perform the challenge.
        :param challenges: List of valid group challenges to choose from.
        :param players_list: List of all players in the lobby.
        :return: Selected group challenge with players placed in the description, or None if no valid challenge found.
        """
        if not challenges:
            return None

        challenges_list = challenges.copy()
        max_attempts = len(challenges_list) * 2
        attempts = 0

        challenge_found = False
        challenge = None
        selected_players: list[PlayerInfo] = []
        while not challenge_found and attempts < max_attempts:
            if not challenges_list:
                break

            challenge = self._choice_with_probabilities(challenges_list)

            player_quantity = getattr(challenge, 'player_quantity', 0) or 0
            needed_males = getattr(challenge, 'males', 0) or 0
            needed_females = getattr(challenge, 'females', 0) or 0

            valid_players: list[PlayerInfo] = []
            for p in players_list:
                if not hasattr(p, 'username'):
                    continue
                if p.username == player:
                    continue
                elif self._valid_player(p, challenge):
                    valid_players.append(p)

            if player_quantity > len(valid_players):
                challenges_list.remove(challenge)
                attempts += 1
                continue

            shuffle(valid_players)
            males_left = needed_males
            females_left = needed_females
            for p in valid_players:
                if len(selected_players) >= player_quantity:
                    challenge_found = True
                    break

                gender = getattr(p, 'gender', None)
                gender_value = getattr(gender, 'value', gender)
                if not males_left and not females_left:
                    if self._valid_player(p, challenge):
                        selected_players.append(p)
                elif males_left and (gender == 'male' or gender_value == 'male'):
                    if self._valid_player(p, challenge):
                        selected_players.append(p)
                        males_left -= 1
                elif females_left and (gender == 'female' or gender_value == 'female'):
                    if self._valid_player(p, challenge):
                        selected_players.append(p)
                        females_left -= 1
            else:
                if len(selected_players) >= player_quantity:
                    challenge_found = True
                else:
                    challenges_list.remove(challenge)
                    attempts += 1

        if challenge_found and challenge:
            shuffle(selected_players)
            challenge.description = RestrictionAdapter.place_players(challenge.description, selected_players, player)
            return challenge
        
        return None
    
    def _get_valid_secret_missions(self, code: str, restrictions: dict, player_name: str) -> list[SecretMission]:
        """Get valid secret missions based on lobby composition and player attributes."""

        player:PlayerInfo = self.gc.get_player_info(code, player_name)

        filters = []
        if restrictions:
            num_males = int(restrictions.get('males', 0))
            num_females = int(restrictions.get('females', 0))
            filters += [
                SecretMission.males <= num_males,
                SecretMission.females <= num_females,
            ]

        filters += [
            or_(SecretMission.drinking.is_(False), SecretMission.drinking == player.drinking),
            or_(SecretMission.smoking.is_(False), SecretMission.smoking == player.smoking),
            or_(SecretMission.partner_friendly.is_(True), SecretMission.partner_friendly == player.partnered)
        ]

        return SecretMission.query.filter(*filters).all()
    
    def _choose_secret_mission(self, player:str, challenges: list[SecretMission], players_list: list[PlayerInfo]) -> SecretMission|None:
        """
        Choose a secret mission and select required players based on the secret mission requirements.
        
        :param player: The player who will perform the secret mission.
        :param challenges: List of valid secret missions to choose from.
        :param players_list: List of all players in the lobby.
        :return: Selected secret mission with players placed in the description, or None if no valid secret mission found.
        """
        if not challenges:
            return None
        
        players_list.remove(next(filter(lambda x: hasattr(x, 'username') and x.username == player, players_list)))

        selected_players:list[PlayerInfo] = []

        challenge = self._choice_with_probabilities(challenges)
        if not challenge:
            return None
        
        needed_males = getattr(challenge, 'males', 0) or 0
        needed_females = getattr(challenge, 'females', 0) or 0

        shuffle(players_list)

        males_left = needed_males
        females_left = needed_females
        for p in players_list:

            gender = getattr(p, 'gender', None)
            gender_value = getattr(gender, 'value', gender)
            if not males_left and not females_left:
                if self._valid_player(p, challenge):
                    selected_players.append(p)
            elif males_left and (gender == 'male' or gender_value == 'male'):
                if self._valid_player(p, challenge):
                    selected_players.append(p)
                    males_left -= 1
            elif females_left and (gender == 'female' or gender_value == 'female'):
                if self._valid_player(p, challenge):
                    selected_players.append(p)
                    females_left -= 1
        
        shuffle(selected_players)
        challenge.description = RestrictionAdapter.place_players(challenge.description, selected_players, player)
        return challenge
    
    def _get_valid_target_challenges(self, restrictions: dict, players: list[PlayerInfo]) -> list[TargetChallenge]:
        """Get valid target challenges based on lobby composition and player attributes."""
        if not players:
            return []
        
        filters = []
        if restrictions:
            num_males = int(restrictions.get('males', 0))
            num_females = int(restrictions.get('females', 0))
            filters += [
                TargetChallenge.males <= num_males,
                TargetChallenge.females <= num_females,
                TargetChallenge.player_quantity <= num_males + num_females
            ]

        challenges:list[TargetChallenge] = TargetChallenge.query.filter(*filters).all()
        valid_challenges:list[TargetChallenge] = []
        for challenge in challenges:
            if challenge.group_challenge:
                valid_males = 0
                valid_females = 0
                for p in players:
                    if self._valid_player(p, challenge):
                        gender = getattr(p, 'gender', None)
                        gender_value = getattr(gender, 'value', gender)

                        if gender_value == 'male': valid_males += 1
                        else: valid_females += 1

                        if valid_males >= challenge.males and valid_females >= challenge.females:
                            valid_challenges.append(challenge)
                            break
            else:
                valid_player = any(self._valid_player(p, challenge) for p in players)
                if valid_player:
                    valid_challenges.append(challenge)
        return valid_challenges

    def _choose_target_challenge(self, challenges: list[TargetChallenge], players_list: list[PlayerInfo]) -> TargetChallenge|None:
        """
        Choose a target challenge and select required players based on the target challenge requirements.

        :param challenges: List of valid target challenges to choose from.
        :param players_list: List of all players in the lobby.
        :return: Selected target challenge with listo of possible players placed in the description, or None if no valid target challenge found.
        """
        if not challenges:
            return None
        
        valid_players:list[PlayerInfo] = []
        challenge:TargetChallenge|None = None

        challenge_found = False
        max_attempts = len(challenges) * 2
        attempts = 0
        while not challenge_found and attempts < max_attempts:
            challenge = self._choice_with_probabilities(challenges)
            valid_players = self._get_valid_players(players_list, challenge)
            if challenge.group_challenge:
                if len(valid_players) < challenge.player_quantity:
                    attempts += 1
                    continue
                challenge_found = True
            else:
                if not valid_players:
                    attempts += 1
                    continue
                challenge_found = True

        if challenge_found and challenge:
            challenge.description = RestrictionAdapter.possible_target_players(challenge, valid_players, players_list)
            return challenge
    
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
                cha = self._choose_challenge(player_name, self._get_valid_challenges(lobby_code, game_state.get("restrictions", {"males": 0, "females": 0}), player_name), [self.gc.get_player_info(lobby_code, p) for p in game_state.get("order", [])])
                if cha:
                    return cha.to_dict()
                else:
                    raise ValueError("No valid challenges available for the current restrictions")
                
            case TurnTypeEnum.GROUP_CHALLENGE:
                gro = self._choose_group_challenge(player_name, self._get_valid_group_challenges(lobby_code, game_state.get("restrictions", {"males": 0, "females": 0}), player_name), [self.gc.get_player_info(lobby_code, p) for p in game_state.get("order", [])])
                if gro:
                    return gro.to_dict()
                else:
                    raise ValueError("No valid group challenges available for the current restrictions")
                
            case TurnTypeEnum.SECRET_MISSION:
                secr = self._choose_secret_mission(player_name, self._get_valid_secret_missions(lobby_code, game_state.get("restrictions", {"males": 0, "females": 0}), player_name), [self.gc.get_player_info(lobby_code, p) for p in game_state.get("order", [])])
                if secr:
                    return secr.to_dict()
                else:
                    raise ValueError("No valid secret missions available for the current restrictions")
                
            case TurnTypeEnum.TARGET_CHALLENGE:
                all_players:list[PlayerInfo] = [self.gc.get_player_info(lobby_code, p) for p in game_state.get("order", [])]
                targ = self._choose_target_challenge(self._get_valid_target_challenges(game_state.get("restrictions", {"males": 0, "females": 0}), all_players), all_players)
                if targ:
                    return targ.to_dict()
                else:
                    raise ValueError("No valid target challenges available for the current restrictions")
            
            case _:
                raise ValueError(f"Unsupported turn type: {type}. Supported types are: {[e.value for e in TurnTypeEnum]}")

    
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
    
    def skip_turn(self, lobby_code: str, player:str, turn_type: TurnTypeEnum, title: str) -> int:
        if not lobby_code:
            raise ValueError("Lobby code is required to skip a turn")
        if not player:
            raise ValueError("Player is required to skip a turn")
        if not turn_type:
            raise ValueError("Turn type is required to skip a turn")
        if not title:
            raise ValueError("Challenge title is required to skip a turn")

        def points_to_deduct(punishment:float) -> int:
            player_points:int = self.gc.get_player_state(lobby_code, player).points
            return int(-abs(punishment/100) * player_points)

        match turn_type:
            case TurnTypeEnum.CHALLENGE:
                challenge:Challenge = Challenge.query.get(title)
                if not challenge:
                    raise ValueError(f"Challenge '{title}' not found to skip")
                if challenge.skipping is None:
                    raise ValueError(f"Challenge '{title}' cannot be skipped")
                return self.gc.update_score(lobby_code, player, points_to_deduct(challenge.skipping))
            
            case TurnTypeEnum.GROUP_CHALLENGE:
                group_challenge:GroupChallenge = GroupChallenge.query.get(title)
                if not group_challenge:
                    raise ValueError(f"Group challenge '{title}' not found to skip")
                if group_challenge.skipping is None:
                    raise ValueError(f"Group challenge '{title}' cannot be skipped")
                return self.gc.update_score(lobby_code, player, points_to_deduct(group_challenge.skipping))
            
            case TurnTypeEnum.SECRET_MISSION:
                raise ValueError(f"Secret missions cannot be skipped")
            
            case TurnTypeEnum.TARGET_CHALLENGE:
                target_challenge:TargetChallenge = TargetChallenge.query.get(title)
                if not target_challenge:
                    raise ValueError(f"Target challenge '{title}' not found to skip")
                if target_challenge.skipping is None:
                    raise ValueError(f"Target challenge '{title}' cannot be skipped")
                return self.gc.update_score(lobby_code, player, points_to_deduct(target_challenge.skipping))
            
            case _:
                raise ValueError(f"Unsupported turn type: {turn_type}. Supported types are: {(e.value for e in TurnTypeEnum)}")
            
    def complete_turn(self, lobby_code: str, player:str, turn_type: TurnTypeEnum, title: str) -> tuple[int, bool]:
        if not lobby_code:
            raise ValueError("Lobby code is required to complete a turn")
        if not player:
            raise ValueError("Player is required to complete a turn")
        if not turn_type:
            raise ValueError("Turn type is required to complete a turn")
        if not title:
            raise ValueError("Challenge title is required to complete a turn")

        match turn_type:
            case TurnTypeEnum.CHALLENGE:
                challenge:Challenge = Challenge.query.get(title)
                if not challenge:
                    raise ValueError(f"Challenge '{title}' not found to complete")

                return challenge.prize, challenge.voting
            
            case TurnTypeEnum.GROUP_CHALLENGE:
                group_challenge:GroupChallenge = GroupChallenge.query.get(title)
                if not group_challenge:
                    raise ValueError(f"Group challenge '{title}' not found to complete")
                
                return group_challenge.prize, group_challenge.voting
            
            case TurnTypeEnum.SECRET_MISSION:
                secret_mission:SecretMission = SecretMission.query.get(title)
                if not secret_mission:
                    raise ValueError(f"Secret Mission '{title}' not found to complete")
                
                return secret_mission.prize, False
            
            case TurnTypeEnum.TARGET_CHALLENGE:
                target_challenge:TargetChallenge = TargetChallenge.query.get(title)
                if not target_challenge:
                    raise ValueError(f"Target challenge '{title}' not found to complete")
                
                return target_challenge.prize, target_challenge.voting
            
            case _:
                raise ValueError(f"Unsupported turn type: {turn_type}. Supported types are: {(e.value for e in TurnTypeEnum)}")
            
    def compute_award_from_votes(self, potential_prize: int, votes: list[int]) -> int:
        if not votes:
            return 0
        avg = sum(votes) / len(votes)
        return int(round(potential_prize * (avg / 10.0)))
