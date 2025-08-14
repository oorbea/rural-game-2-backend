from dataclasses import dataclass
from typing import Optional

from enums.GenderEnum import GenderEnum

@dataclass
class PlayerInfo:
    """Static information about a player provided when they join a lobby.

    These fields capture per-user attributes that do not change during a single game session. They are stored in Redis when the player joins so that reconnects can recover their state.
    """

    username: str
    drinking: bool
    smoking: bool
    partnered: bool
    virgin: bool
    gender: GenderEnum
    profile_pic: Optional[str] = None