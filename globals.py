import os
from dotenv import load_dotenv

VERSION = '0.1'

DEFAULT_VERSION_ENDPOINT = '/api/version'

DEFAULT_API_PREFIX = '/api/v1'
DEFAULT_API_TITLE = 'Rural Game 2 API'
DEFAULT_SWAGGER_URL = '/api-docs'
DEFAULT_DEBUG = False
DEFAULT_PORT = 5000

#------------------------------

load_dotenv()

#DB

DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')

DB_SSL = os.getenv("DB_SSL", "false").lower() in ('t', 'true', '1', 'y', 'yes')
DB_SSL_CA = os.getenv("DB_SSL_CA")

DB_AUTO_MIGRATE = os.getenv("DB_AUTO_MIGRATE", "true").lower() in ('t', 'true', '1', 'y', 'yes')

#------------------------------

VERSION_ENDPOINT = os.getenv('VERSION_ENDPOINT', DEFAULT_VERSION_ENDPOINT)
API_PREFIX=os.getenv('API_PREFIX', DEFAULT_API_PREFIX)
API_TITLE=os.getenv('API_TITLE', DEFAULT_API_TITLE)
API_VERSION=os.getenv('API_VERSION', VERSION)
SWAGGER_URL=os.getenv('SWAGGER_URL', DEFAULT_SWAGGER_URL)
DEBUG = str(os.getenv('DEBUG', DEFAULT_DEBUG)).lower() in ('t', 'true', '1', 'y', 'yes')
PORT = int(os.getenv('PORT', DEFAULT_PORT))
HOST_NAME = os.getenv('HOST_NAME', f'http://localhost:{PORT}')

#------------------------------

ALLOWED_PICTURE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
PROFILE_PICTURES_DIR = "public/ChallengePics"

JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
JWT_TOKEN_LOCATION = os.getenv('JWT_TOKEN_LOCATION', 'headers')
JWT_HEADER_NAME = os.getenv('JWT_HEADER_NAME', 'Authorization')
JWT_HEADER_TYPE = os.getenv('JWT_HEADER_TYPE', 'Bearer')

ADMINS = os.getenv('ADMINS', '').split(',')
USERS = ADMINS.copy() + os.getenv('USERS', '').split(',')