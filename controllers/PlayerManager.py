import json
from typing import Any

import redis
from helpers.IPlayerManager import PlayerManager as IPlayerManager
from helpers.PlayerInfo import PlayerInfo
from helpers.PlayerState import PlayerState
from helpers.normalize_value import normalize_value

class PlayerManager(IPlayerManager):
    """Concrete implementation of PlayerManager interface."""
    LOBBY_KEY_TEMPLATE = "lobby:{code}"
    PLAYERS_LIST_TEMPLATE = "lobby:{code}:players"
    PLAYER_STATE_TEMPLATE = "lobby:{code}:player:{username}"
    USER_INFO_TEMPLATE = "user:{username}"
    ACTIVE_LOBBIES_SET = "lobbies:active"

    def __init__(self, redis_client: redis.Redis) -> None:
        self.redis = redis_client

    def update_player_info(self, code: str, current_username: str, new_info: dict[str, Any]) -> None:
        """Update a player's static information in the lobby.

        Supports partial updates. If 'username' is provided and differs from the
        current one, this will atomically:
        - replace the username in the lobby's ordered players list,
        - rename the player's dynamic state key,
        - update the lobby host if the host was the renamed player,
        - move/rename the user info key.
        Other fields are updated in the user's static info hash.

        :param code: lobby code
        :param current_username: the player's current username
        :param new_info: partial PlayerInfo fields to update
        """
        if not self.redis.sismember(self.ACTIVE_LOBBIES_SET, code):
            raise ValueError(f"Lobby {code} does not exist or is not active")

        allowed = {"username", "drinking", "smoking", "partnered", "virgin", "gender", "profile_pic"}
        updates_raw = {k: v for k, v in (new_info or {}).items() if k in allowed}

        if "gender" in updates_raw and updates_raw["gender"] is not None:
            g = updates_raw["gender"]
            try:
                from enums.GenderEnum import GenderEnum
                if isinstance(g, GenderEnum):
                    updates_raw["gender"] = g  # _normalize_value will store .value
                else:
                    gs = str(g).lower()
                    if gs not in ("male", "female"):
                        raise ValueError("gender must be 'male' or 'female'")
                    updates_raw["gender"] = GenderEnum(gs)
            except Exception:
                gs = str(g).lower()
                if gs not in ("male", "female"):
                    raise ValueError("gender must be 'male' or 'female'")
                updates_raw["gender"] = gs

        lobby_key = self.LOBBY_KEY_TEMPLATE.format(code=code)
        players_list_key = self.PLAYERS_LIST_TEMPLATE.format(code=code)
        user_key_old = self.USER_INFO_TEMPLATE.format(username=current_username)
        state_key_old = self.PLAYER_STATE_TEMPLATE.format(code=code, username=current_username)

        desired_username = updates_raw.get("username", current_username)
        user_key_new = self.USER_INFO_TEMPLATE.format(username=desired_username)
        state_key_new = self.PLAYER_STATE_TEMPLATE.format(code=code, username=desired_username)

        def _b2s(x):
            return x.decode() if isinstance(x, (bytes, bytearray)) else x

        with self.redis.pipeline() as pipe:
            while True:
                try:
                    watch_keys = [players_list_key, lobby_key]
                    if desired_username != current_username:
                        watch_keys += [state_key_old, user_key_old]
                    pipe.watch(*watch_keys)

                    players = pipe.lrange(players_list_key, 0, -1)
                    players = [_b2s(p) for p in players]
                    if current_username not in players:
                        pipe.unwatch()
                        raise ValueError(f"Player '{current_username}' is not in lobby {code}")

                    host_raw = pipe.hget(lobby_key, "host")
                    host_val = _b2s(host_raw)

                    idx = -1
                    if desired_username != current_username:
                        if desired_username in players:
                            pipe.unwatch()
                            raise ValueError(f"Username '{desired_username}' is already in the lobby")

                        if not pipe.exists(state_key_old):
                            pipe.unwatch()
                            raise ValueError(f"No state for player {current_username} in lobby {code}")

                        idx = players.index(current_username)

                    to_update = {k: updates_raw[k] for k in updates_raw if k not in ("username", "profile_pic")}
                    serial_map = {k: normalize_value(v) for k, v in to_update.items()}

                    pic_in_payload = "profile_pic" in updates_raw
                    pic_value = updates_raw.get("profile_pic", None)

                    pipe.multi()

                    if desired_username != current_username:
                        pipe.lset(players_list_key, idx, desired_username)

                        pipe.renamenx(state_key_old, state_key_new)

                        pipe.renamenx(user_key_old, user_key_new)

                        if host_val == current_username:
                            pipe.hset(lobby_key, "host", desired_username)

                        target_user_key = user_key_new
                    else:
                        target_user_key = user_key_old

                    if serial_map:
                        pipe.hset(target_user_key, mapping=serial_map)

                    if pic_in_payload:
                        if pic_value is None:
                            pipe.hdel(target_user_key, "profile_pic")
                        else:
                            pipe.hset(target_user_key, "profile_pic", normalize_value(pic_value))

                    pipe.execute()
                    break
                except ValueError as e:
                    raise e
                except redis.WatchError:
                    continue
                
    def get_player_info(self, code: str, username: str) -> PlayerInfo:
        """Retrieve a player's static information in the lobby."""
        if not self.redis.sismember(self.ACTIVE_LOBBIES_SET, code):
            raise ValueError(f"Lobby {code} does not exist or is not active")

        players_list_key = self.PLAYERS_LIST_TEMPLATE.format(code=code)
        players:list[str] = self.redis.lrange(players_list_key, 0, -1)
        if username not in players:
            raise ValueError(f"Player '{username}' is not in lobby {code}")

        user_key = self.USER_INFO_TEMPLATE.format(username=username)
        if not self.redis.exists(user_key):
            raise ValueError(f"No static info for player '{username}'")

        data = self.redis.hgetall(user_key)

        def _as_bool(x):
            if x is None:
                return False
            if isinstance(x, (int, float)):
                return bool(x)
            s = str(x).strip().lower()
            if s in ("1", "true", "t", "yes", "y"):
                return True
            if s in ("0", "false", "f", "no", "n", ""):
                return False
            try:
                j = json.loads(s)
                if isinstance(j, bool):
                    return j
                if isinstance(j, (int, float)):
                    return bool(j)
            except Exception:
                pass
            return bool(s)

        profile_pic = data.get("profile_pic")

        gender_raw = data.get("gender")
        if gender_raw is None:
            raise ValueError(f"Missing gender for user '{username}'")
        try:
            from enums.GenderEnum import GenderEnum
            try:
                gender = GenderEnum(gender_raw)
            except ValueError:
                gender = GenderEnum(json.loads(gender_raw))
        except Exception as e:
            raise ValueError(f"Invalid gender value '{gender_raw}' for user '{username}'") from e

        return PlayerInfo(
            username=username,
            drinking=_as_bool(data.get("drinking")),
            smoking=_as_bool(data.get("smoking")),
            partnered=_as_bool(data.get("partnered")),
            virgin=_as_bool(data.get("virgin")),
            gender=gender,
            profile_pic=profile_pic,
        )


    def get_player_state(self, code: str, username: str) -> PlayerState:
        """Retrieve a player's dynamic state in the lobby."""
        if not self.redis.sismember(self.ACTIVE_LOBBIES_SET, code):
            raise ValueError(f"Lobby {code} does not exist or is not active")

        players_list_key = self.PLAYERS_LIST_TEMPLATE.format(code=code)
        players:list[str] = self.redis.lrange(players_list_key, 0, -1)
        if username not in players:
            raise ValueError(f"Player '{username}' is not in lobby {code}")

        state_key = self.PLAYER_STATE_TEMPLATE.format(code=code, username=username)
        if not self.redis.exists(state_key):
            raise ValueError(f"No state for player '{username}' in lobby {code}")

        raw = self.redis.hgetall(state_key)

        try:
            points = int(raw.get("points", 0))
        except (TypeError, ValueError):
            points = 0

        role = raw.get("role")
        role = role if role not in (None, "", "null") else None

        missions_raw = raw.get("secret_missions")
        missions: list[str]
        if missions_raw:
            try:
                parsed = json.loads(missions_raw)
                if isinstance(parsed, list):
                    missions = [str(x) for x in parsed]
                else:
                    missions = []
            except Exception:
                missions = []
        else:
            missions = []

        conn_raw = raw.get("connected")
        def _as_bool(x):
            if x is None:
                return True
            if isinstance(x, (int, float)):
                return bool(x)
            s = str(x).strip().lower()
            if s in ("1", "true", "t", "yes", "y"):
                return True
            if s in ("0", "false", "f", "no", "n", ""):
                return False
            try:
                j = json.loads(s)
                if isinstance(j, bool):
                    return j
                if isinstance(j, (int, float)):
                    return bool(j)
            except Exception:
                pass
            return bool(s)

        connected = _as_bool(conn_raw)

        return PlayerState(
            username=username,
            points=points,
            role=role,
            secret_missions=missions,
            connected=connected,
        )
