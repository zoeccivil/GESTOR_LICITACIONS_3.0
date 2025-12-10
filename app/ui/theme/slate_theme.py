# ui/themes/slate_theme.py
from __future__ import annotations
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt

def apply_slate_theme(app: QApplication) -> None:
    """
    Aplica un tema "Pizarra Azulada" (slate) con acentos turquesa.
    """
    app.setStyle("Fusion")

    pal = QPalette()
    
    # --- Colores Base (Azules Oscuros) ---
    COLOR_BASE = QColor(44, 62, 80)         # Fondo de inputs (#2c3e50)
    COLOR_WINDOW = QColor(52, 73, 94)       # Fondo principal (#34495e)
    COLOR_ALT_BASE = QColor(47, 67, 86)     # Filas alternas
    COLOR_BORDER = QColor(68, 90, 112)      # Bordes

    # --- Colores de Texto ---
    COLOR_TEXT = QColor(236, 240, 241)      # Texto principal (#ecf0f1)
    COLOR_DISABLED_TEXT = QColor(149, 165, 166) # Texto deshabilitado (#95a5a6)

    # --- Colores de Acento (Turquesa/Verde) ---
    COLOR_HIGHLIGHT = QColor(26, 188, 156)  # Turquesa (#1abc9c)
    COLOR_HIGHLIGHT_TEXT = QColor(255, 255, 255)
    COLOR_LINK = QColor(52, 152, 219)       # Azul (#3498db)

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
    pal.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    pal.setColor(QPalette.ColorRole.Link, COLOR_LINK)

    pal.setColor(QPalette.ColorRole.Highlight, COLOR_HIGHLIGHT)
    pal.setColor(QPalette.ColorRole.HighlightedText, COLOR_HIGHLIGHT_TEXT)

    # Colores deshabilitados
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, COLOR_DISABLED_TEXT)
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, COLOR_DISABLED_TEXT)
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, COLOR_DISABLED_TEXT)
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Base, COLOR_BASE.lighter(90))
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Highlight, COLOR_WINDOW)
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
            background: {COLOR_BASE.name()}; /* El fondo del panel */
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
            background-color: {COLOR_WINDOW.lighter(110).name()};
            border: 1px solid {COLOR_BORDER.lighter(120).name()};
        }}
        QPushButton:pressed {{
            background-color: {COLOR_WINDOW.darker(110).name()};
        }}
        QComboBox, QLineEdit, QDateEdit {{
            border: 1px solid {COLOR_BORDER.name()};
            border-radius: 4px;
            padding: 3px 5px;
        }}
        QComboBox:hover, QLineEdit:hover, QDateEdit:hover {{
            border: 1px solid {COLOR_BORDER.lighter(130).name()};
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