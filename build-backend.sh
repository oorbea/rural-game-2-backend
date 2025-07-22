#!/bin/bash

set -e

# 1. Comprobar si Docker está instalado
if ! command -v docker >/dev/null 2>&1; then
  echo "Docker no está instalado o no está en el PATH."
  echo "Por favor, instala Docker Desktop o Docker Engine desde https://docs.docker.com/get-docker/"
  xdg-open https://docs.docker.com/get-docker/ 2>/dev/null || echo "Abre manualmente: https://docs.docker.com/get-docker/"
  read -p "Pulsa [Enter] para salir..."
  exit 1
fi

# 2. Comprobar si Docker está en ejecución
if ! docker info >/dev/null 2>&1; then
  echo "Docker no se está ejecutando."
  echo "Por favor, inicia Docker (por ejemplo, 'sudo systemctl start docker') y vuelve a ejecutar este script."
  read -p "Pulsa [Enter] para salir..."
  exit 1
fi

# 3. Comprobar si docker-compose está disponible (soporta tanto 'docker compose' como 'docker-compose')
if command -v docker-compose >/dev/null 2>&1; then
  DOCKER_COMPOSE_CMD="docker-compose"
elif docker compose version >/dev/null 2>&1; then
  DOCKER_COMPOSE_CMD="docker compose"
else
  echo "docker-compose no está instalado ni disponible como plugin."
  echo "Por favor, instala Docker Compose: https://docs.docker.com/compose/install/"
  xdg-open https://docs.docker.com/compose/install/ 2>/dev/null || echo "Abre manualmente: https://docs.docker.com/compose/install/"
  read -p "Pulsa [Enter] para salir..."
  exit 1
fi

# 4. Parar los contenedores solo si hay activos
if $DOCKER_COMPOSE_CMD ps -q | grep -q .; then
  echo "Stopping and removing project containers..."
  $DOCKER_COMPOSE_CMD down
else
  echo "No project containers are running. Skipping stop step."
fi

# 5. Build y up
echo "Building and starting the containers..."
if $DOCKER_COMPOSE_CMD up --build; then
  echo "Containers rebuilt and started successfully!"
else
  echo "ERROR: There was a problem building or starting the containers."
fi

read -p "Pulsa [Enter] para salir..."
