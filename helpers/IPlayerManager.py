from abc import ABC, abstractmethod
from typing import Any, ClassVar

from helpers.PlayerInfo import PlayerInfo
from helpers.PlayerState import PlayerState

class PlayerManager(ABC):
    """Interface for managing player information and state in a game lobby."""
    LOBBY_KEY_TEMPLATE: ClassVar[str]
    PLAYERS_LIST_TEMPLATE: ClassVar[str]
    PLAYER_STATE_TEMPLATE: ClassVar[str]
    LOBBY_USER_TEMPLATE: ClassVar[str]
    ACTIVE_LOBBIES_SET: ClassVar[str]

    REQUIRED_CLASS_ATTRS: ClassVar[tuple[str, ...]] = (
        "LOBBY_KEY_TEMPLATE",
        "PLAYERS_LIST_TEMPLATE",
        "PLAYER_STATE_TEMPLATE",
        "LOBBY_USER_TEMPLATE",
        "ACTIVE_LOBBIES_SET",
    )

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        missing = [a for a in cls.REQUIRED_CLASS_ATTRS if not hasattr(cls, a)]
        if missing:
            raise TypeError(
                f"{cls.__name__} must define attributes in: {', '.join(missing)}"
            )

    @abstractmethod
    def update_player_info(self, code: str, current_username: str, new_info: dict[str, Any]) -> None:
        """Update a player's static information in the lobby.

        :param code: lobby code
        :param current_username: the player's current username
        :param new_info: dictionary containing updated player information
        """
        raise NotImplementedError("This method should be implemented by subclasses")

    @abstractmethod
    def get_player_info(self, code: str, username: str) -> PlayerInfo:
        """Retrieve a player's static information in the lobby.

        :param code: lobby code
        :param username: the player's username
        :returns: a PlayerInfo object containing the player's static information
        """
        raise NotImplementedError("This method should be implemented by subclasses")
    
    @abstractmethod
    def get_player_state(self, code: str, username: str) -> PlayerState:
        """Retrieve a player's dynamic state in the lobby.

        :param code: lobby code
        :param username: the player's username
        :returns: a PlayerState object containing the player's dynamic state
        """
        raise NotImplementedError("This method should be implemented by subclasses")
    
    @abstractmethod
    def remove_player(self, code: str, username: str) -> str | None:
        """Remove a player from a lobby, delete their profile picture on disk,
        and return the resulting host (None if lobby deleted)."""
        raise NotImplementedError("This method should be implemented by subclasses")