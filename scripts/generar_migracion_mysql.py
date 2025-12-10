#!/usr/bin/env python3
"""
Script para generar migración de Alembic para MySQL desde esquema SQLite.
"""

import sqlite3
import sys
from pathlib import Path

# Agregar raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

def get_sqlite_schema(db_path):
    """Obtener esquema desde SQLite"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Obtener todas las tablas (excepto FTS y schema_migrations)
    cursor.execute("""
        SELECT name, sql FROM sqlite_master 
        WHERE type='table' 
        AND name NOT LIKE 'fts_%'
        AND name NOT LIKE 'sqlite_%'
        AND name != 'schema_migrations'
        ORDER BY name
    """)
    
    tables = {}
    for name, sql in cursor.fetchall():
        tables[name] = sql
    
    conn.close()
    return tables

def convert_to_mysql(sqlite_sql):
    """Convertir SQL de SQLite a MySQL"""
    if not sqlite_sql:
        return None
    
    # Reemplazos básicos
    mysql_sql = sqlite_sql
    
    # AUTOINCREMENT → AUTO_INCREMENT
    mysql_sql = mysql_sql.replace('AUTOINCREMENT', 'AUTO_INCREMENT')
    
    # INTEGER PRIMARY KEY → INT AUTO_INCREMENT PRIMARY KEY
    mysql_sql = mysql_sql.replace('INTEGER PRIMARY KEY', 'INT AUTO_INCREMENT PRIMARY KEY')
    
    # Tipos de datos
    mysql_sql = mysql_sql.replace(' TEXT', ' VARCHAR(500)')
    mysql_sql = mysql_sql.replace(' REAL', ' DECIMAL(15,2)')
    mysql_sql = mysql_sql.replace(' BLOB', ' LONGBLOB')
    
    # DEFAULT CURRENT_TIMESTAMP
    mysql_sql = mysql_sql.replace("DEFAULT CURRENT_TIMESTAMP", "DEFAULT CURRENT_TIMESTAMP")
    
    return mysql_sql

def generate_migration(tables):
    """Generar código de migración Alembic"""
    
    revision_id = 'a1b2c3d4e5f6'
    
    migration_code = f'''"""Migración inicial del esquema MySQL

Revision ID: {revision_id}
Revises: 
Create Date: 2025-11-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '{revision_id}'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Actualizar esquema - crear todas las tablas."""
    
'''
    
    # Orden de tablas (maestras primero)
    table_order = [
        'config_app', 'categorias', 'subcategorias', 'cuentas',
        'instituciones_maestras', 'empresas_maestras', 'competidores_maestros',
        'responsables_maestros', 'criterios_bnb', 'documentos_maestros',
        'kits_de_requisitos', 'kit_items', 'backups_log',
        'proyectos', 'proyecto_cuentas', 'presupuestos', 'transacciones',
        'licitaciones', 'licitacion_empresas_nuestras', 
        'lotes', 'documentos', 'oferentes', 'ofertas_lote_oferentes',
        'licitacion_ganadores_lote', 'ganadores_canonicos', 'historial_ganadores',
        'bnb_evaluaciones', 'descalificaciones_fase_a', 'subsanacion_historial',
        'expedientes', 'expediente_items', 'riesgos'
    ]
    
    for table_name in table_order:
        if table_name in tables:
            migration_code += f"    # Tabla: {table_name}\n"
            mysql_sql = convert_to_mysql(tables[table_name])
            if mysql_sql:
                # Extraer CREATE TABLE
                migration_code += f'    op.execute("""\n{mysql_sql}\n    """)\n\n'
    
    migration_code += '''

def downgrade():
    """Revertir esquema - eliminar todas las tablas."""
    
'''
    
    # Agregar DROP TABLE en orden inverso
    for table_name in reversed(table_order):
        if table_name in tables:
            migration_code += f"    op.drop_table('{table_name}')\n"
    
    return migration_code

def main():
    db_path = 'LICITACIONES_GENERALES.db'
    if not Path(db_path).exists():
        print(f"Error: No se encuentra {db_path}")
        return 1
    
    print("Extrayendo esquema de SQLite...")
    tables = get_sqlite_schema(db_path)
    print(f"Encontradas {len(tables)} tablas")
    
    print("Generando migración para MySQL...")
    migration_code = generate_migration(tables)
    
    # Guardar migración
    output_file = Path('alembic/versions/a1b2c3d4e5f6_initial_mysql_schema.py')
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(migration_code)
    
    print(f"✓ Migración generada: {output_file}")
    print("\nPara aplicar:")
    print("  alembic upgrade head")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
