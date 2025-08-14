from abc import ABC, abstractmethod
from typing import Any

class ChallengeProvider(ABC):
    """Interface for providing challenges, player roles and more for a game lobby."""

    @abstractmethod
    def get_next_challenge(self, lobby_code: str, game_state: dict[str, Any]) -> dict[str, Any]:
        """Return the next challenge for the lobby.

        :param lobby_code: unique code identifying the lobby
        :param game_state: current state of the lobby, including
            players, turn index, roles and any custom flags
        :returns: a serialisable dictionary representing the challenge
        """
        raise NotImplementedError("This method should be implemented by subclasses")

    @abstractmethod
    def get_player_roles(self, lobby_code: str, players: list[str]) -> dict[str, str]:
        """Return a mapping of players to their assigned roles.
        This method is called when the game starts to assign roles to players.

        :param lobby_code: unique code identifying the lobby
        :param players: list of player usernames in the lobby
        :returns: a dictionary mapping usernames to their assigned roles
        """
        raise NotImplementedError("This method should be implemented by subclasses")