from db import db
from models.Challenge import ChallengeDict

class TargetChallengeDict(ChallengeDict):
    title: str
    description: str
    drinking: bool = False
    sex: bool = False
    smoking: bool = False
    partner_friendly: bool = True
    probability: float = 1.0
    icon: str|None = None
    skipping: float|None = None
    voting: bool = False
    prize: int
    males: int|None = None
    females: int|None = None

class TargetChallenge(db.Model): 
    __tablename__ = 'target_challenges'
    
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
    males = db.Column(db.Integer, nullable=True, default=None)
    females = db.Column(db.Integer, nullable=True, default=None)
    player_quantity = db.Column(db.Integer, nullable=False, default=1)
    group_challenge = db.Column(db.Boolean, nullable=False, default=False)
    pass #TODO: Implement specific fields for TargetChallenge if needed

    def __repr__(self):
        return f"<Target Challenge {self.title}>"
    
    def to_dict(self):
        return TargetChallengeDict(
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
            males=self.males,
            females=self.females,
            player_quantity = self.player_quantity,
            group_challenge = self.group_challenge
        )

    def __len__(self) -> int:
        """
        Returns the length of the challenge description.
        """
        return len(self.description)