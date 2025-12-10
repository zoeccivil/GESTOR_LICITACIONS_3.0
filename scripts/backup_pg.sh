#!/bin/bash

# Script de backup para PostgreSQL
# Uso: ./backup_pg.sh [nombre_backup]

set -e

# Cargar variables de entorno
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Configuración por defecto
DB_HOST=${DB_HOST:-127.0.0.1}
DB_PORT=${DB_PORT:-5432}
DB_NAME=${DB_NAME:-zoec_db}
DB_USER=${DB_USER:-zoec_app}
BACKUP_DIR=${BACKUP_DIR:-./backups}

# Crear directorio de backups si no existe
mkdir -p "$BACKUP_DIR"

# Nombre del backup
if [ -z "$1" ]; then
    BACKUP_NAME="zoec_db_$(date +%Y%m%d_%H%M%S).dump"
else
    BACKUP_NAME="$1"
fi

BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"

echo "=========================================="
echo "Backup de PostgreSQL"
echo "=========================================="
echo "Host:     $DB_HOST:$DB_PORT"
echo "Database: $DB_NAME"
echo "Usuario:  $DB_USER"
echo "Destino:  $BACKUP_PATH"
echo "=========================================="
echo ""

# Ejecutar pg_dump
echo "Iniciando backup..."
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -F c -b -v -f "$BACKUP_PATH" "$DB_NAME"

if [ $? -eq 0 ]; then
    SIZE=$(du -h "$BACKUP_PATH" | cut -f1)
    echo ""
    echo "✓ Backup completado exitosamente"
    echo "  Archivo: $BACKUP_PATH"
    echo "  Tamaño:  $SIZE"
    
    # Mantener solo los últimos 10 backups
    echo ""
    echo "Limpiando backups antiguos (manteniendo últimos 10)..."
    ls -t "$BACKUP_DIR"/*.dump 2>/dev/null | tail -n +11 | xargs -r rm -v
    
    echo ""
    echo "✓ Proceso completado"
else
    echo ""
    echo "✗ Error al crear el backup"
    exit 1
fi
