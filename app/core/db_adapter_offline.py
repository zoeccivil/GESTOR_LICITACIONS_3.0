"""
Adaptador de base de datos para modo offline usando respaldos locales.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from app.core.models import Licitacion
from app.core.firestore_backup import OfflineDataAdapter


class OfflineDatabaseAdapter:
    """
    Adaptador de base de datos que funciona en modo offline usando respaldos locales.
    Proporciona una interfaz compatible con DatabaseAdapter pero en modo solo-lectura.
    """
    
    def __init__(self, offline_adapter: OfflineDataAdapter):
        """
        Inicializa el adaptador offline.
        
        Args:
            offline_adapter: Adaptador de datos offline
        """
        self.offline_adapter = offline_adapter
        self._client = None  # Para compatibilidad
        self.is_offline = True
    
    def open(self):
        """Abre la conexión (no-op en modo offline)."""
        pass
    
    def close(self):
        """Cierra la conexión (no-op en modo offline)."""
        pass
    
    def load_all_licitaciones(self) -> List[Licitacion]:
        """Carga todas las licitaciones desde el respaldo."""
        from app.core.db_adapter import _dict_to_licitacion
        
        docs = self.offline_adapter.get_all("licitaciones")
        licitaciones = []
        
        for doc in docs:
            try:
                lic = _dict_to_licitacion(doc)
                licitaciones.append(lic)
            except Exception as e:
                print(f"⚠ Error al cargar licitación {doc.get('id')}: {e}")
        
        return licitaciones
    
    def load_licitacion_by_id(self, lic_id: str) -> Optional[Licitacion]:
        """Carga una licitación por ID desde el respaldo."""
        from app.core.db_adapter import _dict_to_licitacion
        
        doc = self.offline_adapter.get_by_id("licitaciones", str(lic_id))
        if not doc:
            return None
        
        try:
            return _dict_to_licitacion(doc)
        except Exception as e:
            print(f"⚠ Error al cargar licitación {lic_id}: {e}")
            return None
    
    def save_licitacion(self, licitacion: Licitacion) -> str:
        """
        Intenta guardar una licitación (no permitido en modo offline).
        """
        raise RuntimeError(
            "No se pueden guardar cambios en modo offline.\n\n"
            "Los datos están en modo solo-lectura usando un respaldo local.\n"
            "Restaure la conexión a Internet para guardar cambios."
        )
    
    def delete_licitacion(self, lic_id: str) -> bool:
        """
        Intenta eliminar una licitación (no permitido en modo offline).
        """
        raise RuntimeError(
            "No se pueden eliminar datos en modo offline.\n\n"
            "Los datos están en modo solo-lectura usando un respaldo local.\n"
            "Restaure la conexión a Internet para realizar cambios."
        )
    
    def get_empresas_maestras(self) -> List[Dict[str, Any]]:
        """Obtiene las empresas maestras del respaldo."""
        return self.offline_adapter.get_all("empresas_maestras")
    
    def save_empresas_maestras(self, empresas: List[Dict[str, Any]]) -> bool:
        """No permitido en modo offline."""
        raise RuntimeError("No se pueden guardar cambios en modo offline")
    
    def get_instituciones_maestras(self) -> List[Dict[str, Any]]:
        """Obtiene las instituciones maestras del respaldo."""
        return self.offline_adapter.get_all("instituciones_maestras")
    
    def save_instituciones_maestras(self, instituciones: List[Dict[str, Any]]) -> bool:
        """No permitido en modo offline."""
        raise RuntimeError("No se pueden guardar cambios en modo offline")
    
    def get_documentos_maestros(self) -> List[Dict[str, Any]]:
        """Obtiene los documentos maestros del respaldo."""
        return self.offline_adapter.get_all("documentos_maestros")
    
    def save_documentos_maestros(self, documentos: List[Dict[str, Any]]) -> bool:
        """No permitido en modo offline."""
        raise RuntimeError("No se pueden guardar cambios en modo offline")
    
    def get_competidores_maestros(self) -> List[Dict[str, Any]]:
        """Obtiene los competidores maestros del respaldo."""
        return self.offline_adapter.get_all("competidores_maestros")
    
    def save_competidores_maestros(self, competidores: List[Dict[str, Any]]) -> bool:
        """No permitido en modo offline."""
        raise RuntimeError("No se pueden guardar cambios en modo offline")
    
    def get_responsables_maestros(self) -> List[Dict[str, Any]]:
        """Obtiene los responsables maestros del respaldo."""
        return self.offline_adapter.get_all("responsables_maestros")
    
    def save_responsables_maestros(self, responsables: List[Dict[str, Any]]) -> bool:
        """No permitido en modo offline."""
        raise RuntimeError("No se pueden guardar cambios en modo offline")
    
    def get_fallas_fase_a_maestras(self) -> List[Dict[str, Any]]:
        """Obtiene las fallas fase A del respaldo."""
        return self.offline_adapter.get_all("fallas_fase_a")
    
    def save_fallas_fase_a_maestras(self, fallas: List[Dict[str, Any]]) -> bool:
        """No permitido en modo offline."""
        raise RuntimeError("No se pueden guardar cambios en modo offline")
    
    def get_subsanaciones_eventos(self, lic_id: str) -> List[Dict[str, Any]]:
        """Obtiene los eventos de subsanación del respaldo."""
        all_eventos = self.offline_adapter.get_all("subsanaciones_eventos")
        return [e for e in all_eventos if e.get("licitacion_id") == str(lic_id)]
    
    def save_subsanaciones_eventos(self, lic_id: str, eventos: List[Dict[str, Any]]) -> bool:
        """No permitido en modo offline."""
        raise RuntimeError("No se pueden guardar cambios en modo offline")
