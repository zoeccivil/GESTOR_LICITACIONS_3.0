# app/ui/models/icons/icon_loader.py (y app/ui/theme/icons/icon_loader.py)
from __future__ import annotations
import os
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QStyle

# Mapa semántico de iconos
ICON_MAP = {
    "new": ("fa.plus", "add.svg", QStyle.StandardPixmap.SP_FileIcon),
    "edit": ("fa.pencil", "edit.svg", QStyle.StandardPixmap.SP_DialogOkButton),
    "report": ("fa.file-text-o", "report.svg", QStyle.StandardPixmap.SP_FileDialogInfoView),
    "dashboard": ("fa.bar-chart", "dashboard.svg", QStyle.StandardPixmap.SP_ComputerIcon),
    "db-open": ("fa.database", "database.svg", QStyle.StandardPixmap.SP_DriveHDIcon),
    "backup": ("fa.cloud-download", "backup.svg", QStyle.StandardPixmap.SP_DialogSaveButton),
    "restore": ("fa.cloud-upload", "restore.svg", QStyle.StandardPixmap.SP_DialogOpenButton),
    "docs": ("fa.file-o", "docs.svg", QStyle.StandardPixmap.SP_DirIcon),
    # --- CORRECCIÓN AQUÍ ---
    "competitors": ("fa.users", "users.svg", QStyle.StandardPixmap.SP_DirIcon), # Cambiado SP_GroupBoxIcon por SP_DirIcon
    # --- FIN CORRECCIÓN ---
    "responsables": ("fa.user", "user.svg", QStyle.StandardPixmap.SP_DirHomeIcon),
}

_qta = None
try:
    import qtawesome as qta
    _qta = qta
except Exception:
    pass

def _icons_dir() -> str:
    # Coloca tus SVG en app/resources/icons/
    # Asume que este archivo está en app/ui/models/icons o app/ui/theme/icons
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    return os.path.join(base, "resources", "icons")

def get_icon(name: str) -> QIcon:
    entry = ICON_MAP.get(name)
    if not entry:
        return QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)
    qta_name, svg_name, std_fallback = entry

    # 1) QtAwesome
    if _qta and isinstance(qta_name, str):
        try:
            return _qta.icon(qta_name)
        except Exception:
            pass

    # 2) SVG local
    svg_path = os.path.join(_icons_dir(), svg_name)
    if os.path.exists(svg_path):
        return QIcon(svg_path)

    # 3) Fallback nativo
    return QApplication.style().standardIcon(std_fallback)