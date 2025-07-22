from typing import TypedDict
from db import db

class SecretMissionDict(TypedDict):
    title: str
    description: str
    drinking: bool = False
    sex: bool = False
    smoking: bool = False
    partner_friendly: bool = True
    probability: float = 1.0
    icon: str|None = None
    prize: int
    punishment: float

class SecretMission(db.Model):
    __tablename__ = 'secret_missions'
    
    title = db.Column(db.String(100), primary_key=True)
    description = db.Column(db.String(500), nullable=False)
    drinking = db.Column(db.Boolean, nullable=False, default=False)
    sex = db.Column(db.Boolean, nullable=False, default=False)
    smoking = db.Column(db.Boolean, nullable=False, default=False)
    partner_friendly = db.Column(db.Boolean, nullable=False, default=True)
    probability = db.Column(db.Float, nullable=False, default=1.0)
    icon = db.Column(db.String(100), nullable=True, default=None)
    prize = db.Column(db.Integer, nullable=False)
    punishment = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f"<Secret Mission {self.title}>"
    
    def to_dict(self) -> SecretMissionDict:
        return SecretMissionDict(
            title=self.title,
            description=self.description,
            drinking=self.drinking,
            sex=self.sex,
            smoking=self.smoking,
            partner_friendly=self.partner_friendly,
            probability=self.probability,
            icon=self.icon,
            prize=self.prize,
            punishment=self.punishment
        )

    def __len__(self) -> int:
        """
        Returns the length of the secret mission description.
        """
        return len(self.description)