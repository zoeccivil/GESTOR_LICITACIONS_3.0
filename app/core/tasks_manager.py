"""
Tasks Manager Module - Gestión de tareas y responsables

Este módulo maneja la asignación de tareas a responsables, estados,
fechas límite y seguimiento.

Colección Firestore: /tasks/{id}
Campos:
- entity: Tipo de entidad relacionada (ej: 'licitacion', 'documento')
- entity_id: ID del registro relacionado
- responsable_id: ID del usuario responsable
- responsable_nombre: Nombre del responsable
- titulo: Título de la tarea
- descripcion: Descripción detallada
- estado: Estado actual (To-Do, En curso, Hecho)
- fecha_limite: Fecha límite para completar
- prioridad: Prioridad (Alta, Media, Baja)
- comentarios: Lista de comentarios/actualizaciones
- created_at: Fecha de creación
- updated_at: Fecha de última actualización
- completed_at: Fecha de completitud (opcional)
"""
from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field

from . import firebase_adapter

TASKS_COLLECTION = "tasks"


@dataclass
class Task:
    """Modelo de tarea."""
    id: Optional[str] = None
    entity: str = ""
    entity_id: str = ""
    responsable_id: str = ""
    responsable_nombre: str = ""
    titulo: str = ""
    descripcion: str = ""
    estado: str = "To-Do"  # To-Do, En curso, Hecho
    fecha_limite: Optional[str] = None
    prioridad: str = "Media"  # Alta, Media, Baja
    comentarios: List[Dict[str, Any]] = field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convierte la tarea a diccionario para Firestore."""
        return {
            "entity": self.entity,
            "entity_id": self.entity_id,
            "responsable_id": self.responsable_id,
            "responsable_nombre": self.responsable_nombre,
            "titulo": self.titulo,
            "descripcion": self.descripcion,
            "estado": self.estado,
            "fecha_limite": self.fecha_limite,
            "prioridad": self.prioridad,
            "comentarios": self.comentarios,
            "created_at": self.created_at or datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Task:
        """Crea una tarea desde un diccionario."""
        return cls(
            id=data.get("id"),
            entity=data.get("entity", ""),
            entity_id=data.get("entity_id", ""),
            responsable_id=data.get("responsable_id", ""),
            responsable_nombre=data.get("responsable_nombre", ""),
            titulo=data.get("titulo", ""),
            descripcion=data.get("descripcion", ""),
            estado=data.get("estado", "To-Do"),
            fecha_limite=data.get("fecha_limite"),
            prioridad=data.get("prioridad", "Media"),
            comentarios=data.get("comentarios", []),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            completed_at=data.get("completed_at"),
        )


class TasksManager:
    """Gestor de tareas para la aplicación."""

    def __init__(self):
        self._subscriptions: List[Callable] = []

    def create_task(
        self,
        entity: str,
        entity_id: str,
        titulo: str,
        descripcion: str = "",
        responsable_id: str = "",
        responsable_nombre: str = "",
        fecha_limite: Optional[str] = None,
        prioridad: str = "Media"
    ) -> str:
        """
        Crea una nueva tarea.

        Args:
            entity: Tipo de entidad relacionada
            entity_id: ID de la entidad
            titulo: Título de la tarea
            descripcion: Descripción detallada
            responsable_id: ID del responsable
            responsable_nombre: Nombre del responsable
            fecha_limite: Fecha límite (ISO format)
            prioridad: Prioridad (Alta, Media, Baja)

        Returns:
            ID de la tarea creada
        """
        task = Task(
            entity=entity,
            entity_id=entity_id,
            titulo=titulo,
            descripcion=descripcion,
            responsable_id=responsable_id,
            responsable_nombre=responsable_nombre,
            fecha_limite=fecha_limite,
            prioridad=prioridad,
            estado="To-Do",
        )
        
        task_id = firebase_adapter.add_doc(TASKS_COLLECTION, task.to_dict())
        
        # Registrar en auditoría
        try:
            from .audit_logger import get_logger
            logger = get_logger()
            logger.log_change(
                entity="task",
                entity_id=task_id,
                action="create",
                new_values=task.to_dict(),
                changes_summary=f"Creada tarea: {titulo}"
            )
        except Exception:
            pass

        return task_id

    def get_task(self, task_id: str) -> Optional[Task]:
        """Obtiene una tarea por su ID."""
        data = firebase_adapter.get_by_id(TASKS_COLLECTION, task_id)
        if not data:
            return None
        return Task.from_dict(data)

    def get_all_tasks(self) -> List[Task]:
        """Obtiene todas las tareas."""
        docs = firebase_adapter.get_all(TASKS_COLLECTION)
        return [Task.from_dict(doc) for doc in docs]

    def get_tasks_by_entity(self, entity: str, entity_id: str) -> List[Task]:
        """Obtiene todas las tareas relacionadas con una entidad específica."""
        all_tasks = self.get_all_tasks()
        return [
            task for task in all_tasks
            if task.entity == entity and task.entity_id == entity_id
        ]

    def get_tasks_by_responsable(self, responsable_id: str) -> List[Task]:
        """Obtiene todas las tareas asignadas a un responsable."""
        all_tasks = self.get_all_tasks()
        return [task for task in all_tasks if task.responsable_id == responsable_id]

    def get_tasks_by_estado(self, estado: str) -> List[Task]:
        """Obtiene tareas filtradas por estado."""
        all_tasks = self.get_all_tasks()
        return [task for task in all_tasks if task.estado == estado]

    def update_task_estado(self, task_id: str, nuevo_estado: str) -> None:
        """
        Actualiza el estado de una tarea.

        Args:
            task_id: ID de la tarea
            nuevo_estado: Nuevo estado (To-Do, En curso, Hecho)
        """
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Tarea {task_id} no encontrada")

        old_estado = task.estado
        update_data = {
            "estado": nuevo_estado,
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

        # Si se marca como Hecho, registrar completed_at
        if nuevo_estado == "Hecho" and old_estado != "Hecho":
            update_data["completed_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

        firebase_adapter.update_doc(TASKS_COLLECTION, task_id, update_data)

        # Registrar en auditoría
        try:
            from .audit_logger import get_logger
            logger = get_logger()
            logger.log_change(
                entity="task",
                entity_id=task_id,
                action="update",
                old_values={"estado": old_estado},
                new_values={"estado": nuevo_estado},
                changes_summary=f"Estado cambiado: {old_estado} → {nuevo_estado}"
            )
        except Exception:
            pass

    def add_comentario(self, task_id: str, comentario: str, autor: str = "system") -> None:
        """
        Añade un comentario a una tarea.

        Args:
            task_id: ID de la tarea
            comentario: Texto del comentario
            autor: Autor del comentario
        """
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Tarea {task_id} no encontrada")

        nuevo_comentario = {
            "texto": comentario,
            "autor": autor,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

        comentarios = task.comentarios.copy()
        comentarios.append(nuevo_comentario)

        firebase_adapter.update_doc(
            TASKS_COLLECTION,
            task_id,
            {
                "comentarios": comentarios,
                "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
        )

    def delete_task(self, task_id: str) -> None:
        """Elimina una tarea."""
        task = self.get_task(task_id)
        if task:
            firebase_adapter.delete_doc(TASKS_COLLECTION, task_id)
            
            # Registrar en auditoría
            try:
                from .audit_logger import get_logger
                logger = get_logger()
                logger.log_change(
                    entity="task",
                    entity_id=task_id,
                    action="delete",
                    old_values=task.to_dict(),
                    changes_summary=f"Eliminada tarea: {task.titulo}"
                )
            except Exception:
                pass

    def get_overdue_tasks(self) -> List[Task]:
        """Obtiene tareas vencidas (fecha límite pasada y no completadas)."""
        all_tasks = self.get_all_tasks()
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        overdue = []
        for task in all_tasks:
            if task.estado != "Hecho" and task.fecha_limite:
                if task.fecha_limite < now:
                    overdue.append(task)
        
        return overdue

    def subscribe_to_tasks(self, callback: Callable[[List[Task]], None]):
        """
        Suscribirse a cambios en tiempo real de las tareas.

        Args:
            callback: Función a llamar cuando hay cambios
        """
        def _on_update(items: List[Dict[str, Any]]):
            tasks = [Task.from_dict(item) for item in items]
            callback(tasks)

        unsubscribe = firebase_adapter.subscribe_collection(TASKS_COLLECTION, _on_update)
        self._subscriptions.append(unsubscribe)

    def unsubscribe_all(self):
        """Cancela todas las suscripciones activas."""
        for unsubscribe in self._subscriptions:
            try:
                unsubscribe()
            except Exception:
                pass
        self._subscriptions.clear()
