"""
Adaptador SQLite que envuelve el DatabaseManager legacy.

Este adaptador proporciona la misma interfaz que el adaptador de Firestore
para mantener compatibilidad con el código de la UI.
"""
from __future__ import annotations

import datetime as _dt
import sys
import os
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

# Importar el DatabaseManager original
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from db_manager import DatabaseManager
from .models import Documento, Empresa, Licitacion, Lote, Oferente


class SQLiteDatabaseAdapter:
    """
    Wrapper sobre DatabaseManager (SQLite) que implementa la misma interfaz
    que el adaptador de Firestore.
    """
    
    def __init__(self, db_path: str) -> None:
        """
        Inicializa el adaptador SQLite.
        
        Args:
            db_path: Ruta al archivo de base de datos SQLite
        """
        self.db_path = db_path
        self._db_manager: Optional[DatabaseManager] = None
        self._subscriptions: List[Callable[[], None]] = []
    
    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def open(self) -> None:
        """Abre la conexión a la base de datos SQLite."""
        if self._db_manager is None:
            self._db_manager = DatabaseManager(self.db_path)
    
    def close(self) -> None:
        """Cierra la conexión a la base de datos."""
        if self._db_manager is not None:
            self._db_manager.conn.close()
            self._db_manager = None
        for unsubscribe in self._subscriptions:
            try:
                unsubscribe()
            except Exception:
                pass
        self._subscriptions.clear()
    
    def _ensure_db(self) -> DatabaseManager:
        """Asegura que el DatabaseManager esté inicializado."""
        if self._db_manager is None:
            self.open()
        return self._db_manager
    
    # ------------------------------------------------------------------
    # Licitaciones CRUD
    # ------------------------------------------------------------------
    def subscribe_to_licitaciones(self, callback: Callable[[List[Licitacion]], None]) -> None:
        """
        SQLite no soporta suscripciones en tiempo real.
        Esta función es un no-op para mantener compatibilidad.
        """
        # No se puede suscribir en SQLite, pero mantenemos la interfaz
        pass
    
    def load_all_licitaciones(self) -> List[Licitacion]:
        """Carga todas las licitaciones desde SQLite."""
        db = self._ensure_db()
        return db.cargar_licitaciones()
    
    def list_licitaciones(self) -> List[Licitacion]:
        """Alias para load_all_licitaciones."""
        return self.load_all_licitaciones()
    
    def load_licitacion_by_id(self, lic_id: Any) -> Optional[Licitacion]:
        """Carga una licitación por su ID."""
        if lic_id is None:
            return None
        db = self._ensure_db()
        return db.cargar_licitacion_completa(int(lic_id))
    
    def load_licitacion_by_numero(self, numero: str) -> Optional[Licitacion]:
        """Carga una licitación por su número de proceso."""
        numero_norm = (numero or "").strip().lower()
        for lic in self.load_all_licitaciones():
            if (lic.numero_proceso or "").strip().lower() == numero_norm:
                return lic
        return None
    
    def save_licitacion(self, licitacion: Licitacion) -> str:
        """Guarda una licitación (crea o actualiza)."""
        db = self._ensure_db()
        
        if licitacion.id is None:
            # Crear nueva licitación
            lic_id = db.crear_licitacion(
                nombre_proceso=licitacion.nombre_proceso,
                numero_proceso=licitacion.numero_proceso,
                institucion=licitacion.institucion,
                estado=licitacion.estado,
                empresas_nuestras=[emp.nombre for emp in licitacion.empresas_nuestras],
                lotes=licitacion.lotes,
                oferentes_participantes=licitacion.oferentes_participantes,
                documentos_solicitados=licitacion.documentos_solicitados,
                cronograma=licitacion.cronograma,
                fallas_fase_a=licitacion.fallas_fase_a,
                parametros_evaluacion=licitacion.parametros_evaluacion,
            )
            licitacion.id = lic_id
        else:
            # Actualizar licitación existente
            db.actualizar_licitacion_completa(licitacion)
        
        return str(licitacion.id)
    
    def delete_licitacion(self, lic_id: Any) -> None:
        """Elimina una licitación."""
        if lic_id is None:
            return
        db = self._ensure_db()
        db.eliminar_licitacion(int(lic_id))
    
    # ------------------------------------------------------------------
    # Master collections helpers
    # ------------------------------------------------------------------
    def get_empresas_maestras(self) -> List[Dict[str, Any]]:
        """Obtiene la lista de empresas maestras."""
        db = self._ensure_db()
        empresas = db.cargar_empresas_maestras()
        return [{"id": emp, "nombre": emp} for emp in empresas]
    
    def save_empresas_maestras(self, lista_empresas: List[Dict[str, Any]]) -> bool:
        """Guarda la lista de empresas maestras."""
        db = self._ensure_db()
        empresas = [emp.get("nombre", "") for emp in lista_empresas]
        db.guardar_empresas_maestras(empresas)
        return True
    
    def get_instituciones_maestras(self) -> List[Dict[str, Any]]:
        """Obtiene la lista de instituciones maestras."""
        db = self._ensure_db()
        instituciones = db.cargar_instituciones_maestras()
        return [{"id": inst, "nombre": inst} for inst in instituciones]
    
    def save_instituciones_maestras(self, lista_instituciones: List[Dict[str, Any]]) -> bool:
        """Guarda la lista de instituciones maestras."""
        db = self._ensure_db()
        instituciones = [inst.get("nombre", "") for inst in lista_instituciones]
        db.guardar_instituciones_maestras(instituciones)
        return True
    
    def get_documentos_maestros(self) -> List[Documento]:
        """Obtiene la lista de documentos maestros."""
        db = self._ensure_db()
        docs_dict = db.cargar_documentos_maestros()
        return [
            Documento(
                id=doc.get("id"),
                codigo=doc.get("codigo", ""),
                nombre=doc.get("nombre", ""),
                categoria=doc.get("categoria", ""),
                comentario=doc.get("comentario", ""),
                subsanable=doc.get("subsanable", "Subsanable"),
                obligatorio=bool(doc.get("obligatorio", False)),
            )
            for doc in docs_dict
        ]
    
    def save_documentos_maestros(self, docs: List[Documento]) -> bool:
        """Guarda la lista de documentos maestros."""
        db = self._ensure_db()
        docs_dict = [doc.to_dict() for doc in docs]
        db.guardar_documentos_maestros(docs_dict)
        return True
    
    def get_competidores_maestros(self) -> List[Dict[str, Any]]:
        """Obtiene la lista de competidores maestros."""
        db = self._ensure_db()
        competidores = db.cargar_competidores_maestros()
        return [{"id": comp, "nombre": comp} for comp in competidores]
    
    def save_competidores_maestros(self, items: List[Dict[str, Any]]) -> bool:
        """Guarda la lista de competidores maestros."""
        db = self._ensure_db()
        competidores = [item.get("nombre", "") for item in items]
        db.guardar_competidores_maestros(competidores)
        return True
    
    def get_responsables_maestros(self) -> List[Dict[str, Any]]:
        """Obtiene la lista de responsables maestros."""
        db = self._ensure_db()
        responsables = db.cargar_responsables_maestros()
        return [{"id": resp, "nombre": resp} for resp in responsables]
    
    def save_responsables_maestros(self, items: List[Dict[str, Any]]) -> bool:
        """Guarda la lista de responsables maestros."""
        db = self._ensure_db()
        responsables = [item.get("nombre", "") for item in items]
        db.guardar_responsables_maestros(responsables)
        return True
    
    def save_master_lists(
        self,
        *,
        empresas: Optional[List[Dict[str, Any]]] = None,
        instituciones: Optional[List[Dict[str, Any]]] = None,
        documentos_maestros: Optional[List[Dict[str, Any]]] = None,
        competidores_maestros: Optional[List[Dict[str, Any]]] = None,
        responsables_maestros: Optional[List[Dict[str, Any]]] = None,
        replace_tables: Optional[Iterable[str]] = None,
    ) -> None:
        """Guarda múltiples listas maestras."""
        if empresas is not None:
            self.save_empresas_maestras(empresas)
        if instituciones is not None:
            self.save_instituciones_maestras(instituciones)
        if documentos_maestros is not None:
            docs = [
                Documento(
                    id=doc.get("id"),
                    codigo=doc.get("codigo", ""),
                    nombre=doc.get("nombre", ""),
                    categoria=doc.get("categoria", ""),
                    comentario=doc.get("comentario", ""),
                )
                for doc in documentos_maestros
            ]
            self.save_documentos_maestros(docs)
        if competidores_maestros is not None:
            self.save_competidores_maestros(competidores_maestros)
        if responsables_maestros is not None:
            self.save_responsables_maestros(responsables_maestros)
    
    def _get_master_table(self, table_name: str) -> List[Dict[str, Any]]:
        """Obtiene una tabla maestra por nombre."""
        if table_name == "empresas_maestras":
            return self.get_empresas_maestras()
        elif table_name == "instituciones_maestras":
            return self.get_instituciones_maestras()
        elif table_name == "documentos_maestros":
            return [doc.to_dict() for doc in self.get_documentos_maestros()]
        elif table_name == "competidores_maestros":
            return self.get_competidores_maestros()
        elif table_name == "responsables_maestros":
            return self.get_responsables_maestros()
        return []
    
    def is_institucion_en_uso(self, nombre_institucion: str) -> bool:
        """Verifica si una institución está en uso."""
        db = self._ensure_db()
        return db.is_institucion_en_uso(nombre_institucion)
    
    def is_empresa_en_uso(self, nombre_empresa: str) -> bool:
        """Verifica si una empresa está en uso."""
        db = self._ensure_db()
        return db.is_empresa_en_uso(nombre_empresa)
    
    # ------------------------------------------------------------------
    # Aggregates / helpers
    # ------------------------------------------------------------------
    def get_all_data(self) -> List[Any]:
        """Obtiene todos los datos de la base de datos."""
        return [
            [lic.to_dict() for lic in self.load_all_licitaciones()],
            self.get_empresas_maestras(),
            self.get_instituciones_maestras(),
            [doc.to_dict() for doc in self.get_documentos_maestros()],
            self.get_competidores_maestros(),
            self.get_responsables_maestros(),
        ]
    
    def get_all_licitaciones_basic_info(self) -> List[Dict[str, Any]]:
        """Obtiene información básica de todas las licitaciones."""
        result: List[Dict[str, Any]] = []
        for lic in self.load_all_licitaciones():
            result.append(
                {
                    "id": lic.id,
                    "nombre_proceso": lic.nombre_proceso,
                    "numero_proceso": lic.numero_proceso,
                    "institucion": lic.institucion,
                    "estado": lic.estado,
                }
            )
        return result
    
    def guardar_orden_documentos(self, licitacion_id: Any, orden_por_categoria_or_pairs: Any) -> bool:
        """Guarda el orden de los documentos."""
        db = self._ensure_db()
        db.guardar_orden_documentos(int(licitacion_id), orden_por_categoria_or_pairs)
        return True
    
    def marcar_ganador_lote(
        self,
        licitacion_id: Any,
        lote_num: str,
        ganador: str,
        empresa_nuestra: Optional[str],
    ) -> bool:
        """Marca el ganador de un lote."""
        db = self._ensure_db()
        db.marcar_ganador_lote(int(licitacion_id), lote_num, ganador, empresa_nuestra)
        return True
    
    def borrar_ganador_lote(self, licitacion_id: Any, lote_num: str) -> bool:
        """Borra el ganador de un lote."""
        db = self._ensure_db()
        db.borrar_ganador_lote(int(licitacion_id), lote_num)
        return True
    
    # ------------------------------------------------------------------
    # Fallas Fase A management
    # ------------------------------------------------------------------
    def get_fallas_fase_a(self, licitacion_id: Any) -> List[Dict[str, Any]]:
        """Obtiene las fallas de fase A."""
        db = self._ensure_db()
        return db.cargar_fallas_fase_a(int(licitacion_id))
    
    def insertar_falla_por_ids(
        self,
        licitacion_id: Any,
        participante_nombre: str,
        documento_id: Any,
        comentario: str,
        es_nuestro: bool,
    ) -> str:
        """Inserta una falla por IDs."""
        db = self._ensure_db()
        falla_id = db.insertar_falla_por_ids(
            int(licitacion_id),
            participante_nombre,
            int(documento_id),
            comentario,
            es_nuestro,
        )
        return str(falla_id)
    
    def eliminar_fallas_por_ids(self, licitacion_id: Any, falla_ids: Iterable[str]) -> int:
        """Elimina fallas por IDs."""
        db = self._ensure_db()
        count = 0
        for falla_id in falla_ids:
            db.eliminar_falla_por_id(int(falla_id))
            count += 1
        return count
    
    def eliminar_falla_por_ids(self, licitacion_id: Any, documento_id: Any, participante_nombre: str) -> int:
        """Elimina una falla específica."""
        db = self._ensure_db()
        return db.eliminar_falla_por_ids(int(licitacion_id), int(documento_id), participante_nombre)
    
    def eliminar_falla_por_campos(self, institucion: str, participante_nombre: str, documento_nombre: str) -> int:
        """Elimina una falla por campos."""
        db = self._ensure_db()
        return db.eliminar_falla_por_campos(institucion, participante_nombre, documento_nombre)
    
    def actualizar_comentarios_por_ids(self, licitacion_id: Any, items: Iterable[Dict[str, Any]]) -> int:
        """Actualiza comentarios de fallas."""
        db = self._ensure_db()
        return db.actualizar_comentarios_por_ids(int(licitacion_id), items)
    
    def actualizar_comentario_falla_por_ids(
        self,
        licitacion_id: Any,
        documento_id: Any,
        participante_nombre: str,
        comentario: str,
    ) -> int:
        """Actualiza el comentario de una falla."""
        db = self._ensure_db()
        return db.actualizar_comentario_falla_por_ids(
            int(licitacion_id), int(documento_id), participante_nombre, comentario
        )
    
    def actualizar_comentario_falla(self, institucion: str, participante_nombre: str, documento_nombre: str, comentario: str) -> int:
        """Actualiza el comentario de una falla por campos."""
        db = self._ensure_db()
        return db.actualizar_comentario_falla(institucion, participante_nombre, documento_nombre, comentario)
    
    def obtener_todas_las_fallas(self) -> List[Dict[str, Any]]:
        """Obtiene todas las fallas."""
        db = self._ensure_db()
        return db.obtener_todas_las_fallas()
    
    # ------------------------------------------------------------------
    # Subsanaciones management
    # ------------------------------------------------------------------
    def registrar_eventos_subsanacion(self, licitacion_id: Any, eventos: Iterable[Dict[str, Any]]) -> None:
        """Registra eventos de subsanación."""
        db = self._ensure_db()
        db.registrar_eventos_subsanacion(int(licitacion_id), eventos)
    
    def existe_evento_subsanacion_pendiente(self, licitacion_id: Any, documento_id: Any) -> bool:
        """Verifica si existe un evento de subsanación pendiente."""
        db = self._ensure_db()
        return db.existe_evento_subsanacion_pendiente(int(licitacion_id), int(documento_id))
    
    def completar_evento_subsanacion(self, licitacion_id: Any, documento_id: Any, documento_codigo: str) -> None:
        """Completa un evento de subsanación."""
        db = self._ensure_db()
        db.completar_evento_subsanacion(int(licitacion_id), int(documento_id), documento_codigo)
    
    def obtener_historial_subsanacion(self, licitacion_id: Any) -> List[Dict[str, Any]]:
        """Obtiene el historial de subsanaciones."""
        db = self._ensure_db()
        return db.obtener_historial_subsanacion(int(licitacion_id))
    
    # ------------------------------------------------------------------
    # Settings helpers
    # ------------------------------------------------------------------
    def get_setting(self, clave: str, default: Optional[str] = None) -> Optional[str]:
        """Obtiene una configuración."""
        db = self._ensure_db()
        return db.get_setting(clave, default)
    
    def set_setting(self, clave: str, valor: str) -> None:
        """Establece una configuración."""
        db = self._ensure_db()
        db.set_setting(clave, valor)
    
    # ------------------------------------------------------------------
    # Compatibility fallbacks
    # ------------------------------------------------------------------
    def run_sanity_checks(self) -> Dict[str, Any]:
        """Ejecuta verificaciones de sanidad."""
        db = self._ensure_db()
        return db.run_sanity_checks()
    
    def auto_repair(self, issues: Dict[str, Any]) -> Tuple[bool, str]:
        """Intenta reparar problemas automáticamente."""
        db = self._ensure_db()
        return db.auto_repair(issues)
