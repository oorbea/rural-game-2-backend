from typing import TypedDict
from db import db
from enums.AuthRoleEnum import AuthRoleEnum

class AuthTokenDict(TypedDict):
    id: int
    jti: str
    identity: str
    role: AuthRoleEnum

class AuthToken(db.Model):
    __tablename__ = 'auth_tokens'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    jti = db.Column(db.String(80), nullable=False, unique=True)
    identity = db.Column(db.String(32), nullable=False)
    role = db.Column(db.Enum(AuthRoleEnum), nullable=False, default=AuthRoleEnum.USER)

    def __repr__(self):
        return f"<AuthToken {self.jti}>"

    def to_dict(self) -> AuthTokenDict:
        return AuthTokenDict(
            id=self.id,
            jti=self.jti,
            identity=self.identity,
            role=self.role,
        )