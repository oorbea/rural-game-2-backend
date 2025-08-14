from dataclasses import dataclass, field
from typing import Optional

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