from db import db
from models.Challenge import ChallengeDict

class GroupChallengeDict(ChallengeDict):
    player_quantity: int = 1
    teams: int = 1

class GroupChallenge(db.Model):
    __tablename__ = 'group_challenges'
    
    title = db.Column(db.String(100), primary_key=True)
    description = db.Column(db.String(500), nullable=False)
    drinking = db.Column(db.Boolean, nullable=False, default=False)
    sex = db.Column(db.Boolean, nullable=False, default=False)
    smoking = db.Column(db.Boolean, nullable=False, default=False)
    partner_friendly = db.Column(db.Boolean, nullable=False, default=True)
    probability = db.Column(db.Float, nullable=False, default=1.0)
    icon = db.Column(db.String(100), nullable=True, default=None)
    skipping = db.Column(db.Float, nullable=True, default=None)
    voting = db.Column(db.Boolean, nullable=False, default=False)
    prize = db.Column(db.Integer, nullable=False)
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