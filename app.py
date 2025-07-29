import os
import traceback
from flask import Flask, abort, jsonify, request
from flask_cors import CORS
from flask_smorest import Api
from flask_jwt_extended import JWTManager
from sqlalchemy.exc import SQLAlchemyError

from resources.Challenge import blp as ChallengeBlueprint

def create_app(settings_module: str | None = None):
    """
    Creates a new instace of Flask application.
    
    Args:
        settings_module (str, optional): Configuration module to use.
    """
    app = Flask(__name__)
    
    if settings_module is None:
        settings_module = 'globals'
    
    app.config.from_object(settings_module)

    DB_USER = app.config['DB_USER']
    DB_PASSWORD = app.config['DB_PASSWORD']
    DB_HOST = app.config['DB_HOST']
    DB_PORT = app.config['DB_PORT']
    DB_NAME = app.config['DB_NAME']

    app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
    CORS(
       app,
       resources={r"/api/*": {"origins": "*"}},
       allow_headers=["Content-Type", "Authorization"],
       supports_credentials=True
    )

    API_TITLE = app.config.get('API_TITLE')
    API_VERSION = app.config.get('API_VERSION')
    SWAGGER_URL = app.config.get('SWAGGER_URL')
    
    app.config['API_TITLE'] = API_TITLE
    app.config['API_VERSION'] = API_VERSION
    app.config['OPENAPI_VERSION'] = '3.0.3'
    app.config['OPENAPI_URL_PREFIX'] = '/'
    app.config['OPENAPI_SWAGGER_UI_PATH'] = SWAGGER_URL
    app.config['OPENAPI_SWAGGER_UI_URL'] = 'https://cdn.jsdelivr.net/npm/swagger-ui-dist/'
        
    app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024
    
    @app.errorhandler(NotImplementedError)
    def handle_not_implemented_error(error):
        response = {
            "error_message": str(error),
            "code": 501,
            "status": "Not Implemented"
        }
        return jsonify(response), 501
    
    def getApiPrefix(url:str) -> str: return f"{app.config['API_PREFIX']}/{url}"

    api = Api(app)

    api.register_blueprint(ChallengeBlueprint, url_prefix=getApiPrefix('challenge'))

    from db import create_db
    import models

    with app.app_context():
        db = create_db(app)
        db.create_all()
        
    jwt = JWTManager(app)
    
    ##JWT CHECK
    
    @jwt.token_in_blocklist_loader
    def check_if_token_in_blocklist(jwt_header, jwt_payload):
        
        try:
            tokenId = jwt_payload['token']
            jti = jwt_payload['jti']
            identity = jwt_payload['sub']
                        
            print("jti", jti)
                        
            try:
                session_token = db.getTokenModel().get(tokenId)
            except SQLAlchemyError as e:
                traceback.print_exc()
                abort(500, message = str(e))
            
            print("session_token", session_token)
            
            if not session_token: return True
            
            return not (session_token['jti'] == jti and session_token["identity"] == identity)
            
        except KeyError:
            return True
            
    ##JWT ERRORS
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):                
        return jsonify({"message": error, "error": "invalid_token"}), 401
    
    @jwt.needs_fresh_token_loader
    def token_not_fresh_callback(jwt_header, jwt_payload):
        return jsonify({"message": "The token is not fresh.", "error": "fresh_token_required"}), 401
    
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        try:
            db.getTokenModel().delete(jwt_payload['token'])
        except Exception as e:
            traceback.print_exc()
            abort(500, message = str(e))
        return jsonify({"message": "The token has expired.", "error": "token_expired"}), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        headers = request.headers
        for header in headers:
            print(header)
        return jsonify({"message": error, "error": "token_unauthorized"}), 401

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return jsonify({"message": "The token has been revoked.", "error": "token_revoked"}), 401
    
    ##NotImplementedError
    
    @app.errorhandler(NotImplementedError)
    def handle_not_implemented_error(error):
        response = {
            "error_message": str(error),
            "code": 501,
            "status": "Not Implemented"
        }
        return jsonify(response), 501
    
    return app

app = create_app(os.getenv('SETTINGS_MODULE', None))

if __name__ == "__main__":    
    app.run(threaded=True, host="0.0.0.0", port=app.config.get('PORT', 5000), debug=app.config.get('DEBUG', False), use_reloader=app.config.get('DEBUG', False))