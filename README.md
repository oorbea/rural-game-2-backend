# Rural Game 2 - Backend API

A real-time multiplayer drinking game backend API built with Flask, Socket.IO, and Redis. This project provides both HTTP REST endpoints and WebSocket communication for a turn-based group game where players complete challenges and earn points.

## About the Project

Rural Game 2 is a turn-based multiplayer drinking game where players are assigned challenges, truth-or-dare tasks, and other activities to complete for points. The backend handles real-time communication through WebSockets, manages game state with Redis, and persists data in a MySQL database.

**Developed by:** 6 computer science students from FIB - UPC (Barcelona)
- 3 students working on frontend/react app [Check it too!](https://github.com/Yearsuck/Rural_Game-Frontend)
- 3 students working on backend/devops

## Features

- **REST API**: HTTP endpoints for game management and data operations
- **Real-time Communication**: WebSocket support via Socket.IO for live game interactions
- **Authentication**: JWT-based authentication with role-based access control
- **Database**: MySQL with automatic migrations via Flask-Migrate
- **Caching**: Redis for session management and real-time data
- **Documentation**: Swagger/OpenAPI for REST API and AsyncAPI for WebSocket documentation
- **Containerization**: Full Docker support with docker-compose

## Tech Stack

- **Framework**: Flask (Python)
- **Real-time**: Socket.IO
- **Database**: MySQL
- **Cache/Message Queue**: Redis
- **Authentication**: Flask-JWT-Extended
- **API Documentation**: Flask-Smorest (Swagger/OpenAPI), AsyncAPI
- **Containerization**: Docker & Docker Compose
- **Database Migrations**: Flask-Migrate

## Prerequisites

- **Docker Desktop** (Windows/Mac) or **Docker Engine** (Linux)
- **Docker Compose** (usually included with Docker Desktop)
- **Git** (for cloning the repository)

### Optional (for local development without Docker):
- **Python 3.13.2** (project tested on this version)
- **MySQL Server** (if not using external database)

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd rural-game-2-backend
```

### 2. Environment Configuration

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit the `.env` file with your configuration:

```env
# Application Settings
SETTINGS_MODULE=globals
FLASK_ENV=development
FLASK_APP=app.py
PORT=5000
DEBUG=true
FLASK_PORT=5000

# Database Configuration (External Server - Recommended)
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=your-database-server.com
DB_PORT=3306
DB_NAME=rural_game2
DB_AUTO_MIGRATE=true
DB_SSL=false
DB_SSL_CA=/app/certs/ca.pem

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379

# JWT Authentication
JWT_SECRET_KEY=your_super_secret_jwt_key_here
JWT_TOKEN_LOCATION=headers
JWT_HEADER_NAME=Authorization
JWT_HEADER_TYPE=Bearer

# User Roles (comma-separated usernames)
ADMINS=admin1,admin2,admin3
USERS=user1,user2,user3
```

### 3. Database Setup

#### Option A: External Database (Recommended)
If you have a MySQL server available, update the database credentials in your `.env` file and skip to step 4.

#### Option B: Local MySQL Setup
If you need a local MySQL instance, you can add it to the docker-compose.yml:

```yaml
# Add this service to your docker-compose.yml
mysql:
  image: mysql:8.0
  container_name: mysql_db
  restart: unless-stopped
  environment:
    MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
    MYSQL_DATABASE: ${DB_NAME}
    MYSQL_USER: ${DB_USER}
    MYSQL_PASSWORD: ${DB_PASSWORD}
  ports:
    - "3306:3306"
  volumes:
    - mysql_data:/var/lib/mysql

# Add this to the volumes section
volumes:
  redis_data:
  mysql_data:
```

Then update your `.env` file:
```env
DB_HOST=mysql
DB_PORT=3306
```

### 4. Build and Start the Application

#### Windows:
```cmd
# Build and start (first time or when dependencies change)
./build-backend.bat

# Or just start existing containers
./run-backend.bat
```

#### Linux/macOS:
```bash
# Make scripts executable
chmod +x build-backend.sh run-backend.sh migrate-db.sh

# Build and start (first time or when dependencies change)
./build-backend.sh

# Or just start existing containers
./run-backend.sh
```

#### Manual Docker Commands:
```bash
# Build and start all services
docker-compose up --build

# Start in background
docker-compose up -d --build

# Stop services
docker-compose down
```

## Database Migrations

The application supports automatic database migrations. When `DB_AUTO_MIGRATE=true` is set in your environment, migrations run automatically on startup.

### Manual Migration Management

#### Windows:
```cmd
./migrate-db.bat
```

#### Linux/macOS:
```bash
./migrate-db.sh
```

#### Manual Migration Commands:
```bash
# Generate a new migration
docker-compose exec flask_api flask db migrate -m "description of changes"

# Apply migrations
docker-compose exec flask_api flask db upgrade

# View migration history
docker-compose exec flask_api flask db history
```

## API Documentation

Once the application is running, you can access the documentation at:

### REST API Documentation (Swagger/OpenAPI)
- **URL**: `http://localhost:5000/api-docs`
- **Format**: Interactive Swagger UI interface
- **Content**: All HTTP REST endpoints with request/response schemas

### WebSocket API Documentation (AsyncAPI)
- **URL**: `http://localhost:5000/api/v1/docs`
- **Format**: AsyncAPI specification
- **Content**: Socket.IO events, namespaces, and real-time communication patterns

## Authentication & Authorization

The API uses JWT (JSON Web Tokens) for authentication with role-based access control:

### User Roles:
- **USER**: Basic user access, can participate in games
- **ADMIN**: Full access, developer/administrative operations

## Development

### Project Structure
```
rural-game-2-backend/
├── app.py                 # Application entry point
├── globals.py            # Configuration settings
├── controllers/          # Business logic controllers
├── resources/            # API route definitions
├── models/              # Database models
├── events/              # Socket.IO event handlers
├── helpers/             # Utility functions and decorators
├── migrations/          # Database migration files
├── requirements.txt     # Python dependencies
├── Dockerfile          # Docker container definition
├── docker-compose.yml  # Multi-container orchestration
└── *.bat, *.sh         # Convenience scripts
```

### Local Development Tips

1. **Logs**: Monitor application logs with `docker-compose logs -f flask_api`
2. **Database Access**: Connect to your database using the credentials in `.env`
3. **Redis Monitoring**: Access Redis CLI with `docker-compose exec redis redis-cli`
4. **Code Changes**: Volume mounting enables live code reloading in development mode

### Environment Variables Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Enable debug mode | `false` |
| `PORT` | Application port | `5000` |
| `DB_HOST` | Database host | - |
| `DB_PORT` | Database port | - |
| `DB_USER` | Database username | - |
| `DB_PASSWORD` | Database password | - |
| `DB_NAME` | Database name | - |
| `DB_AUTO_MIGRATE` | Auto-run migrations | `true` |
| `JWT_SECRET_KEY` | JWT signing key | - |
| `ADMINS` | Admin usernames (comma-separated) | - |
| `USERS` | Regular usernames (comma-separated) | - |

## Production Deployment

For production environments:

1. **Security**: Use strong JWT secret keys and secure database credentials
2. **SSL/TLS**: Configure HTTPS and secure database connections
3. **Environment**: Set `FLASK_ENV=production` and `DEBUG=false`
4. **Monitoring**: Implement logging and monitoring solutions
5. **Scaling**: Consider using production WSGI servers like Gunicorn

## Troubleshooting

### Common Issues:

**Docker not starting:**
- Ensure Docker Desktop is running (Windows/Mac)
- Check Docker daemon status (Linux): `sudo systemctl status docker`

**Database connection errors:**
- Verify database credentials in `.env`
- Ensure database server is accessible
- Check firewall settings for database port

**Migration failures:**
- Ensure database exists and user has appropriate permissions
- Check database connection before running migrations
- Review migration files for syntax errors

**Port conflicts:**
- Change `FLASK_PORT` in `.env` if port 5000 is in use
- Update port mapping in `docker-compose.yml` if needed

### Getting Help:

1. Check application logs: `docker-compose logs flask_api`
2. Verify environment configuration in `.env`
3. Ensure all required services are running: `docker-compose ps`
4. Test database connectivity independently