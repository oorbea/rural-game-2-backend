from abc import ABC, abstractmethod
from typing import Any

from enums.TurnType import TurnTypeEnum

class ChallengeProvider(ABC):
    """Interface for providing challenges, player roles and more for a game lobby."""

    @abstractmethod
    def get_next_challenge(self, lobby_code: str, game_state: dict[str, Any], type:TurnTypeEnum|str = TurnTypeEnum.CHALLENGE) -> dict[str, Any]:
        """Return the next challenge for the lobby.

        :param lobby_code: unique code identifying the lobby
        :param game_state: current state of the lobby, including
            players, turn index, roles and any custom flags
        :param type: the type of challenge to return
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
    
    @abstractmethod
    def skip_turn(self, lobby_code: str, player: str, turn_type: TurnTypeEnum, title: str) -> int:
        """Skip the current turn for the specified player.
        This method is called when a player chooses to skip their turn.

        :param lobby_code: unique code identifying the lobby
        :param player: player who is skipping their turn
        :param turn_type: the type of turn being skipped
        :param title: the title of the challenge being skipped
        :returns: the new total score for the player
        """
        raise NotImplementedError("This method should be implemented by subclasses")
    
    @abstractmethod
    def complete_turn(self, lobby_code: str, player: str, turn_type: TurnTypeEnum, title: str) -> tuple[int, bool]:
        """Mark the current turn as completed.
        This method is called when a player completes their turn.

        :param lobby_code: unique code identifying the lobby
        :param player: player who is completing their turn
        :param turn_type: the type of turn being completed
        :param title: the title of the challenge being completed
        :returns: a tuple containing the prize score for the player
            and a boolean indicating if the lobby should vote the performance
        """
        raise NotImplementedError("This method should be implemented by subclasses")
    
    @abstractmethod
    def compute_award_from_votes(self, potential_prize: int, votes: list[int]) -> int:
        """
        Calculates the final points based on the ratings (0..10).

        :param potential_prize: The maximum prize that can be awarded.
        :param votes: List of integer votes (0 to 10).
        :return: The calculated award points.
        """
        raise NotImplementedError("This method should be implemented by subclasses")