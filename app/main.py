"""PyQt6 bootstrap for the Licitaciones application with multi-backend support."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from PyQt6.QtWidgets import QApplication, QMessageBox, QWidget

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.windows.main_window import MainWindow
from app.ui.theme.titanium_theme import apply_titanium_theme
from app.ui.dialogs.firebase_config_dialog import show_firebase_config_dialog


def _initialize_firebase() -> Optional[object]:
    """
    Inicializa Firebase si el backend es Firestore.

    Estrategia:
    1. Intentar credenciales desde configuración propia (lic_config) si existe.
    2. Intentar GOOGLE_APPLICATION_CREDENTIALS.
    3. Intentar JSON en LICITACIONES_FIRESTORE_KEY_JSON.
    4. Si nada de lo anterior funciona, abrir diálogo de configuración de Firebase.
       - Si el usuario configura y guarda, usar esas credenciales.
       - Si cancela, avisar y devolver None (la UI puede manejarlo).

    Returns:
        Cliente de Firestore o None si no se puede inicializar.
    """
    from firebase_admin import App, credentials, firestore, initialize_app
    from app.core import firebase_adapter

    load_dotenv()

    credentials_path: Optional[str] = None
    project_id: Optional[str] = None

    # 1) Intentar leer desde una configuración propia (lic_config), si existe
    try:
        import lic_config  # módulo de configuración de la app
        if hasattr(lic_config, "get_firebase_config"):
            cfg_cred_path, cfg_bucket = lic_config.get_firebase_config()
            if cfg_cred_path:
                credentials_path = cfg_cred_path
            # project_id podría derivarse del bucket si quieres, por ahora opcional
    except Exception:
        pass

    # 2) Intentar variable de entorno GOOGLE_APPLICATION_CREDENTIALS
    if not credentials_path:
        env_cred = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if env_cred:
            credentials_path = env_cred

    # 3) Intentar JSON directo en LICITACIONES_FIRESTORE_KEY_JSON
    json_key = os.getenv("LICITACIONES_FIRESTORE_KEY_JSON")

    cred: Optional[credentials.Certificate] = None

    if credentials_path and os.path.exists(credentials_path):
        # Usar archivo de credenciales
        cred = credentials.Certificate(credentials_path)
    elif json_key:
        # Usar JSON embebido en variable de entorno
        try:
            cred_data = json.loads(json_key)
            cred = credentials.Certificate(cred_data)
        except Exception:
            cred = None

    # 4) Si aún no tenemos credenciales, abrir diálogo de configuración
    if cred is None:
        # Asegurarnos de que exista una QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
            apply_titanium_theme(app)

        parent = QWidget()
        parent.hide()

        configured = show_firebase_config_dialog(parent=parent)
        if not configured:
            QMessageBox.warning(
                parent,
                "Firebase no configurado",
                (
                    "No se encontraron credenciales de Firebase y la configuración "
                    "fue cancelada. Algunas funciones de la aplicación pueden no "
                    "estar disponibles."
                ),
            )
            return None

        # Reintentar obtener credenciales desde la config guardada
        try:
            import lic_config
            if hasattr(lic_config, "get_firebase_config"):
                credentials_path, _bucket = lic_config.get_firebase_config()
        except Exception:
            credentials_path = None

        if credentials_path and os.path.exists(credentials_path):
            cred = credentials.Certificate(credentials_path)
            # Opcional: setear GOOGLE_APPLICATION_CREDENTIALS para otras librerías
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
        else:
            QMessageBox.critical(
                parent,
                "Error en configuración de Firebase",
                "No se pudo obtener una ruta de credenciales válida tras la configuración.",
            )
            return None

    # Opciones de inicialización (projectId opcional)
    project_id = os.getenv("FIREBASE_PROJECT_ID")
    options = {"projectId": project_id} if project_id else None

    try:
        app_fb: Optional[App] = initialize_app(cred, options)
    except ValueError:
        # App ya inicializada; reutilizar instancia por defecto
        app_fb = None

    client = firestore.client(app_fb)
    firebase_adapter.set_client(client)
    return client


def main() -> None:
    """Punto de entrada principal de la aplicación."""
    load_dotenv()

    # Iniciar la aplicación PyQt6
    app = QApplication(sys.argv)
    app.setApplicationName("Gestor de Licitaciones (PyQt6)")

    # Aplicar tema Titanium Construct globalmente
    apply_titanium_theme(app)

    # Determinar el backend a usar
    backend = os.getenv("APP_DB_BACKEND", "firestore").lower()

    # Inicializar cliente según el backend
    db_client = None
    if backend == "firestore":
        db_client = _initialize_firebase()

    # Crear y mostrar ventana principal
    window = MainWindow(db_client=db_client)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()