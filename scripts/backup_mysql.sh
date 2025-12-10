#!/bin/bash
# Script de backup para MySQL
# Crea un respaldo de la base de datos usando mysqldump

# Cargar variables de entorno
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Configuración por defecto
DB_HOST=${DB_HOST:-127.0.0.1}
DB_PORT=${DB_PORT:-3306}
DB_NAME=${DB_NAME:-zoec_db}
DB_USER=${DB_USER:-zoec_app}
DB_PASSWORD=${DB_PASSWORD:-CambiaEstaClave}

# Directorio de backups
BACKUP_DIR="./backups"
mkdir -p "$BACKUP_DIR"

# Nombre del archivo con fecha y hora
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/mysql_backup_$TIMESTAMP.sql.gz"

echo "======================================================================"
echo "Backup de MySQL"
echo "======================================================================"
echo "Base de datos: $DB_NAME"
echo "Servidor: $DB_HOST:$DB_PORT"
echo "Archivo: $BACKUP_FILE"
echo "======================================================================"

# Crear backup usando mysqldump con compresión
if command -v docker &> /dev/null && docker ps | grep -q zoec_mysql; then
    # Si Docker está disponible y el contenedor está corriendo, usar docker exec
    echo "Usando contenedor Docker..."
    docker exec zoec_mysql mysqldump \
        -u"$DB_USER" \
        -p"$DB_PASSWORD" \
        --single-transaction \
        --routines \
        --triggers \
        --events \
        "$DB_NAME" | gzip > "$BACKUP_FILE"
else
    # Usar mysqldump local
    echo "Usando mysqldump local..."
    mysqldump \
        -h"$DB_HOST" \
        -P"$DB_PORT" \
        -u"$DB_USER" \
        -p"$DB_PASSWORD" \
        --single-transaction \
        --routines \
        --triggers \
        --events \
        "$DB_NAME" | gzip > "$BACKUP_FILE"
fi

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Backup creado exitosamente"
    echo "Tamaño: $(du -h "$BACKUP_FILE" | cut -f1)"
    
    # Limpiar backups antiguos (mantener últimos 7 días)
    find "$BACKUP_DIR" -name "mysql_backup_*.sql.gz" -mtime +7 -delete
    echo "✓ Backups antiguos limpiados (>7 días)"
else
    echo ""
    echo "✗ Error al crear backup"
    exit 1
fi

echo "======================================================================"
