"""
Utilidad para detectar conexión a Firebase y manejar modo offline.
"""
from __future__ import annotations

import os
from typing import Optional

try:
    from google.cloud import firestore
    from google.api_core import exceptions as firestore_exceptions
    FIRESTORE_AVAILABLE = True
except ImportError:
    FIRESTORE_AVAILABLE = False


def check_firestore_connection(client) -> bool:
    """
    Verifica si hay conexión activa a Firestore.
    
    Args:
        client: Cliente de Firestore
        
    Returns:
        True si hay conexión, False si no
    """
    if not FIRESTORE_AVAILABLE or client is None:
        return False
    
    try:
        # Intentar una operación simple para verificar conexión
        # Usamos settings que es una colección pequeña
        test_collection = client.collection('settings')
        list(test_collection.limit(1).stream())
        return True
    except Exception as e:
        # Cualquier excepción indica que no hay conexión
        print(f"⚠ Sin conexión a Firestore: {e}")
        return False


def get_offline_adapter():
    """
    Obtiene un adaptador para modo offline usando el respaldo más reciente.
    
    Returns:
        OfflineDataAdapter o None si no hay respaldos
    """
    from app.core.firestore_backup import FirestoreBackupManager, OfflineDataAdapter
    
    backup_manager = FirestoreBackupManager()
    backups = backup_manager.list_backups()
    
    if not backups:
        print("❌ No hay respaldos disponibles para modo offline")
        return None
    
    # Usar el respaldo más reciente
    latest_backup = backups[0]
    print(f"📴 Usando respaldo del {latest_backup['created_str']} para modo offline")
    
    return OfflineDataAdapter(latest_backup["path"])


def initialize_database_with_fallback(db_client=None):
    """
    Inicializa la base de datos con fallback automático a modo offline.
    
    Args:
        db_client: Cliente de Firestore opcional
        
    Returns:
        Tupla (DatabaseAdapter, is_online)
    """
    from app.core.db_adapter_selector import get_database_adapter
    
    backend = os.getenv("APP_DB_BACKEND", "firestore")
    
    if backend != "firestore":
        # Para otros backends, usar el adaptador normal
        adapter = get_database_adapter(db_client=db_client)
        adapter.open()
        return adapter, True
    
    # Para Firestore, intentar conexión
    try:
        adapter = get_database_adapter(db_client=db_client)
        adapter.open()
        
        # Verificar si realmente hay conexión
        if hasattr(adapter, '_client') and adapter._client:
            if check_firestore_connection(adapter._client):
                print("✅ Conectado a Firebase Firestore")
                return adapter, True
        
        # Si llegamos aquí, no hay conexión real
        raise ConnectionError("No se pudo verificar conexión a Firestore")
        
    except Exception as e:
        print(f"⚠ No se pudo conectar a Firestore: {e}")
        print("📴 Intentando modo offline con respaldo local...")
        
        # Intentar usar modo offline
        offline_adapter = get_offline_adapter()
        
        if offline_adapter is None:
            raise ConnectionError(
                "No hay conexión a Firestore y no hay respaldos locales disponibles.\n\n"
                "Para trabajar sin conexión, primero debe crear un respaldo local "
                "cuando tenga conexión a internet."
            )
        
        # Crear un adaptador que use los datos offline
        from app.core.db_adapter_offline import OfflineDatabaseAdapter
        adapter = OfflineDatabaseAdapter(offline_adapter)
        
        print("📴 Modo offline activado - usando respaldo local")
        return adapter, False
