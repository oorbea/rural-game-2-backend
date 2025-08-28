"""
This module provides a high-level controller for managing multi-player turn-based games using Redis as the backing store. It encapsulates lobby creation, player management and per-game state without persisting long-term accounts in a relational database. The implementation follows the SOLID principles: it separates concerns between the controller, data models and external dependencies and provides clear extension points for custom challenge selection and game rules.
"""

from __future__ import annotations

import json
import os
import random
import string

from datetime import datetime
from typing import Any, Iterable
import redis

from enums.GenderEnum import GenderEnum
from enums.TurnType import TurnTypeEnum
from helpers.normalize_value import normalize_value
from helpers.IChallengeProvider import ChallengeProvider
from helpers.IPlayerManager import PlayerManager
from helpers.PlayerInfo import PlayerInfo
from helpers.PlayerState import PlayerState

class GameController:
    """Controller responsible for managing game lobbies and state.

    The controller provides high-level methods to create lobbies, join players, start games, progress turns and track scores, storing all state in Redis. It does not directly interact with WebSocket connections; instead, it returns serialisable data structures which the calling layer can emit to clients.
    """

    LOBBY_KEY_TEMPLATE = "lobby:{code}"
    PLAYERS_LIST_TEMPLATE = "lobby:{code}:players"
    PLAYER_STATE_TEMPLATE = "lobby:{code}:player:{username}"
    LOBBY_USER_TEMPLATE = "lobby:{code}:user:{username}"
    ACTIVE_LOBBIES_SET = "lobbies:active"
    VOTE_SESSION_KEY_TEMPLATE = "lobby:{code}:vote:session"
    VOTE_VOTES_KEY_TEMPLATE = "lobby:{code}:vote:votes"
    CURRENT_CHALLENGE_KEY = "lobby:{code}:current_challenge"
    TEAM_VOTE_SESSION_KEY_TEMPLATE = "lobby:{code}:team_vote:session"
    TEAM_VOTE_VOTES_KEY_TEMPLATE = "lobby:{code}:team_vote:votes"


    def __init__(self, redis_client: redis.Redis, challenge_provider: ChallengeProvider, player_manager: PlayerManager) -> None:
        self.redis = redis_client
        self.challenge_provider = challenge_provider
        self.player_manager = player_manager

        try:
            setattr(self.challenge_provider, 'gc', self)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Lobby management
    # ------------------------------------------------------------------
    def create_lobby(self, host: PlayerInfo) -> str:
        code = self._generate_unique_code()
        lobby_key = self.LOBBY_KEY_TEMPLATE.format(code=code)
        players_list_key = self.PLAYERS_LIST_TEMPLATE.format(code=code)

        lobby_meta = {
            "created_at": datetime.now().astimezone().isoformat(),
            "current_turn": 0,
            "active": True,
            "host": host.username,
        }
        self._hset_serialized(lobby_key, mapping=lobby_meta)
        self.redis.sadd(self.ACTIVE_LOBBIES_SET, code)

        self.redis.rpush(players_list_key, host.username)
        self._persist_lobby_user_info(code, host)
        self._persist_player_state(code, PlayerState(username=host.username))
        return code

    def join_lobby(self, code: str, player: PlayerInfo) -> None:
        if not self.redis.sismember(self.ACTIVE_LOBBIES_SET, code):
            raise ValueError(f"Lobby {code} does not exist or is not active")
        players_list_key = self.PLAYERS_LIST_TEMPLATE.format(code=code)
        existing_players: list[str] = self.redis.lrange(players_list_key, 0, -1)
        if player.username in existing_players:
            raise ValueError(f"Player '{player.username}' already in lobby")

        self._persist_lobby_user_info(code, player)  # <- per-lobby
        self._persist_player_state(code, PlayerState(username=player.username))
        self.redis.rpush(players_list_key, player.username)

    def leave_lobby(self, code: str, username: str) -> str | None:
        """Remove a player from a lobby, reassign host if needed, and
        atomically delete the lobby if it becomes empty.

        :returns: the username of the current host after the removal,
                or None if the lobby was deleted (became empty).
        """
        if not self.redis.sismember(self.ACTIVE_LOBBIES_SET, code):
            raise ValueError(f"Lobby {code} does not exist or is not active")

        lobby_key = self.LOBBY_KEY_TEMPLATE.format(code=code)
        players_list_key = self.PLAYERS_LIST_TEMPLATE.format(code=code)
        state_key = self.PLAYER_STATE_TEMPLATE.format(code=code, username=username)

        with self.redis.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(players_list_key, lobby_key)

                    players: list[str] = pipe.lrange(players_list_key, 0, -1)
                    host_raw = pipe.hget(lobby_key, "host")
                    host_val = host_raw.decode() if isinstance(host_raw, (bytes, bytearray)) else host_raw

                    if username not in players:
                        pipe.unwatch()
                        return host_val

                    remaining = [p for p in players if p != username]
                    new_len = len(remaining)
                    next_host = remaining[0] if new_len > 0 else None

                    if new_len == 0:
                        result_host = None
                    else:
                        if not host_val or host_val == username:
                            result_host = next_host
                        else:
                            result_host = host_val

                    pipe.multi()
                    pipe.lrem(players_list_key, 0, username)
                    pipe.delete(state_key)

                    if new_len == 0:
                        pipe.delete(players_list_key)
                        pipe.delete(lobby_key)
                        pipe.srem(self.ACTIVE_LOBBIES_SET, code)
                    else:
                        if (not host_val) or (host_val == username):
                            pipe.hset(lobby_key, "host", result_host)

                    pipe.execute()
                    return result_host
                except redis.WatchError:
                    continue

    def end_lobby(self, code: str) -> None:
        """End a lobby and clean up all associated state."""
        self.redis.srem(self.ACTIVE_LOBBIES_SET, code)
        lobby_key = self.LOBBY_KEY_TEMPLATE.format(code=code)
        players_list_key = self.PLAYERS_LIST_TEMPLATE.format(code=code)
        player_names = self.redis.lrange(players_list_key, 0, -1)

        vote_sess_key = self.VOTE_SESSION_KEY_TEMPLATE.format(code=code)
        vote_votes_key = self.VOTE_VOTES_KEY_TEMPLATE.format(code=code)
        try:
            self.redis.delete(vote_sess_key)
            self.redis.delete(vote_votes_key)
        except Exception:
            pass

        for name in player_names:
            state_key = self.PLAYER_STATE_TEMPLATE.format(code=code, username=name)
            self.redis.delete(state_key)

            lobby_user_key = self.LOBBY_USER_TEMPLATE.format(code=code, username=name)
            rel_path = self.redis.hget(lobby_user_key, "profile_pic")
            self.redis.delete(lobby_user_key)
            try:
                if rel_path:
                    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
                    abs_path = rel_path if os.path.isabs(rel_path) else os.path.join(base_dir, rel_path.lstrip('/'))
                    if os.path.exists(abs_path):
                        os.remove(abs_path)
            except Exception:
                pass

        self.redis.delete(lobby_key)
        self.redis.delete(players_list_key)
        self.redis.delete(self.CURRENT_CHALLENGE_KEY.format(code=code))
        self.redis.delete(self.TEAM_VOTE_SESSION_KEY_TEMPLATE.format(code=code))
        self.redis.delete(self.TEAM_VOTE_VOTES_KEY_TEMPLATE.format(code=code))


    # ------------------------------------------------------------------
    # Game state management
    # ------------------------------------------------------------------
    def start_game(self, code: str, player: str) -> None:
        """Mark a lobby as started.

        :param code: lobby code
        :param player: player who initiated the game start
        """
        lobby_key = self.LOBBY_KEY_TEMPLATE.format(code=code)
        if not self.redis.exists(lobby_key):
            raise ValueError(f"Lobby {code} does not exist")
        players_list_key = self.PLAYERS_LIST_TEMPLATE.format(code=code)
        existing_players:list[str] = self.redis.lrange(players_list_key, 0, -1)
        if not existing_players or len(existing_players) < 2:
            raise ValueError(f"Cannot start game; lobby {code} has less than 2 players")
        host = self.redis.hget(lobby_key, "host")
        if host != player:
            raise ValueError(f"Only the host ({host}) can start the game")
        roles = self.challenge_provider.get_player_roles(code, existing_players)
        for player in existing_players:
            self.assign_role(code, player, roles.get(player, "default"))
            self.set_player_connected(code, player, True)
        self.redis.hset(lobby_key, "current_turn", 0)
        self.redis.hset(lobby_key, "started_at", datetime.now().astimezone().isoformat())

    def next_turn(self, code: str, turn_type:TurnTypeEnum|str) -> tuple[dict[str, Any], str]:
        """Advance to the next player's turn and return the next challenge.

        The current_turn counter is incremented modulo the number of
        players.  The challenge provider is called with the latest
        game state to determine the next action or challenge.  If
        there are no players in the lobby, a ValueError is raised.

        :param code: lobby code
        :param turn_type: the type of turn to progress to
        :returns: a challenge dictionary as provided by the
            challenge provider and the username of the player whose turn it is
        """
        players_list_key = self.PLAYERS_LIST_TEMPLATE.format(code=code)
        lobby_key = self.LOBBY_KEY_TEMPLATE.format(code=code)
        player_count:int = self.redis.llen(players_list_key)
        if player_count == 0:
            raise ValueError(f"Cannot progress turn; lobby {code} has no players")

        player:str = None
        with self.redis.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(lobby_key)
                    current_turn = int(pipe.hget(lobby_key, "current_turn") or 0)
                    next_turn_index = (current_turn + 1) % player_count
                    pipe.multi()
                    pipe.hset(lobby_key, "current_turn", next_turn_index)
                    player = self.get_lobby_state(code)['order'][next_turn_index]
                    pipe.execute()
                    break
                except redis.WatchError:
                    continue
        game_state = self.get_lobby_state(code)
        challenge = self.challenge_provider.get_next_challenge(code, game_state, turn_type)
        return challenge, player
    
    def skip_turn(self, code: str, player:str, turn_type: TurnTypeEnum|str, title: str) -> int:
        """Skip the current turn without changing the turn index.

        This is useful for challenges that do not require a player action,
        such as group challenges or secret missions. The turn index remains
        unchanged, so the same player will be up next.

        :param code: lobby code
        :param player: player who is skipping their turn
        :param turn_type: the type of turn to skip
        :param title: the title of the challenge being skipped
        :returns: the new total score for the player
        """
        players_list_key = self.PLAYERS_LIST_TEMPLATE.format(code=code)
        player_count:int = self.redis.llen(players_list_key)
        if player_count == 0:
            raise ValueError(f"Cannot skip turn; lobby {code} has no players")

        turn_type = TurnTypeEnum(turn_type) if isinstance(turn_type, str) else turn_type
        return self.challenge_provider.skip_turn(code, player, turn_type, title)

    def complete_turn(self, code: str, player:str, turn_type: TurnTypeEnum|str, title: str) -> tuple[int, bool]:
        """Mark the current turn as completed.

        This method updates the player's score based on the challenge's prize if voting is not required. If voting is required, it returns the prize and a flag indicating that voting is needed without updating the score.

        :param code: lobby code
        :param player: player who is completing their turn
        :param turn_type: the type of turn being completed
        :param title: the title of the challenge being completed
        :returns: a tuple containing the prize score for the player or the new total score if no voting is needed, and a boolean indicating if the lobby should vote the performance
        """
        players_list_key = self.PLAYERS_LIST_TEMPLATE.format(code=code)
        player_count:int = self.redis.llen(players_list_key)
        if player_count == 0:
            raise ValueError(f"Cannot complete turn; lobby {code} has no players")

        turn_type = TurnTypeEnum(turn_type) if isinstance(turn_type, str) else turn_type
        prize, voting = self.challenge_provider.complete_turn(code, player, turn_type, title)
        if voting:
            self._begin_vote_session(code, player, turn_type, title, int(prize))
            return int(prize), True
        else:
            new_score = self.update_score(code, player, int(prize))
            return new_score, False

    def update_score(self, code: str, username: str, delta: int) -> int:
        """Adjust a player's score by a delta.

        :param code: lobby code
        :param username: player whose score to update
        :param delta: signed integer to add to the player's points
        :returns: the new total score for the player
        """
        state_key = self.PLAYER_STATE_TEMPLATE.format(code=code, username=username)
        if not self.redis.exists(state_key):
            raise ValueError(f"No state for player {username} in lobby {code}")
        self.redis.hincrby(state_key, "points", delta)
        return int(self.redis.hget(state_key, "points") or 0)

    def assign_role(self, code: str, username: str, role: str) -> None:
        """Assign a role to a player.

        Roles might influence challenge assignments or scoring.  The
        role is stored in the player's dynamic state.  Calling this
        method will overwrite any previous role.
        """
        state_key = self.PLAYER_STATE_TEMPLATE.format(code=code, username=username)
        if not self.redis.exists(state_key):
            raise ValueError(f"No state for player {username} in lobby {code}")
        self.redis.hset(state_key, "role", role)

    def assign_secret_mission(self, code: str, username: str, mission: str) -> None:
        """Append a secret mission to a player's state.

        Secret missions are stored as a JSON encoded list in the
        player's dynamic state.  Existing missions are preserved.
        """
        state_key = self.PLAYER_STATE_TEMPLATE.format(code=code, username=username)
        if not self.redis.exists(state_key):
            raise ValueError(f"No state for player {username} in lobby {code}")
        missions_json = self.redis.hget(state_key, "secret_missions")
        missions = json.loads(missions_json) if missions_json else []
        missions.append(mission)
        self.redis.hset(state_key, "secret_missions", json.dumps(missions))

    def set_player_connected(self, code: str, username: str, connected: bool) -> None:
        """Mark a player's connection status without removing them from the lobby.

        This is useful for handling transient disconnects. When a player disconnects, set `connected=False`; upon reconnection, set `connected=True`.  A disconnected player remains in the turn rotation until explicitly removed.
        """
        state_key = self.PLAYER_STATE_TEMPLATE.format(code=code, username=username)
        if not self.redis.exists(state_key):
            raise ValueError(f"No state for player {username} in lobby {code}")
        self._hset_serialized(state_key, key="connected", value=connected)

    def get_lobby_state(self, code: str) -> dict[str, Any]:
        """Retrieve the full state of a lobby.

        This returns a dictionary containing lobby metadata, the ordered list of players and each player's dynamic state. It can be used by the caller to transmit state to clients or to compute game logic.

        :param code: lobby code
        :returns: mapping of lobby state and per-player states
        """
        lobby_key = self.LOBBY_KEY_TEMPLATE.format(code=code)
        players_list_key = self.PLAYERS_LIST_TEMPLATE.format(code=code)
        if not self.redis.exists(lobby_key):
            raise ValueError(f"Lobby {code} does not exist")
        lobby_meta:dict = self.redis.hgetall(lobby_key)
        if "current_turn" in lobby_meta:
            try:
                lobby_meta["current_turn"] = int(lobby_meta["current_turn"])
            except (TypeError, ValueError):
                pass
        if "active" in lobby_meta:
            try:
                lobby_meta["active"] = bool(lobby_meta["active"])
            except (TypeError, ValueError):
                pass
        player_names = self.redis.lrange(players_list_key, 0, -1)
        players_state: dict[str, Any] = {}
        restrictions = {
            "males": 0,
            "females": 0
        }
        for name in player_names:
            state_key = self.PLAYER_STATE_TEMPLATE.format(code=code, username=name)
            raw_state = self.redis.hgetall(state_key)
            points_str = raw_state.get("points", "0")
            try:
                points = int(points_str)
            except (TypeError, ValueError):
                points = 0
            role = raw_state.get("role") or None
            missions_json = raw_state.get("secret_missions")
            secret_missions = json.loads(missions_json) if missions_json else []
            connected_str = raw_state.get("connected")
            if connected_str is None:
                connected = True
            else:
                try:
                    connected = json.loads(connected_str)
                    connected = bool(connected)
                except json.JSONDecodeError:
                    connected = bool(connected_str)
            players_state[name] = {
                "points": points,
                "role": role,
                "secret_missions": secret_missions,
                "connected": connected,
            }

            user_key = self.LOBBY_USER_TEMPLATE.format(code=code, username=name)
            gender = self.redis.hget(user_key, "gender")
            if gender == GenderEnum.MALE.value:
                restrictions["males"] += 1
            elif gender == GenderEnum.FEMALE.value:
                restrictions["females"] += 1
        return {
            "lobby": lobby_meta,
            "players": players_state,
            "order": player_names,
            "restrictions": restrictions
        }
    
    def get_connected_players(self, code: str) -> list[dict[str, Any]]:
        """Return connected players with their profile picture bytes (not path)."""
        lobby_key = self.LOBBY_KEY_TEMPLATE.format(code=code)
        if not self.redis.exists(lobby_key):
            raise ValueError(f"Lobby {code} does not exist")

        players_list_key = self.PLAYERS_LIST_TEMPLATE.format(code=code)
        player_names: list[str] = self.redis.lrange(players_list_key, 0, -1)

        result: list[dict[str, Any]] = []
        for name in player_names:
            try:
                info: PlayerInfo = self.player_manager.get_player_info(code, name)
                result.append({
                    "username": name,
                    "profile_picture": info.profile_pic
                })
            except Exception:
                result.append({
                    "username": name,
                    "profile_picture": None
                })
        return result

    
    def update_player_info(self, code: str, current_username: str, new_info: dict[str, Any]):
        """Update a player's static information in the lobby.

        :param code: lobby code
        :param current_username: the player's current username
        :param new_info: dictionary containing updated player information
        """
        return self.player_manager.update_player_info(code, current_username, new_info)
    
    def get_player_info(self, code: str, username: str):
        """Retrieve a player's static information in the lobby.

        :param code: lobby code
        :param username: the player's username
        :returns: a PlayerInfo object containing the player's static information
        """
        return self.player_manager.get_player_info(code, username)
    
    def get_player_state(self, code: str, username: str):
        """Retrieve a player's dynamic state in the lobby.

        :param code: lobby code
        :param username: the player's username
        :returns: a PlayerState object containing the player's dynamic state
        """
        return self.player_manager.get_player_state(code, username)
    
    def get_current_turn_player(self, code: str) -> str:
        """Retrieve the username of the player whose turn it currently is.

        :param code: lobby code
        :returns: the username of the current turn player
        """
        lobby_key = self.LOBBY_KEY_TEMPLATE.format(code=code)
        if not self.redis.exists(lobby_key):
            raise ValueError(f"Lobby {code} does not exist")
        players_list_key = self.PLAYERS_LIST_TEMPLATE.format(code=code)
        player_count:int = self.redis.llen(players_list_key)
        if player_count == 0:
            raise ValueError(f"Cannot get current turn; lobby {code} has no players")
        current_turn_raw = self.redis.hget(lobby_key, "current_turn")
        try:
            current_turn = int(current_turn_raw) if current_turn_raw is not None else 0
        except (TypeError, ValueError):
            current_turn = 0
        current_turn_index = current_turn % player_count
        player:str = self.redis.lindex(players_list_key, current_turn_index)
        return player
    
    def award_points_to(self, code: str, awardees: list[str], delta: int) -> dict[str, int]:
        totals = {}
        for u in awardees:
            totals[u] = self.update_score(code, u, delta)
        return totals

    def cast_vote(self, code: str, voter: str, vote_value: int) -> dict:
        if not self.redis.sismember(self.ACTIVE_LOBBIES_SET, code):
            raise ValueError(f"Lobby {code} does not exist or is not active")

        session_key = self.VOTE_SESSION_KEY_TEMPLATE.format(code=code)
        votes_key = self.VOTE_VOTES_KEY_TEMPLATE.format(code=code)
        players_list_key = self.PLAYERS_LIST_TEMPLATE.format(code=code)

        sess = self.redis.hgetall(session_key)
        if not sess or str(sess.get("status")) != "open":
            raise ValueError("No active voting session")

        performer_label = sess.get("performer")
        turn_type = sess.get("turn_type")
        title = sess.get("title")
        try:
            potential_prize = int(sess.get("prize", 0))
        except (TypeError, ValueError):
            potential_prize = 0
        awardees = json.loads(sess.get("awardees", "[]"))

        current_players:list[str] = self.redis.lrange(players_list_key, 0, -1)
        if voter not in current_players:
            raise ValueError("Voter is not in this lobby")

        if not (0 <= int(vote_value) <= 10):
            raise ValueError("Vote must be between 0 and 10")

        with self.redis.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(votes_key)
                    if pipe.hexists(votes_key, voter):
                        pipe.unwatch()
                        raise ValueError("You have already voted")
                    pipe.multi()
                    pipe.hset(votes_key, voter, int(vote_value))
                    pipe.execute()
                    break
                except redis.WatchError:
                    continue

        votes_map = self.redis.hgetall(votes_key) or {}
        votes = [int(v) for v in votes_map.values()]
        voters_list = list(votes_map.keys())

        connected = self._eligible_connected_players(code)
        eligibles = [u for u in connected if u not in set(awardees)]
        if not eligibles and set(connected) == set(awardees):
            eligibles = connected

        expected_now = len(eligibles)
        received = len(votes)
        remaining = max(0, expected_now - received)

        if expected_now > 0 and received < expected_now:
            return {
                "completed": False,
                "player": performer_label,
                "turn_type": turn_type,
                "title": title,
                "received": received,
                "remaining": remaining,
                "voters": voters_list,
            }

        if expected_now == 0:
            avg = 10.0
            awarded = potential_prize
        else:
            avg = (sum(votes) / max(1, len(votes))) if votes else 0.0
            if hasattr(self.challenge_provider, "compute_award_from_votes"):
                awarded = int(self.challenge_provider.compute_award_from_votes(potential_prize, votes))
            else:
                awarded = int(round(potential_prize * (avg / 10.0)))

        new_totals = self.award_points_to(code, awardees, awarded)
        try:
            with self.redis.pipeline() as pipe:
                pipe.delete(votes_key)
                pipe.delete(session_key)
                pipe.execute()
        except Exception:
            try:
                self._hset_serialized(session_key, key="status", value="closed")
            except Exception:
                pass

        return {
            "completed": True,
            "player": performer_label,
            "turn_type": turn_type,
            "title": title,
            "new_scores": new_totals,
            "awarded": awarded,
            "average_vote": round(avg, 2),
            "votes": len(votes),
            "received": received,
            "remaining": 0,
            "voters": voters_list,
        }
    
    def begin_team_vote(self, code: str, *, teams: list[dict], participants: list[str], title: str, turn_type: TurnTypeEnum) -> dict:
        """
        Opens a team-vote session. Eligibles: connected players except participants,
        unless the whole lobby participates, then everyone votes.
        """
        if isinstance(turn_type, str):
            turn_type = TurnTypeEnum(turn_type)

        session_key = self.TEAM_VOTE_SESSION_KEY_TEMPLATE.format(code=code)
        votes_key = self.TEAM_VOTE_VOTES_KEY_TEMPLATE.format(code=code)

        if self.redis.exists(session_key):
            sess = self.redis.hgetall(session_key)
            if sess and str(sess.get("status", "open")) == "open":
                raise ValueError("A team voting session is already active")

        self.redis.delete(votes_key)

        connected = self._eligible_connected_players(code)
        eligibles = [u for u in connected if u not in set(participants)]
        if not eligibles and set(connected) == set(participants):
            eligibles = connected

        payload = {
            "status": "open",
            "title": title,
            "turn_type": turn_type.value,
            "teams": json.dumps(teams),
            "participants": json.dumps(participants),
            "expected": len(eligibles),
            "created_at": datetime.now().astimezone().isoformat(),
        }
        self._hset_serialized(session_key, mapping=payload)
        return {"expected": len(eligibles), "teams": teams}

    def cast_team_vote(self, code: str, voter: str, team_name: str) -> dict:
        session_key = self.TEAM_VOTE_SESSION_KEY_TEMPLATE.format(code=code)
        votes_key = self.TEAM_VOTE_VOTES_KEY_TEMPLATE.format(code=code)
        players_list_key = self.PLAYERS_LIST_TEMPLATE.format(code=code)

        sess = self.redis.hgetall(session_key)
        if not sess or sess.get("status") != "open":
            raise ValueError("No active team voting session")

        teams = json.loads(sess.get("teams", "[]"))
        valid_team_names = {t["name"] for t in teams}
        if team_name not in valid_team_names:
            raise ValueError("Invalid team")

        current_players:list[str] = self.redis.lrange(players_list_key, 0, -1)
        if voter not in current_players:
            raise ValueError("Voter is not in this lobby")

        with self.redis.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(votes_key)
                    if pipe.hexists(votes_key, voter):
                        pipe.unwatch()
                        raise ValueError("You have already voted")
                    pipe.multi()
                    pipe.hset(votes_key, voter, team_name)
                    pipe.execute()
                    break
                except redis.WatchError:
                    continue

        votes_map = self.redis.hgetall(votes_key) or {}
        received = len(votes_map)
        expected = int(sess.get("expected", 0))
        remaining = max(0, expected - received)

        if received < expected:
            return {"completed": False, "received": received, "remaining": remaining, "voters": list(votes_map.keys())}

        counts: dict[str, int] = {}
        for choice in votes_map.values():
            counts[choice] = counts.get(choice, 0) + 1
        top_count = max(counts.values()) if counts else 0
        candidates = [name for name, c in counts.items() if c == top_count]

        if len(candidates) == 1:
            winner = candidates[0]
        else:
            def team_avg_points(name: str) -> float:
                members = next((t["members"] for t in teams if t["name"] == name), [])
                vals = []
                for u in members:
                    st_key = self.PLAYER_STATE_TEMPLATE.format(code=code, username=u)
                    try:
                        pts = int(self.redis.hget(st_key, "points") or 0)
                    except Exception:
                        pts = 0
                    vals.append(pts)
                return (sum(vals) / len(vals)) if vals else 0.0

            winner = min(candidates, key=team_avg_points)

        try:
            with self.redis.pipeline() as pipe:
                pipe.delete(votes_key)
                pipe.hset(session_key, mapping={"status": "closed", "winner": winner})
        except Exception:
            pass

        return {"completed": True, "winner": winner}

    def set_current_challenge_meta(self, code: str, meta: dict) -> None:
        key = self.CURRENT_CHALLENGE_KEY.format(code=code)
        self._hset_serialized(key, mapping=meta)

    def get_current_challenge_meta(self, code: str) -> dict:
        key = self.CURRENT_CHALLENGE_KEY.format(code=code)
        return self.redis.hgetall(key) or {}

    def clear_current_challenge_meta(self, code: str) -> None:
        key = self.CURRENT_CHALLENGE_KEY.format(code=code)
        self.redis.delete(key)


    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _generate_unique_code(self) -> str:
        """Generate a unique 4-digit lobby code.

        Codes are numeric strings to facilitate easy entry for
        players.  Collisions are avoided by checking the Redis set
        of active lobbies.  In the unlikely event that all 9000
        possible codes are exhausted, a RuntimeError will be raised.
        """
        attempts = 0
        while attempts < 10_000:
            code = "".join(random.choices(string.digits, k=4))
            if not self.redis.sismember(self.ACTIVE_LOBBIES_SET, code):
                return code
            attempts += 1
        raise RuntimeError("Unable to generate unique lobby code; too many active lobbies")

    def _persist_player_state(self, code: str, state: PlayerState) -> None:
        """Persist the dynamic state of a player within a lobby.

        Initial dynamic fields are stored for each new player. This method will not overwrite existing state (except where explicitly set), so repeated calls for the same player are idempotent.
        """
        state_key = self.PLAYER_STATE_TEMPLATE.format(code=code, username=state.username)
        mapping = {
            "points": state.points,
            "role": state.role,
            "secret_missions": state.secret_missions,
            "connected": state.connected,
        }
        self._hset_serialized(state_key, mapping=mapping)

    def _persist_lobby_user_info(self, code: str, info: PlayerInfo) -> None:
        """Stores static player info per-lobby."""
        lobby_user_key = self.LOBBY_USER_TEMPLATE.format(code=code, username=info.username)
        gender_value = info.gender.value if hasattr(info.gender, "value") else info.gender
        mapping = {
            "username": info.username,
            "drinking": info.drinking,
            "smoking": info.smoking,
            "partnered": info.partnered,
            "virgin": info.virgin,
            "gender": gender_value,
        }
        if isinstance(info.profile_pic, str) and info.profile_pic:
            mapping["profile_pic"] = info.profile_pic
        self._hset_serialized(lobby_user_key, mapping=mapping)

    def _hset_serialized(
        self,
        name: str,
        *,
        mapping: dict | None = None,
        items: Iterable[tuple[str, Any]] | None = None,
        key: str | None = None,
        value: Any | None = None,
    ) -> int:
        """
        Safe HSET wrapper: serializes values to Redis-friendly types and
        enforces the correct usage of redis.hset (either key/value OR mapping/items).

        :param name: Redis key to set
        :param mapping: dictionary to set in Redis
        :param items: iterable of (key, value) pairs to set in Redis
        :param key: key to set in Redis (if using key/value)
        :param value: value to set in Redis (if using key/value)
        :returns: number of fields added to the hash
        """
        modes = sum([
            mapping is not None,
            items is not None,
            key is not None,
        ])
        if modes != 1:
            raise ValueError("Use exactly one of: (mapping) OR (items) OR (key+value)")

        if mapping is not None:
            serial = {k: normalize_value(v) for k, v in mapping.items()}
            return self.redis.hset(name, mapping=serial)

        if items is not None:
            serial = {k: normalize_value(v) for (k, v) in items}
            return self.redis.hset(name, mapping=serial)

        if key is None:
            raise ValueError("If using key/value, 'key' must be provided")
        return self.redis.hset(name, key, normalize_value(value))

    def _eligible_connected_players(self, code: str) -> list[str]:
        players_list_key = self.PLAYERS_LIST_TEMPLATE.format(code=code)
        names = self.redis.lrange(players_list_key, 0, -1)
        result = []
        for n in names:
            state_key = self.PLAYER_STATE_TEMPLATE.format(code=code, username=n)
            raw = self.redis.hget(state_key, "connected")
            connected = True if raw is None else bool(json.loads(raw) if isinstance(raw, str) else raw)
            if connected:
                result.append(n)
        return result

    def begin_vote_session(self, code: str, *, performer_label: str, turn_type: TurnTypeEnum, title: str, potential_prize: int, awardees: list[str]) -> None:
        """
        Opens a performance voting session. Awardees receive the prize (possibly scaled).
        Eligibles: connected players except awardees; if no one remains and the whole lobby participates, then everyone votes.
        """
        if isinstance(turn_type, str):
            turn_type = TurnTypeEnum(turn_type)

        session_key = self.VOTE_SESSION_KEY_TEMPLATE.format(code=code)
        votes_key = self.VOTE_VOTES_KEY_TEMPLATE.format(code=code)

        if self.redis.exists(session_key):
            sess = self.redis.hgetall(session_key)
            if sess and str(sess.get("status", "open")) == "open":
                raise ValueError("A voting session is already active")

        self.redis.delete(votes_key)

        connected = self._eligible_connected_players(code)
        eligibles = [u for u in connected if u not in set(awardees)]
        if not eligibles and set(connected) == set(awardees):
            eligibles = connected

        mapping = {
            "performer": performer_label,
            "turn_type": turn_type.value,
            "title": title,
            "prize": int(potential_prize),
            "awardees": json.dumps(list(awardees)),
            "created_at": datetime.now().astimezone().isoformat(),
            "status": "open",
            "expected": len(eligibles),
        }
        self._hset_serialized(session_key, mapping=mapping)
