@echo off
setlocal

REM 1. Comprobar si Docker está instalado
where docker >nul 2>&1
IF ERRORLEVEL 1 (
    echo Docker no esta instalado o no esta en el PATH.
    echo Por favor, instala Docker Desktop desde https://www.docker.com/products/docker-desktop/
    start https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)

REM 2. Comprobar si Docker Desktop esta ejecutandose
docker info >nul 2>&1
IF ERRORLEVEL 1 (
    echo Docker no se esta ejecutando.
    echo Por favor, inicia Docker Desktop y vuelve a ejecutar este script.
    pause
    exit /b 1
)

REM 3. Parar los contenedores solo si hay activos
docker-compose ps -q >nul 2>&1
IF ERRORLEVEL 1 (
    echo docker-compose no esta disponible.
    pause
    exit /b 1
)
set FOUND=
for /f "delims=" %%i in ('docker-compose ps -q') do set FOUND=1

if defined FOUND (
    echo Stopping and removing project containers...
    docker-compose down
) else (
    echo No project containers are running. Skipping stop step.
)

REM 4. Build y up
echo Building and starting the containers...
docker-compose up --build
IF %ERRORLEVEL% EQU 0 (
    echo Containers rebuilt and started successfully!
) else (
    echo ERROR: There was a problem building or starting the containers.
)

endlocal
pause
