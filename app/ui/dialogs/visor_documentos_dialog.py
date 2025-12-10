# app/ui/dialogs/visor_documentos_dialog.py
from __future__ import annotations
import os
from typing import TYPE_CHECKING, List, Dict, Any, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QPushButton,
    QHBoxLayout, QMessageBox, QApplication, QStyle
)
from PyQt6.QtCore import Qt, QUrl, QModelIndex
from PyQt6.QtGui import QIcon, QDesktopServices, QBrush, QColor, QGuiApplication, QPalette

from app.core.models import Licitacion, Documento
from app.core.utils import reconstruir_ruta_absoluta

if TYPE_CHECKING:
    pass

DEFAULT_CATEGORIES = ["Legal", "Técnica", "Económica", "Otros"]


class VisorDocumentosDialog(QDialog):
    """
    Diálogo modal para visualizar el checklist de documentos de una licitación,
    organizado por categorías en pestañas. Permite abrir archivos adjuntos.
    Adaptado a tema activo (QPalette) con QSS dinámico.
    """
    # Column indices
    COL_ESTADO = 0
    COL_CODIGO = 1
    COL_NOMBRE = 2
    COL_CONDICION = 3
    COL_REVISADO = 4
    COL_ADJUNTO = 5
    COL_ORDEN = 6

    def __init__(self, parent: QWidget, licitacion: Licitacion, categorias: List[str] | None = None):
        super().__init__(parent)
        self.licitacion = licitacion
        self.categorias = categorias or DEFAULT_CATEGORIES
        self._docs_by_category: Dict[str, List[Documento]] = {}
        self._all_docs_sorted: List[Documento] = []

        # Tema desde QPalette
        self._resolve_theme_colors()

        self.setWindowTitle(f"Checklist Documentos - {self.licitacion.numero_proceso}")
        self.setMinimumSize(950, 600)

        # Ventana redimensionable/maximizable
        current_flags = self.windowFlags()
        self.setWindowFlags(current_flags | Qt.WindowType.WindowMaximizeButtonHint)

        self._prepare_data()
        self._build_ui()
        self._populate_tabs()

    # ---------- Tema/QSS ----------
    def _resolve_theme_colors(self):
        app = QGuiApplication.instance()
        pal: QPalette = app.palette() if app else QPalette()

        def hx(brush_or_color: Any, fallback: str) -> str:
            try:
                if hasattr(brush_or_color, "color"):
                    c = brush_or_color.color()
                    if isinstance(c, QColor):
                        return c.name()
                if isinstance(brush_or_color, QColor):
                    return brush_or_color.name()
            except Exception:
                pass
            return fallback

        self.COLOR_ACCENT = hx(pal.highlight(), "#3B82F6")
        self.COLOR_TEXT = hx(pal.text(), "#E6E9EF")
        self.COLOR_TEXT_SEC = hx(getattr(pal, "placeholderText", lambda: pal.mid())(), "#B9C0CC")
        self.COLOR_WINDOW = hx(pal.window(), "#262A33")
        self.COLOR_BASE = hx(pal.base(), "#262A33")
        self.COLOR_ALT = hx(pal.alternateBase(), "#2B303B")
        self.COLOR_BORDER = hx(pal.mid(), "#3A4152")
        self.COLOR_DANGER = "#EF4444"
        self.COLOR_WARNING = "#F59E0B"

        self._TABS_QSS = (
            f"QTabWidget::pane{{border:1px solid {self.COLOR_BORDER};background:{self.COLOR_BASE};border-radius:6px;}}"
            f"QTabBar::tab{{background:{self.COLOR_ALT};border:1px solid {self.COLOR_BORDER};padding:6px 12px;"
            f"border-top-left-radius:6px;border-top-right-radius:6px;margin-right:2px;color:{self.COLOR_TEXT_SEC};}}"
            f"QTabBar::tab:selected{{color:{self.COLOR_TEXT};background:{self.COLOR_BASE};"
            f"border-bottom:1px solid {self.COLOR_BASE};}}"
        )

    def _style_table(self, t: QTableWidget):
        t.setStyleSheet(
            f"QTableWidget{{gridline-color:{self.COLOR_BORDER}; background:{self.COLOR_BASE}; "
            f"alternate-background-color:{self.COLOR_ALT}; selection-background-color:{self.COLOR_ACCENT}; "
            f"selection-color:#ffffff; color:{self.COLOR_TEXT};}} "
            f"QHeaderView::section{{background:{self.COLOR_ALT}; padding:6px; border:1px solid {self.COLOR_BORDER}; "
            f"font-weight:600; color:{self.COLOR_TEXT}; min-height:26px;}}"
        )

    def _overlay(self, hex_color: str, alpha: int) -> QColor:
        c = QColor(hex_color)
        c.setAlpha(max(0, min(255, alpha)))
        return c

    # ---------- Datos ----------
    def _prepare_data(self):
        """Sorts documents and groups them by category."""
        docs = sorted(
            self.licitacion.documentos_solicitados,
            key=lambda d: (getattr(d, 'orden_pliego', 99999), d.codigo or "", d.nombre or "")
        )
        self._all_docs_sorted = docs

        self._docs_by_category = {cat: [] for cat in self.categorias}
        self._docs_by_category["Todos"] = docs

        for doc in docs:
            cat = doc.categoria or "Otros"
            if cat in self._docs_by_category:
                self._docs_by_category[cat].append(doc)
            elif "Otros" in self._docs_by_category:
                self._docs_by_category["Otros"].append(doc)

    # ---------- UI ----------
    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(self._TABS_QSS)
        main_layout.addWidget(self.tab_widget)

        self._tables: Dict[str, QTableWidget] = {}

        tab_order = ["Todos"] + [cat for cat in self.categorias if cat in self._docs_by_category]
        for cat_name in tab_order:
            tab_content = QWidget()
            tab_layout = QVBoxLayout(tab_content)
            tab_layout.setContentsMargins(5, 5, 5, 5)

            table = QTableWidget()
            table.setColumnCount(7)
            table.setHorizontalHeaderLabels(["✓", "Código", "Documento", "Condición", "👁️", "📎", "Orden"])
            table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
            table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            table.verticalHeader().setVisible(False)
            table.setSortingEnabled(True)
            table.doubleClicked.connect(self._on_double_click)
            table.setAlternatingRowColors(True)

            header = table.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            header.resizeSection(self.COL_ESTADO, 40)
            header.setSectionResizeMode(self.COL_ESTADO, QHeaderView.ResizeMode.Fixed)
            header.resizeSection(self.COL_CODIGO, 120)
            header.setSectionResizeMode(self.COL_NOMBRE, QHeaderView.ResizeMode.Stretch)
            header.resizeSection(self.COL_CONDICION, 110)
            header.resizeSection(self.COL_REVISADO, 40)
            header.setSectionResizeMode(self.COL_REVISADO, QHeaderView.ResizeMode.Fixed)
            header.resizeSection(self.COL_ADJUNTO, 40)
            header.setSectionResizeMode(self.COL_ADJUNTO, QHeaderView.ResizeMode.Fixed)
            header.resizeSection(self.COL_ORDEN, 60)

            # Estilo acorde al tema
            self._style_table(table)

            tab_layout.addWidget(table)
            self.tab_widget.addTab(tab_content, cat_name)
            self._tables[cat_name] = table

        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.accept)
        button_layout.addWidget(btn_close)
        main_layout.addLayout(button_layout)

    # ---------- Poblar ----------
    def _populate_tabs(self):
        """Fills all table widgets with data."""
        for cat_name, table in self._tables.items():
            self._populate_table(table, self._docs_by_category.get(cat_name, []))

    def _populate_table(self, table: QTableWidget, documents: List[Documento]):
        """Fills a specific table widget with document data."""
        table.setSortingEnabled(False)
        table.setRowCount(0)
        for doc in documents:
            row = table.rowCount()
            table.insertRow(row)

            # Row state -> light overlays to respect theme
            row_brush: Optional[QBrush] = None
            if getattr(doc, 'requiere_subsanacion', False):
                row_brush = QBrush(self._overlay(self.COLOR_DANGER, 58))
            elif not getattr(doc, 'presentado', False):
                row_brush = QBrush(self._overlay(self.COLOR_WARNING, 46))

            estado_icon = "✅" if getattr(doc, 'presentado', False) else "❌"
            if getattr(doc, 'requiere_subsanacion', False):
                estado_icon = "⚠️"
            revisado_icon = "👁️" if getattr(doc, 'revisado', False) else ""
            adjunto_icon = "📎" if getattr(doc, 'ruta_archivo', '') else ""
            condicion = getattr(doc, 'subsanable', 'N/D') or 'N/D'
            orden = getattr(doc, 'orden_pliego', None)
            orden_display = str(orden) if orden is not None else ""

            item_estado = QTableWidgetItem(estado_icon)
            item_codigo = QTableWidgetItem(doc.codigo or "")
            item_nombre = QTableWidgetItem(doc.nombre or "")
            item_condicion = QTableWidgetItem(condicion)
            item_revisado = QTableWidgetItem(revisado_icon)
            item_adjunto = QTableWidgetItem(adjunto_icon)
            item_orden = QTableWidgetItem()

            sort_order_data = orden if orden is not None else 999999
            item_orden.setData(Qt.ItemDataRole.DisplayRole, orden_display)
            item_orden.setData(Qt.ItemDataRole.UserRole + 1, sort_order_data)

            item_estado.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_revisado.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_adjunto.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_condicion.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_orden.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_nombre.setData(Qt.ItemDataRole.UserRole, doc)

            table.setItem(row, self.COL_ESTADO, item_estado)
            table.setItem(row, self.COL_CODIGO, item_codigo)
            table.setItem(row, self.COL_NOMBRE, item_nombre)
            table.setItem(row, self.COL_CONDICION, item_condicion)
            table.setItem(row, self.COL_REVISADO, item_revisado)
            table.setItem(row, self.COL_ADJUNTO, item_adjunto)
            table.setItem(row, self.COL_ORDEN, item_orden)

            # Fondo sólo si hay estado especial (para respetar alternancia)
            if row_brush is not None:
                for col in range(table.columnCount()):
                    current_item = table.item(row, col)
                    if not current_item:
                        current_item = QTableWidgetItem()
                        table.setItem(row, col, current_item)
                    current_item.setBackground(row_brush)

            # Hacer seleccionables columnas de texto; las de icono solo enabled
            for col in range(table.columnCount()):
                current_item = table.item(row, col)
                if not current_item:
                    current_item = QTableWidgetItem()
                    table.setItem(row, col, current_item)
                if col not in [self.COL_ESTADO, self.COL_REVISADO, self.COL_ADJUNTO]:
                    current_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                else:
                    current_item.setFlags(Qt.ItemFlag.ItemIsEnabled)

        table.horizontalHeader().setSortIndicator(self.COL_ORDEN, Qt.SortOrder.AscendingOrder)
        table.setSortingEnabled(True)

    # ---------- Interacción ----------
    def _on_double_click(self, index: QModelIndex):
        """Handles double-clicking on a row to open the associated file."""
        if not index.isValid():
            return

        table = self.sender()
        if not isinstance(table, QTableWidget):
            return

        item_nombre = table.item(index.row(), self.COL_NOMBRE)
        if not item_nombre:
            return
        doc: Documento | None = item_nombre.data(Qt.ItemDataRole.UserRole)

        if doc and doc.ruta_archivo:
            try:
                ruta_absoluta = reconstruir_ruta_absoluta(doc.ruta_archivo)
                if ruta_absoluta and os.path.exists(ruta_absoluta):
                    if not QDesktopServices.openUrl(QUrl.fromLocalFile(ruta_absoluta)):
                        QMessageBox.warning(self, "Error al Abrir", f"No se pudo iniciar la aplicación asociada para abrir:\n{ruta_absoluta}")
                else:
                    QMessageBox.warning(
                        self, "Archivo no encontrado",
                        f"No se pudo encontrar el archivo adjunto en la ruta:\n{ruta_absoluta}\n\n"
                        f"(Ruta guardada: {doc.ruta_archivo})"
                    )
            except ImportError:
                QMessageBox.critical(self, "Error de Configuración", "Falta la función 'reconstruir_ruta_absoluta' en utils.")
            except Exception as e:
                QMessageBox.critical(self, "Error al abrir archivo", f"No se pudo abrir el archivo:\n{e}")
        else:
            item_adjunto = table.item(index.row(), self.COL_ADJUNTO)
            if item_adjunto and item_adjunto.text() == "📎":
                QMessageBox.information(self, "Sin Ruta", "Este documento está marcado como adjunto, pero la ruta no es válida o está vacía.")