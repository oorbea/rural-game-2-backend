@echo off
setlocal

set SERVICE=backend
set DETACH=-d

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

REM 4) Verificar que el servicio backend existe en el compose
docker-compose config --services | findstr /R /C:"^%SERVICE%$" >nul
IF ERRORLEVEL 1 (
    echo El servicio "%SERVICE%" no existe en docker-compose.yml.
    pause
    exit /b 1
)

REM 5) Levantar el backend
echo Starting "%SERVICE%" service...
docker-compose up %DETACH% %SERVICE%
IF %ERRORLEVEL% EQU 0 (
    echo Service "%SERVICE%" started successfully!
) ELSE (
    echo ERROR: There was a problem starting the "%SERVICE%" service.
)

endlocal
pause
