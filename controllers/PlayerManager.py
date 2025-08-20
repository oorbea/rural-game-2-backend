import json
import os
from typing import Any

import redis
from helpers.IPlayerManager import PlayerManager as IPlayerManager
from helpers.PlayerInfo import PlayerInfo
from helpers.PlayerState import PlayerState
from helpers.normalize_value import normalize_value

class PlayerManager(IPlayerManager):
    LOBBY_KEY_TEMPLATE = "lobby:{code}"
    PLAYERS_LIST_TEMPLATE = "lobby:{code}:players"
    PLAYER_STATE_TEMPLATE = "lobby:{code}:player:{username}"
    LOBBY_USER_TEMPLATE = "lobby:{code}:user:{username}"
    ACTIVE_LOBBIES_SET = "lobbies:active"

    def __init__(self, redis_client: redis.Redis) -> None:
        self.redis = redis_client
        self._base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    def _resolve_fs(self, path: str | None) -> str | None:
        if not path:
            return None
        return path if os.path.isabs(path) else os.path.join(self._base_dir, path.lstrip('/'))

    def update_player_info(self, code: str, current_username: str, new_info: dict[str, Any]) -> None:
        if not self.redis.sismember(self.ACTIVE_LOBBIES_SET, code):
            raise ValueError(f"Lobby {code} does not exist or is not active")

        allowed = {"username", "drinking", "smoking", "partnered", "virgin", "gender", "profile_pic"}
        updates_raw = {k: v for k, v in (new_info or {}).items() if k in allowed}

        if "gender" in updates_raw and updates_raw["gender"] is not None:
            g = updates_raw["gender"]
            try:
                from enums.GenderEnum import GenderEnum
                if not isinstance(g, GenderEnum):
                    g = GenderEnum(str(g).lower())
                updates_raw["gender"] = g
            except Exception:
                gs = str(g).lower()
                if gs not in ("male", "female"):
                    raise ValueError("gender must be 'male' or 'female'")
                updates_raw["gender"] = gs

        lobby_key = self.LOBBY_KEY_TEMPLATE.format(code=code)
        players_list_key = self.PLAYERS_LIST_TEMPLATE.format(code=code)
        state_key_old = self.PLAYER_STATE_TEMPLATE.format(code=code, username=current_username)
        lobby_user_old = self.LOBBY_USER_TEMPLATE.format(code=code, username=current_username)

        desired_username = updates_raw.get("username", current_username)
        state_key_new = self.PLAYER_STATE_TEMPLATE.format(code=code, username=desired_username)
        lobby_user_new = self.LOBBY_USER_TEMPLATE.format(code=code, username=desired_username)

        def _b2s(x): return x.decode() if isinstance(x, (bytes, bytearray)) else x

        with self.redis.pipeline() as pipe:
            while True:
                try:
                    watch_keys = [players_list_key, lobby_key, lobby_user_old]
                    if desired_username != current_username:
                        watch_keys += [state_key_old]
                    pipe.watch(*watch_keys)

                    players = [_b2s(p) for p in pipe.lrange(players_list_key, 0, -1)]
                    if current_username not in players:
                        pipe.unwatch()
                        raise ValueError(f"Player '{current_username}' is not in lobby {code}")

                    host_val = _b2s(pipe.hget(lobby_key, "host"))

                    idx = -1
                    if desired_username != current_username:
                        if desired_username in players:
                            pipe.unwatch()
                            raise ValueError(f"Username '{desired_username}' is already in the lobby")
                        if not pipe.exists(state_key_old):
                            pipe.unwatch()
                            raise ValueError(f"No state for player {current_username} in lobby {code}")
                        idx = players.index(current_username)

                    # normalizamos mapping para guardar en la hash por-lobby
                    to_update = {k: updates_raw[k] for k in updates_raw if k != "username"}
                    serial_map = {}
                    for k, v in to_update.items():
                        if k == "gender" and hasattr(v, "value"):
                            serial_map[k] = normalize_value(v.value)
                        else:
                            serial_map[k] = normalize_value(v)

                    target_lobby_user = lobby_user_old
                    pipe.multi()

                    if desired_username != current_username:
                        # renombrar lista
                        pipe.lset(players_list_key, idx, desired_username)
                        # renombrar estado
                        pipe.renamenx(state_key_old, state_key_new)
                        # renombrar hash por-lobby
                        if pipe.exists(lobby_user_old):
                            pipe.renamenx(lobby_user_old, lobby_user_new)
                        target_lobby_user = lobby_user_new
                        # host
                        if host_val == current_username:
                            pipe.hset(lobby_key, "host", desired_username)

                    if serial_map:
                        pipe.hset(target_lobby_user, mapping=serial_map)

                    pipe.execute()
                    break
                except ValueError:
                    raise
                except redis.WatchError:
                    continue

    def get_player_info(self, code: str, username: str) -> PlayerInfo:
        if not self.redis.sismember(self.ACTIVE_LOBBIES_SET, code):
            raise ValueError(f"Lobby {code} does not exist or is not active")

        players_list_key = self.PLAYERS_LIST_TEMPLATE.format(code=code)
        players_list:list[str] = self.redis.lrange(players_list_key, 0, -1)
        if username not in players_list:
            raise ValueError(f"Player '{username}' is not in lobby {code}")

        lobby_user_key = self.LOBBY_USER_TEMPLATE.format(code=code, username=username)
        if not self.redis.exists(lobby_user_key):
            raise ValueError(f"No static info for player '{username}' in lobby {code}")

        data = self.redis.hgetall(lobby_user_key)

        def _as_bool(x):
            if x is None: return False
            if isinstance(x, (int, float)): return bool(x)
            s = str(x).strip().lower()
            if s in ("1","true","t","yes","y"): return True
            if s in ("0","false","f","no","n",""): return False
            try:
                j = json.loads(s)
                if isinstance(j, bool): return j
                if isinstance(j, (int, float)): return bool(j)
            except Exception:
                pass
            return bool(s)

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

        profile_pic_bytes = None
        rel_path = data.get("profile_pic")
        if rel_path:
            abs_path = self._resolve_fs(rel_path)
            if abs_path and os.path.exists(abs_path):
                try:
                    with open(abs_path, 'rb') as f:
                        profile_pic_bytes = f.read()
                except Exception:
                    profile_pic_bytes = None

        return PlayerInfo(
            username=username,
            drinking=_as_bool(data.get("drinking")),
            smoking=_as_bool(data.get("smoking")),
            partnered=_as_bool(data.get("partnered")),
            virgin=_as_bool(data.get("virgin")),
            gender=gender,
            profile_pic=profile_pic_bytes,
        )

    def get_player_state(self, code: str, username: str) -> PlayerState:
        state_key = self.PLAYER_STATE_TEMPLATE.format(code=code, username=username)
        if not self.redis.exists(state_key):
            raise ValueError(f"No state for player '{username}' in lobby {code}")
        raw = self.redis.hgetall(state_key)
        try:
            points = int(raw.get("points", 0))
        except (TypeError, ValueError):
            points = 0
        role = raw.get("role") or None
        missions_raw = raw.get("secret_missions")
        try:
            secret_missions = list(json.loads(missions_raw)) if missions_raw else []
        except Exception:
            secret_missions = []
        conn_raw = raw.get("connected")
        connected = True
        if conn_raw is not None:
            try:
                connected = bool(json.loads(conn_raw))
            except Exception:
                connected = bool(conn_raw)
        return PlayerState(username=username, points=points, role=role, secret_missions=secret_missions, connected=connected)

    def remove_player(self, code: str, username: str) -> str | None:
        if not self.redis.sismember(self.ACTIVE_LOBBIES_SET, code):
            raise ValueError(f"Lobby {code} does not exist or is not active")

        lobby_key = self.LOBBY_KEY_TEMPLATE.format(code=code)
        players_list_key = self.PLAYERS_LIST_TEMPLATE.format(code=code)
        state_key = self.PLAYER_STATE_TEMPLATE.format(code=code, username=username)
        lobby_user_key = self.LOBBY_USER_TEMPLATE.format(code=code, username=username)

        def _b2s(x): return x.decode() if isinstance(x, (bytes, bytearray)) else x

        old_pic_path: str | None = None
        result_host: str | None = None

        with self.redis.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(players_list_key, lobby_key, lobby_user_key)
                    players = [_b2s(p) for p in pipe.lrange(players_list_key, 0, -1)]
                    if username not in players:
                        pipe.unwatch()
                        host_raw = self.redis.hget(lobby_key, "host")
                        return _b2s(host_raw)

                    host_val = _b2s(pipe.hget(lobby_key, "host"))
                    old_pic_path = _b2s(pipe.hget(lobby_user_key, "profile_pic"))

                    remaining = [p for p in players if p != username]
                    new_len = len(remaining)
                    next_host = remaining[0] if new_len > 0 else None
                    result_host = None if new_len == 0 else (next_host if (not host_val or host_val == username) else host_val)

                    pipe.multi()
                    pipe.lrem(players_list_key, 0, username)
                    pipe.delete(state_key)
                    pipe.delete(lobby_user_key)

                    if new_len == 0:
                        pipe.delete(players_list_key)
                        pipe.delete(lobby_key)
                        pipe.srem(self.ACTIVE_LOBBIES_SET, code)
                    else:
                        if (not host_val) or (host_val == username):
                            pipe.hset(lobby_key, "host", result_host)

                    pipe.execute()
                    break
                except redis.WatchError:
                    continue

        try:
            abs_old = self._resolve_fs(old_pic_path)
            if abs_old and os.path.exists(abs_old):
                os.remove(abs_old)
        except Exception:
            pass

        return result_host
