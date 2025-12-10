# ui/themes/warm_light_theme.py
from __future__ import annotations
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt

def apply_warm_light_theme(app: QApplication) -> None:
    """
    Aplica un tema claro, cálido (marfil) y minimalista con acentos ámbar.
    """
    app.setStyle("Fusion")

    pal = QPalette()
    
    # --- Colores Base (Blancos Cálidos) ---
    COLOR_BASE = QColor(254, 254, 250)      # Fondo de inputs, tablas (#FEFEFA - Marfil)
    COLOR_WINDOW = QColor(249, 249, 245)    # Fondo principal (#F9F9F5)
    COLOR_ALT_BASE = QColor(245, 245, 241)  # Filas alternas
    COLOR_BORDER = QColor(220, 220, 215)    # Bordes sutiles (#DCDCDC)

    # --- Colores de Texto ---
    COLOR_TEXT = QColor(50, 50, 45)         # Texto principal (Gris cálido)
    COLOR_DISABLED_TEXT = QColor(160, 160, 155) # Texto deshabilitado

    # --- Colores de Acento (Ámbar/Naranja) ---
    COLOR_HIGHLIGHT = QColor(230, 126, 34)  # Acento principal (Naranja, #e67e22)
    COLOR_HIGHLIGHT_TEXT = QColor(255, 255, 255) # Texto sobre el acento
    COLOR_LINK = QColor(211, 84, 0)         # Link (Naranja oscuro)

    # Asignar paleta
    pal.setColor(QPalette.ColorRole.Window, COLOR_WINDOW)
    pal.setColor(QPalette.ColorRole.WindowText, COLOR_TEXT)
    pal.setColor(QPalette.ColorRole.Base, COLOR_BASE)
    pal.setColor(QPalette.ColorRole.AlternateBase, COLOR_ALT_BASE)
    pal.setColor(QPalette.ColorRole.ToolTipBase, COLOR_BASE)
    pal.setColor(QPalette.ColorRole.ToolTipText, COLOR_TEXT)
    pal.setColor(QPalette.ColorRole.Text, COLOR_TEXT)
    pal.setColor(QPalette.ColorRole.Button, COLOR_WINDOW)
    pal.setColor(QPalette.ColorRole.ButtonText, COLOR_TEXT)
    pal.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.white)
    pal.setColor(QPalette.ColorRole.Link, COLOR_LINK)

    pal.setColor(QPalette.ColorRole.Highlight, COLOR_HIGHLIGHT)
    pal.setColor(QPalette.ColorRole.HighlightedText, COLOR_HIGHLIGHT_TEXT)

    # Colores deshabilitados
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, COLOR_DISABLED_TEXT)
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, COLOR_DISABLED_TEXT)
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, COLOR_DISABLED_TEXT)
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Base, COLOR_WINDOW)
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Highlight, COLOR_WINDOW.lighter(105))
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.HighlightedText, COLOR_DISABLED_TEXT)

    app.setPalette(pal)

    # Estilos QSS para afinar detalles
    app.setStyleSheet(f"""
        QToolTip {{
            color: {COLOR_TEXT.name()};
            background-color: {COLOR_BASE.name()};
            border: 1px solid {COLOR_BORDER.name()};
            border-radius: 4px;
        }}
        QTabWidget::pane {{
            border: 1px solid {COLOR_BORDER.name()};
            background: {COLOR_BASE.name()};
        }}
        QTabBar::tab {{
            background: {COLOR_WINDOW.name()};
            border: 1px solid {COLOR_BORDER.name()};
            border-bottom: none;
            padding: 6px 10px;
            margin-right: 2px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }}
        QTabBar::tab:selected {{
            background: {COLOR_BASE.name()};
            border-bottom: 1px solid {COLOR_BASE.name()};
        }}
        QTabBar::tab:!selected {{
            color: {COLOR_DISABLED_TEXT.name()};
            background: {COLOR_WINDOW.name()};
        }}
        QHeaderView::section {{
            background-color: {COLOR_WINDOW.name()};
            padding: 4px;
            border: 1px solid {COLOR_BORDER.name()};
            font-weight: bold;
        }}
        QTableView {{
            gridline-color: {COLOR_BORDER.name()};
            selection-background-color: {COLOR_HIGHLIGHT.name()};
            selection-color: {COLOR_HIGHLIGHT_TEXT.name()};
        }}
        QGroupBox {{
            background-color: {COLOR_BASE.name()};
            border: 1px solid {COLOR_BORDER.name()};
            border-radius: 6px;
            margin-top: 6px;
            font-weight: bold;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 5px 0 5px;
            left: 10px;
        }}
        QPushButton {{
            background-color: {COLOR_WINDOW.name()};
            border: 1px solid {COLOR_BORDER.name()};
            padding: 5px 10px;
            border-radius: 4px;
        }}
        QPushButton:hover {{
            background-color: {COLOR_WINDOW.darker(102).name()};
            border: 1px solid {COLOR_BORDER.darker(110).name()};
        }}
        QPushButton:pressed {{
            background-color: {COLOR_WINDOW.darker(105).name()};
        }}
        QComboBox, QLineEdit, QDateEdit {{
            border: 1px solid {COLOR_BORDER.name()};
            border-radius: 4px;
            padding: 3px 5px;
        }}
        QComboBox:hover, QLineEdit:hover, QDateEdit:hover {{
            border: 1px solid {COLOR_BORDER.darker(120).name()};
        }}
        QComboBox::drop-down {{
            border: none;
        }}
        QComboBox QAbstractItemView {{
            background-color: {COLOR_BASE.name()};
            border: 1px solid {COLOR_BORDER.name()};
            selection-background-color: {COLOR_HIGHLIGHT.name()};
        }}
    """)