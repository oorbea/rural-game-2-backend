from db import db
from sqlalchemy import Enum
from enums.GenderEnum import GenderEnum

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(300), unique=True, nullable=False)
    drinks = db.Column(db.Boolean, nullable=False)
    virgin = db.Column(db.Boolean, nullable=False)
    smokes = db.Column(db.Boolean, nullable=False)
    has_partner = db.Column(db.Boolean, nullable=False)
    gender = db.Column(Enum(GenderEnum), nullable=False)

    def __repr__(self):
        return f"<User {self.username} with ID {self.id}>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "drinks": self.drinks,
            "virgin": self.virgin,
            "smokes": self.smokes,
            "has_partner": self.has_partner,
            "gender": self.gender.value
        }