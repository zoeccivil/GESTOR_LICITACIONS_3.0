"""
Selector de backend de base de datos para la aplicación LICITACIONES.

Este módulo permite seleccionar entre diferentes backends (Firestore, SQLite, MySQL)
mediante variables de entorno, manteniendo compatibilidad con código existente.
"""
from __future__ import annotations

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_database_adapter(db_client=None, db_path: Optional[str] = None):
    """
    Obtiene el adaptador de base de datos según la configuración.
    
    Args:
        db_client: Cliente de Firestore (opcional, para backend Firestore)
        db_path: Ruta a la base de datos SQLite (opcional, para backend SQLite)
    
    Returns:
        Una instancia del adaptador de base de datos apropiado
    
    Ejemplo de uso:
        # En .env:
        # APP_DB_BACKEND=firestore  # o 'sqlite' o 'mysql'
        
        db = get_database_adapter(db_client=firestore_client)
    """
    backend = os.getenv("APP_DB_BACKEND", "firestore").lower()
    
    logger.info(f"Inicializando adaptador de base de datos: {backend}")
    
    if backend == "firestore":
        from app.core.db_adapter import DatabaseAdapter
        adapter = DatabaseAdapter(client=db_client)
        logger.info("Usando backend Firestore")
        return adapter
    
    elif backend == "sqlite":
        from app.core.db_adapter_sqlite import SQLiteDatabaseAdapter
        if not db_path:
            db_path = os.getenv("SQLITE_DB_PATH", "LICITACIONES_GENERALES.db")
        adapter = SQLiteDatabaseAdapter(db_path=db_path)
        logger.info(f"Usando backend SQLite: {db_path}")
        return adapter
    
    elif backend == "mysql":
        from app.core.db_adapter_mysql import DatabaseAdapter as MySQLAdapter
        adapter = MySQLAdapter(db_path=None)  # MySQL usa .env para configuración
        logger.info("Usando backend MySQL")
        return adapter
    
    else:
        logger.warning(f"Backend desconocido '{backend}', usando Firestore por defecto")
        from app.core.db_adapter import DatabaseAdapter
        return DatabaseAdapter(client=db_client)
