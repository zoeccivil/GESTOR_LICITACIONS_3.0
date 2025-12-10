from __future__ import annotations
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt

ACCENT = QColor("#00B7C2")        # turquesa
ACCENT_ALT = QColor("#00D0D9")
BG_WINDOW = QColor("#1C2228")     # azul-gris profundo (no negro)
BG_BASE = QColor("#20262E")
BG_ALT = QColor("#252C35")
FG_TEXT = QColor("#EAF1F5")
FG_TEXT_SEC = QColor("#B9C7CF")
BORDER = QColor("#32414B")
DISABLED_FG = QColor("#7F8B93")
LINK = QColor("#00C2C7")
VISITED = QColor("#06B6D4")

def apply_oceanic_dim_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    pal = QPalette()

    pal.setColor(QPalette.ColorRole.Window, BG_WINDOW)
    pal.setColor(QPalette.ColorRole.WindowText, FG_TEXT)
    pal.setColor(QPalette.ColorRole.Base, BG_BASE)
    pal.setColor(QPalette.ColorRole.AlternateBase, BG_ALT)
    pal.setColor(QPalette.ColorRole.ToolTipBase, QColor("#22303A"))
    pal.setColor(QPalette.ColorRole.ToolTipText, FG_TEXT)
    pal.setColor(QPalette.ColorRole.Text, FG_TEXT)
    pal.setColor(QPalette.ColorRole.Button, BG_ALT)
    pal.setColor(QPalette.ColorRole.ButtonText, FG_TEXT)
    pal.setColor(QPalette.ColorRole.BrightText, QColor("#FF6B6B"))

    pal.setColor(QPalette.ColorRole.Highlight, ACCENT)
    pal.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)

    pal.setColor(QPalette.ColorRole.Link, LINK)
    pal.setColor(QPalette.ColorRole.LinkVisited, VISITED)

    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, DISABLED_FG)
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, DISABLED_FG)
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, DISABLED_FG)
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Highlight, QColor("#2A3A44"))
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.HighlightedText, QColor("#A5B3BB"))

    app.setPalette(pal)

    app.setStyleSheet(f"""
        QWidget {{
            color: {FG_TEXT.name()};
            background-color: {BG_WINDOW.name()};
        }}

        QMenuBar {{
            background: {BG_WINDOW.name()};
            border-bottom: 1px solid {BORDER.name()};
        }}
        QMenuBar::item {{
            padding: 6px 10px;
        }}
        QMenuBar::item:selected {{
            background: {BG_ALT.name()};
            border-radius: 4px;
        }}
        QMenu {{
            background: {BG_BASE.name()};
            border: 1px solid {BORDER.name()};
        }}
        QMenu::item:selected {{
            background: {ACCENT.name()}22;
        }}

        QToolBar {{
            background: {BG_WINDOW.name()};
            border-bottom: 1px solid {BORDER.name()};
        }}
        QToolButton {{
            padding: 6px 10px; border-radius: 6px;
        }}
        QToolButton:hover {{ background: {BG_ALT.name()}; }}
        QToolButton:pressed {{ background: {ACCENT.name()}22; }}

        QPushButton {{
            background-color: {BG_ALT.name()};
            border: 1px solid {BORDER.name()};
            padding: 6px 12px; border-radius: 6px;
        }}
        QPushButton:hover {{ border-color: {ACCENT_ALT.name()}; }}
        QPushButton:pressed {{ background: {ACCENT.name()}33; }}
        QPushButton:default {{
            background-color: {ACCENT.name()};
            border: 1px solid {ACCENT_ALT.name()};
            color: #ffffff;
        }}

        QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox {{
            background: {BG_BASE.name()};
            border: 1px solid {BORDER.name()};
            border-radius: 6px; padding: 6px 8px;
        }}
        QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
            border: 1px solid {ACCENT.name()};
        }}
        QComboBox {{
            background: {BG_BASE.name()};
            border: 1px solid {BORDER.name()};
            border-radius: 6px; padding: 6px 8px;
        }}
        QComboBox QAbstractItemView {{
            background: {BG_BASE.name()};
            border: 1px solid {BORDER.name()};
            selection-background-color: {ACCENT.name()};
            selection-color: #fff;
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
            background: {BG_ALT.name()};
            color: {FG_TEXT.name()};
            padding: 6px; border: 1px solid {BORDER.name()};
        }}
        QTableView {{
            gridline-color: {BORDER.name()};
            background: {BG_BASE.name()};
            alternate-background-color: {BG_ALT.name()};
            selection-background-color: {ACCENT.name()};
            selection-color: #fff;
        }}

        QProgressBar {{
            background: {BG_ALT.name()};
            border: 1px solid {BORDER.name()};
            border-radius: 6px; text-align: center;
        }}
        QProgressBar::chunk {{
            background: {ACCENT.name()};
            border-radius: 6px;
        }}

        QScrollBar:vertical, QScrollBar:horizontal {{
            background: transparent;
        }}
        QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
            background: {BORDER.name()};
            border-radius: 5px;
        }}
        QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{
            background: {ACCENT.name()};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            height: 0px; width: 0px; background: none; border: none;
        }}
    """)