"""
This module provides a high-level controller for managing multi-player turn-based games using Redis as the backing store. It encapsulates lobby creation, player management and per-game state without persisting long-term accounts in a relational database. The implementation follows the SOLID principles: it separates concerns between the controller, data models and external dependencies and provides clear extension points for custom challenge selection and game rules.
"""

from __future__ import annotations

import json
import random
import string

from datetime import datetime, date
from typing import Any, Iterable
import redis

from helpers.IChallengeProvider import ChallengeProvider
from helpers.PlayerInfo import PlayerInfo
from helpers.PlayerState import PlayerState

class GameController:
    """Controller responsible for managing game lobbies and state.

    The controller provides high-level methods to create lobbies, join players, start games, progress turns and track scores, storing all state in Redis. It does not directly interact with WebSocket connections; instead, it returns serialisable data structures which the calling layer can emit to clients.
    """

    LOBBY_KEY_TEMPLATE = "lobby:{code}"
    PLAYERS_LIST_TEMPLATE = "lobby:{code}:players"
    PLAYER_STATE_TEMPLATE = "lobby:{code}:player:{username}"
    USER_INFO_TEMPLATE = "user:{username}"
    ACTIVE_LOBBIES_SET = "lobbies:active"

    def __init__(self, redis_client: redis.Redis, challenge_provider: ChallengeProvider) -> None:
        self.redis = redis_client
        self.challenge_provider = challenge_provider

    # ------------------------------------------------------------------
    # Lobby management
    # ------------------------------------------------------------------
    def create_lobby(self, host: PlayerInfo) -> str:
        """Create a new lobby and register the host as the first player.

        A unique 4-digit lobby code is generated and stored in a Redis set so that codes are not reused while active. The host's static information is stored under their user key and their initial game state is stored under the lobby.

        :param host: information about the player creating the lobby
        :returns: the 4-digit lobby code
        """
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
        self._persist_user_info(host)
        self._persist_player_state(code, PlayerState(username=host.username))
        return code

    def join_lobby(self, code: str, player: PlayerInfo) -> None:
        """Join an existing lobby.

        If the lobby is active, the player is appended to the ordered list of participants. Their static information is stored (or updated) under their user key and their dynamic lobby state is initialised. Attempting to join a non-existent or inactive lobby will raise a ValueError.

        :param code: lobby code
        :param player: static player information
        """
        if not self.redis.sismember(self.ACTIVE_LOBBIES_SET, code):
            raise ValueError(f"Lobby {code} does not exist or is not active")
        players_list_key = self.PLAYERS_LIST_TEMPLATE.format(code=code)
        existing_players:list[str] = self.redis.lrange(players_list_key, 0, -1)
        if player.username in existing_players:
            raise ValueError(f"Player '{player.username}' already in lobby")
        self._persist_user_info(player)
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
        """Clean up all data associated with a lobby.

        The lobby metadata, players list and per-player states are removed. The lobby code is released so that it may be reused for future games.

        :param code: lobby code to remove
        """
        self.redis.srem(self.ACTIVE_LOBBIES_SET, code)
        lobby_key = self.LOBBY_KEY_TEMPLATE.format(code=code)
        players_list_key = self.PLAYERS_LIST_TEMPLATE.format(code=code)
        player_names = self.redis.lrange(players_list_key, 0, -1)
        self.redis.delete(lobby_key)
        for name in player_names:
            state_key = self.PLAYER_STATE_TEMPLATE.format(code=code, username=name)
            self.redis.delete(state_key)
        self.redis.delete(players_list_key)

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
        if not existing_players:
            raise ValueError(f"Cannot start game; lobby {code} has no players")
        host = self.redis.hget(lobby_key, "host")
        if host != player:
            raise ValueError(f"Only the host ({host}) can start the game")
        roles = self.challenge_provider.get_player_roles(code, existing_players)
        for player in existing_players:
            self.assign_role(code, player, roles.get(player, "default"))
            self.set_player_connected(code, player, True)
        self.redis.hset(lobby_key, "current_turn", 0)
        self.redis.hset(lobby_key, "started_at", datetime.now().astimezone().isoformat())

    def next_turn(self, code: str) -> dict[str, Any]:
        """Advance to the next player's turn and return the next challenge.

        The current_turn counter is incremented modulo the number of
        players.  The challenge provider is called with the latest
        game state to determine the next action or challenge.  If
        there are no players in the lobby, a ValueError is raised.

        :param code: lobby code
        :returns: a challenge dictionary as provided by the
            challenge provider
        """
        players_list_key = self.PLAYERS_LIST_TEMPLATE.format(code=code)
        lobby_key = self.LOBBY_KEY_TEMPLATE.format(code=code)
        player_count:int = self.redis.llen(players_list_key)
        if player_count == 0:
            raise ValueError(f"Cannot progress turn; lobby {code} has no players")

        with self.redis.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(lobby_key)
                    current_turn = int(pipe.hget(lobby_key, "current_turn") or 0)
                    next_turn_index = (current_turn + 1) % player_count
                    pipe.multi()
                    pipe.hset(lobby_key, "current_turn", next_turn_index)
                    pipe.execute()
                    break
                except redis.WatchError:
                    continue
        game_state = self.get_lobby_state(code)
        challenge = self.challenge_provider.get_next_challenge(code, game_state)
        return challenge

    def update_score(self, code: str, username: str, delta: int) -> None:
        """Adjust a player's score by a delta.

        :param code: lobby code
        :param username: player whose score to update
        :param delta: signed integer to add to the player's points
        """
        state_key = self.PLAYER_STATE_TEMPLATE.format(code=code, username=username)
        if not self.redis.exists(state_key):
            raise ValueError(f"No state for player {username} in lobby {code}")
        self.redis.hincrby(state_key, "points", delta)

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
        player_names = self.redis.lrange(players_list_key, 0, -1)
        players_state: dict[str, Any] = {}
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
                except json.JSONDecodeError:
                    connected = bool(connected_str)
            players_state[name] = {
                "points": points,
                "role": role,
                "secret_missions": secret_missions,
                "connected": connected,
            }
        return {
            "lobby": lobby_meta,
            "players": players_state,
            "order": player_names,
        }
    
    def get_connected_players(self, code: str) -> list[str]:
        """Retrieve a list of players currently connected to the lobby."""
        lobby_key = self.LOBBY_KEY_TEMPLATE.format(code=code)
        if not self.redis.exists(lobby_key):
            raise ValueError(f"Lobby {code} does not exist")
        players_list_key = self.PLAYERS_LIST_TEMPLATE.format(code=code)
        player_names = self.redis.lrange(players_list_key, 0, -1)
        return player_names

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

    def _persist_user_info(self, info: PlayerInfo) -> None:
        """Persist static user information under a Redis key.

        This method stores per-user attributes independently from
        lobby state so that reconnections or participation in
        multiple games reuse the same data.  Existing fields will
        be updated; unspecified fields are left untouched.
        """
        user_key = self.USER_INFO_TEMPLATE.format(username=info.username)
        update_data = {
            "drinking": info.drinking,
            "smoking": info.smoking,
            "partnered": info.partnered,
            "virgin": info.virgin,
            "gender": info.gender
        }
        if info.profile_pic is not None:
            update_data["profile_pic"] = info.profile_pic
        self._hset_serialized(user_key, mapping=update_data)

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
    
    def _normalize_value(self, v: Any) -> str | int | float:
        """Normalize Python values to Redis-compatible types."""
        if v is None:
            return ""
        if isinstance(v, bool):
            return int(v)
        if isinstance(v, (int, float, str)):
            return v
        if isinstance(v, (datetime, date)):
            return v.isoformat()
        try:
            from enum import Enum
            if isinstance(v, Enum):
                return str(v.value)
        except Exception:
            pass
        return json.dumps(v, separators=(",", ":"))

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
            serial = {k: self._normalize_value(v) for k, v in mapping.items()}
            return self.redis.hset(name, mapping=serial)

        if items is not None:
            serial = {k: self._normalize_value(v) for (k, v) in items}
            return self.redis.hset(name, mapping=serial)

        if key is None:
            raise ValueError("If using key/value, 'key' must be provided")
        return self.redis.hset(name, key, self._normalize_value(value))
