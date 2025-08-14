from abc import ABC, abstractmethod
from typing import Any

from helpers.PlayerInfo import PlayerInfo
from helpers.PlayerState import PlayerState

class PlayerManager(ABC):
    """Interface for managing player information and state in a game lobby."""
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