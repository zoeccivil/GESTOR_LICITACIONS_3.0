"""
Firebase Firestore Backup Module - Respaldo automático local

Este módulo maneja el respaldo automático diario de la base de datos Firebase Firestore
a archivos JSON locales, permitiendo trabajo offline y recuperación de datos.

Características:
- Backup automático diario de todas las colecciones
- Almacenamiento en formato JSON comprimido
- Modo offline: usar respaldo local cuando no hay conexión
- Restauración desde respaldos locales
- Limpieza automática de respaldos antiguos
"""
from __future__ import annotations

import os
import json
import gzip
import datetime
import shutil
from typing import Any, Dict, List, Optional
from pathlib import Path
import threading
import time

try:
    from google.cloud import firestore
    from google.api_core import exceptions as firestore_exceptions
    FIRESTORE_AVAILABLE = True
except ImportError:
    FIRESTORE_AVAILABLE = False


class FirestoreBackupManager:
    """Gestor de respaldos locales de Firebase Firestore."""
    
    def __init__(self, backup_dir: str = "backups/firestore"):
        """
        Inicializa el gestor de respaldos.
        
        Args:
            backup_dir: Directorio donde almacenar los respaldos
        """
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Archivo para el último respaldo (usado en modo offline)
        self.current_backup_file = self.backup_dir / "current_backup.json.gz"
        
        # Configuración de auto-backup
        self.auto_backup_enabled = False
        self.backup_thread: Optional[threading.Thread] = None
        self.backup_interval_hours = 24  # Backup diario por defecto
        
    def create_backup(self, firestore_client) -> str:
        """
        Crea un respaldo completo de todas las colecciones de Firestore.
        
        Args:
            firestore_client: Cliente de Firestore
            
        Returns:
            Ruta del archivo de respaldo creado
        """
        if not FIRESTORE_AVAILABLE:
            raise ImportError("firebase-admin no está instalado")
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = self.backup_dir / f"backup_{timestamp}.json.gz"
        
        # Colecciones a respaldar
        collections_to_backup = [
            "licitaciones",
            "empresas_maestras",
            "instituciones_maestras",
            "documentos_maestros",
            "competidores_maestros",
            "responsables_maestros",
            "fallas_fase_a",
            "subsanaciones_eventos",
            "tasks",
            "audits",
            "competitors",
            "settings"
        ]
        
        backup_data = {
            "timestamp": timestamp,
            "created_at": datetime.datetime.now().isoformat(),
            "collections": {}
        }
        
        # Respaldar cada colección
        for collection_name in collections_to_backup:
            try:
                collection_data = []
                collection_ref = firestore_client.collection(collection_name)
                docs = collection_ref.stream()
                
                for doc in docs:
                    doc_data = doc.to_dict()
                    doc_data['_id'] = doc.id
                    collection_data.append(doc_data)
                
                backup_data["collections"][collection_name] = collection_data
                print(f"✓ Respaldados {len(collection_data)} documentos de {collection_name}")
                
            except Exception as e:
                print(f"⚠ Error al respaldar {collection_name}: {e}")
                backup_data["collections"][collection_name] = []
        
        # Guardar como JSON comprimido
        with gzip.open(backup_filename, 'wt', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False, default=str)
        
        # Actualizar el respaldo actual (para modo offline)
        shutil.copy(backup_filename, self.current_backup_file)
        
        # Limpiar respaldos antiguos (mantener últimos 30 días)
        self._cleanup_old_backups(days_to_keep=30)
        
        file_size = backup_filename.stat().st_size / (1024 * 1024)  # MB
        print(f"✅ Respaldo creado: {backup_filename.name} ({file_size:.2f} MB)")
        
        return str(backup_filename)
    
    def load_backup(self, backup_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Carga un respaldo desde archivo.
        
        Args:
            backup_file: Ruta del archivo de respaldo. Si es None, usa el último respaldo.
            
        Returns:
            Datos del respaldo
        """
        if backup_file is None:
            # Usar el respaldo actual (más reciente)
            backup_file = str(self.current_backup_file)
            
            if not self.current_backup_file.exists():
                # Buscar el respaldo más reciente
                backups = self.list_backups()
                if not backups:
                    raise FileNotFoundError("No hay respaldos disponibles")
                backup_file = backups[0]["path"]
        
        print(f"📂 Cargando respaldo desde: {Path(backup_file).name}")
        
        with gzip.open(backup_file, 'rt', encoding='utf-8') as f:
            data = json.load(f)
        
        total_docs = sum(len(docs) for docs in data["collections"].values())
        print(f"✓ Respaldo cargado: {total_docs} documentos totales")
        
        return data
    
    def restore_from_backup(self, firestore_client, backup_file: Optional[str] = None, 
                          merge: bool = True) -> Dict[str, int]:
        """
        Restaura datos desde un respaldo a Firestore.
        
        Args:
            firestore_client: Cliente de Firestore
            backup_file: Archivo de respaldo a restaurar
            merge: Si True, mezcla con datos existentes. Si False, sobrescribe.
            
        Returns:
            Diccionario con estadísticas de restauración
        """
        if not FIRESTORE_AVAILABLE:
            raise ImportError("firebase-admin no está instalado")
        
        backup_data = self.load_backup(backup_file)
        
        stats = {
            "collections_restored": 0,
            "documents_restored": 0,
            "errors": 0
        }
        
        for collection_name, documents in backup_data["collections"].items():
            if not documents:
                continue
            
            try:
                collection_ref = firestore_client.collection(collection_name)
                
                for doc_data in documents:
                    doc_id = doc_data.pop('_id', None)
                    if not doc_id:
                        continue
                    
                    try:
                        if merge:
                            collection_ref.document(doc_id).set(doc_data, merge=True)
                        else:
                            collection_ref.document(doc_id).set(doc_data)
                        stats["documents_restored"] += 1
                    except Exception as e:
                        print(f"⚠ Error al restaurar documento {doc_id}: {e}")
                        stats["errors"] += 1
                
                stats["collections_restored"] += 1
                print(f"✓ Restaurada colección {collection_name}: {len(documents)} documentos")
                
            except Exception as e:
                print(f"⚠ Error al restaurar colección {collection_name}: {e}")
                stats["errors"] += 1
        
        print(f"✅ Restauración completada: {stats['documents_restored']} documentos")
        return stats
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """
        Lista todos los respaldos disponibles.
        
        Returns:
            Lista de respaldos ordenados por fecha (más reciente primero)
        """
        backups = []
        
        for backup_file in self.backup_dir.glob("backup_*.json.gz"):
            stat = backup_file.stat()
            backups.append({
                "path": str(backup_file),
                "filename": backup_file.name,
                "size_mb": stat.st_size / (1024 * 1024),
                "created": datetime.datetime.fromtimestamp(stat.st_mtime),
                "created_str": datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            })
        
        # Ordenar por fecha de creación (más reciente primero)
        backups.sort(key=lambda x: x["created"], reverse=True)
        
        return backups
    
    def _cleanup_old_backups(self, days_to_keep: int = 30):
        """
        Elimina respaldos antiguos.
        
        Args:
            days_to_keep: Número de días de respaldos a mantener
        """
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_to_keep)
        
        deleted_count = 0
        for backup_file in self.backup_dir.glob("backup_*.json.gz"):
            stat = backup_file.stat()
            file_date = datetime.datetime.fromtimestamp(stat.st_mtime)
            
            if file_date < cutoff_date:
                try:
                    backup_file.unlink()
                    deleted_count += 1
                except Exception as e:
                    print(f"⚠ Error al eliminar {backup_file.name}: {e}")
        
        if deleted_count > 0:
            print(f"🗑️ Eliminados {deleted_count} respaldos antiguos")
    
    def start_auto_backup(self, firestore_client, interval_hours: int = 24):
        """
        Inicia el respaldo automático en segundo plano.
        
        Args:
            firestore_client: Cliente de Firestore
            interval_hours: Intervalo en horas entre respaldos
        """
        if self.auto_backup_enabled:
            print("⚠ El respaldo automático ya está en ejecución")
            return
        
        self.backup_interval_hours = interval_hours
        self.auto_backup_enabled = True
        
        def backup_loop():
            print(f"🔄 Respaldo automático iniciado (cada {interval_hours} horas)")
            
            while self.auto_backup_enabled:
                try:
                    # Crear respaldo
                    self.create_backup(firestore_client)
                    print(f"⏰ Próximo respaldo en {interval_hours} horas")
                    
                    # Esperar hasta el próximo respaldo
                    time.sleep(interval_hours * 3600)
                    
                except Exception as e:
                    print(f"⚠ Error en respaldo automático: {e}")
                    # Esperar 1 hora antes de reintentar en caso de error
                    time.sleep(3600)
        
        self.backup_thread = threading.Thread(target=backup_loop, daemon=True)
        self.backup_thread.start()
    
    def stop_auto_backup(self):
        """Detiene el respaldo automático."""
        if self.auto_backup_enabled:
            self.auto_backup_enabled = False
            print("⏹️ Respaldo automático detenido")
    
    def get_backup_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de los respaldos.
        
        Returns:
            Diccionario con estadísticas
        """
        backups = self.list_backups()
        
        if not backups:
            return {
                "total_backups": 0,
                "total_size_mb": 0,
                "oldest_backup": None,
                "newest_backup": None
            }
        
        total_size = sum(b["size_mb"] for b in backups)
        
        return {
            "total_backups": len(backups),
            "total_size_mb": round(total_size, 2),
            "oldest_backup": backups[-1]["created_str"],
            "newest_backup": backups[0]["created_str"],
            "auto_backup_enabled": self.auto_backup_enabled,
            "backup_interval_hours": self.backup_interval_hours
        }


class OfflineDataAdapter:
    """Adaptador para usar respaldos locales cuando no hay conexión a Firestore."""
    
    def __init__(self, backup_file: str):
        """
        Inicializa el adaptador offline.
        
        Args:
            backup_file: Ruta del archivo de respaldo a usar
        """
        self.backup_manager = FirestoreBackupManager()
        self.data = self.backup_manager.load_backup(backup_file)
        self.collections = self.data["collections"]
        print(f"📴 Modo offline activado - usando respaldo del {self.data.get('created_at', 'desconocido')}")
    
    def get_all(self, collection: str) -> List[Dict[str, Any]]:
        """Obtiene todos los documentos de una colección."""
        docs = self.collections.get(collection, [])
        # Restaurar el campo 'id' desde '_id'
        return [
            {**doc, "id": doc.get("_id", "")}
            for doc in docs
        ]
    
    def get_by_id(self, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene un documento por ID."""
        docs = self.collections.get(collection, [])
        for doc in docs:
            if doc.get("_id") == doc_id:
                return {**doc, "id": doc_id}
        return None
    
    def is_offline_mode(self) -> bool:
        """Indica que está en modo offline."""
        return True
