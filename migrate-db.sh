#!/usr/bin/env bash
set -e

echo "Introduce el mensaje de la migracion (ej.: add prize to Challenge):"
read -r MSG

# Si no pones mensaje, ponemos uno por defecto
if [ -z "$MSG" ]; then
  MSG="cambio sin descripcion"
fi

# Quita comillas dobles para no romper el comando en la shell del contenedor
MSG="${MSG//\"/}"

echo
echo "Aplicando migracion con mensaje: $MSG"
echo

# Asegura que el contenedor esta levantado
docker compose up -d flask_api >/dev/null 2>&1 || true

# Pasamos el mensaje como variable de entorno al contenedor para evitar problemas de comillas
if ! docker compose exec -e MIG_MSG="$MSG" -w /app flask_api sh -lc 'flask db migrate -m "$MIG_MSG" && flask db upgrade'; then
  ERR=$?
  echo
  echo "ERROR: la migracion fallo. Codigo $ERR."
  exit $ERR
fi

echo
echo "Migracion aplicada correctamente."
exit 0
