from helpers.PlayerInfo import PlayerInfo
from models.TargetChallenge import TargetChallenge


class RestrictionAdapter:
    """
    A class to handle restrictions from challenge descriptions.
    """
    @staticmethod
    def get_restrictions(desc: str) -> dict[str, list[str]]:
        """
        Extracts restrictions from a challenge description.
        
        :param desc: The challenge description containing placeholders.
        :return: A dictionary with players as keys and their restrictions as values.
        """
        if not desc:
            return {}
        try:
            restrictions:dict[str, list[str]] = {}
            restr_list = [part[1:-1] for part in desc.split(' ') if part.startswith('{') and part.endswith('}')]
            for restr in restr_list:
                parts = restr.split(':')
                player = parts[0]
                if player.replace(' ', '') not in restrictions:
                    restrictions[player.replace(' ', '')] = []
                if len(parts) > 1:
                    for r in parts[1:]:
                        restrictions[player.replace(' ', '')].append(r.replace(' ', ''))
            return restrictions
        except Exception as e:
            print(f"Error extracting restrictions: {e}")
            return {}
        
    @staticmethod
    def get_num_participants(desc: str) -> int:
        if not desc:
            return 0
        try:
            restrictions = RestrictionAdapter.get_restrictions(desc)
            return len(restrictions)

        except Exception as e:
            print(f"Error counting group participants: {e}")

    @staticmethod
    def get_num_males(desc: str) -> int:
        if not desc:
            return 0
        try:
            restrictions = RestrictionAdapter.get_restrictions(desc)
            return sum(1 for restrs in restrictions.values() if restrs and 'gender=male' in restrs)

        except Exception as e:
            print(f"Error counting males: {e}")

    @staticmethod
    def get_num_females(desc: str) -> int:
        if not desc:
            return 0
        try:
            restrictions = RestrictionAdapter.get_restrictions(desc)
            return sum(1 for restrs in restrictions.values() if restrs and 'gender=female' in restrs)

        except Exception as e:
            print(f"Error counting females: {e}")
        
    @staticmethod
    def place_players(desc: str, players: list[PlayerInfo], target: str = None) -> str:
        """
        Places players into the challenge description based on restrictions.

        :param desc: The challenge description with placeholders.
        :param players: List of PlayerInfo objects available for placement. Not including the target player.
        :param target: The username of the target player who is performing the challenge.
        :return: The description with players placed in.
        """
        if not desc or not players:
            return desc
        
        try:
            restrictions = RestrictionAdapter.get_restrictions(desc)
            if len(restrictions) > len(players) + 1:
                return desc
            
            target_key = next((k for k, v in restrictions.items() if 'target' in v), None)

            assigned = {}
            if target_key:
                restrictions.pop(target_key)
                assigned[target_key] = target
                try:
                    players.remove(next((p for p in players if p.username == target), None))
                except Exception:
                    pass
            
            for player_key, rest in restrictions.items():
                gender_restr = next((r for r in rest if r.startswith('gender=')), None)
                if gender_restr:
                    gender_val = gender_restr.split('=')[1]
                    player = next((p for p in players if p.username not in assigned.values() and getattr(p, 'gender', None) == gender_val), None)
                    if player:
                        assigned[player_key] = player.username
                    else:
                        assigned[player_key] = f"<no player for {player_key}>"
            
            for player_key, rest in restrictions.items():
                if player_key not in assigned:
                    player = next((p for p in players if p.username not in assigned.values()), None)
                    if player:
                        assigned[player_key] = player.username
                    else:
                        assigned[player_key] = f"<no player for {player_key}>"
            
            for player_key, username in assigned.items():
                desc = desc.replace(f"{{{player_key}}}", username)

            return desc

        except Exception as e:
            print(f"Error placing players: {e}")
            return desc
        
    @staticmethod
    def possible_target_players(target_challenge: TargetChallenge, valid_players: list[PlayerInfo], all_players: list[PlayerInfo] = None) -> str:
        """
        Generates a description of possible target players based on the challenge restrictions.
        
        :param target_challenge: The TargetChallenge object containing the description and group info.
        :param valid_players: List of PlayerInfo objects that are valid for the challenge.
        :param all_players: Llist of all PlayerInfo objects, used for non-group target challenges.
        :return: The challenge description with possible players filled in.
        """
        if not target_challenge:
            raise ValueError("Target challenge is None")
        
        desc:str = target_challenge.description

        if not valid_players:
            return desc
        
        try:
            group:bool = target_challenge.group_challenge
            restrictions = RestrictionAdapter.get_restrictions(desc)
            placeholder_map = {}

            if not group:
                if not all_players:
                    all_players = valid_players
                target_key = next((k for k, v in restrictions.items() if 'target' in v), None)
                if target_key:
                    placeholder_map[target_key] = ','.join([p.username for p in valid_players])
                    restrictions.pop(target_key)

                    for player_key, rest in restrictions.items():
                        gender_restr = next((r for r in rest if r.startswith('gender=')), None)
                        if gender_restr:
                            gender_val = gender_restr.split('=')[1]
                            valid_usernames = [p.username for p in all_players if getattr(p, 'gender', None) == gender_val]
                        else:
                            valid_usernames = [p.username for p in all_players]
                        if not valid_usernames:
                            valid_usernames = ["<no valid players>"]
                        placeholder_map[player_key] = ','.join(valid_usernames)
                else:
                    raise ValueError("No target placeholder found in non-group target challenge description")
            
            else:
                for player_key, rest in restrictions.items():
                    gender_restr = next((r for r in rest if r.startswith('gender=')), None)
                    if gender_restr:
                        gender_val = gender_restr.split('=')[1]
                        valid_usernames = [p.username for p in valid_players if getattr(p, 'gender', None) == gender_val]
                    else:
                        valid_usernames = [p.username for p in valid_players]
                    if not valid_usernames:
                        valid_usernames = ["<no valid players>"]
                    placeholder_map[player_key] = ','.join(valid_usernames)

            for player_key, usernames in placeholder_map.items():
                desc = desc.replace(f"{{{player_key}}}", f"{{{usernames}}}")

            return desc

        except Exception as e:
            print(f"Error generating possible target players: {e}")
            return desc