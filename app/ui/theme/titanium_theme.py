"""
Titanium Construct - Modern PyQt6 Theme
Professional light theme with cyan-900 accent for construction/civil engineering applications
"""
from __future__ import annotations
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt

# Titanium Construct Color Palette
PRIMARY_500 = QColor("#155E75")     # Cyan-800 (primary accent)
PRIMARY_700 = QColor("#0E4F70")     # Darker cyan for hover
PRIMARY_100 = QColor("#E0F2FE")     # Light cyan for selections
NEUTRAL_50 = QColor("#F9FAFB")      # Very light gray
NEUTRAL_100 = QColor("#F3F4F6")     # Light gray background
NEUTRAL_200 = QColor("#E5E7EB")     # Tab inactive
NEUTRAL_300 = QColor("#D1D5DB")     # Borders
NEUTRAL_500 = QColor("#6B7280")     # Secondary text
NEUTRAL_700 = QColor("#374151")     # Header text
NEUTRAL_900 = QColor("#111827")     # Primary text

# Semantic colors
SUCCESS_BG = QColor("#D1FAE5")      # Green for winners
SUCCESS_TEXT = QColor("#065F46")    # Dark green text
INFO_BG = QColor("#EEF2FF")         # Indigo for our company
INFO_TEXT = QColor("#4F46E5")       # Indigo text
DANGER_BG = QColor("#FEF2F2")       # Light red for disqualified
DANGER_TEXT = QColor("#DC2626")     # Red text
DANGER_BORDER = QColor("#EF4444")   # Red border

THEME_NAME = "Titanium Construct"

TITANIUM_THEME = """
/* === RESET Y BASE === */
QWidget {
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
    color: #111827; /* Neutral-900 */
}

QMainWindow, QDialog {
    background-color: #F3F4F6; /* Neutral-100 */
}

/* === GROUP BOX === */
QGroupBox {
    background-color: #FFFFFF;
    border: 1px solid #D1D5DB; /* Neutral-300 */
    border-radius: 6px;
    margin-top: 1.2em; /* Espacio para el título */
    padding-top: 10px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 5px;
    color: #155E75; /* Primary-500 */
    font-weight: bold;
    font-size: 14px;
    left: 10px;
}

/* === TABS (QTabWidget) === */
QTabWidget::pane {
    border: 1px solid #D1D5DB;
    background: #FFFFFF;
    border-radius: 4px;
}

QTabBar::tab {
    background: #E5E7EB; /* Neutral-200 */
    color: #6B7280; /* Neutral-500 */
    padding: 8px 16px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background: #FFFFFF;
    color: #155E75; /* Primary-500 */
    font-weight: bold;
    border-top: 3px solid #155E75; /* Indicador activo */
}

QTabBar::tab:hover:!selected {
    background: #D1D5DB;
}

/* === TABLAS (QTableWidget) === */
QTableWidget {
    background-color: #FFFFFF;
    gridline-color: #E5E7EB;
    border: 1px solid #D1D5DB;
    border-radius: 4px;
    selection-background-color: #E0F2FE; /* Primary-100 */
    selection-color: #0E4F70; /* Primary-700 */
}

QHeaderView::section {
    background-color: #F9FAFB; /* Gris muy claro */
    padding: 6px;
    border: 0px;
    border-bottom: 2px solid #D1D5DB;
    font-weight: bold;
    color: #374151; /* Neutral-700 */
}

QTableWidget::item {
    padding: 4px;
}

/* === BOTONES === */
QPushButton {
    background-color: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 4px;
    padding: 6px 12px;
    color: #374151;
}

QPushButton:hover {
    background-color: #F3F4F6;
}

QPushButton:pressed {
    background-color: #E5E7EB;
}

/* Botón Primario */
QPushButton[class="primary"] {
    background-color: #155E75; /* Primary-500 */
    color: #FFFFFF;
    border: 1px solid #155E75;
}

QPushButton[class="primary"]:hover {
    background-color: #0E4F70; /* Primary-700 */
}

QPushButton[class="primary"]:pressed {
    background-color: #164E63;
}

/* Botón Destructivo */
QPushButton[class="danger"] {
    background-color: #FFFFFF;
    color: #DC2626;
    border: 1px solid #EF4444;
}

QPushButton[class="danger"]:hover {
    background-color: #FEF2F2;
}

QPushButton[class="danger"]:pressed {
    background-color: #FEE2E2;
}

/* === INPUTS === */
QLineEdit, QComboBox, QSpinBox, QDateEdit, QDoubleSpinBox, QDateTimeEdit {
    background-color: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 4px;
    padding: 5px;
    min-height: 20px;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDateEdit:focus, QDoubleSpinBox:focus {
    border: 1px solid #155E75;
    background-color: #F0F9FF; /* Tinte azul muy leve al foco */
}

QComboBox::drop-down {
    border: none;
    padding-right: 5px;
}

QComboBox QAbstractItemView {
    background: #FFFFFF;
    border: 1px solid #D1D5DB;
    selection-background-color: #E0F2FE;
    selection-color: #0E4F70;
}

/* === TEXT EDIT === */
QPlainTextEdit, QTextEdit {
    background-color: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 4px;
    padding: 5px;
    selection-background-color: #E0F2FE;
    selection-color: #0E4F70;
}

QPlainTextEdit:focus, QTextEdit:focus {
    border: 1px solid #155E75;
    background-color: #F0F9FF;
}

/* === SCROLLBARS === */
QScrollBar:vertical {
    border: none;
    background: #F3F4F6;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #9CA3AF;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #6B7280;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background: #F3F4F6;
    height: 10px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background: #9CA3AF;
    min-width: 20px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal:hover {
    background: #6B7280;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* === MENUBAR === */
QMenuBar {
    background-color: #FFFFFF;
    border-bottom: 1px solid #D1D5DB;
}

QMenuBar::item {
    padding: 6px 10px;
    background: transparent;
}

QMenuBar::item:selected {
    background: #F3F4F6;
    border-radius: 4px;
}

QMenu {
    background: #FFFFFF;
    border: 1px solid #D1D5DB;
}

QMenu::item {
    padding: 6px 18px;
}

QMenu::item:selected {
    background: #E0F2FE;
    color: #0E4F70;
}

/* === TOOLBAR === */
QToolBar {
    background: #FFFFFF;
    border-bottom: 1px solid #D1D5DB;
    spacing: 6px;
    padding: 4px;
}

QToolButton {
    background: transparent;
    border-radius: 4px;
    padding: 6px 10px;
}

QToolButton:hover {
    background: #F3F4F6;
}

QToolButton:pressed {
    background: #E5E7EB;
}

/* === STATUS BAR === */
QStatusBar {
    background: #FFFFFF;
    color: #6B7280;
    border-top: 1px solid #D1D5DB;
}

/* === PROGRESS BAR === */
QProgressBar {
    background: #E5E7EB;
    border: 1px solid #D1D5DB;
    border-radius: 4px;
    text-align: center;
    color: #111827;
}

QProgressBar::chunk {
    background: #155E75;
    border-radius: 4px;
}

/* === CHECKBOX & RADIO === */
QCheckBox, QRadioButton {
    spacing: 5px;
}

QCheckBox::indicator, QRadioButton::indicator {
    width: 16px;
    height: 16px;
}

QCheckBox::indicator {
    border: 1px solid #D1D5DB;
    border-radius: 3px;
    background: #FFFFFF;
}

QCheckBox::indicator:checked {
    background: #155E75;
    border-color: #155E75;
}

QRadioButton::indicator {
    border: 1px solid #D1D5DB;
    border-radius: 8px;
    background: #FFFFFF;
}

QRadioButton::indicator:checked {
    background: #155E75;
    border-color: #155E75;
}

/* === TOOLTIP === */
QToolTip {
    background: #374151;
    color: #FFFFFF;
    border: 1px solid #4B5563;
    padding: 4px;
    border-radius: 4px;
}

/* === SPLITTER === */
QSplitter::handle {
    background: #D1D5DB;
}

QSplitter::handle:hover {
    background: #9CA3AF;
}

/* === LIST VIEW === */
QListView {
    background-color: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 4px;
    selection-background-color: #E0F2FE;
    selection-color: #0E4F70;
}

/* === TREE VIEW === */
QTreeView {
    background-color: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 4px;
    selection-background-color: #E0F2FE;
    selection-color: #0E4F70;
}

QTreeView::item:hover {
    background: #F3F4F6;
}

/* === LABEL (ajustes menores) === */
QLabel {
    background: transparent;
}
"""


def apply_theme(app: QApplication) -> None:
    """Apply Titanium Construct theme to the application."""
    app.setStyle("Fusion")
    
    # Set up palette for better consistency
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, NEUTRAL_100)
    pal.setColor(QPalette.ColorRole.WindowText, NEUTRAL_900)
    pal.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
    pal.setColor(QPalette.ColorRole.AlternateBase, NEUTRAL_50)
    pal.setColor(QPalette.ColorRole.Text, NEUTRAL_900)
    pal.setColor(QPalette.ColorRole.Button, QColor("#FFFFFF"))
    pal.setColor(QPalette.ColorRole.ButtonText, NEUTRAL_700)
    pal.setColor(QPalette.ColorRole.Highlight, PRIMARY_100)
    pal.setColor(QPalette.ColorRole.HighlightedText, PRIMARY_700)
    pal.setColor(QPalette.ColorRole.Link, PRIMARY_500)
    
    app.setPalette(pal)
    app.setStyleSheet(TITANIUM_THEME)


def apply_titanium_theme(app: QApplication) -> None:
    """Alias for apply_theme for backwards compatibility."""
    apply_theme(app)
