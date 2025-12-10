@echo off
REM Script de backup para PostgreSQL en Windows
REM Uso: backup_pg.bat [nombre_backup]

setlocal enabledelayedexpansion

REM Cargar variables de entorno desde .env si existe
if exist .env (
    for /f "tokens=1,2 delims==" %%a in (.env) do (
        if not "%%a"=="" if not "%%a:~0,1%"=="#" (
            set %%a=%%b
        )
    )
)

REM Configuración por defecto
if not defined DB_HOST set DB_HOST=127.0.0.1
if not defined DB_PORT set DB_PORT=5432
if not defined DB_NAME set DB_NAME=zoec_db
if not defined DB_USER set DB_USER=zoec_app
if not defined BACKUP_DIR set BACKUP_DIR=backups

REM Crear directorio de backups si no existe
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

REM Nombre del backup
if "%~1"=="" (
    for /f "tokens=2-4 delims=/ " %%a in ('date /t') do set FECHA=%%c%%b%%a
    for /f "tokens=1-2 delims=: " %%a in ('time /t') do set HORA=%%a%%b
    set BACKUP_NAME=zoec_db_!FECHA!_!HORA!.dump
) else (
    set BACKUP_NAME=%~1
)

set BACKUP_PATH=%BACKUP_DIR%\%BACKUP_NAME%

echo ==========================================
echo Backup de PostgreSQL
echo ==========================================
echo Host:     %DB_HOST%:%DB_PORT%
echo Database: %DB_NAME%
echo Usuario:  %DB_USER%
echo Destino:  %BACKUP_PATH%
echo ==========================================
echo.

REM Ejecutar pg_dump
echo Iniciando backup...

REM Buscar pg_dump en las ubicaciones comunes
set PG_DUMP=pg_dump.exe
if exist "C:\Program Files\PostgreSQL\16\bin\pg_dump.exe" (
    set PG_DUMP=C:\Program Files\PostgreSQL\16\bin\pg_dump.exe
)
if exist "C:\Program Files\PostgreSQL\15\bin\pg_dump.exe" (
    set PG_DUMP=C:\Program Files\PostgreSQL\15\bin\pg_dump.exe
)

"%PG_DUMP%" -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -F c -b -v -f "%BACKUP_PATH%" %DB_NAME%

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✓ Backup completado exitosamente
    echo   Archivo: %BACKUP_PATH%
    
    REM Limpiar backups antiguos (mantener últimos 10)
    echo.
    echo Limpiando backups antiguos (manteniendo últimos 10)...
    for /f "skip=10 delims=" %%i in ('dir /b /o-d "%BACKUP_DIR%\*.dump" 2^>nul') do (
        echo Eliminando: %%i
        del "%BACKUP_DIR%\%%i"
    )
    
    echo.
    echo ✓ Proceso completado
) else (
    echo.
    echo ✗ Error al crear el backup
    exit /b 1
)

endlocal
