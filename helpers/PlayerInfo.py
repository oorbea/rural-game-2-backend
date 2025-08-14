from dataclasses import dataclass
from typing import Optional, TypedDict

from enums.GenderEnum import GenderEnum

class InfoDict(TypedDict):
    """Dictionary type for player information."""
    username: str
    drinking: bool
    smoking: bool
    partnered: bool
    virgin: bool
    gender: str
    profile_pic: Optional[str]

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

    def to_dict(self):
        """Convert the PlayerInfo object to a dictionary."""
        gender = self.gender.value if isinstance(self.gender, GenderEnum) else self.gender
        return InfoDict(
            username=self.username,
            drinking=self.drinking,
            smoking=self.smoking,
            partnered=self.partnered,
            virgin=self.virgin,
            gender=gender,
            profile_pic=self.profile_pic
        )
            