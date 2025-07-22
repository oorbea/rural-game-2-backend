from db import db
from models.Challenge import Challenge, ChallengeDict

class GroupChallengeDict(ChallengeDict):
    player_quantity: int = 1
    teams: int = 1

class GroupChallenge(Challenge):
    __tablename__ = 'group_challenges'
    
    player_quantity = db.Column(db.Integer, nullable=False, default=1)
    teams = db.Column(db.Integer, nullable=False, default=1)

    def __repr__(self):
        return f"<Group Challenge {self.title} with ID {self.id}>"
    
    def to_dict(self) -> GroupChallengeDict:
        return GroupChallengeDict(
            title=self.title,
            description=self.description,
            drinking=self.drinking,
            sex=self.sex,
            smoking=self.smoking,
            partner_friendly=self.partner_friendly,
            probability=self.probability,
            icon=self.icon,
            skipping=self.skipping,
            voting=self.voting,
            prize=self.prize,
            player_quantity=self.player_quantity,
            teams=self.teams
        )

    def __len__(self) -> int:
        """
        Returns the length of the group challenge description.
        """
        return len(self.description)