"""
Competitor Insights Module - Inteligencia de competidores

Este módulo analiza y registra información sobre competidores, incluyendo
historial de participaciones, tasas de éxito, precios ofertados, etc.

Colección Firestore: /competitors/{id}
Campos:
- nombre: Nombre del competidor
- rnc: RNC o identificador fiscal
- proyectos: Lista de proyectos en los que ha participado
- participaciones: Historial de participaciones con detalles
- montos_ofertados: Lista de montos ofertados por proyecto
- proyectos_ganados: Lista de proyectos ganados
- win_rate: Tasa de éxito (% de proyectos ganados)
- ultima_participacion: Fecha de última participación
- categorias: Categorías o rubros principales
- promedio_monto: Monto promedio ofertado
- created_at: Fecha de creación del registro
- updated_at: Fecha de última actualización
"""
from __future__ import annotations

import datetime
import statistics
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field

from . import firebase_adapter

COMPETITORS_COLLECTION = "competitors"


@dataclass
class CompetitorParticipation:
    """Registro de una participación de un competidor."""
    proyecto_id: str
    proyecto_nombre: str
    fecha: str
    monto_ofertado: float
    ganado: bool
    categoria: str = ""
    lote: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "proyecto_id": self.proyecto_id,
            "proyecto_nombre": self.proyecto_nombre,
            "fecha": self.fecha,
            "monto_ofertado": self.monto_ofertado,
            "ganado": self.ganado,
            "categoria": self.categoria,
            "lote": self.lote,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CompetitorParticipation:
        return cls(
            proyecto_id=data.get("proyecto_id", ""),
            proyecto_nombre=data.get("proyecto_nombre", ""),
            fecha=data.get("fecha", ""),
            monto_ofertado=data.get("monto_ofertado", 0.0),
            ganado=data.get("ganado", False),
            categoria=data.get("categoria", ""),
            lote=data.get("lote", ""),
        )


@dataclass
class Competitor:
    """Modelo de competidor."""
    id: Optional[str] = None
    nombre: str = ""
    rnc: str = ""
    participaciones: List[CompetitorParticipation] = field(default_factory=list)
    proyectos_ganados: List[str] = field(default_factory=list)
    categorias: List[str] = field(default_factory=list)
    win_rate: float = 0.0
    promedio_monto: float = 0.0
    mediana_monto: float = 0.0
    ultima_participacion: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el competidor a diccionario para Firestore."""
        return {
            "nombre": self.nombre,
            "rnc": self.rnc,
            "participaciones": [p.to_dict() for p in self.participaciones],
            "proyectos_ganados": self.proyectos_ganados,
            "categorias": self.categorias,
            "win_rate": self.win_rate,
            "promedio_monto": self.promedio_monto,
            "mediana_monto": self.mediana_monto,
            "ultima_participacion": self.ultima_participacion,
            "created_at": self.created_at or datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Competitor:
        """Crea un competidor desde un diccionario."""
        participaciones_data = data.get("participaciones", [])
        participaciones = [
            CompetitorParticipation.from_dict(p) for p in participaciones_data
        ]
        
        return cls(
            id=data.get("id"),
            nombre=data.get("nombre", ""),
            rnc=data.get("rnc", ""),
            participaciones=participaciones,
            proyectos_ganados=data.get("proyectos_ganados", []),
            categorias=data.get("categorias", []),
            win_rate=data.get("win_rate", 0.0),
            promedio_monto=data.get("promedio_monto", 0.0),
            mediana_monto=data.get("mediana_monto", 0.0),
            ultima_participacion=data.get("ultima_participacion"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


class CompetitorInsights:
    """Gestor de inteligencia de competidores."""

    def __init__(self):
        self._subscriptions: List[Callable] = []

    def register_competitor(self, nombre: str, rnc: str = "") -> str:
        """
        Registra un nuevo competidor.

        Args:
            nombre: Nombre del competidor
            rnc: RNC o identificador fiscal

        Returns:
            ID del competidor creado
        """
        competitor = Competitor(nombre=nombre, rnc=rnc)
        competitor_id = firebase_adapter.add_doc(COMPETITORS_COLLECTION, competitor.to_dict())
        
        # Registrar en auditoría
        try:
            from .audit_logger import get_logger
            logger = get_logger()
            logger.log_change(
                entity="competitor",
                entity_id=competitor_id,
                action="create",
                new_values=competitor.to_dict(),
                changes_summary=f"Registrado competidor: {nombre}"
            )
        except Exception:
            pass
        
        return competitor_id

    def get_competitor(self, competitor_id: str) -> Optional[Competitor]:
        """Obtiene un competidor por su ID."""
        data = firebase_adapter.get_by_id(COMPETITORS_COLLECTION, competitor_id)
        if not data:
            return None
        return Competitor.from_dict(data)

    def get_all_competitors(self) -> List[Competitor]:
        """Obtiene todos los competidores."""
        docs = firebase_adapter.get_all(COMPETITORS_COLLECTION)
        return [Competitor.from_dict(doc) for doc in docs]

    def find_competitor_by_name(self, nombre: str) -> Optional[Competitor]:
        """
        Busca un competidor por nombre (case-insensitive).
        
        Note: Current implementation uses linear search. For better performance
        with large datasets, consider:
        1. Adding a Firestore index on 'nombre' field
        2. Using Firestore queries with where() clause
        3. Implementing a local cache with name-based lookup
        
        Example optimized query:
            docs = firebase_adapter._collection(COMPETITORS_COLLECTION)
                .where("nombre", "==", nombre).limit(1).stream()
        """
        nombre_lower = nombre.lower().strip()
        for comp in self.get_all_competitors():
            if comp.nombre.lower().strip() == nombre_lower:
                return comp
        return None

    def add_participation(
        self,
        competitor_id: str,
        proyecto_id: str,
        proyecto_nombre: str,
        monto_ofertado: float,
        ganado: bool,
        categoria: str = "",
        lote: str = "",
        fecha: Optional[str] = None
    ) -> None:
        """
        Registra una participación de un competidor.

        Args:
            competitor_id: ID del competidor
            proyecto_id: ID del proyecto/licitación
            proyecto_nombre: Nombre del proyecto
            monto_ofertado: Monto ofertado
            ganado: Si ganó el proyecto
            categoria: Categoría o rubro
            lote: Número de lote
            fecha: Fecha de participación (ISO format)
        """
        competitor = self.get_competitor(competitor_id)
        if not competitor:
            raise ValueError(f"Competidor {competitor_id} no encontrado")

        participation = CompetitorParticipation(
            proyecto_id=proyecto_id,
            proyecto_nombre=proyecto_nombre,
            fecha=fecha or datetime.datetime.now(datetime.timezone.utc).isoformat(),
            monto_ofertado=monto_ofertado,
            ganado=ganado,
            categoria=categoria,
            lote=lote,
        )

        competitor.participaciones.append(participation)
        
        if ganado:
            if proyecto_id not in competitor.proyectos_ganados:
                competitor.proyectos_ganados.append(proyecto_id)
        
        if categoria and categoria not in competitor.categorias:
            competitor.categorias.append(categoria)
        
        # Recalcular métricas
        self._recalculate_metrics(competitor)
        
        # Actualizar en Firestore
        firebase_adapter.update_doc(
            COMPETITORS_COLLECTION,
            competitor_id,
            competitor.to_dict()
        )

    def _recalculate_metrics(self, competitor: Competitor) -> None:
        """Recalcula las métricas de un competidor."""
        if not competitor.participaciones:
            competitor.win_rate = 0.0
            competitor.promedio_monto = 0.0
            competitor.mediana_monto = 0.0
            competitor.ultima_participacion = None
            return

        # Win rate
        total_participaciones = len(competitor.participaciones)
        total_ganados = len(competitor.proyectos_ganados)
        competitor.win_rate = (total_ganados / total_participaciones) * 100 if total_participaciones > 0 else 0.0

        # Montos
        montos = [p.monto_ofertado for p in competitor.participaciones if p.monto_ofertado > 0]
        if montos:
            competitor.promedio_monto = statistics.mean(montos)
            competitor.mediana_monto = statistics.median(montos)
        else:
            competitor.promedio_monto = 0.0
            competitor.mediana_monto = 0.0

        # Última participación
        fechas = [p.fecha for p in competitor.participaciones if p.fecha]
        if fechas:
            competitor.ultima_participacion = max(fechas)

    def get_competitors_by_categoria(self, categoria: str) -> List[Competitor]:
        """Obtiene competidores que participan en una categoría específica."""
        all_competitors = self.get_all_competitors()
        return [
            comp for comp in all_competitors
            if categoria in comp.categorias
        ]

    def get_price_statistics_by_categoria(self, categoria: str) -> Dict[str, float]:
        """
        Calcula estadísticas de precios por categoría.

        Args:
            categoria: Categoría a analizar

        Returns:
            Dict con promedio, mediana, mínimo y máximo
        """
        all_competitors = self.get_all_competitors()
        montos = []
        
        for comp in all_competitors:
            for part in comp.participaciones:
                if part.categoria == categoria and part.monto_ofertado > 0:
                    montos.append(part.monto_ofertado)
        
        if not montos:
            return {
                "promedio": 0.0,
                "mediana": 0.0,
                "minimo": 0.0,
                "maximo": 0.0,
                "count": 0,
            }
        
        return {
            "promedio": statistics.mean(montos),
            "mediana": statistics.median(montos),
            "minimo": min(montos),
            "maximo": max(montos),
            "count": len(montos),
        }

    def get_top_competitors(self, limit: int = 10, by: str = "win_rate") -> List[Competitor]:
        """
        Obtiene los mejores competidores según un criterio.

        Args:
            limit: Número máximo de competidores a retornar
            by: Criterio de ordenamiento ('win_rate', 'participaciones', 'promedio_monto')

        Returns:
            Lista de competidores ordenados
        """
        all_competitors = self.get_all_competitors()
        
        if by == "win_rate":
            sorted_competitors = sorted(
                all_competitors,
                key=lambda c: c.win_rate,
                reverse=True
            )
        elif by == "participaciones":
            sorted_competitors = sorted(
                all_competitors,
                key=lambda c: len(c.participaciones),
                reverse=True
            )
        elif by == "promedio_monto":
            sorted_competitors = sorted(
                all_competitors,
                key=lambda c: c.promedio_monto,
                reverse=True
            )
        else:
            sorted_competitors = all_competitors
        
        return sorted_competitors[:limit]

    def delete_competitor(self, competitor_id: str) -> None:
        """Elimina un competidor."""
        competitor = self.get_competitor(competitor_id)
        if competitor:
            firebase_adapter.delete_doc(COMPETITORS_COLLECTION, competitor_id)
            
            # Registrar en auditoría
            try:
                from .audit_logger import get_logger
                logger = get_logger()
                logger.log_change(
                    entity="competitor",
                    entity_id=competitor_id,
                    action="delete",
                    old_values=competitor.to_dict(),
                    changes_summary=f"Eliminado competidor: {competitor.nombre}"
                )
            except Exception:
                pass
