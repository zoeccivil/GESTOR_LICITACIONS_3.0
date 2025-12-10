@echo off
REM Script de backup para MySQL en Windows
REM Crea un respaldo de la base de datos usando mysqldump

setlocal enabledelayedexpansion

REM Leer variables de .env si existe
if exist .env (
    for /f "usebackq tokens=1,2 delims==" %%a in (".env") do (
        set %%a=%%b
    )
)

REM Configuración por defecto
if not defined DB_HOST set DB_HOST=127.0.0.1
if not defined DB_PORT set DB_PORT=3306
if not defined DB_NAME set DB_NAME=zoec_db
if not defined DB_USER set DB_USER=zoec_app
if not defined DB_PASSWORD set DB_PASSWORD=CambiaEstaClave

REM Directorio de backups
set BACKUP_DIR=backups
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

REM Nombre del archivo con fecha y hora
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set MYDATE=%%c%%a%%b)
for /f "tokens=1-2 delims=/: " %%a in ('time /t') do (set MYTIME=%%a%%b)
set TIMESTAMP=%MYDATE%_%MYTIME%
set BACKUP_FILE=%BACKUP_DIR%\mysql_backup_%TIMESTAMP%.sql

echo ======================================================================
echo Backup de MySQL
echo ======================================================================
echo Base de datos: %DB_NAME%
echo Servidor: %DB_HOST%:%DB_PORT%
echo Archivo: %BACKUP_FILE%
echo ======================================================================

REM Verificar si Docker está disponible
docker ps >nul 2>&1
if %errorlevel% == 0 (
    REM Usar Docker si está disponible
    echo Usando contenedor Docker...
    docker exec zoec_mysql mysqldump -u%DB_USER% -p%DB_PASSWORD% --single-transaction --routines --triggers --events %DB_NAME% > "%BACKUP_FILE%"
) else (
    REM Usar mysqldump local
    echo Usando mysqldump local...
    mysqldump -h%DB_HOST% -P%DB_PORT% -u%DB_USER% -p%DB_PASSWORD% --single-transaction --routines --triggers --events %DB_NAME% > "%BACKUP_FILE%"
)

if %errorlevel% == 0 (
    echo.
    echo Backup creado exitosamente: %BACKUP_FILE%
    
    REM Limpiar backups antiguos (mantener últimos 7)
    for /f "skip=7 delims=" %%F in ('dir /b /o-d "%BACKUP_DIR%\mysql_backup_*.sql" 2^>nul') do (
        del "%BACKUP_DIR%\%%F"
    )
    echo Backups antiguos limpiados
) else (
    echo.
    echo Error al crear backup
    exit /b 1
)

echo ======================================================================
endlocal
