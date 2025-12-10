"""
Adaptador de Base de Datos MySQL para la aplicación de Licitaciones.

Este módulo reemplaza el DatabaseManager basado en SQLite con una implementación
que usa MySQL a través de SQLAlchemy. Mantiene la misma interfaz para compatibilidad
con la UI existente.

Autor: Sistema de Migración MySQL
Fecha: 2025
"""

from __future__ import annotations

import os
import sys
import datetime as _dt
from typing import Any, Dict, List, Optional, Tuple
from dotenv import load_dotenv

# Importar módulos MySQL que creamos
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from db import get_engine, get_session, test_connection
from sqlalchemy import text

# Modelos de la aplicación
from .models import Documento, Empresa, Licitacion, Lote, Oferente


def _to_bool(v: Any) -> bool:
    """Convierte un valor a booleano de forma segura."""
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    try:
        return bool(int(v))
    except Exception:
        return str(v).strip().lower() in ("true", "t", "yes", "y", "1", "sí")


def _to_float(v: Any, default: float = 0.0) -> float:
    """Convierte un valor a float de forma segura."""
    try:
        return float(v if v is not None else default)
    except Exception:
        return default


def _to_int(v: Any, default: int = 0) -> int:
    """Convierte un valor a int de forma segura."""
    try:
        return int(v if v is not None else default)
    except Exception:
        return default


class DatabaseAdapter:
    """
    Adaptador que conecta la UI PyQt6 con MySQL.
    
    Reemplaza la funcionalidad del DatabaseManager (SQLite) pero mantiene
    la misma interfaz para que la UI no requiera cambios.
    
    Características:
    - Usa MySQL vía SQLAlchemy
    - Pool de conexiones (10-30 conexiones simultáneas)
    - Lee configuración desde archivo .env
    - Compatible con multi-usuario
    - Mantiene métodos del DatabaseManager original
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        """
        Inicializa el adaptador.
        
        Nota: db_path se ignora (compatibilidad), la configuración viene de .env
        """
        # Cargar variables de entorno
        load_dotenv()
        
        self.db_path = db_path  # Solo para compatibilidad, no se usa
        self.engine = None
        self._connected = False

    @property
    def path(self) -> Optional[str]:
        """Compatibilidad: devuelve info de conexión en lugar de ruta."""
        if self._connected:
            host = os.getenv('DB_HOST', 'localhost')
            db_name = os.getenv('DB_NAME', 'zoec_db')
            return f"mysql://{host}/{db_name}"
        return None

    @property
    def schema(self) -> str:
        """Versión del esquema (compatibilidad con UI)."""
        return "mysql_normalized_v1"

    # ----------------------------
    # Ciclo de vida
    # ----------------------------
    
    def open(self, db_path: Optional[str] = None) -> None:
        """
        Abre la conexión a MySQL.
        
        Args:
            db_path: Ignorado (compatibilidad). La configuración viene de .env
        """
        try:
            # Obtener engine global
            self.engine = get_engine()
            
            # Probar conexión
            test_connection()
            
            self._connected = True
            print(f"✅ Conectado a MySQL: {os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}")
            
        except Exception as e:
            self._connected = False
            raise RuntimeError(f"No se pudo conectar a MySQL: {e}")

    def close(self) -> None:
        """Cierra la conexión (en SQLAlchemy el pool se maneja automáticamente)."""
        self._connected = False
        # El engine se cierra automáticamente al finalizar la app

    @staticmethod
    def create_new_db(path: str) -> None:
        """
        Crea una nueva base de datos.
        
        En MySQL esto requiere ejecutar las migraciones Alembic.
        """
        print("Para crear la base de datos MySQL, ejecuta:")
        print("  alembic upgrade head")
        raise NotImplementedError("Usa 'alembic upgrade head' para crear el esquema MySQL")

    # ----------------------------
    # Lectura de Licitaciones
    # ----------------------------
    
    def load_all_licitaciones(self) -> List[Licitacion]:
        """
        Carga TODAS las licitaciones con sus relaciones completas.
        
        Returns:
            Lista de objetos Licitacion con lotes, documentos, oferentes
        """
        if not self._connected:
            raise RuntimeError("Base de datos no conectada. Llama a open() primero.")
        
        with get_session() as session:
            # Consulta principal de licitaciones
            query = text("""
                SELECT 
                    id, nombre_proceso, numero_proceso, institucion, estado,
                    fase_A_superada, fase_B_superada, adjudicada, adjudicada_a,
                    motivo_descalificacion, fecha_creacion, cronograma, parametros_evaluacion
                FROM licitaciones
                ORDER BY fecha_creacion DESC, id DESC
            """)
            
            result = session.execute(query)
            licitaciones = []
            
            for row in result:
                lic_dict = {
                    'id': row.id,
                    'nombre_proceso': row.nombre_proceso,
                    'numero_proceso': row.numero_proceso,
                    'institucion': row.institucion,
                    'estado': row.estado,
                    'fase_A_superada': row.fase_A_superada,
                    'fase_B_superada': row.fase_B_superada,
                    'adjudicada': row.adjudicada,
                    'adjudicada_a': row.adjudicada_a,
                    'motivo_descalificacion': row.motivo_descalificacion,
                    'fecha_creacion': row.fecha_creacion,
                    'cronograma': row.cronograma,
                    'parametros_evaluacion': row.parametros_evaluacion,
                }
                
                # Cargar relaciones
                lic_id = row.id
                lic_dict['empresas_nuestras'] = self._load_empresas_nuestras(session, lic_id)
                lic_dict['lotes'] = self._load_lotes(session, lic_id)
                lic_dict['oferentes_participantes'] = self._load_oferentes(session, lic_id)
                lic_dict['documentos_solicitados'] = self._load_documentos(session, lic_id)
                
                # Convertir a modelo
                lic = self._map_licitacion_dict_to_model(lic_dict)
                licitaciones.append(lic)
            
            return licitaciones

    def _load_empresas_nuestras(self, session, licitacion_id: int) -> List[str]:
        """Carga las empresas nuestras asociadas a una licitación."""
        query = text("""
            SELECT empresa_nombre
            FROM licitacion_empresas_nuestras
            WHERE licitacion_id = :lic_id
            ORDER BY empresa_nombre
        """)
        result = session.execute(query, {'lic_id': licitacion_id})
        return [row.empresa_nombre for row in result]

    def _load_lotes(self, session, licitacion_id: int) -> List[Dict]:
        """Carga los lotes de una licitación."""
        query = text("""
            SELECT 
                id, numero, nombre, monto_base, monto_base_personal, 
                monto_ofertado, participamos, fase_A_superada,
                ganador_nombre, empresa_nuestra, ganado_por_nosotros
            FROM lotes
            WHERE licitacion_id = :lic_id
            ORDER BY numero
        """)
        result = session.execute(query, {'lic_id': licitacion_id})
        
        lotes = []
        for row in result:
            lotes.append({
                'id': row.id,
                'numero': row.numero,
                'nombre': row.nombre,
                'monto_base': row.monto_base,
                'monto_base_personal': row.monto_base_personal,
                'monto_ofertado': row.monto_ofertado,
                'participamos': row.participamos,
                'fase_A_superada': row.fase_A_superada,
                'ganador_nombre': row.ganador_nombre,
                'empresa_nuestra': row.empresa_nuestra,
                'ganado_por_nosotros': row.ganado_por_nosotros,
            })
        return lotes

    def _load_oferentes(self, session, licitacion_id: int) -> List[Dict]:
        """Carga los oferentes de una licitación."""
        query_oferentes = text("""
            SELECT DISTINCT nombre, comentario
            FROM oferentes
            WHERE licitacion_id = :lic_id
            ORDER BY nombre
        """)
        result = session.execute(query_oferentes, {'lic_id': licitacion_id})
        
        oferentes = []
        for row in result:
            oferente = {
                'nombre': row.nombre,
                'comentario': row.comentario,
                'ofertas_por_lote': []
            }
            
            # Cargar ofertas por lote de este oferente
            query_ofertas = text("""
                SELECT lote_numero, monto, paso_fase_A, plazo_entrega, garantia_meses
                FROM ofertas_lote_oferentes
                WHERE licitacion_id = :lic_id AND oferente_nombre = :nombre
                ORDER BY lote_numero
            """)
            ofertas = session.execute(query_ofertas, {'lic_id': licitacion_id, 'nombre': row.nombre})
            
            for oferta in ofertas:
                oferente['ofertas_por_lote'].append({
                    'lote_numero': oferta.lote_numero,
                    'monto': oferta.monto,
                    'paso_fase_A': oferta.paso_fase_A,
                    'plazo_entrega': oferta.plazo_entrega,
                    'garantia_meses': oferta.garantia_meses,
                })
            
            oferentes.append(oferente)
        
        return oferentes

    def _load_documentos(self, session, licitacion_id: int) -> List[Dict]:
        """Carga los documentos de una licitación."""
        query = text("""
            SELECT 
                id, codigo, nombre, categoria, comentario, presentado,
                subsanable, ruta_archivo, responsable, revisado, obligatorio,
                orden_pliego, requiere_subsanacion
            FROM documentos
            WHERE licitacion_id = :lic_id
            ORDER BY orden_pliego, id
        """)
        result = session.execute(query, {'lic_id': licitacion_id})
        
        documentos = []
        for row in result:
            documentos.append({
                'id': row.id,
                'codigo': row.codigo,
                'nombre': row.nombre,
                'categoria': row.categoria,
                'comentario': row.comentario,
                'presentado': row.presentado,
                'subsanable': row.subsanable,
                'ruta_archivo': row.ruta_archivo,
                'responsable': row.responsable,
                'revisado': row.revisado,
                'obligatorio': row.obligatorio,
                'orden_pliego': row.orden_pliego,
                'requiere_subsanacion': row.requiere_subsanacion,
            })
        return documentos

    def list_licitaciones(self) -> List[Licitacion]:
        """Alias de load_all_licitaciones() para compatibilidad."""
        return self.load_all_licitaciones()

    def load_licitacion_by_id(self, lic_id: int) -> Optional[Licitacion]:
        """
        Carga una licitación específica por su ID.
        
        Args:
            lic_id: ID de la licitación
            
        Returns:
            Objeto Licitacion o None si no existe
        """
        if not self._connected:
            raise RuntimeError("Base de datos no conectada.")
        
        # Por eficiencia, podríamos hacer una consulta específica,
        # pero por compatibilidad usamos el método existente
        licitaciones = self.load_all_licitaciones()
        for lic in licitaciones:
            if int(getattr(lic, "id", 0) or 0) == int(lic_id):
                return lic
        return None

    def get_licitacion_by_id(self, lic_id: int):
        """Alias para compatibilidad con la UI."""
        return self.load_licitacion_by_id(lic_id)

    def load_licitacion_by_numero(self, numero: str) -> Optional[Licitacion]:
        """Busca una licitación por su número de proceso."""
        if not self._connected:
            raise RuntimeError("Base de datos no conectada.")
        
        num_norm = (numero or "").strip().lower()
        for lic in self.load_all_licitaciones():
            n = (getattr(lic, "numero_proceso", "") or "").strip().lower()
            if n == num_norm:
                return lic
        return None

    # ----------------------------
    # Escritura de Licitaciones
    # ----------------------------
    
    def save_licitacion(self, licitacion: Licitacion) -> int:
        """
        Guarda o actualiza una licitación completa.
        
        Args:
            licitacion: Objeto Licitacion con todos sus datos
            
        Returns:
            ID de la licitación guardada
        """
        if not self._connected:
            raise RuntimeError("Base de datos no conectada.")
        
        with get_session() as session:
            with session.begin():
                # Convertir cronograma y parámetros a JSON si necesario
                import json
                cronograma = getattr(licitacion, 'cronograma', {}) or {}
                if isinstance(cronograma, str):
                    cronograma_json = cronograma
                else:
                    cronograma_json = json.dumps(cronograma)
                
                params = getattr(licitacion, 'parametros_evaluacion', {}) or {}
                if isinstance(params, str):
                    params_json = params
                else:
                    params_json = json.dumps(params)
                
                lic_id = getattr(licitacion, 'id', None)
                
                if lic_id:
                    # Actualizar existente
                    query = text("""
                        UPDATE licitaciones SET
                            nombre_proceso = :nombre,
                            numero_proceso = :numero,
                            institucion = :institucion,
                            estado = :estado,
                            fase_A_superada = :fase_a,
                            fase_B_superada = :fase_b,
                            adjudicada = :adjudicada,
                            adjudicada_a = :adjudicada_a,
                            motivo_descalificacion = :motivo,
                            cronograma = :cronograma,
                            parametros_evaluacion = :parametros
                        WHERE id = :id
                    """)
                    session.execute(query, {
                        'id': lic_id,
                        'nombre': getattr(licitacion, 'nombre_proceso', ''),
                        'numero': getattr(licitacion, 'numero_proceso', ''),
                        'institucion': getattr(licitacion, 'institucion', ''),
                        'estado': getattr(licitacion, 'estado', 'Iniciada'),
                        'fase_a': _to_bool(getattr(licitacion, 'fase_A_superada', False)),
                        'fase_b': _to_bool(getattr(licitacion, 'fase_B_superada', False)),
                        'adjudicada': _to_bool(getattr(licitacion, 'adjudicada', False)),
                        'adjudicada_a': getattr(licitacion, 'adjudicada_a', None),
                        'motivo': getattr(licitacion, 'motivo_descalificacion', None),
                        'cronograma': cronograma_json,
                        'parametros': params_json,
                    })
                else:
                    # Insertar nueva
                    query = text("""
                        INSERT INTO licitaciones (
                            nombre_proceso, numero_proceso, institucion, estado,
                            fase_A_superada, fase_B_superada, adjudicada, adjudicada_a,
                            motivo_descalificacion, fecha_creacion, cronograma, parametros_evaluacion
                        ) VALUES (
                            :nombre, :numero, :institucion, :estado,
                            :fase_a, :fase_b, :adjudicada, :adjudicada_a,
                            :motivo, :fecha, :cronograma, :parametros
                        )
                    """)
                    result = session.execute(query, {
                        'nombre': getattr(licitacion, 'nombre_proceso', ''),
                        'numero': getattr(licitacion, 'numero_proceso', ''),
                        'institucion': getattr(licitacion, 'institucion', ''),
                        'estado': getattr(licitacion, 'estado', 'Iniciada'),
                        'fase_a': _to_bool(getattr(licitacion, 'fase_A_superada', False)),
                        'fase_b': _to_bool(getattr(licitacion, 'fase_B_superada', False)),
                        'adjudicada': _to_bool(getattr(licitacion, 'adjudicada', False)),
                        'adjudicada_a': getattr(licitacion, 'adjudicada_a', None),
                        'motivo': getattr(licitacion, 'motivo_descalificacion', None),
                        'fecha': getattr(licitacion, 'fecha_creacion', str(_dt.date.today())),
                        'cronograma': cronograma_json,
                        'parametros': params_json,
                    })
                    lic_id = result.lastrowid
                    setattr(licitacion, 'id', lic_id)
                
                # TODO: Guardar relaciones (lotes, documentos, oferentes, empresas_nuestras)
                # Por ahora solo guardamos la licitación principal
                
                return int(lic_id)

    # ----------------------------
    # Catálogos Maestros
    # ----------------------------
    
    def get_empresas_maestras(self) -> List[Dict[str, Any]]:
        """Obtiene la lista de empresas maestras."""
        if not self._connected:
            raise RuntimeError("Base de datos no conectada.")
        
        with get_session() as session:
            query = text("SELECT nombre, rnc, telefono, email, direccion FROM empresas_maestras ORDER BY nombre")
            result = session.execute(query)
            return [dict(row._mapping) for row in result]

    def get_instituciones_maestras(self) -> List[Dict[str, Any]]:
        """Obtiene la lista de instituciones maestras."""
        if not self._connected:
            raise RuntimeError("Base de datos no conectada.")
        
        with get_session() as session:
            query = text("SELECT nombre, tipo, contacto, telefono, email FROM instituciones_maestras ORDER BY nombre")
            result = session.execute(query)
            return [dict(row._mapping) for row in result]

    def get_documentos_maestros(self) -> List[Documento]:
        """Obtiene los documentos maestros como objetos Documento."""
        if not self._connected:
            raise RuntimeError("Base de datos no conectada.")
        
        with get_session() as session:
            query = text("""
                SELECT id, codigo, nombre, categoria, comentario, ruta_archivo
                FROM documentos_maestros
                WHERE empresa_nombre IS NULL
                ORDER BY categoria, nombre
            """)
            result = session.execute(query)
            
            documentos = []
            for row in result:
                doc = Documento(
                    id=row.id,
                    codigo=row.codigo,
                    nombre=row.nombre,
                    categoria=row.categoria,
                    comentario=row.comentario,
                    ruta_archivo=row.ruta_archivo,
                )
                documentos.append(doc)
            return documentos

    def get_competidores_maestros(self) -> List[Dict[str, Any]]:
        """Obtiene la lista de competidores maestros."""
        if not self._connected:
            raise RuntimeError("Base de datos no conectada.")
        
        with get_session() as session:
            query = text("SELECT nombre, rnc, sector FROM competidores_maestros ORDER BY nombre")
            result = session.execute(query)
            return [dict(row._mapping) for row in result]

    def get_responsables_maestros(self) -> List[Dict[str, Any]]:
        """Obtiene la lista de responsables maestros."""
        if not self._connected:
            raise RuntimeError("Base de datos no conectada.")
        
        with get_session() as session:
            query = text("SELECT nombre, cargo, email, telefono FROM responsables_maestros ORDER BY nombre")
            result = session.execute(query)
            return [dict(row._mapping) for row in result]

    # ----------------------------
    # Utilitarios
    # ----------------------------
    
    def create_backup(self, dst_path: str) -> None:
        """
        Crea un backup de la base de datos MySQL.
        
        Args:
            dst_path: Ruta donde guardar el backup (archivo .sql)
        """
        import subprocess
        
        host = os.getenv('DB_HOST', 'localhost')
        port = os.getenv('DB_PORT', '3306')
        user = os.getenv('DB_USER', 'zoec_app')
        password = os.getenv('DB_PASSWORD', '')
        database = os.getenv('DB_NAME', 'zoec_db')
        
        # Usar mysqldump
        cmd = [
            'mysqldump',
            '-h', host,
            '-P', port,
            '-u', user,
            f'-p{password}',
            database
        ]
        
        with open(dst_path, 'w', encoding='utf-8') as f:
            subprocess.run(cmd, stdout=f, check=True)
        
        print(f"✅ Backup creado: {dst_path}")

    def search_global(self, term: str) -> List[Dict[str, Any]]:
        """Búsqueda global en licitaciones."""
        # TODO: Implementar búsqueda fulltext en MySQL
        return []

    def get_setting(self, clave: str, default: Optional[str] = None) -> Optional[str]:
        """Obtiene una configuración de la app."""
        if not self._connected:
            return default
        
        with get_session() as session:
            query = text("SELECT valor FROM config_app WHERE clave = :clave")
            result = session.execute(query, {'clave': clave})
            row = result.fetchone()
            return row.valor if row else default

    def set_setting(self, clave: str, valor: str) -> None:
        """Guarda una configuración de la app."""
        if not self._connected:
            return
        
        with get_session() as session:
            with session.begin():
                # INSERT ... ON DUPLICATE KEY UPDATE
                query = text("""
                    INSERT INTO config_app (clave, valor)
                    VALUES (:clave, :valor)
                    ON DUPLICATE KEY UPDATE valor = :valor
                """)
                session.execute(query, {'clave': clave, 'valor': valor})

    # ----------------------------
    # Mapeo de Datos
    # ----------------------------
    
    def _map_licitacion_dict_to_model(self, d: Dict[str, Any]) -> Licitacion:
        """Convierte un diccionario a objeto Licitacion."""
        import json
        
        # Parsear JSON si es string
        cronograma = d.get('cronograma') or {}
        if isinstance(cronograma, str):
            try:
                cronograma = json.loads(cronograma)
            except:
                cronograma = {}
        
        params = d.get('parametros_evaluacion') or {}
        if isinstance(params, str):
            try:
                params = json.loads(params)
            except:
                params = {}
        
        # Crear licitación
        lic = Licitacion(
            id=d.get('id'),
            nombre_proceso=d.get('nombre_proceso', ''),
            numero_proceso=d.get('numero_proceso', ''),
            institucion=d.get('institucion', ''),
            estado=d.get('estado', 'Iniciada'),
            fase_A_superada=_to_bool(d.get('fase_A_superada')),
            fase_B_superada=_to_bool(d.get('fase_B_superada')),
            adjudicada=_to_bool(d.get('adjudicada')),
            adjudicada_a=d.get('adjudicada_a'),
            motivo_descalificacion=d.get('motivo_descalificacion'),
            fecha_creacion=d.get('fecha_creacion', str(_dt.date.today())),
            empresas_nuestras=[Empresa(e) for e in (d.get('empresas_nuestras') or [])],
        )
        
        # Agregar datos adicionales
        lic.cronograma = cronograma
        if hasattr(lic, 'parametros_evaluacion'):
            setattr(lic, 'parametros_evaluacion', params)
        
        # Mapear relaciones
        lic.lotes = [self._map_lote_dict_to_model(l) for l in (d.get('lotes') or [])]
        lic.oferentes_participantes = [self._map_oferente_dict_to_model(o) for o in (d.get('oferentes_participantes') or [])]
        lic.documentos_solicitados = [self._map_documento_dict_to_model(doc) for doc in (d.get('documentos_solicitados') or [])]
        
        return lic

    def _map_lote_dict_to_model(self, l: Dict[str, Any]) -> Lote:
        """Convierte un diccionario a objeto Lote."""
        return Lote(
            id=l.get('id'),
            numero=str(l.get('numero', '')),
            nombre=l.get('nombre', ''),
            monto_base=_to_float(l.get('monto_base'), 0.0),
            monto_base_personal=_to_float(l.get('monto_base_personal'), 0.0),
            monto_ofertado=_to_float(l.get('monto_ofertado'), 0.0),
            participamos=_to_bool(l.get('participamos')),
            fase_A_superada=_to_bool(l.get('fase_A_superada')),
            ganador_nombre=l.get('ganador_nombre', ''),
            empresa_nuestra=l.get('empresa_nuestra'),
            ganado_por_nosotros=_to_bool(l.get('ganado_por_nosotros')),
        )

    def _map_documento_dict_to_model(self, d: Dict[str, Any]) -> Documento:
        """Convierte un diccionario a objeto Documento."""
        return Documento(
            id=d.get('id'),
            codigo=d.get('codigo', ''),
            nombre=d.get('nombre', ''),
            categoria=d.get('categoria', ''),
            comentario=d.get('comentario', ''),
            presentado=_to_bool(d.get('presentado')),
            subsanable=d.get('subsanable', 'Subsanable'),
            ruta_archivo=d.get('ruta_archivo', ''),
            responsable=d.get('responsable', 'Sin Asignar'),
            revisado=_to_bool(d.get('revisado')),
            obligatorio=_to_bool(d.get('obligatorio')),
            orden_pliego=_to_int(d.get('orden_pliego')),
            requiere_subsanacion=_to_bool(d.get('requiere_subsanacion')),
        )

    def _map_oferente_dict_to_model(self, o: Dict[str, Any]) -> Oferente:
        """Convierte un diccionario a objeto Oferente."""
        of = Oferente(
            nombre=o.get('nombre', ''),
            comentario=o.get('comentario', ''),
            ofertas_por_lote=[]
        )
        
        offers = []
        for it in (o.get('ofertas_por_lote') or []):
            offers.append({
                'lote_numero': str(it.get('lote_numero', '')),
                'monto': _to_float(it.get('monto'), 0.0),
                'paso_fase_A': _to_bool(it.get('paso_fase_A')),
                'plazo_entrega': _to_int(it.get('plazo_entrega'), 0),
                'garantia_meses': _to_int(it.get('garantia_meses'), 0),
            })
        of.ofertas_por_lote = offers
        
        return of
