from db import db
from models.Challenge import ChallengeDict

class SecretMissionDict(ChallengeDict):
    punishment: float

class SecretMission(db.Model):
    __tablename__ = 'secret_missions'
    
    title = db.Column(db.String(100), primary_key=True)
    description = db.Column(db.String(500), nullable=False)
    drinking = db.Column(db.Boolean, nullable=False, default=False)
    smoking = db.Column(db.Boolean, nullable=False, default=False)
    partner_friendly = db.Column(db.Boolean, nullable=False, default=True)
    probability = db.Column(db.Float, nullable=False, default=1.0)
    icon = db.Column(db.String(100), nullable=True, default=None)
    prize = db.Column(db.Integer, nullable=False)
    males = db.Column(db.Integer, nullable=True, default=None)
    females = db.Column(db.Integer, nullable=True, default=None)
    punishment = db.Column(db.Float, nullable=False)
    pass #TODO: Implement specific fields for SecretMission if needed

    def __repr__(self):
        return f"<Secret Mission {self.title}>"
    
    def to_dict(self) -> SecretMissionDict:
        return SecretMissionDict(
            title=self.title,
            description=self.description,
            drinking=self.drinking,
            smoking=self.smoking,
            partner_friendly=self.partner_friendly,
            probability=self.probability,
            icon=self.icon,
            prize=self.prize,
            males=self.males,
            females=self.females,
            punishment=self.punishment
        )

    def __len__(self) -> int:
        """
        Returns the length of the secret mission description.
        """
        return len(self.description)