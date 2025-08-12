@echo off
setlocal ENABLEDELAYEDEXPANSION

echo Introduce el mensaje de la migracion (ej.: add prize to Challenge):
set /p MSG="> "

rem Si no pones mensaje, ponemos uno por defecto
if "%MSG%"=="" set "MSG=cambio sin descripcion"

rem Quita comillas dobles para no romper el comando en la shell del contenedor
set "MSG=%MSG:"=%"

echo.
echo Aplicando migracion con mensaje: %MSG%
echo.

rem Asegura que el contenedor esta levantado
docker compose up -d flask_api >nul 2>&1

rem Pasamos el mensaje como variable de entorno al contenedor para evitar problemas de comillas
docker compose exec -e MIG_MSG=%MSG% -w /app flask_api sh -lc "flask db migrate -m \"$MIG_MSG\" && flask db upgrade"
set ERR=%ERRORLEVEL%

if %ERR% neq 0 (
  echo.
  echo ERROR: la migracion fallo. Codigo %ERR%.
  exit /b %ERR%
)

echo.
echo Migracion aplicada correctamente.
exit /b 0
