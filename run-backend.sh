#!/usr/bin/env bash
set -euo pipefail

SERVICE="flask_api"
DETACH="-d"

# 1) Comprobar Docker
if ! command -v docker >/dev/null 2>&1; then
  echo "Docker no está instalado o no está en el PATH."
  echo "Instalación: https://docs.docker.com/engine/install/"
  exit 1
fi

# 2) Comprobar que el daemon de Docker está activo
if ! docker info >/dev/null 2>&1; then
  echo "Docker no se está ejecutando. Arráncalo y vuelve a intentarlo."
  exit 1
fi

# 3) Detectar 'docker compose' (nuevo) o 'docker-compose' (legacy)
if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  echo "No se encontró 'docker compose' ni 'docker-compose'."
  exit 1
fi

# 4) Validar que hay un docker-compose.yml válido en el directorio
if ! "${COMPOSE[@]}" config >/dev/null 2>&1; then
  echo "No se encontró un docker-compose.yml válido en el directorio actual."
  exit 1
fi

# 5) Verificar que el servicio backend existe
if ! "${COMPOSE[@]}" config --services | grep -Fxq "$SERVICE"; then
  echo "El servicio \"$SERVICE\" no existe en docker-compose.yml."
  exit 1
fi

# 6) Levantar backend y dependencias en segundo plano
echo "Levantando \"$SERVICE\" y dependencias (sin reconstruir imágenes)..."
if "${COMPOSE[@]}" up $DETACH --no-build "$SERVICE"; then
  echo "Servicio \"$SERVICE\" iniciado en segundo plano."
  echo "Logs: ${COMPOSE[*]} logs -f $SERVICE"
else
  echo "ERROR: No se pudo iniciar \"$SERVICE\"."
  echo "Si la imagen no existe, ejecuta primero el script de build para crearla."
  exit 1
fi
