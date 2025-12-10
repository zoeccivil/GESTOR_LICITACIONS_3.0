# ui/themes/fresh_light_theme.py
from __future__ import annotations
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt

def apply_fresh_light_theme(app: QApplication) -> None:
    """
    Aplica un tema claro y fresco con acentos verdes.
    """
    app.setStyle("Fusion")

    pal = QPalette()
    
    # --- Colores Base (Blancos y Grises Claros) ---
    COLOR_BASE = QColor(255, 255, 255)      # Fondo de inputs, tablas (#FFFFFF)
    COLOR_WINDOW = QColor(247, 248, 250)    # Fondo principal (#F7F8FA)
    COLOR_ALT_BASE = QColor(242, 243, 245)  # Filas alternas (#F2F3F5)
    COLOR_BORDER = QColor(224, 224, 224)    # Bordes sutiles (#E0E0E0)

    # --- Colores de Texto ---
    COLOR_TEXT = QColor(33, 33, 33)         # Texto principal (casi negro, #212121)
    COLOR_DISABLED_TEXT = QColor(158, 158, 158) # Texto deshabilitado (#9E9E9E)

    # --- Colores de Acento (Verde) ---
    COLOR_HIGHLIGHT = QColor(76, 175, 80)   # Acento principal (Verde, #4CAF50)
    COLOR_HIGHLIGHT_TEXT = QColor(255, 255, 255) # Texto sobre el acento
    COLOR_LINK = QColor(46, 125, 50)        # Link (Verde oscuro)

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