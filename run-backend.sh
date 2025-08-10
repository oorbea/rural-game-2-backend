#!/usr/bin/env bash
set -euo pipefail

# Ir al directorio del script (donde está el compose)
cd "$(dirname "${BASH_SOURCE[0]}")"

# === Configuración ===
SERVICE_API="${SERVICE_API:-flask_api}"
DETACH="${DETACH:--d}"      # dejar vacío para primer plano

# 1) Comprobar Docker instalado
if ! command -v docker >/dev/null 2>&1; then
  echo "Docker no está instalado o no está en el PATH."
  echo "Instálalo: https://docs.docker.com/engine/install/"
  exit 1
fi

# 2) Comprobar que el daemon de Docker está en ejecución
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

# 4) Levantar phpMyAdmin y el backend en segundo plano (sin reconstruir)
echo "Starting \"$SERVICE_API\" services in background..."
if ! "${COMPOSE[@]}" up ${DETACH} --no-build "$SERVICE_API"; then
  echo "ERROR: There was a problem starting the services."
  exit 1
fi

echo "Services started successfully!"
echo "Showing ONLY \"$SERVICE_API\" logs (press Ctrl+C to stop)..."
echo

# 5) Mostrar únicamente los logs de flask_api
exec "${COMPOSE[@]}" logs -f "$SERVICE_API"
