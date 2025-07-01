import os
from flask import Flask, jsonify
from flask_cors import CORS
from flask_smorest import Api
from flask_sqlalchemy import SQLAlchemy

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

    api = Api(app) #TODO: Aquí se meterán los recursos de la API, autenticación, prefijo, etc
    
    return app

app = create_app(os.getenv('SETTINGS_MODULE', None))

if __name__ == "__main__":

    with app.app_context():
        from db import create_db
        import models

        db = create_db(app)
        db.create_all()
    
    app.run(threaded=True, host="0.0.0.0", port=app.config.get('PORT', 5000), debug=app.config.get('DEBUG', False), use_reloader=app.config.get('DEBUG', False))