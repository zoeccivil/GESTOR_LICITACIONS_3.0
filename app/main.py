"""PyQt6 bootstrap for the Licitaciones application with multi-backend support."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from PyQt6.QtWidgets import QApplication

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.windows.main_window import MainWindow


def _initialize_firebase() -> Optional[object]:
    """
    Inicializa Firebase si el backend es Firestore.
    
    Returns:
        Cliente de Firestore o None si no se usa Firestore
    """
    from firebase_admin import App, credentials, firestore, initialize_app
    from app.core import firebase_adapter
    
    load_dotenv()
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    if not credentials_path:
        # Intentar con JSON directo en variable de entorno
        json_key = os.getenv("LICITACIONES_FIRESTORE_KEY_JSON")
        if json_key:
            import json
            cred = credentials.Certificate(json.loads(json_key))
        else:
            raise RuntimeError(
                "GOOGLE_APPLICATION_CREDENTIALS is not set. Configure it in your .env file."
            )
    else:
        cred = credentials.Certificate(credentials_path)
    
    project_id = os.getenv("FIREBASE_PROJECT_ID")
    options = {"projectId": project_id} if project_id else None
    
    try:
        app: Optional[App] = initialize_app(cred, options)
    except ValueError:
        # App already initialised; reuse default instance
        app = None
    
    client = firestore.client(app)
    firebase_adapter.set_client(client)
    return client


def main() -> None:
    """Punto de entrada principal de la aplicación."""
    load_dotenv()
    
    # Determinar el backend a usar
    backend = os.getenv("APP_DB_BACKEND", "firestore").lower()
    
    # Inicializar cliente según el backend
    db_client = None
    if backend == "firestore":
        db_client = _initialize_firebase()
    
    # Iniciar la aplicación PyQt6
    app = QApplication(sys.argv)
    app.setApplicationName("Gestor de Licitaciones (PyQt6)")

    window = MainWindow(db_client=db_client)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
