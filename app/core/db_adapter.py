"""Database adapter that proxies all persistence to Firebase Firestore."""
from __future__ import annotations

import datetime as _dt
import unicodedata
from typing import Any, Callable, Dict, Iterable, List, Optional

from google.cloud.firestore import Client

from .firebase_adapter import (
    add_doc,
    delete_doc,
    get_all,
    get_by_id,
    get_client,
    set_doc,
    subscribe_collection,
    update_doc,
    find_one_by_field,  # requiere versión actualizada de firebase_adapter
)
from .models import Documento, Empresa, Licitacion, Lote, Oferente
from app.core.log_utils import get_logger

logger = get_logger("db_adapter")


LICITACIONES_COLLECTION = "licitaciones"
EMPRESAS_COLLECTION = "empresas_maestras"
INSTITUCIONES_COLLECTION = "instituciones_maestras"
DOCUMENTOS_COLLECTION = "documentos_maestros"
COMPETIDORES_COLLECTION = "competidores_maestros"
RESPONSABLES_COLLECTION = "responsables_maestros"
FALLAS_COLLECTION = "fallas_fase_a"
SUBSANACIONES_COLLECTION = "subsanaciones_eventos"
SETTINGS_COLLECTION = "settings"


def _slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    value = "".join(ch for ch in value if ch.isalnum() or ch in ("-", "_"))
    return value.strip().lower() or "item"


def _canon(s: str) -> str:
    """
    Canonicaliza un número de proceso:
    - recorta bordes,
    - colapsa espacios internos,
    - convierte a mayúsculas.
    """
    if not s:
        return ""
    s = " ".join((s or "").strip().split())
    return s.upper()


class DatabaseAdapter:
    """High level helper used by the PyQt UI to interact with Firestore."""

    def __init__(self, client: Optional[Client] = None) -> None:
        self._client = client
        self._subscriptions: List[Callable[[], None]] = []

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def open(self) -> None:  # compatibility no-op
        if self._client is None:
            self._client = get_client()

    def close(self) -> None:
        for unsubscribe in self._subscriptions:
            try:
                unsubscribe()
            except Exception:
                pass
        self._subscriptions.clear()

    # ------------------------------------------------------------------
    # Firestore helpers
    # ------------------------------------------------------------------
    def _ensure_client(self) -> Client:
        if self._client is None:
            self._client = get_client()
        return self._client

    # ------------------------------------------------------------------
    # Licitaciones CRUD
    # ------------------------------------------------------------------
    def subscribe_to_licitaciones(self, callback: Callable[[List[Licitacion]], None]) -> None:
        def _on_update(items: List[Dict[str, Any]]):
            callback([self._map_licitacion_dict_to_model(item) for item in items])

        unsubscribe = subscribe_collection(LICITACIONES_COLLECTION, _on_update)
        self._subscriptions.append(unsubscribe)

    def load_all_licitaciones(self) -> List[Licitacion]:
        docs = get_all(LICITACIONES_COLLECTION)
        return [self._map_licitacion_dict_to_model(doc) for doc in docs]

    def list_licitaciones(self) -> List[Licitacion]:
        return self.load_all_licitaciones()

    def load_licitacion_by_id(self, lic_id: Any) -> Optional[Licitacion]:
        if lic_id is None:
            return None
        data = get_by_id(LICITACIONES_COLLECTION, str(lic_id))
        if not data:
            return None
        return self._map_licitacion_dict_to_model(data)

    def _find_existing_by_numero(self, numero_raw: str) -> Optional[Dict[str, Any]]:
        """
        Busca una licitación existente por número:
        1) numero_canon (preferido),
        2) numero_proceso exacto,
        3) barrido en memoria comparando canónico (compatibilidad).
        Devuelve el dict del documento (incluye 'id') o None.
        """
        numero_canon = _canon(numero_raw)
        if numero_canon:
            found = find_one_by_field(LICITACIONES_COLLECTION, "numero_canon", numero_canon)
            if found:
                return found
        # Intento exacto por numero_proceso (por compatibilidad)
        if numero_raw:
            found = find_one_by_field(LICITACIONES_COLLECTION, "numero_proceso", numero_raw)
            if found:
                return found
        # Último recurso: barrido en memoria (dataset pequeño)
        for doc in get_all(LICITACIONES_COLLECTION):
            doc_num = doc.get("numero_proceso") or ""
            if _canon(doc_num) == numero_canon and numero_canon:
                return doc
        return None

    def load_licitacion_by_numero(self, numero: str) -> Optional[Licitacion]:
        numero = (numero or "").strip()
        if not numero:
            return None
        found = self._find_existing_by_numero(numero)
        if not found:
            return None
        return self._map_licitacion_dict_to_model(found)

    def save_licitacion(self, licitacion: Licitacion) -> str:
        """
        Guarda/actualiza una licitación.

        Reglas:
        - CREAR (sin id): exige numero_proceso, nombre_proceso y al menos 1 lote.
          Si falta alguno, NO crea y lanza ValueError (evita creaciones accidentales).
        - ACTUALIZAR (con id): actualiza sin exigir lotes (permite ediciones parciales).
        - Upsert robusto por número:
            * Calcula numero_canon y lo guarda en el documento.
            * Busca primero por numero_canon; si no, por numero_proceso; si no, barrido canónico.
            * Si existe: actualiza ese doc (evita duplicados).
            * Si no existe: crea nuevo doc.
        - Limpia 'id': None/"" del payload antes de escribir para no almacenar 'id': None.
        """
        # DEBUG consola
        print("[DEBUG][DB.save_licitacion] Guardando licitación ID actual:",
              getattr(licitacion, "id", None),
              "numero_proceso:", getattr(licitacion, "numero_proceso", None))
        print("[DEBUG][DB.save_licitacion] Lotes en objeto Licitacion antes de to_dict:")
        for l in licitacion.lotes:
            print(f"   [MODEL-LOTE] numero={l.numero!r}, empresa_nuestra={getattr(l, 'empresa_nuestra', None)!r}, monto_ofertado={getattr(l, 'monto_ofertado', None)!r}")

        # DEBUG a archivo
        from app.core.log_utils import get_logger  # import local para evitar ciclos
        logger = get_logger("db_adapter")
        logger.debug(
            "save_licitacion: Guardando licitación ID=%s numero_proceso=%s",
            getattr(licitacion, "id", None),
            getattr(licitacion, "numero_proceso", None),
        )
        for l in licitacion.lotes:
            logger.debug(
                "save_licitacion MODEL-LOTE before to_dict: numero=%r empresa_nuestra=%r monto_base=%r monto_base_personal=%r monto_ofertado=%r participamos=%r fase_A_superada=%r ganador_nombre=%r ganado_por_nosotros=%r",
                getattr(l, "numero", None),
                getattr(l, "empresa_nuestra", None),
                getattr(l, "monto_base", None),
                getattr(l, "monto_base_personal", None),
                getattr(l, "monto_ofertado", None),
                getattr(l, "participamos", None),
                getattr(l, "fase_A_superada", None),
                getattr(l, "ganador_nombre", None),
                getattr(l, "ganado_por_nosotros", None),
            )

        payload = licitacion.to_dict() or {}

        # DEBUG consola: payload inicial
        print("[DEBUG][DB.save_licitacion] Payload.to_dict() lotes a guardar:")
        for l in payload.get("lotes", []):
            print("   [PAYLOAD-LOTE]", l)

        # DEBUG archivo: payload inicial
        logger.debug("save_licitacion: Payload lotes a guardar (después de to_dict):")
        for l in payload.get("lotes", []):
            logger.debug("PAYLOAD-LOTE %s", l)

        # Normalizar campos básicos
        numero_raw = (payload.get("numero_proceso") or licitacion.numero_proceso or "").strip()
        nombre_raw = (payload.get("nombre_proceso") or licitacion.nombre_proceso or "").strip()
        payload["numero_proceso"] = numero_raw
        payload["nombre_proceso"] = nombre_raw
        payload["numero_canon"] = _canon(numero_raw)

        # Evitar escribir 'id': None en el documento
        if not payload.get("id"):
            payload.pop("id", None)

        lic_id = licitacion.id or payload.get("id")

        # DEBUG consola: payload final antes de escribir
        print("[DEBUG][DB.save_licitacion] numero_proceso normalizado:", numero_raw)
        print("[DEBUG][DB.save_licitacion] ID usado para upsert:", lic_id)
        print("[DEBUG][DB.save_licitacion] Lotes en payload final antes de set_doc/add_doc:")
        for l in payload.get("lotes", []):
            print("   [FINAL-LOTE]", l)

        # DEBUG archivo: payload final antes de set_doc/add_doc
        logger.debug("save_licitacion: numero_proceso normalizado=%s ID_usado=%s", numero_raw, lic_id)
        logger.debug("save_licitacion: Lotes en payload final antes de set_doc/add_doc:")
        for l in payload.get("lotes", []):
            logger.debug("FINAL-LOTE %s", l)

        # Si es actualización (hay id), actualiza tal cual
        if lic_id:
            print(f"[DEBUG][DB.save_licitacion] Actualizando documento existente {lic_id} en Firestore")
            logger.debug("save_licitacion: Actualizando documento existente id=%s", lic_id)
            set_doc(LICITACIONES_COLLECTION, str(lic_id), payload)
            licitacion.id = str(lic_id)
            return str(lic_id)

        # Si es creación, validar mínimos
        lotes_payload = payload.get("lotes")
        if lotes_payload is None and getattr(licitacion, "lotes", None) is not None:
            lotes_payload = [
                (l.to_dict() if hasattr(l, "to_dict") else dict(l))  # type: ignore
                for l in licitacion.lotes
            ]

        if not numero_raw or not nombre_raw or not lotes_payload or len(lotes_payload) == 0:
            raise ValueError(
                "Para crear una licitación se requiere: Código (numero_proceso), Nombre y al menos un Lote."
            )

        # Upsert robusto por número
        existing = self._find_existing_by_numero(numero_raw)
        if existing:
            print(f"[DEBUG][DB.save_licitacion] Upsert: actualizando doc existente con id={existing['id']}")
            logger.debug("save_licitacion: Upsert actualizando doc existente id=%s", existing["id"])
            set_doc(LICITACIONES_COLLECTION, existing["id"], payload)
            licitacion.id = existing["id"]
            return str(existing["id"])

        # Crear nuevo documento (ID automático)
        print("[DEBUG][DB.save_licitacion] Creando nuevo documento en Firestore...")
        logger.debug("save_licitacion: Creando nuevo documento en Firestore (add_doc)")
        new_id = add_doc(LICITACIONES_COLLECTION, payload)
        print("[DEBUG][DB.save_licitacion] Nuevo documento creado con id:", new_id)
        logger.debug("save_licitacion: Nuevo documento creado con id=%s", new_id)
        licitacion.id = new_id
        return str(new_id)
    
    def delete_licitacion(self, lic_id: Any) -> None:
        if lic_id is None:
            return
        delete_doc(LICITACIONES_COLLECTION, str(lic_id))

    # ------------------------------------------------------------------
    # Master collections helpers
    # ------------------------------------------------------------------
    def _get_master_items(self, collection: str) -> List[Dict[str, Any]]:
        return get_all(collection)

    def _save_master_items(self, collection: str, items: Iterable[Dict[str, Any]], key: str = "nombre") -> bool:
        existing = {doc["id"]: doc for doc in get_all(collection)}
        new_ids: Dict[str, Dict[str, Any]] = {}
        for item in items:
            if isinstance(item, Documento):
                data = item.to_dict()
            else:
                data = dict(item)
            identifier = data.get("id") or _slugify(str(data.get(key, "")))
            data["id"] = identifier
            set_doc(collection, identifier, data)
            new_ids[identifier] = data
        for doc_id in existing:
            if doc_id not in new_ids:
                delete_doc(collection, doc_id)
        return True

    def get_empresas_maestras(self) -> List[Dict[str, Any]]:
        return self._get_master_items(EMPRESAS_COLLECTION)

    def save_empresas_maestras(self, lista_empresas: List[Dict[str, Any]]) -> bool:
        return self._save_master_items(EMPRESAS_COLLECTION, lista_empresas)

    def get_instituciones_maestras(self) -> List[Dict[str, Any]]:
        return self._get_master_items(INSTITUCIONES_COLLECTION)

    def save_instituciones_maestras(self, lista_instituciones: List[Dict[str, Any]]) -> bool:
        return self._save_master_items(INSTITUCIONES_COLLECTION, lista_instituciones)

    def get_documentos_maestros(self) -> List[Documento]:
        docs = self._get_master_items(DOCUMENTOS_COLLECTION)
        return [self._map_documento_dict_to_model(d) for d in docs]

    def save_documentos_maestros(self, docs: List[Documento]) -> bool:
        return self._save_master_items(DOCUMENTOS_COLLECTION, [doc.to_dict() for doc in docs], key="codigo")

    def get_competidores_maestros(self) -> List[Dict[str, Any]]:
        return self._get_master_items(COMPETIDORES_COLLECTION)

    def save_competidores_maestros(self, items: List[Dict[str, Any]]) -> bool:
        return self._save_master_items(COMPETIDORES_COLLECTION, items)

    def get_responsables_maestros(self) -> List[Dict[str, Any]]:
        return self._get_master_items(RESPONSABLES_COLLECTION)

    def save_responsables_maestros(self, items: List[Dict[str, Any]]) -> bool:
        return self._save_master_items(RESPONSABLES_COLLECTION, items)

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
        replace = set(replace_tables or [])
        if empresas is not None and (not replace or "empresas_maestras" in replace):
            self.save_empresas_maestras(empresas)
        if instituciones is not None and (not replace or "instituciones_maestras" in replace):
            self.save_instituciones_maestras(instituciones)
        if documentos_maestros is not None and (not replace or "documentos_maestros" in replace):
            self._save_master_items(DOCUMENTOS_COLLECTION, documentos_maestros, key="codigo")
        if competidores_maestros is not None and (not replace or "competidores_maestros" in replace):
            self.save_competidores_maestros(competidores_maestros)
        if responsables_maestros is not None and (not replace or "responsables_maestros" in replace):
            self.save_responsables_maestros(responsables_maestros)

    def _get_master_table(self, table_name: str) -> List[Dict[str, Any]]:
        mapping = {
            "empresas_maestras": EMPRESAS_COLLECTION,
            "instituciones_maestras": INSTITUCIONES_COLLECTION,
            "documentos_maestros": DOCUMENTOS_COLLECTION,
            "competidores_maestros": COMPETIDORES_COLLECTION,
            "responsables_maestros": RESPONSABLES_COLLECTION,
        }
        collection = mapping.get(table_name, table_name)
        return self._get_master_items(collection)

    def is_institucion_en_uso(self, nombre_institucion: str) -> bool:
        nombre = (nombre_institucion or "").strip().lower()
        for lic in self.load_all_licititaciones():
            if (lic.institucion or "").strip().lower() == nombre:
                return True
        return False

    def is_empresa_en_uso(self, nombre_empresa: str) -> bool:
        nombre = (nombre_empresa or "").strip().lower()
        for lic in self.load_all_licititaciones():
            if any((emp.nombre or "").strip().lower() == nombre for emp in lic.empresas_nuestras):
                return True
            if any((lote.empresa_nuestra or "").strip().lower() == nombre for lote in lic.lotes):
                return True
        return False

    # ------------------------------------------------------------------
    # Auxiliar mappers
    # ------------------------------------------------------------------
    def _map_licitacion_dict_to_model(self, data: Dict[str, Any]) -> Licitacion:
        # DEBUG consola: ver cómo vienen los lotes crudos desde Firestore
        print("[DEBUG][DB._map_licitacion] Mapeando licitación desde dict. ID:",
              data.get("id"), "numero_proceso:", data.get("numero_proceso"))
        print("[DEBUG][DB._map_licitacion] Lotes crudos desde Firestore:")
        for l in data.get("lotes", []):
            print("   [RAW-LOTE]", l)

        # DEBUG archivo
        from app.core.log_utils import get_logger
        logger = get_logger("db_adapter")
        logger.debug(
            "_map_licitacion_dict_to_model: Mapeando licitación ID=%s numero_proceso=%s",
            data.get("id"),
            data.get("numero_proceso"),
        )
        for l in data.get("lotes", []):
            logger.debug("RAW-LOTE from Firestore: %s", l)

        lic = Licitacion(
            id=data.get("id"),
            nombre_proceso=data.get("nombre_proceso", ""),
            numero_proceso=data.get("numero_proceso", ""),
            institucion=data.get("institucion", ""),
            estado=data.get("estado", "Iniciada"),
            fase_A_superada=bool(data.get("fase_A_superada", False)),
            fase_B_superada=bool(data.get("fase_B_superada", False)),
            adjudicada=bool(data.get("adjudicada", False)),
            adjudicada_a=data.get("adjudicada_a", ""),
            motivo_descalificacion=data.get("motivo_descalificacion", ""),
            docs_completos_manual=bool(data.get("docs_completos_manual", False)),
            last_modified=data.get("last_modified"),
            fecha_creacion=data.get("fecha_creacion", str(_dt.date.today())),
        )

        lic.empresas_nuestras = [Empresa(e.get("nombre", "")) for e in data.get("empresas_nuestras", [])]
        lic.lotes = [self._map_lote_dict_to_model(l) for l in data.get("lotes", [])]
        lic.oferentes_participantes = [
            self._map_oferente_dict_to_model(o) for o in data.get("oferentes_participantes", [])
        ]
        lic.documentos_solicitados = [
            self._map_documento_dict_to_model(d) for d in data.get("documentos_solicitados", [])
        ]
        lic.cronograma = data.get("cronograma", {})
        lic.fallas_fase_a = data.get("fallas_fase_a", [])
        lic.parametros_evaluacion = data.get("parametros_evaluacion", {})

        # DEBUG consola: ver cómo quedan los lotes mapeados
        print("[DEBUG][DB._map_licitacion] Lotes mapeados a modelo:")
        for l in lic.lotes:
            print(f"   [MODEL-LOTE] numero={l.numero!r}, empresa_nuestra={getattr(l, 'empresa_nuestra', None)!r}")

        # DEBUG archivo: lotes mapeados
        logger.debug("_map_licitacion_dict_to_model: Lotes mapeados a modelo:")
        for l in lic.lotes:
            logger.debug(
                "MODEL-LOTE numero=%r empresa_nuestra=%r monto_base=%r monto_base_personal=%r monto_ofertado=%r participamos=%r fase_A_superada=%r ganador_nombre=%r ganado_por_nosotros=%r",
                getattr(l, "numero", None),
                getattr(l, "empresa_nuestra", None),
                getattr(l, "monto_base", None),
                getattr(l, "monto_base_personal", None),
                getattr(l, "monto_ofertado", None),
                getattr(l, "participamos", None),
                getattr(l, "fase_A_superada", None),
                getattr(l, "ganador_nombre", None),
                getattr(l, "ganado_por_nosotros", None),
            )

        return lic    

    def _map_lote_dict_to_model(self, data: Dict[str, Any]) -> Lote:
        return Lote(
            id=data.get("id"),
            numero=str(data.get("numero", "")),
            nombre=data.get("nombre", ""),
            monto_base=float(data.get("monto_base", 0.0) or 0.0),
            monto_base_personal=float(data.get("monto_base_personal", 0.0) or 0.0),
            monto_ofertado=float(data.get("monto_ofertado", 0.0) or 0.0),
            participamos=bool(data.get("participamos", True)),
            fase_A_superada=bool(data.get("fase_A_superada", True)),
            ganador_nombre=data.get("ganador_nombre", ""),
            ganado_por_nosotros=bool(data.get("ganado_por_nosotros", False)),
            empresa_nuestra=data.get("empresa_nuestra"),
        )

    def _map_documento_dict_to_model(self, data: Dict[str, Any]) -> Documento:
        return Documento(
            id=data.get("id"),
            codigo=data.get("codigo", ""),
            nombre=data.get("nombre", ""),
            categoria=data.get("categoria", ""),
            comentario=data.get("comentario", ""),
            presentado=bool(data.get("presentado", False)),
            subsanable=data.get("subsanable", "Subsanable"),
            ruta_archivo=data.get("ruta_archivo", ""),
            responsable=data.get("responsable", "Sin Asignar"),
            revisado=bool(data.get("revisado", False)),
            obligatorio=bool(data.get("obligatorio", False)),
            orden_pliego=data.get("orden_pliego"),
            requiere_subsanacion=bool(data.get("requiere_subsanacion", False)),
        )

    def _map_oferente_dict_to_model(self, data: Dict[str, Any]) -> Oferente:
        of = Oferente(nombre=data.get("nombre", ""), comentario=data.get("comentario", ""))
        of.ofertas_por_lote = list(data.get("ofertas_por_lote", []))
        return of

    # ------------------------------------------------------------------
    # Aggregates / helpers
    # ------------------------------------------------------------------
    def get_all_data(self) -> List[Any]:
        licitaciones = [lic.to_dict() for lic in self.load_all_licitaciones()]
        return [
            licitaciones,
            self.get_empresas_maestras(),
            self.get_instituciones_maestras(),
            [doc.to_dict() for doc in self.get_documentos_maestros()],
            self.get_competidores_maestros(),
            self.get_responsables_maestros(),
        ]

    def get_all_licitaciones_basic_info(self) -> List[Dict[str, Any]]:
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
        lic = self.load_licitacion_by_id(licitacion_id)
        if not lic:
            return False
        if isinstance(orden_por_categoria_or_pairs, (list, tuple)):
            order_map = {
                int(doc_id): int(order)
                for doc_id, order in orden_por_categoria_or_pairs
                if doc_id is not None
            }
            for doc in lic.documentos_solicitados:
                doc_id = getattr(doc, "id", None)
                if doc_id is not None and int(doc_id) in order_map:
                    doc.orden_pliego = order_map[int(doc_id)]
            lic.documentos_solicitados.sort(key=lambda d: d.orden_pliego or 9999)
        self.save_licitacion(lic)
        return True

    def marcar_ganador_lote(
        self,
        licitacion_id: Any,
        lote_num: str,
        ganador: str,
        empresa_nuestra: Optional[str],
    ) -> bool:
        """
        Marca el ganador de un lote y actualiza los flags en el modelo.

        Comportamiento importante:
        - Siempre actualiza lote.ganador_nombre.
        - Solo SOBREESCRIBE lote.empresa_nuestra si se recibe un nombre no vacío.
        - Si empresa_nuestra es None o "", NO toca lote.empresa_nuestra (para no
          borrar la empresa que ya estuviera asignada al lote desde TabLotes).
        - ganado_por_nosotros se calcula en función de empresa_nuestra:
            * Si se pasa empresa_nuestra válida -> True
            * Si no se pasa, se pone False, pero se preserva lote.empresa_nuestra.
        """
        lic = self.load_licitacion_by_id(licitacion_id)
        if not lic:
            return False

        for lote in lic.lotes:
            if (lote.numero or "") == str(lote_num):
                # Siempre actualizamos el nombre del ganador
                lote.ganador_nombre = ganador or ""

                # Solo si nos pasan una empresa_nuestra válida, la escribimos
                if empresa_nuestra is not None and empresa_nuestra.strip() != "":
                    lote.empresa_nuestra = empresa_nuestra
                    lote.ganado_por_nosotros = True
                else:
                    # No tocar lote.empresa_nuestra existente; solo marcar que
                    # este ganador no es "nuestro" explícitamente
                    lote.ganado_por_nosotros = False

                break

        self.save_licitacion(lic)
        return True
    

    def borrar_ganador_lote(self, licitacion_id: Any, lote_num: str) -> bool:
        lic = self.load_licitacion_by_id(licitacion_id)
        if not lic:
            return False
        for lote in lic.lotes:
            if (lote.numero or "") == str(lote_num):
                lote.ganador_nombre = ""
                lote.empresa_nuestra = None
                lote.ganado_por_nosotros = False
                break
        self.save_licitacion(lic)
        return True

    # ------------------------------------------------------------------
    # Fallas Fase A management
    # ------------------------------------------------------------------
    def get_fallas_fase_a(self, licitacion_id: Any) -> List[Dict[str, Any]]:
        rows = [doc for doc in get_all(FALLAS_COLLECTION) if str(doc.get("licitacion_id")) == str(licitacion_id)]
        return rows

    def insertar_falla_por_ids(
        self,
        licitacion_id: Any,
        participante_nombre: str,
        documento_id: Any,
        comentario: str,
        es_nuestro: bool,
    ) -> str:
        lic = self.load_licitacion_by_id(licitacion_id)
        documento_nombre = ""
        institucion = lic.institucion if lic else ""
        if lic:
            for doc in lic.documentos_solicitados:
                if str(getattr(doc, "id", "")) == str(documento_id):
                    documento_nombre = doc.nombre
                    break
        data = {
            "licitacion_id": str(licitacion_id),
            "participante_nombre": participante_nombre,
            "documento_id": str(documento_id),
            "documento_nombre": documento_nombre,
            "comentario": comentario,
            "es_nuestro": bool(es_nuestro),
            "institucion": institucion,
        }
        return add_doc(FALLAS_COLLECTION, data)

    def eliminar_fallas_por_ids(self, licitacion_id: Any, falla_ids: Iterable[str]) -> int:
        count = 0
        for item_id in falla_ids:
            delete_doc(FALLAS_COLLECTION, str(item_id))
            count += 1
        return count

    def eliminar_falla_por_ids(self, licitacion_id: Any, documento_id: Any, participante_nombre: str) -> int:
        eliminados = 0
        for doc in get_all(FALLAS_COLLECTION):
            if (
                str(doc.get("licitacion_id")) == str(licitacion_id)
                and str(doc.get("documento_id")) == str(documento_id)
                and (doc.get("participante_nombre") or "") == participante_nombre
            ):
                delete_doc(FALLAS_COLLECTION, doc["id"])
                eliminados += 1
        return eliminados

    def eliminar_falla_por_campos(self, institucion: str, participante_nombre: str, documento_nombre: str) -> int:
        eliminados = 0
        for doc in get_all(FALLAS_COLLECTION):
            if (
                (doc.get("institucion") or "") == institucion
                and (doc.get("participante_nombre") or "") == participante_nombre
                and (doc.get("documento_nombre") or "") == documento_nombre
            ):
                delete_doc(FALLAS_COLLECTION, doc["id"])
                eliminados += 1
        return eliminados

    def actualizar_comentarios_por_ids(self, licitacion_id: Any, items: Iterable[Dict[str, Any]]) -> int:
        updated = 0
        for item in items:
            doc_id = item.get("id")
            if not doc_id:
                continue
            update_doc(FALLAS_COLLECTION, str(doc_id), {"comentario": item.get("comentario", "")})
            updated += 1
        return updated

    def actualizar_comentario_falla_por_ids(
        self,
        licitacion_id: Any,
        documento_id: Any,
        participante_nombre: str,
        comentario: str,
    ) -> int:
        updated = 0
        for doc in get_all(SUBSANACIONES_COLLECTION):
            if (
                str(doc.get("licitacion_id")) == str(licitacion_id)
                and str(doc.get("documento_id")) == str(documento_id)
                and (doc.get("participante_nombre") or "") == participante_nombre
            ):
                update_doc(FALLAS_COLLECTION, doc["id"], {"comentario": comentario})
                updated += 1
        return updated

    def actualizar_comentario_falla(self, institucion: str, participante_nombre: str, documento_nombre: str, comentario: str) -> int:
        updated = 0
        for doc in get_all(FALLAS_COLLECTION):
            if (
                (doc.get("institucion") or "") == institucion
                and (doc.get("participante_nombre") or "") == participante_nombre
                and (doc.get("documento_nombre") or "") == documento_nombre
            ):
                update_doc(FALLAS_COLLECTION, doc["id"], {"comentario": comentario})
                updated += 1
        return updated

    def obtener_historial_subsanacion(self, licitacion_id: Any) -> List[Dict[str, Any]]:
        return [
            evento
            for evento in get_all(SUBSANACIONES_COLLECTION)
            if str(evento.get("licitacion_id")) == str(licitacion_id)
        ]

    # ------------------------------------------------------------------
    # Settings helpers
    # ------------------------------------------------------------------
    def get_setting(self, clave: str, default: Optional[str] = None) -> Optional[str]:
        doc = get_by_id(SETTINGS_COLLECTION, clave)
        if not doc:
            return default
        return doc.get("valor", default)

    def set_setting(self, clave: str, valor: str) -> None:
        set_doc(SETTINGS_COLLECTION, clave, {"valor": valor})

    # ------------------------------------------------------------------
    # Compatibility fallbacks
    # ------------------------------------------------------------------
    def run_sanity_checks(self) -> Dict[str, Any]:
        return {"firestore": True}

    def auto_repair(self, issues: Dict[str, Any]) -> tuple[bool, str]:
        return True, "No repair required with Firestore."