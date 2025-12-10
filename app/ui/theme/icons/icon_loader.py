"""
Gestor de iconos semánticos.

- Busca icons en este orden:
  1) qtawesome (si está instalado) usando el nombre semántico.
  2) SVGs locales en app/resources/icons (soporta PyInstaller onefile via sys._MEIPASS).
  3) iconos nativos de QStyle como fallback.

- Uso:
    from app.ui.icons.icon_loader import get_icon
    btn.setIcon(get_icon("report"))
"""
from __future__ import annotations
import os
import sys
import importlib
from typing import Optional, Dict, Tuple

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QStyle

# Mapa semántico de iconos: (qtawesome_name, local_svg_filename, QStyle.StandardPixmap fallback)
ICON_MAP: Dict[str, Tuple[str, str, QStyle.StandardPixmap]] = {
    "new": ("fa.plus", "add.svg", QStyle.StandardPixmap.SP_FileIcon),
    "edit": ("fa.pencil", "edit.svg", QStyle.StandardPixmap.SP_DialogOkButton),
    "report": ("fa.file-text-o", "report.svg", QStyle.StandardPixmap.SP_FileDialogInfoView),
    "dashboard": ("fa.bar-chart", "dashboard.svg", QStyle.StandardPixmap.SP_ComputerIcon),
    "db-open": ("fa.database", "database.svg", QStyle.StandardPixmap.SP_DriveHDIcon),
    "backup": ("fa.cloud-download", "backup.svg", QStyle.StandardPixmap.SP_DialogSaveButton),
    "restore": ("fa.cloud-upload", "restore.svg", QStyle.StandardPixmap.SP_DialogOpenButton),
    "docs": ("fa.file-o", "docs.svg", QStyle.StandardPixmap.SP_DirIcon),
    "competitors": ("fa.users", "users.svg", QStyle.StandardPixmap.SP_GroupBoxIcon),
    "responsables": ("fa.user", "user.svg", QStyle.StandardPixmap.SP_DirHomeIcon),
}

# Cache de iconos ya cargados
_ICON_CACHE: Dict[Tuple[str, Optional[int]], QIcon] = {}

# Referencia a qtawesome si está disponible (cargada perezosamente)
_qtawesome = None  # type: Optional[object]


def _icons_dir() -> str:
    """
    Devuelve la carpeta donde están los SVG de los iconos.
    Soporta ejecución empaquetada por PyInstaller (sys._MEIPASS).
    """
    # Si estamos congelados por PyInstaller, los datos se extraen en _MEIPASS
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS  # type: ignore[attr-defined]
    else:
        # ruta relativa al paquete: app/resources/icons
        base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base, "resources", "icons")


def _try_load_qtawesome(icon_name: str) -> Optional[QIcon]:
    """
    Intentar cargar un icono desde qtawesome (si está instalado).
    Carga qtawesome de forma perezosa y cachea la referencia.
    """
    global _qtawesome
    try:
        if _qtawesome is None:
            _qtawesome = importlib.import_module("qtawesome")
        if hasattr(_qtawesome, "icon"):
            # qtawesome acepta nombres como 'fa.plus' o 'fa5s.file'
            return _qtawesome.icon(icon_name)
    except Exception:
        # cualquier error -> no usamos qtawesome
        _qtawesome = None
    return None


def get_icon(name: str, size: Optional[int] = None) -> QIcon:
    """
    Devuelve un QIcon para el nombre semántico dado.
    - name: clave del ICON_MAP (ej. 'report', 'docs', 'edit').
    - size: (opcional) tamaño solicitado; se ignora cuando se devuelve QIcon (puedes usar setIconSize en widgets).
    """
    key = (name, size)
    if key in _ICON_CACHE:
        return _ICON_CACHE[key]

    entry = ICON_MAP.get(name)
    if not entry:
        # Nombre desconocido -> icono genérico
        ico = QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)
        _ICON_CACHE[key] = ico
        return ico

    qta_name, svg_name, std_fallback = entry

    # 1) Intentar qtawesome (perezoso)
    try:
        if isinstance(qta_name, str) and qta_name:
            ico = _try_load_qtawesome(qta_name)
            if isinstance(ico, QIcon):
                _ICON_CACHE[key] = ico
                return ico
    except Exception:
        pass

    # 2) Intentar SVG local (app/resources/icons/<svg_name>)
    try:
        svg_path = os.path.join(_icons_dir(), svg_name)
        if os.path.exists(svg_path) and os.path.isfile(svg_path):
            ico = QIcon(svg_path)
            _ICON_CACHE[key] = ico
            return ico
    except Exception:
        pass

    # 3) Intentar icon name via theme (QIcon.fromTheme), útil en Linux
    try:
        theme_icon = QIcon.fromTheme(svg_name.split(".")[0])
        if not theme_icon.isNull():
            _ICON_CACHE[key] = theme_icon
            return theme_icon
    except Exception:
        pass

    # 4) Fallback nativo de QStyle
    try:
        ico = QApplication.style().standardIcon(std_fallback)
        _ICON_CACHE[key] = ico
        return ico
    except Exception:
        # último recurso: icono vacío
        return QIcon()