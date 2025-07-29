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
    jti = db.Column(db.String(64), nullable=False, unique=True)
    identity = db.Column(db.String(32), nullable=False, index=True)
    role = db.Column(
        db.Enum(AuthRoleEnum,
                values_callable=lambda enum_class: [e.value for e in enum_class],
                name="auth_role_enum",
                native_enum=False,
                validate_strings=True),
        nullable=False,
        default=AuthRoleEnum.USER.value
    )


    def __repr__(self):
        return f"<AuthToken {self.jti}>"

    def to_dict(self) -> AuthTokenDict:
        return AuthTokenDict(
            id=self.id,
            jti=self.jti,
            identity=self.identity,
            role=self.role.value,
        )