"""
Configuración de Firebase para la aplicación de licitaciones.

En esta implementación básica, se guarda la configuración en un JSON
local en el directorio del usuario. Puedes adaptar esto a tu sistema
de configuración preferido más adelante.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Tuple

# Ruta por defecto para el archivo de configuración
CONFIG_DIR = Path.home() / ".gestor_licitaciones"
CONFIG_FILE = CONFIG_DIR / "config.json"


def _ensure_config_dir() -> None:
    """Asegura que exista el directorio de configuración."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def get_firebase_config() -> Tuple[str, str]:
    """
    Retorna la configuración de Firebase almacenada.

    Returns:
        (cred_path, bucket)
        - cred_path: ruta al archivo de credenciales (puede ser vacío)
        - bucket: nombre del bucket de Storage (puede ser vacío)
    """
    if not CONFIG_FILE.exists():
        return "", ""

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return "", ""

    cred_path = data.get("firebase_credentials_path", "") or ""
    bucket = data.get("firebase_storage_bucket", "") or ""
    return cred_path, bucket


def set_firebase_config(cred_path: str, bucket: str) -> None:
    """
    Guarda la configuración de Firebase.

    Args:
        cred_path: ruta al archivo de credenciales JSON
        bucket: nombre del bucket de Storage
    """
    _ensure_config_dir()

    data = {}
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

    data["firebase_credentials_path"] = cred_path
    data["firebase_storage_bucket"] = bucket

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)