#!/usr/bin/env python3
"""
Script to generate PostgreSQL schema from SQLite schema.

This script analyzes the existing SQLite database and generates
the SQL statements needed to create an equivalent PostgreSQL schema.
"""

import sqlite3
import json
import re
from pathlib import Path
from typing import List, Dict, Any


# Type mapping from SQLite to PostgreSQL
TYPE_MAPPING = {
    'INTEGER': 'INTEGER',
    'TEXT': 'TEXT',
    'REAL': 'REAL',
    'BOOLEAN': 'BOOLEAN',
    'BLOB': 'BYTEA',
}


def sqlite_type_to_postgres(sqlite_type: str, is_pk: bool = False, is_autoincrement: bool = False) -> str:
    """Convert SQLite type to PostgreSQL type."""
    sqlite_type = sqlite_type.upper()
    
    # Handle PRIMARY KEY AUTOINCREMENT -> SERIAL
    if is_pk and is_autoincrement and 'INTEGER' in sqlite_type:
        return 'SERIAL'
    
    # Map basic types
    for sqlite, postgres in TYPE_MAPPING.items():
        if sqlite in sqlite_type:
            return postgres
    
    # Default to TEXT if unknown
    return 'TEXT'


def extract_table_names(db_path: str) -> List[str]:
    """Get all table names from SQLite database, excluding FTS and system tables."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        AND name NOT LIKE 'sqlite_%'
        AND name NOT LIKE 'fts_%'
        ORDER BY name
    """)
    
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    return tables


def get_table_schema(db_path: str, table_name: str) -> Dict[str, Any]:
    """Get detailed schema information for a table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get column info
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = []
    for row in cursor.fetchall():
        columns.append({
            'cid': row[0],
            'name': row[1],
            'type': row[2],
            'notnull': row[3],
            'default': row[4],
            'pk': row[5]
        })
    
    # Get foreign keys
    cursor.execute(f"PRAGMA foreign_key_list({table_name})")
    foreign_keys = []
    for row in cursor.fetchall():
        foreign_keys.append({
            'id': row[0],
            'seq': row[1],
            'table': row[2],
            'from': row[3],
            'to': row[4],
            'on_update': row[5],
            'on_delete': row[6]
        })
    
    # Get indexes
    cursor.execute(f"PRAGMA index_list({table_name})")
    indexes = []
    for row in cursor.fetchall():
        index_name = row[1]
        is_unique = row[2]
        
        # Skip auto-generated indexes
        if index_name.startswith('sqlite_autoindex'):
            continue
        
        # Get index columns
        cursor.execute(f"PRAGMA index_info({index_name})")
        index_columns = [r[2] for r in cursor.fetchall()]
        
        indexes.append({
            'name': index_name,
            'unique': is_unique,
            'columns': index_columns
        })
    
    conn.close()
    
    return {
        'columns': columns,
        'foreign_keys': foreign_keys,
        'indexes': indexes
    }


def generate_create_table_sql(table_name: str, schema: Dict[str, Any]) -> str:
    """Generate PostgreSQL CREATE TABLE statement."""
    lines = [f"CREATE TABLE {table_name} ("]
    
    column_defs = []
    pk_columns = []
    
    # Process columns
    for col in schema['columns']:
        parts = [f"    {col['name']}"]
        
        # Type
        pg_type = sqlite_type_to_postgres(
            col['type'],
            is_pk=col['pk'] > 0,
            is_autoincrement=True  # Assume all INTEGER PKs are autoincrement
        )
        parts.append(pg_type)
        
        # Primary key (for SERIAL)
        if col['pk'] > 0 and pg_type == 'SERIAL':
            parts.append("PRIMARY KEY")
            pk_columns.append(col['name'])
        
        # NOT NULL
        elif col['notnull'] and col['pk'] == 0:
            parts.append("NOT NULL")
        
        # DEFAULT
        if col['default'] is not None and pg_type != 'SERIAL':
            default_val = col['default']
            # Convert boolean defaults
            if default_val in ('0', '1'):
                default_val = 'FALSE' if default_val == '0' else 'TRUE'
            # Quote text defaults
            elif not default_val.replace('.', '').replace('-', '').isdigit():
                default_val = f"'{default_val}'"
            parts.append(f"DEFAULT {default_val}")
        
        column_defs.append(" ".join(parts))
    
    lines.extend(f"{col_def}," for col_def in column_defs)
    
    # Add foreign keys
    for fk in schema['foreign_keys']:
        fk_def = f"    FOREIGN KEY ({fk['from']}) REFERENCES {fk['table']} ({fk['to']})"
        if fk['on_delete'] != 'NO ACTION':
            fk_def += f" ON DELETE {fk['on_delete']}"
        if fk['on_update'] != 'NO ACTION':
            fk_def += f" ON UPDATE {fk['on_update']}"
        lines.append(fk_def + ",")
    
    # Remove trailing comma from last item
    if lines[-1].endswith(','):
        lines[-1] = lines[-1][:-1]
    
    lines.append(");")
    
    return "\n".join(lines)


def generate_create_indexes_sql(table_name: str, schema: Dict[str, Any]) -> List[str]:
    """Generate CREATE INDEX statements."""
    statements = []
    
    for idx in schema['indexes']:
        unique = "UNIQUE " if idx['unique'] else ""
        columns = ", ".join(idx['columns'])
        sql = f"CREATE {unique}INDEX {idx['name']} ON {table_name} ({columns});"
        statements.append(sql)
    
    return statements


def generate_migration_sql(db_path: str) -> str:
    """Generate complete migration SQL."""
    sql_parts = []
    
    sql_parts.append("-- Migration from SQLite to PostgreSQL")
    sql_parts.append("-- Generated automatically from existing schema")
    sql_parts.append("")
    
    # Get all tables
    tables = extract_table_names(db_path)
    
    print(f"Found {len(tables)} tables to migrate:")
    for table in tables:
        print(f"  - {table}")
    
    # Generate CREATE TABLE statements
    for table_name in tables:
        schema = get_table_schema(db_path, table_name)
        
        sql_parts.append(f"\n-- Table: {table_name}")
        sql_parts.append(generate_create_table_sql(table_name, schema))
        
        # Generate indexes
        index_sqls = generate_create_indexes_sql(table_name, schema)
        for index_sql in index_sqls:
            sql_parts.append(index_sql)
    
    return "\n".join(sql_parts)


def main():
    """Main function."""
    db_path = Path(__file__).parent.parent / "LICITACIONES_GENERALES.db"
    
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return
    
    print(f"Analyzing SQLite database: {db_path}")
    print("")
    
    sql = generate_migration_sql(str(db_path))
    
    # Save to file
    output_path = Path(__file__).parent / "schema_migration.sql"
    output_path.write_text(sql)
    
    print("")
    print(f"✓ Migration SQL generated: {output_path}")
    print("")
    print("Next steps:")
    print("1. Review the generated SQL file")
    print("2. Create an Alembic migration:")
    print("   alembic revision -m 'initial_schema'")
    print("3. Copy the SQL to the migration file's upgrade() function")


if __name__ == "__main__":
    main()
