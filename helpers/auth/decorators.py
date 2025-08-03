from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt
from flask import abort
from enums.AuthRoleEnum import AuthRoleEnum
from flask import current_app as app


def roles_required(*roles: AuthRoleEnum):
    """Decorator that validates the user has one of the allowed roles."""
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            roles_str:list[str] = [role.value for role in roles]
            identity = claims.get('sub')
            role = claims.get('role')
            if not identity or not role:
                abort(401, description="Invalid token")
            if roles_str and role not in roles_str:
                abort(403, description="You do not have permission for this operation")
            if role == AuthRoleEnum.ADMIN and identity not in app.config['ADMINS']:
                abort(403, description="You do not have permission for this operation")
            return fn(*args, **kwargs)
        return decorator
    return wrapper

def login_required(fn):
    return roles_required(AuthRoleEnum.USER, AuthRoleEnum.ADMIN)(fn)

def admin_required(fn):
    return roles_required(AuthRoleEnum.ADMIN)(fn)
