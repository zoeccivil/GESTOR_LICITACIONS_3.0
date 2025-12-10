from __future__ import annotations
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QColor

def accent_hex() -> str:
    app = QApplication.instance()
    if not app:
        return "#3B82F6"
    return app.palette().highlight().color().name()

def text_hex() -> str:
    app = QApplication.instance()
    if not app:
        return "#E6E9EF"
    return app.palette().text().color().name()

def base_bg_hex() -> str:
    app = QApplication.instance()
    if not app:
        return "#262A33"
    return app.palette().base().color().name()

def alt_bg_hex() -> str:
    app = QApplication.instance()
    if not app:
        return "#2B303B"
    return app.palette().alternateBase().color().name()

def border_hex() -> str:
    app = QApplication.instance()
    if not app:
        return "#3A4152"
    # No hay role de border; aproximamos con mid()
    return app.palette().mid().color().name()