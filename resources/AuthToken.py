from flask import Blueprint, request, jsonify, abort
from flask.views import MethodView
from flask_jwt_extended import create_access_token
from flask_jwt_extended.utils import get_jti  # para extraer el jti
from db import db
from models.AuthToken import AuthToken
from enums.AuthRoleEnum import AuthRoleEnum

blp = Blueprint('auth', __name__, description='Gestión de autenticación')

@blp.route('')
class AuthTokenResource(MethodView):
    """

    Emite un nuevo token. Usa identity y rol suministrados en la petición.
    Roles válidos: 'U' (USER) y 'A' (ADMIN).
    """
    def post(self):
        json_data = request.get_json() or {}
        identity = json_data.get('identity', 'frontend')  # p. ej. 'frontend'
        role_value = json_data.get('role', 'U')  # 'U' por defecto
        # validar rol
        try:
            role_enum = AuthRoleEnum(role_value)
        except ValueError:
            abort(400, description=f"Rol '{role_value}' no válido")

        # 1) Crear la fila en AuthToken sin jti (esto nos da un id)
        auth_token = AuthToken(identity=identity, role=role_enum.value)
        db.session.add(auth_token)
        db.session.flush()  # obtiene auth_token.id sin hacer commit

        # 2) Generar el token con claims adicionales; incluimos el ID del registro y el rol
        claims = {
            'token': auth_token.id,
            'role': role_enum.value,
        }
        access_token = create_access_token(identity=identity, additional_claims=claims)

        # 3) Obtener jti y guardar en la fila de AuthToken
        jti = get_jti(access_token)  # o decode_token(access_token)['jti']
        auth_token.jti = jti
        db.session.commit()

        # 4) Devolver el token al cliente
        return jsonify({
            'access_token': access_token,
            'token_id': auth_token.id,
            'identity': identity,
            'role': role_enum.value,
        }), 201