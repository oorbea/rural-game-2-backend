from importlib import import_module
import os
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_smorest import Api
from flask_migrate import Migrate, upgrade as alembic_upgrade
from flask_socketio import SocketIO, emit, join_room, leave_room
import redis

from controllers.GameController import GameController
from db import create_db

from resources.Challenge import blp as ChallengeBlueprint

from events.LobbyEvents import LobbyEvents

socketio = SocketIO(message_queue="redis://redis:6379/0", cors_allowed_origins='*')

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
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "pool_pre_ping": True,
        "pool_recycle": 1800,
    }

    DB_SSL:bool = app.config.get("DB_SSL", False)
    DB_SSL_CA = app.config.get("DB_SSL_CA")
    if DB_SSL and DB_SSL_CA:
        app.config.setdefault("SQLALCHEMY_ENGINE_OPTIONS", {})
        app.config["SQLALCHEMY_ENGINE_OPTIONS"]["connect_args"] = {
            "ssl": {"ca": DB_SSL_CA}
        }
        
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
    
    def getApiPrefix(url:str) -> str: return f"{app.config['API_PREFIX']}/{url}"
    def getSocketIOPrefix(url:str) -> str: return f"{app.config['SOCKETIO_PREFIX']}/{url}"

    jwt = JWTManager(app)

    api = Api(app)

    api.spec.components.security_scheme(
        'jwt', {'type': 'http', 'scheme': 'bearer', 'bearerFormat': 'JWT', 'x-bearerInfoFunc': 'app.decode_token'}
    )

    socketio.init_app(app, cors_allowed_origins='*')

    r = redis.Redis(host="redis", port=6379, decode_responses=True)
    module_name = app.config.get('CHALLENGE_PROVIDER_MODULE', 'controllers.TurnManager')
    try:
        turn_module = import_module(module_name)
        turn_manager = turn_module.TurnManager()
        app.extensions['game_controller'] = GameController(r, turn_manager)
    except ImportError as e:
        raise ImportError(f"Failed to import module '{module_name}': {e}")
    except AttributeError as e:
        raise AttributeError(f"Module '{module_name}' does not have 'TurnManager' class: {e}")
    except Exception as e:
        raise Exception(f"An error occurred while initializing the game controller: {e}")

    # HTTP routes
    api.register_blueprint(ChallengeBlueprint, url_prefix=getApiPrefix('challenge'))

    # SocketIO events
    socketio.on_namespace(LobbyEvents(getSocketIOPrefix('lobby')))

    with app.app_context():
        db = create_db(app)
        import models
        migrate = Migrate(app, db)
        DB_AUTO_MIGRATE = app.config.get("DB_AUTO_MIGRATE", True)
        migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
        if DB_AUTO_MIGRATE and os.path.isdir(migrations_dir) and os.path.isfile(os.path.join(migrations_dir, "env.py")):
            alembic_upgrade()
    
    ## NotImplementedError
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
    socketio.run(app, host="0.0.0.0", port=app.config.get('PORT', 5000), debug=app.config.get('DEBUG', False), use_reloader=app.config.get('DEBUG', False))