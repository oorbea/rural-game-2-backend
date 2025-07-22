from typing import TypedDict
from db import db

class RoleDict(TypedDict):
    title: str
    description: str
    quantity_per_game: int|None = None

class Role(db.Model):
    __tablename__ = 'roles'
    
    title = db.Column(db.String(100), primary_key=True)
    description = db.Column(db.String(500), nullable=False)
    quantity_per_game = db.Column(db.Integer, nullable=True, default=None)

    def __repr__(self):
        return f"<Role {self.title}>"

    def to_dict(self) -> RoleDict:
        return RoleDict(
            title=self.title,
            description=self.description,
            quantity_per_game=self.quantity_per_game
        )

    def __len__(self) -> int:
        """
        Returns the length of the role description.
        """
        return len(self.description)