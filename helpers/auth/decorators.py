from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt
from flask import abort
from models.AuthToken import AuthToken
from enums.AuthRoleEnum import AuthRoleEnum

def roles_required(*roles: AuthRoleEnum):
    """Decorator that validates the user has one of the allowed roles."""
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            token_id = claims.get("token")
            token = AuthToken.query.get(token_id)
            if not token:
                abort(401, description="Invalid token")
            if roles and token.role not in roles:
                abort(403, description="You do not have permission for this operation")
            return fn(*args, **kwargs)
        return decorator
    return wrapper

def login_required(fn):
    return roles_required(AuthRoleEnum.USER, AuthRoleEnum.ADMIN)(fn)

def admin_required(fn):
    return roles_required(AuthRoleEnum.ADMIN)(fn)
