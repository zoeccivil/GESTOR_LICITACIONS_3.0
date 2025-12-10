"""Firebase Firestore helper utilities for the LICITACIONES app.

Esta versión usa FieldFilter (cuando está disponible) con el parámetro keyword
'filter=' en .where(...) para evitar el warning:
  UserWarning: Detected filter using positional arguments. Prefer using the 'filter' keyword argument instead.

Si FieldFilter no está disponible en tu versión de google-cloud-firestore, cae
en el uso clásico con argumentos posicionales (seguirá funcionando, pero puede
mostrar el warning).
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from google.cloud.firestore import Client

# FieldFilter está en firestore_v1 (recomendado en versiones recientes)
try:
    from google.cloud.firestore_v1 import FieldFilter  # type: ignore
    _HAS_FIELD_FILTER = True
except Exception:
    FieldFilter = None  # type: ignore
    _HAS_FIELD_FILTER = False

FirestoreCallback = Callable[[List[Dict[str, Any]]], None]

_client: Optional[Client] = None


def set_client(client: Client) -> None:
    """Register the global Firestore client used throughout the application."""
    global _client
    _client = client


def get_client() -> Client:
    if _client is None:
        raise RuntimeError("Firestore client has not been configured. Call set_client() first.")
    return _client


def _collection(collection: str):
    return get_client().collection(collection)


def _where_eq(query, field: str, value: Any):
    """
    Aplica un filtro de igualdad de forma compatible con versiones:
    - Preferido (sin warnings): where(filter=FieldFilter(...))
    - Fallback: where(field, "==", value)
    """
    if _HAS_FIELD_FILTER and FieldFilter is not None:
        return query.where(filter=FieldFilter(field, "==", value))  # evita warning
    return query.where(field, "==", value)  # fallback (puede advertir, pero funciona)


def get_all(collection: str) -> List[Dict[str, Any]]:
    """
    Devuelve todos los documentos de una colección como lista de diccionarios.
    Cada dict incluirá el campo 'id' con el ID del documento.
    """
    docs = _collection(collection).stream()
    results: List[Dict[str, Any]] = []
    for doc in docs:
        data = doc.to_dict() or {}
        data.setdefault("id", doc.id)
        results.append(data)
    return results


def get_by_id(collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
    """
    Devuelve un documento por ID como dict (incluye 'id') o None si no existe.
    """
    snapshot = _collection(collection).document(str(doc_id)).get()
    if not snapshot.exists:
        return None
    data = snapshot.to_dict() or {}
    data.setdefault("id", snapshot.id)
    return data


def add_doc(collection: str, data: Dict[str, Any]) -> str:
    """
    Crea un nuevo documento con ID automático y devuelve dicho ID.
    """
    ref = _collection(collection).document()
    ref.set(data)
    return ref.id


def set_doc(collection: str, doc_id: str, data: Dict[str, Any]) -> None:
    """
    Crea o reemplaza el documento con ID doc_id (operación tipo 'set' sin merge).
    """
    _collection(collection).document(str(doc_id)).set(data)


def update_doc(collection: str, doc_id: str, data: Dict[str, Any]) -> None:
    """
    Actualiza (merge) el documento con ID doc_id. Crea campos nuevos sin borrar los existentes.
    """
    _collection(collection).document(str(doc_id)).set(data, merge=True)


def delete_doc(collection: str, doc_id: str) -> None:
    """
    Elimina el documento con ID doc_id.
    """
    _collection(collection).document(str(doc_id)).delete()


def subscribe_collection(collection: str, callback: FirestoreCallback):
    """
    Subscribe to real-time updates for a collection.

    Retorna una función que, al llamarse, cancela la suscripción (unsubscribe).
    """

    def _on_snapshot(docs, changes, read_time):
        items: List[Dict[str, Any]] = []
        for snap in docs:
            data = snap.to_dict() or {}
            data.setdefault("id", snap.id)
            items.append(data)
        callback(items)

    watch = _collection(collection).on_snapshot(_on_snapshot)
    return watch.unsubscribe


# Helpers de consulta simples
def find_one_by_field(collection: str, field: str, value: Any) -> Optional[Dict[str, Any]]:
    """
    Devuelve el primer documento de 'collection' cuyo campo 'field' == value.
    Incluye 'id' en el dict resultado. Devuelve None si no hay coincidencias.
    """
    if value is None:
        return None
    query = _where_eq(_collection(collection), field, value).limit(1)
    for snap in query.stream():
        data = snap.to_dict() or {}
        data.setdefault("id", snap.id)
        return data
    return None


def find_all_by_field(collection: str, field: str, value: Any, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Devuelve todos los documentos que cumplan field == value.
    Si 'limit' se especifica, limita el número de resultados.
    """
    if value is None:
        return []
    q = _where_eq(_collection(collection), field, value)
    if isinstance(limit, int) and limit > 0:
        q = q.limit(limit)
    results: List[Dict[str, Any]] = []
    for snap in q.stream():
        data = snap.to_dict() or {}
        data.setdefault("id", snap.id)
        results.append(data)
    return results