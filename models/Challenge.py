from typing import TypedDict
from db import db

class ChallengeDict(TypedDict):
    id: int
    title: str
    description: str
    drinking: bool = False
    sex: bool = False
    smoking: bool = False
    partner_friendly: bool = True
    probability: float = 1.0
    icon: str|None = None
    skipping: int|None = None
    voting: bool = False
    prize: int = 0

class Challenge(db.Model):
    __tablename__ = 'challenges'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.String(500), nullable=False)
    drinking = db.Column(db.Boolean, nullable=False, default=False)
    sex = db.Column(db.Boolean, nullable=False, default=False)
    smoking = db.Column(db.Boolean, nullable=False, default=False)
    partner_friendly = db.Column(db.Boolean, nullable=False, default=True)
    probability = db.Column(db.Float, nullable=False, default=1.0)
    icon = db.Column(db.String(100), nullable=True, default=None)
    skipping = db.Column(db.Integer, nullable=True, default=None)
    voting = db.Column(db.Boolean, nullable=False, default=False)
    prize = db.Column(db.Integer, nullable=False, default=0)

    def __repr__(self):
        return f"<Challenge {self.title} with ID {self.id}>"
    
    def to_dict(self) -> ChallengeDict:
        return ChallengeDict(
            id=self.id,
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
        )

    def __len__(self) -> int:
        """
        Returns the length of the challenge description.
        """
        return len(self.description)