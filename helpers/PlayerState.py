from dataclasses import dataclass, field
from typing import Optional, TypedDict

class StateDict(TypedDict):
    """Dictionary type for player state."""
    username: str
    points: int
    role: Optional[str]
    secret_missions: list[str]
    connected: bool

@dataclass
class PlayerState:
    """Dynamic state of a player within a lobby.

    This object stores mutable fields that can change as the game progresses: points, assigned roles and secret missions. It is separate from PlayerInfo to honour the Single Responsibility principle: `PlayerInfo` describes who the participant is, whereas `PlayerState` describes their current standing in a particular game.
    """

    username: str
    points: int = 0
    role: Optional[str] = None
    secret_missions: list[str] = field(default_factory=list)
    connected: bool = True

    def to_dict(self):
        """Convert the PlayerState object to a dictionary."""
        return StateDict(
            username=self.username,
            points=self.points,
            role=self.role,
            secret_missions=self.secret_missions,
            connected=self.connected
        )