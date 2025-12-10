from __future__ import annotations
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt

ACCENT = QColor("#3B82F6")        # azul moderno
ACCENT_ALT = QColor("#60A5FA")    # azul claro para hover
BG_WINDOW = QColor("#23262E")     # gris grafito (no muy oscuro)
BG_BASE = QColor("#262A33")
BG_ALT = QColor("#2B303B")
FG_TEXT = QColor("#E6E9EF")       # texto principal
FG_TEXT_SEC = QColor("#B9C0CC")   # texto secundario
BORDER = QColor("#3A4152")
DISABLED_FG = QColor("#7A8599")
LINK = QColor("#60A5FA")
VISITED = QColor("#A78BFA")       # violeta claro

def apply_dim_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    pal = QPalette()

    # Base
    pal.setColor(QPalette.ColorRole.Window, BG_WINDOW)
    pal.setColor(QPalette.ColorRole.WindowText, FG_TEXT)
    pal.setColor(QPalette.ColorRole.Base, BG_BASE)
    pal.setColor(QPalette.ColorRole.AlternateBase, BG_ALT)
    pal.setColor(QPalette.ColorRole.ToolTipBase, QColor("#2D3340"))
    pal.setColor(QPalette.ColorRole.ToolTipText, FG_TEXT)
    pal.setColor(QPalette.ColorRole.Text, FG_TEXT)
    pal.setColor(QPalette.ColorRole.Button, BG_ALT)
    pal.setColor(QPalette.ColorRole.ButtonText, FG_TEXT)
    pal.setColor(QPalette.ColorRole.BrightText, QColor("#FF5A5F"))

    # Selección
    pal.setColor(QPalette.ColorRole.Highlight, ACCENT)
    pal.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)

    # Links
    pal.setColor(QPalette.ColorRole.Link, LINK)
    pal.setColor(QPalette.ColorRole.LinkVisited, VISITED)

    # Deshabilitado
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, DISABLED_FG)
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, DISABLED_FG)
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, DISABLED_FG)
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Highlight, QColor("#3A3F4A"))
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.HighlightedText, QColor("#9AA3B2"))

    app.setPalette(pal)

    # QSS moderno
    app.setStyleSheet(f"""
        QWidget {{
            color: {FG_TEXT.name()};
            background-color: {BG_WINDOW.name()};
            selection-background-color: {ACCENT.name()};
            selection-color: #ffffff;
        }}

        QMenuBar {{
            background-color: {BG_WINDOW.name()};
            border-bottom: 1px solid {BORDER.name()};
        }}
        QMenuBar::item {{
            padding: 6px 10px;
            background: transparent;
        }}
        QMenuBar::item:selected {{
            background: {BG_ALT.name()};
            border-radius: 4px;
        }}
        QMenu {{
            background: {BG_BASE.name()};
            border: 1px solid {BORDER.name()};
        }}
        QMenu::item {{
            padding: 6px 18px;
        }}
        QMenu::item:selected {{
            background: {BG_ALT.name()};
        }}

        QToolBar {{
            background: {BG_WINDOW.name()};
            border-bottom: 1px solid {BORDER.name()};
            spacing: 6px;
        }}
        QToolButton {{
            background: transparent;
            border-radius: 6px;
            padding: 6px 10px;
        }}
        QToolButton:hover {{
            background: {BG_ALT.name()};
        }}
        QToolButton:pressed {{
            background: {ACCENT.name()}22;
        }}

        QPushButton {{
            background-color: {BG_ALT.name()};
            border: 1px solid {BORDER.name()};
            padding: 6px 12px;
            border-radius: 6px;
        }}
        QPushButton:hover {{
            border-color: {ACCENT_ALT.name()};
        }}
        QPushButton:pressed {{
            background-color: {ACCENT.name()}33;
        }}
        QPushButton:default {{
            background-color: {ACCENT.name()};
            border: 1px solid {ACCENT_ALT.name()};
            color: #ffffff;
        }}

        QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox {{
            background: {BG_BASE.name()};
            border: 1px solid {BORDER.name()};
            border-radius: 6px;
            padding: 6px 8px;
            selection-background-color: {ACCENT.name()};
            selection-color: #ffffff;
        }}
        QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
            border: 1px solid {ACCENT.name()};
            box-shadow: 0 0 0 2px {ACCENT.name()}33;
        }}

        QComboBox {{
            background: {BG_BASE.name()};
            border: 1px solid {BORDER.name()};
            border-radius: 6px;
            padding: 6px 8px;
        }}
        QComboBox:focus {{
            border: 1px solid {ACCENT.name()};
        }}
        QComboBox QAbstractItemView {{
            background: {BG_BASE.name()};
            alternate-background-color: {BG_ALT.name()};
            border: 1px solid {BORDER.name()};
            selection-background-color: {ACCENT.name()};
            selection-color: #ffffff;
        }}

        QTabWidget::pane {{
            border: 1px solid {BORDER.name()};
            background: {BG_BASE.name()};
            border-radius: 6px;
        }}
        QTabBar::tab {{
            background: {BG_ALT.name()};
            border: 1px solid {BORDER.name()};
            padding: 6px 12px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            margin-right: 2px;
            color: {FG_TEXT_SEC.name()};
        }}
        QTabBar::tab:selected {{
            color: {FG_TEXT.name()};
            background: {BG_BASE.name()};
            border-bottom: 1px solid {BG_BASE.name()};
        }}

        QHeaderView::section {{
            background-color: {BG_ALT.name()};
            color: {FG_TEXT.name()};
            padding: 6px;
            border: 1px solid {BORDER.name()};
        }}
        QTableView {{
            gridline-color: {BORDER.name()};
            background: {BG_BASE.name()};
            alternate-background-color: {BG_ALT.name()};
            selection-background-color: {ACCENT.name()};
            selection-color: #ffffff;
        }}

        QProgressBar {{
            background: {BG_ALT.name()};
            border: 1px solid {BORDER.name()};
            border-radius: 6px;
            text-align: center;
            color: {FG_TEXT.name()};
        }}
        QProgressBar::chunk {{
            background: {ACCENT.name()};
            border-radius: 6px;
        }}

        QScrollBar:vertical {{
            background: transparent;
            width: 10px;
            margin: 2px;
        }}
        QScrollBar::handle:vertical {{
            background: {BORDER.name()};
            min-height: 24px;
            border-radius: 5px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {ACCENT.name()};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px; background: none; border: none;
        }}

        QScrollBar:horizontal {{
            background: transparent;
            height: 10px;
            margin: 2px;
        }}
        QScrollBar::handle:horizontal {{
            background: {BORDER.name()};
            min-width: 24px;
            border-radius: 5px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {ACCENT.name()};
        }}

        QToolTip {{
            background: #2D3340;
            color: {FG_TEXT.name()};
            border: 1px solid {BORDER.name()};
        }}

        QStatusBar {{
            background: {BG_WINDOW.name()};
            color: {FG_TEXT_SEC.name()};
        }}
    """)