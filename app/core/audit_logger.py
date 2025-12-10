"""
Audit Logger Module - Historial y bitácora de cambios

Este módulo registra automáticamente todos los cambios realizados en la aplicación,
manteniendo un historial completo de quién, qué y cuándo se modificó.

Colección Firestore: /audits/{id}
Campos:
- entity: Tipo de entidad (licitacion, documento, etc.)
- entity_id: ID del registro modificado
- action: Acción realizada (create, update, delete)
- old_values: Valores anteriores (dict)
- new_values: Valores nuevos (dict)
- user_id: ID del usuario que realizó la acción
- timestamp: Marca de tiempo
- changes_summary: Resumen de cambios
"""
from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional, Callable
from functools import wraps

from . import firebase_adapter

AUDITS_COLLECTION = "audits"


class AuditLogger:
    """Registrador de auditoría para cambios en Firestore."""

    def __init__(self, user_id: str = "system"):
        self.user_id = user_id

    def log_change(
        self,
        entity: str,
        entity_id: str,
        action: str,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        changes_summary: str = ""
    ) -> str:
        """
        Registra un cambio en el log de auditoría.

        Args:
            entity: Tipo de entidad (ej: 'licitacion', 'documento')
            entity_id: ID del registro modificado
            action: Acción realizada ('create', 'update', 'delete')
            old_values: Valores anteriores (opcional)
            new_values: Valores nuevos (opcional)
            changes_summary: Resumen legible del cambio

        Returns:
            ID del registro de auditoría creado
        """
        audit_data = {
            "entity": entity,
            "entity_id": str(entity_id),
            "action": action,
            "old_values": old_values or {},
            "new_values": new_values or {},
            "user_id": self.user_id,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "changes_summary": changes_summary or self._generate_summary(action, entity),
        }

        return firebase_adapter.add_doc(AUDITS_COLLECTION, audit_data)

    def _generate_summary(self, action: str, entity: str) -> str:
        """Genera un resumen automático del cambio."""
        action_map = {
            "create": "creó",
            "update": "actualizó",
            "delete": "eliminó",
        }
        verb = action_map.get(action, action)
        return f"Usuario {self.user_id} {verb} {entity}"

    def get_history(
        self,
        entity: Optional[str] = None,
        entity_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Obtiene el historial de cambios con filtros opcionales.

        Args:
            entity: Filtrar por tipo de entidad
            entity_id: Filtrar por ID de entidad
            user_id: Filtrar por usuario
            limit: Número máximo de registros a retornar

        Returns:
            Lista de registros de auditoría
        """
        all_audits = firebase_adapter.get_all(AUDITS_COLLECTION)
        
        # Aplicar filtros
        filtered = all_audits
        if entity:
            filtered = [a for a in filtered if a.get("entity") == entity]
        if entity_id:
            filtered = [a for a in filtered if a.get("entity_id") == str(entity_id)]
        if user_id:
            filtered = [a for a in filtered if a.get("user_id") == user_id]

        # Ordenar por timestamp descendente
        filtered.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        return filtered[:limit]

    def get_entity_history(self, entity: str, entity_id: str) -> List[Dict[str, Any]]:
        """Obtiene el historial completo de una entidad específica."""
        return self.get_history(entity=entity, entity_id=entity_id)

    def get_changes_diff(self, audit_entry: Dict[str, Any]) -> List[str]:
        """
        Genera una lista legible de los cambios realizados.

        Args:
            audit_entry: Entrada de auditoría

        Returns:
            Lista de strings describiendo cada cambio
        """
        old = audit_entry.get("old_values", {})
        new = audit_entry.get("new_values", {})
        changes = []

        all_keys = set(old.keys()) | set(new.keys())
        for key in sorted(all_keys):
            old_val = old.get(key)
            new_val = new.get(key)
            
            if old_val != new_val:
                if old_val is None:
                    changes.append(f"+ {key}: {new_val}")
                elif new_val is None:
                    changes.append(f"- {key}: {old_val}")
                else:
                    changes.append(f"~ {key}: {old_val} → {new_val}")

        return changes


def audit_decorator(entity_type: str, action: str = "update"):
    """
    Decorador para registrar automáticamente cambios en métodos.

    Uso:
        @audit_decorator("licitacion", "update")
        def update_licitacion(self, lic_id, data):
            # ... código de actualización
            pass

    Args:
        entity_type: Tipo de entidad que se está modificando
        action: Tipo de acción (create, update, delete)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Ejecutar la función original
            result = func(*args, **kwargs)
            
            # Intentar extraer entity_id de los argumentos
            # Típicamente el segundo argumento después de self
            entity_id = None
            if len(args) > 1:
                entity_id = args[1]
            elif "id" in kwargs:
                entity_id = kwargs["id"]
            elif "doc_id" in kwargs:
                entity_id = kwargs["doc_id"]
            
            # Registrar en auditoría si tenemos un ID válido
            if entity_id:
                logger = AuditLogger()
                try:
                    logger.log_change(
                        entity=entity_type,
                        entity_id=str(entity_id),
                        action=action,
                        changes_summary=f"Llamada a {func.__name__}"
                    )
                except Exception as e:
                    # No fallar si el log de auditoría falla
                    print(f"Warning: Audit log failed: {e}")
            
            return result
        return wrapper
    return decorator


# Instancia global para uso simple
_default_logger: Optional[AuditLogger] = None


def set_current_user(user_id: str):
    """Establece el usuario actual para los logs de auditoría."""
    global _default_logger
    _default_logger = AuditLogger(user_id)


def get_logger() -> AuditLogger:
    """Obtiene el logger de auditoría actual."""
    global _default_logger
    if _default_logger is None:
        _default_logger = AuditLogger()
    return _default_logger
