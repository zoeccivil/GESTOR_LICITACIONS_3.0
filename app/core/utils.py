from __future__ import annotations
import os
import sys
import json
from typing import Any, Dict, Optional

import re

def normalize_lote_numero(raw: str | None) -> str:
    """
    Normaliza cualquier formato de número de lote a: 'LOTE X'
    Ejemplos:
    '1' -> 'LOTE 1'
    'Lote 11' -> 'LOTE 11'
    ' lote   3 ' -> 'LOTE 3'
    """
    if not raw:
        return ""

    s = str(raw).strip().upper()

    m = re.search(r"(\d+)", s)
    if not m:
        return s

    return f"LOTE {int(m.group(1))}"



def as_dict(value: Any, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Normaliza un valor a dict:
    - dict -> igual
    - str  -> json.loads si se puede; si no -> {}
    - None/otros -> {}
    """
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return {} if default is None else default
        try:
            return json.loads(s)
        except Exception:
            return {} if default is None else default
    return {} if default is None else default


def obtener_ruta_dropbox() -> Optional[str]:
    """
    Lee la configuración local de Dropbox y devuelve la ruta base si existe.
    """
    try:
        if sys.platform == "win32":
            appdata_path = os.getenv("APPDATA")
            local_appdata_path = os.getenv("LOCALAPPDATA")
            info_json_paths = [
                os.path.join(appdata_path or "", "Dropbox", "info.json"),
                os.path.join(local_appdata_path or "", "Dropbox", "info.json"),
            ]
        else:
            info_json_paths = [os.path.expanduser("~/.dropbox/info.json")]

        for json_path in info_json_paths:
            if os.path.exists(json_path):
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return (data.get("personal") or {}).get("path")
        return None
    except Exception:
        return None


def reconstruir_ruta_absoluta(ruta_guardada: str) -> Optional[str]:
    """
    Convierte una ruta guardada (posiblemente relativa a Dropbox) en una ruta absoluta utilizable.
    """
    if not ruta_guardada:
        return None
    if os.path.isabs(ruta_guardada):
        return ruta_guardada

    dropbox_base = obtener_ruta_dropbox()
    if dropbox_base:
        ruta_norm = ruta_guardada.replace("/", os.sep)
        return os.path.join(dropbox_base, ruta_norm)
    return None

# En app/core/utils.py
import os
import platform
import subprocess
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QMessageBox # Para mostrar errores

def previsualizar_archivo(ruta_archivo: str):
    """
    Intenta abrir un archivo usando la aplicación predeterminada del sistema.
    Usa QDesktopServices para compatibilidad multiplataforma.
    """
    if not ruta_archivo or not os.path.exists(ruta_archivo):
        print(f"WARN: previsualizar_archivo - Archivo no existe o ruta vacía: {ruta_archivo}")
        # Considerar mostrar un QMessageBox aquí si se llama desde la UI
        # QMessageBox.warning(None, "Archivo no encontrado", f"No se pudo encontrar el archivo:\n{ruta_archivo}")
        return False

    print(f"Intentando abrir archivo con QDesktopServices: {ruta_archivo}")
    try:
        # QUrl.fromLocalFile asegura formato correcto para QDesktopServices
        url = QUrl.fromLocalFile(ruta_archivo)
        if not QDesktopServices.openUrl(url):
            print(f"ERROR: QDesktopServices.openUrl falló para: {ruta_archivo}")
            # Mostrar error al usuario si falla
            QMessageBox.warning(None, "Error al Abrir",
                                f"No se pudo abrir el archivo con la aplicación predeterminada:\n{ruta_archivo}")
            return False
        return True # Éxito al lanzar la aplicación
    except Exception as e:
        print(f"ERROR: Excepción inesperada en QDesktopServices.openUrl: {e}")
        QMessageBox.critical(None, "Error Inesperado",
                             f"Ocurrió un error al intentar abrir el archivo:\n{e}")
        return False