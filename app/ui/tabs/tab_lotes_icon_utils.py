from PyQt6.QtWidgets import QStyle
from PyQt6.QtGui import QIcon

PYQT6_ICON_MAP = {
    # No existe en PyQt6:
    "SP_DialogNewButton": "SP_FileDialogNewFolder",
    # Ejemplos de alias opcionales si los usabas:
    "SP_DialogYes": "SP_DialogYesButton",
    "SP_DialogNo": "SP_DialogNoButton",
    "SP_DialogApply": "SP_DialogApplyButton",
}

def safe_std_icon(style, sp_name: str, fallback: str = "SP_FileIcon") -> QIcon:
    # Mapea a nombres válidos en PyQt6 si es necesario
    mapped = PYQT6_ICON_MAP.get(sp_name, sp_name)
    try:
        sp_enum = getattr(QStyle.StandardPixmap, mapped)
        return style.standardIcon(sp_enum)
    except Exception:
        try:
            fb_enum = getattr(QStyle.StandardPixmap, fallback)
            return style.standardIcon(fb_enum)
        except Exception:
            return QIcon()