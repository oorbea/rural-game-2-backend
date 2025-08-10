@echo off
setlocal

REM === Configuración ===
set "SERVICE_API=flask_api"
set "DETACH=-d"

REM 1) Comprobar si Docker está instalado
where docker >nul 2>&1
IF ERRORLEVEL 1 (
    echo Docker no esta instalado o no esta en el PATH.
    echo Por favor, instala Docker Desktop desde https://www.docker.com/products/docker-desktop/
    start https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)

REM 2) Comprobar si Docker Desktop esta ejecutandose
docker info >nul 2>&1
IF ERRORLEVEL 1 (
    echo Docker no se esta ejecutando.
    echo Por favor, inicia Docker Desktop y vuelve a ejecutar este script.
    pause
    exit /b 1
)

REM 3) Comprobar si docker-compose esta disponible
docker-compose version >nul 2>&1
IF ERRORLEVEL 1 (
    echo docker-compose no esta disponible.
    pause
    exit /b 1
)

REM 4) Levantar phpMyAdmin y el backend en segundo plano (sin reconstruir)
echo Starting "%SERVICE_API%" services in background...
docker-compose up %DETACH% --no-build %SERVICE_API%
IF ERRORLEVEL 1 (
    echo ERROR: There was a problem starting the services.
    pause
    exit /b 1
)

echo Services started successfully!
echo Showing ONLY "%SERVICE_API%" logs (press Ctrl+C to stop)...
echo.
docker-compose logs -f %SERVICE_API%

endlocal
pause
