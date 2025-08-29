import re
from helpers.PlayerInfo import PlayerInfo
from models.TargetChallenge import TargetChallenge

TEAM_TOKEN_RE = re.compile(r'^(?:T|t)(\d+)$')

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
        
    @staticmethod
    def place_and_map(desc: str, players: list[PlayerInfo], target: str | None = None) -> tuple[str, dict[str, str]]:
        """
        Same as place_players but also returns the mapping placeholder->username.
        """
        if not desc or not players:
            return desc, {}

        players = list(players)

        try:
            restrictions = RestrictionAdapter.get_restrictions(desc)
            if len(restrictions) > len(players) + 1:
                return desc, {}

            target_key = next((k for k, v in restrictions.items() if 'target' in v), None)

            assigned: dict[str, str] = {}
            if target_key:
                restrictions.pop(target_key)
                assigned[target_key] = target
                try:
                    players.remove(next((p for p in players if p and getattr(p, "username", None) == target), None))
                except Exception:
                    pass

            for player_key, rest in list(restrictions.items()):
                gender_restr = next((r for r in rest if r.startswith('gender=')), None)
                if gender_restr:
                    gender_val = gender_restr.split('=')[1]
                    player = next((p for p in players if p.username not in assigned.values() and getattr(getattr(p, 'gender', None), 'value', getattr(p, 'gender', None)) == gender_val), None)
                    if player:
                        assigned[player_key] = player.username

            for player_key, rest in restrictions.items():
                if player_key not in assigned:
                    player = next((p for p in players if p.username not in assigned.values()), None)
                    if player:
                        assigned[player_key] = player.username
                    else:
                        assigned[player_key] = f"<no player for {player_key}>"

            new_desc = desc
            for player_key, username in assigned.items():
                new_desc = new_desc.replace(f"{{{player_key}}}", username)

            return new_desc, assigned
        except Exception as e:
            print(f"Error place_and_map: {e}")
            return desc, {}

    @staticmethod
    def build_teams_from_assigned(desc: str, assigned: dict[str, str]) -> list[dict]:
        """
        Returns a list [{name:'Team0', members:[...]}...] using Tn tokens in the description.
        """
        restr = RestrictionAdapter.get_restrictions(desc)
        teams: dict[str, list[str]] = {}
        for placeholder, tokens in restr.items():
            team_tokens = [t for t in tokens if TEAM_TOKEN_RE.match(t)]
            if not team_tokens:
                continue
            m = TEAM_TOKEN_RE.match(team_tokens[0])
            idx = int(m.group(1)) if m else 0
            name = f"Team{idx}"
            teams.setdefault(name, [])
            user = assigned.get(placeholder)
            if user:
                teams[name].append(user)

        # Orden estable por nombre
        return [{"name": name, "members": members} for name, members in sorted(teams.items(), key=lambda x: x[0])]

    @staticmethod
    def build_candidates_by_slot(desc: str, valid_players: list[PlayerInfo], all_players: list[PlayerInfo] | None, group: bool) -> tuple[str, dict[str, list[str]], dict[str, str]]:
        """
        Similar to possible_target_players but returns mapping by slot and team by slot.
        """
        if not desc:
            return desc, {}, {}

        restr = RestrictionAdapter.get_restrictions(desc)
        if not restr:
            return desc, {}, {}

        placeholder_map: dict[str, list[str]] = {}
        team_by_slot: dict[str, str] = {}

        def usernames(pool: list[PlayerInfo]) -> list[str]:
            return [p.username for p in pool]

        if not group:
            if not all_players:
                all_players = valid_players
            target_key = next((k for k, v in restr.items() if 'target' in v), None)
            if target_key:
                placeholder_map[target_key] = usernames(valid_players)
                restr.pop(target_key)
            for key, tokens in restr.items():
                gender_restr = next((r for r in tokens if r.startswith('gender=')), None)
                if gender_restr:
                    g = gender_restr.split('=')[1]
                    pool = [p for p in all_players if getattr(getattr(p, 'gender', None), 'value', getattr(p, 'gender', None)) == g]
                else:
                    pool = all_players
                placeholder_map[key] = usernames(pool) if pool else ["<no valid players>"]
                tkn = next((t for t in tokens if TEAM_TOKEN_RE.match(t)), None)
                if tkn:
                    team_by_slot[key] = f"Team{TEAM_TOKEN_RE.match(tkn).group(1)}"
        else:
            for key, tokens in restr.items():
                gender_restr = next((r for r in tokens if r.startswith('gender=')), None)
                if gender_restr:
                    g = gender_restr.split('=')[1]
                    pool = [p for p in valid_players if getattr(getattr(p, 'gender', None), 'value', getattr(p, 'gender', None)) == g]
                else:
                    pool = valid_players
                placeholder_map[key] = usernames(pool) if pool else ["<no valid players>"]
                tkn = next((t for t in tokens if TEAM_TOKEN_RE.match(t)), None)
                if tkn:
                    team_by_slot[key] = f"Team{TEAM_TOKEN_RE.match(tkn).group(1)}"

        new_desc = desc
        for key, names in placeholder_map.items():
            new_desc = new_desc.replace(f"{{{key}}}", "{" + ",".join(names) + "}")

        return new_desc, placeholder_map, team_by_slot

    @staticmethod
    def resolve_slots_from_description(desc: str) -> list[str]:
        """
        Returns the placeholders in the order they appear in the original text.
        Useful for aligning {Andreea} / {Uri} after choose_target with the slots.
        """
        restr = RestrictionAdapter.get_restrictions(desc)
        positions = [(k, desc.find("{" + k + "}")) for k in restr.keys()]
        positions.sort(key=lambda x: x[1] if x[1] >= 0 else 999999)
        return [k for k, _ in positions]

    @staticmethod
    def extract_chosen_from_description(final_desc: str) -> list[str]:
        """
        Extracts the contents between curly braces from the final text, in order.
        It is expected that after choose_target the slots will appear as {Andreea}, {Uri}, ...
        """
        return [m.group(1).strip() for m in re.finditer(r'\{([^}]+)\}', final_desc)]
    
    @staticmethod
    def render_role_description_for_player(
        role_title: str,
        description: str,
        lobby_code: str,
        player_name: str,
        gc
    ) -> str:
        """
        For 'Tortolitos', replaces {player} with the partner:
          - If there are >2 Tortolitos, pick any other (first).
          - If there is only 1 Tortolitos, pick a random other player in lobby.
        For any other role, returns description unchanged.
        """
        if (role_title or "").strip().lower() != "tortolitos":
            return description or ""

        try:
            state = gc.get_lobby_state(lobby_code)
            order = state.get("order", []) or []
            tortos = [u for u in order if (gc.get_player_state(lobby_code, u).role or "").strip().lower() == "tortolitos"]

            partner = None
            others = [u for u in tortos if u != player_name]
            if others:
                partner = others[0]
            else:
                for u in order:
                    if u != player_name:
                        partner = u
                        break

            replace_with = partner or "<no pair>"
            return (description or "").replace("{player}", replace_with)
        except Exception:
            return description or ""
