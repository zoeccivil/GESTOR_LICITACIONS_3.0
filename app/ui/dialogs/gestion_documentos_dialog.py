# app/ui/dialogs/gestion_documentos_dialog.py
from __future__ import annotations  # ¡Debe estar al principio!

import os
import copy
import time
import datetime
import unicodedata
import re
from typing import TYPE_CHECKING, List, Optional, Dict, Set, Callable, Any

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QPushButton, QHBoxLayout, QMessageBox, QStyle,
    QDialogButtonBox, QWidget, QFileDialog, QTabWidget, QGridLayout,
    QLabel, QComboBox, QMenu, QStyleOptionButton, QStyledItemDelegate,
    QApplication, QDateEdit
)
from PyQt6.QtCore import Qt, QUrl, QModelIndex, QSize, QDate
from PyQt6.QtGui import (
    QIcon, QDesktopServices, QBrush, QColor, QAction, QPainter,
    QGuiApplication, QPalette
)

# --- App specific imports ---
from app.core.models import Licitacion, Documento
from app.core.db_adapter import DatabaseAdapter
# Diálogo para editar/añadir UN documento
from .gestionar_documento_dialog import DialogoGestionarDocumento
# Diálogo para seleccionar licitación (para import)
from .select_licitacion_dialog import SelectLicitacionDialog
# --- Diálogos NUEVOS (importaciones para funciones futuras) ---
# (Asegúrate de crear estos archivos más adelante)
from .dialogo_seleccionar_documentos import DialogoSeleccionarDocumentos
from .dialogo_confirmar_importacion import DialogoConfirmarImportacion
from .dialogo_gestion_subsanacion import DialogoGestionSubsanacion

# Helpers
from app.core.utils import reconstruir_ruta_absoluta
from app.core.config import obtener_ruta_dropbox

if TYPE_CHECKING:
    pass

# Estados (se recalculan en base al tema; estos son sólo placeholders de compat)
COLOR_OK = None
COLOR_MISSING = QColor("#FFF9C4")  # Amarillo claro (fallback)
COLOR_SUBSANAR = QColor("#FFCDD2")  # Rojo claro (fallback)
CONDICIONES = ["No Definido", "Subsanable", "No Subsanable"]
DEFAULT_CATEGORIES = ["Legal", "Técnica", "Financiera", "Sobre B", "Otros"]


# --- Delegate (Opcional, para centrar checkboxes) ---
class CenteredCheckboxDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option: QStyleOptionButton, index: QModelIndex):
        check_state = index.data(Qt.ItemDataRole.CheckStateRole)
        if check_state is None:
            super().paint(painter, option, index)
            return
        checkbox_option = QStyleOptionButton()
        checkbox_option.rect = option.rect
        checkbox_option.state = option.state | QStyle.StateFlag.State_Enabled
        if check_state == Qt.CheckState.Checked:
            checkbox_option.state |= QStyle.StateFlag.State_On
        elif check_state == Qt.CheckState.PartiallyChecked:
            checkbox_option.state |= QStyle.StateFlag.State_NoChange
        else:
            checkbox_option.state |= QStyle.StateFlag.State_Off
        style = QApplication.style() if option.widget is None else option.widget.style()
        indicator_size = style.pixelMetric(QStyle.PixelMetric.PM_IndicatorWidth, checkbox_option, option.widget)
        indicator_rect = QStyle.alignedRect(
            option.direction, Qt.AlignmentFlag.AlignCenter,
            QSize(indicator_size, indicator_size), checkbox_option.rect
        )
        checkbox_option.rect = indicator_rect
        style.drawPrimitive(QStyle.PrimitiveElement.PE_IndicatorCheckBox, checkbox_option, painter, option.widget)


class GestionDocumentosDialog(QDialog):
    """
    Diálogo mejorado para gestionar documentos de licitación con pestañas,
    acciones rápidas, menú contextual y más interactividad.
    """
    # Índices de columnas
    COL_PRESENTADO = 0
    COL_REVISADO = 1
    COL_ADJUNTO = 2
    COL_CODIGO = 3
    COL_NOMBRE = 4
    COL_CATEGORIA = 5
    COL_CONDICION = 6
    COL_RESPONSABLE = 7

    # --- ESTE ES EL CONSTRUCTOR CORRECTO ---
    def __init__(self, parent: QWidget, licitacion: Licitacion, db: DatabaseAdapter):
        super().__init__(parent)  # Llamada correcta a super()
        self.licitacion_original = licitacion
        self.db = db
        # Copia profunda para edición segura
        self._documentos_editables: List[Documento] = [
            copy.deepcopy(doc) for doc in self.licitacion_original.documentos_solicitados
        ]
        self.categorias = DEFAULT_CATEGORIES
        self._cargar_responsables()  # Carga self.lista_responsables

        # Tema/colores desde QPalette
        self._resolve_theme_colors()

        self.setWindowTitle(f"Gestionar Documentos - {self.licitacion_original.numero_proceso}")
        self.setMinimumSize(1200, 750)

        # Hacer Redimensionable/Maximizable
        flags = self.windowFlags()
        self.setWindowFlags(flags | Qt.WindowType.WindowMaximizeButtonHint | Qt.WindowType.WindowMinimizeButtonHint)

        # Inicializar atributos
        self.btn_edit: Optional[QPushButton] = None
        self.btn_delete: Optional[QPushButton] = None
        self.btn_attach: Optional[QPushButton] = None
        self.btn_view: Optional[QPushButton] = None
        self.btn_remove_attach: Optional[QPushButton] = None
        self.responsable_combo: Optional[QComboBox] = None
        self.revisado_button: Optional[QPushButton] = None
        self.subsanable_button: Optional[QPushButton] = None
        self.buttons: Dict[str, QPushButton] = {}
        self._tables: Dict[str, QTableWidget] = {}

        self._build_ui()
        self._connect_signals()
        self._populate_all_tabs()
        self._update_button_states()

    # ---------- Tema ----------
    def _resolve_theme_colors(self):
        """Lee colores del tema activo y prepara estilos/QSS."""
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
        # Semánticos
        self.COLOR_SUCCESS = "#22C55E"
        self.COLOR_DANGER = "#EF4444"
        self.COLOR_WARNING = "#F59E0B"

        # QSS de pestañas
        self._TABS_QSS = (
            f"QTabWidget::pane{{border:1px solid {self.COLOR_BORDER};background:{self.COLOR_BASE};border-radius:6px;}}"
            f"QTabBar::tab{{background:{self.COLOR_ALT};border:1px solid {self.COLOR_BORDER};padding:6px 12px;"
            f"border-top-left-radius:6px;border-top-right-radius:6px;margin-right:2px;color:{self.COLOR_TEXT_SEC};}}"
            f"QTabBar::tab:selected{{color:{self.COLOR_TEXT};background:{self.COLOR_BASE};"
            f"border-bottom:1px solid {self.COLOR_BASE};}}"
        )
        # QSS de caja/frames
        self._BOX_QSS = (
            f"QGroupBox,QFrame{{background:{self.COLOR_BASE};border:1px solid {self.COLOR_BORDER};"
            f"border-radius:8px;padding:8px;}}"
            f"QGroupBox::title{{left:8px;padding:0 4px;color:{self.COLOR_TEXT_SEC};font-weight:600;}}"
        )

    def _style_table(self, t: QTableWidget):
        """Aplica QSS de tabla acorde al tema."""
        t.setStyleSheet(
            f"QTableWidget{{gridline-color:{self.COLOR_BORDER}; background:{self.COLOR_BASE}; "
            f"alternate-background-color:{self.COLOR_ALT}; selection-background-color:{self.COLOR_ACCENT}; "
            f"selection-color:#ffffff; color:{self.COLOR_TEXT};}} "
            f"QHeaderView::section{{background:{self.COLOR_ALT}; padding:6px; border:1px solid {self.COLOR_BORDER}; "
            f"font-weight:600; color:{self.COLOR_TEXT}; min-height:26px;}}"
        )

    def _accent_overlay(self, base_hex: str, alpha: int = 45) -> QColor:
        """Devuelve un QColor del hex dado con alpha (0-255)."""
        c = QColor(base_hex)
        c.setAlpha(max(0, min(255, alpha)))
        return c

    # ---------- Datos auxiliares ----------
    def _cargar_responsables(self):
        """Carga la lista de responsables (idealmente de DB)."""
        try:
            # Suponiendo que db_adapter tiene este método
            lista_dicts = self.db.get_responsables_maestros()
            self.lista_responsables = ["Sin Asignar"] + sorted([r.get('nombre', '') for r in lista_dicts if r.get('nombre')])
        except AttributeError:
            print("WARN: db_adapter no tiene 'get_responsables_maestros'. Usando lista estática.")
            self.lista_responsables = ["Sin Asignar", "Juan Perez", "Maria Lopez", "Equipo Técnico", "Legal"]
        except Exception as e:
            print(f"Error cargando responsables: {e}. Usando lista estática.")
            self.lista_responsables = ["Sin Asignar", "Juan Perez", "Maria Lopez", "Equipo Técnico", "Legal"]
        self.lista_responsables.sort(key=lambda x: (x == "Sin Asignar", x))

    # ---------- UI ----------
    def _build_ui(self):
        """Construye la interfaz del diálogo."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # --- Pestañas (Notebook) ---
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(self._TABS_QSS)
        main_layout.addWidget(self.tab_widget)

        tab_names = self.categorias + ["⚠️ Subsanables"]
        for tab_name in tab_names:
            is_subsanables_tab = "Subsanables" in tab_name
            tab_content_widget = QWidget()
            tab_layout = QVBoxLayout(tab_content_widget)
            tab_layout.setContentsMargins(5, 5, 5, 5)

            if is_subsanables_tab:
                self._build_subsanables_header(tab_layout)

            table = QTableWidget()
            self._configure_table(table, is_subsanables_tab)
            tab_layout.addWidget(table)
            self._tables[tab_name] = table

            if is_subsanables_tab:
                self._build_subsanables_footer(tab_layout)

            self.tab_widget.addTab(tab_content_widget, tab_name)

        # --- Panel de Acciones Rápidas (Superior) ---
        action_frame = QWidget()
        action_layout = QHBoxLayout(action_frame)
        action_layout.setContentsMargins(0, 5, 0, 5)

        action_layout.addWidget(QLabel("Asignar Responsable:"))
        self.responsable_combo = QComboBox()
        self.responsable_combo.addItems(self.lista_responsables)
        self.responsable_combo.setMinimumWidth(150)
        action_layout.addWidget(self.responsable_combo)
        action_layout.addSpacing(20)

        self.revisado_button = QPushButton("👁️ Marcar Revisado/No Revisado")
        self.revisado_button.setToolTip("Cambia el estado de revisión")
        action_layout.addWidget(self.revisado_button)

        self.subsanable_button = QPushButton("⚖️ Cambiar Condición")
        self.subsanable_button.setToolTip("Cambia la condición (Subsanable/No/Definido)")
        action_layout.addWidget(self.subsanable_button)

        action_layout.addStretch(1)
        main_layout.addWidget(action_frame)

        # --- Botonera Principal (Inferior - Grid) ---
        button_grid_widget = QWidget()
        button_grid_layout = QGridLayout(button_grid_widget)
        button_grid_layout.setSpacing(5)
        style = self.style()

        acciones = {
            "agregar_manual": ("➕ Añadir Manual...", self._add_document, QStyle.StandardPixmap.SP_FileDialogNewFolder),
            "importar_licitacion": ("📥 Importar de Licitación...", self.importar_desde_licitacion, QStyle.StandardPixmap.SP_ArrowDown),
            "agregar_maestro": ("✨ Añadir de Maestro Global...", self.agregar_desde_maestro, QStyle.StandardPixmap.SP_DriveNetIcon),
            "editar": ("✏️ Editar...", self._edit_document, QStyle.StandardPixmap.SP_FileIcon),
            "eliminar": ("🗑️ Eliminar", self._delete_documents, QStyle.StandardPixmap.SP_TrashIcon),
            "cambiar_estado": ("✔️/❌ Presentado", self.cambiar_estado_presentado, QStyle.StandardPixmap.SP_DialogApplyButton),
            "adjuntar_archivo": ("📎 Adjuntar Archivo...", self._attach_file, QStyle.StandardPixmap.SP_DriveHDIcon),
            "ver_archivo": ("📂 Ver Archivo", self._view_file, QStyle.StandardPixmap.SP_FileDialogContentsView),
            "quitar_adjunto": ("❌ Quitar Adjunto", self._remove_attachment, QStyle.StandardPixmap.SP_DialogCloseButton),
            "gestionar_subsanacion": ("⚠️ Gestionar Subsanación...", self.iniciar_subsanacion, QStyle.StandardPixmap.SP_MessageBoxWarning),
        }

        row, col = 0, 0
        max_cols = 4

        for key, (text, func, icon_enum) in acciones.items():
            btn = QPushButton(text)
            try:
                icon = style.standardIcon(icon_enum)
                if not icon.isNull():
                    btn.setIcon(icon)
            except AttributeError:
                print(f"WARN: Icono {icon_enum} no encontrado para '{key}'")

            # Asignar atributos de instancia
            if key == "editar":
                self.btn_edit = btn
            elif key == "eliminar":
                self.btn_delete = btn
            elif key == "adjuntar_archivo":
                self.btn_attach = btn
            elif key == "ver_archivo":
                self.btn_view = btn
            elif key == "quitar_adjunto":
                self.btn_remove_attach = btn
            elif key == "agregar_manual":
                self.btn_add = btn

            btn.clicked.connect(func)
            button_grid_layout.addWidget(btn, row, col)
            self.buttons[key] = btn
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        # Estilos de acción (acorde al tema)
        action_frame.setStyleSheet(self._BOX_QSS)
        button_grid_widget.setStyleSheet(self._BOX_QSS)
        # Botón primario (aplicar color de acento si quieres resaltar algunos)
        for key_name, btn in self.buttons.items():
            if key_name in ("agregar_manual", "importar_licitacion", "agregar_maestro"):
                btn.setStyleSheet(
                    f"QPushButton{{background:{self.COLOR_ALT};color:{self.COLOR_TEXT};"
                    f"border:1px solid {self.COLOR_BORDER};border-radius:6px;padding:6px 10px;}}"
                    f"QPushButton:hover{{border-color:{self.COLOR_ACCENT};}}"
                )

        main_layout.addWidget(button_grid_widget)

        # --- Botones OK/Cancel ---
        dialog_button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            Qt.Orientation.Horizontal
        )
        dialog_button_box.accepted.connect(self.accept)
        dialog_button_box.rejected.connect(self.reject)
        main_layout.addWidget(dialog_button_box)

    def _build_subsanables_header(self, layout: QVBoxLayout):
        """Crea el frame superior de la pestaña Subsanables."""
        header_frame = QWidget()
        header_frame.setStyleSheet(self._BOX_QSS)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(8, 6, 8, 6)
        datos_evento = self.licitacion_original.cronograma.get("Entrega de Subsanaciones", {})
        fecha = datos_evento.get("fecha_limite", "No definida")
        estado = datos_evento.get("estado", "No iniciado")
        self.subsanables_status_label = QLabel(f"<b>Fecha Límite:</b> {fecha}  |  <b>Estado Proceso:</b> {estado}")
        header_layout.addWidget(self.subsanables_status_label)
        header_layout.addStretch(1)
        btn_finalizar = QPushButton("✅ Finalizar Proceso Subsanación")
        btn_finalizar.setToolTip("Marca el proceso como 'Cumplido' y actualiza el historial.")
        btn_finalizar.clicked.connect(self._finalizar_proceso_subsanacion)
        header_layout.addWidget(btn_finalizar)
        layout.addWidget(header_frame)

    def _build_subsanables_footer(self, layout: QVBoxLayout):
        """Crea la botonera inferior de la pestaña Subsanables."""
        footer_frame = QWidget()
        footer_frame.setStyleSheet(self._BOX_QSS)
        footer_layout = QHBoxLayout(footer_frame)
        footer_layout.setContentsMargins(8, 6, 8, 6)
        btn_marcar_completo = QPushButton("✔️ Marcar Seleccionado(s) como Entregado")
        btn_marcar_completo.clicked.connect(self._marcar_subsanables_completados)
        footer_layout.addWidget(btn_marcar_completo)
        footer_layout.addStretch(1)
        layout.addWidget(footer_frame)

    def _configure_table(self, table: QTableWidget, is_subsanables_tab: bool = False):
        """Configura propiedades comunes y específicas de las tablas."""
        if is_subsanables_tab:
            table.setColumnCount(3)
            table.setHorizontalHeaderLabels(["✓", "Código", "Nombre Documento"])
        else:
            table.setColumnCount(8)
            table.setHorizontalHeaderLabels([
                "✓", "👁️", "📎", "Código", "Nombre Documento", "Categoría",
                "Condición", "Responsable"
            ])

        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.setSortingEnabled(True)

        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

        if is_subsanables_tab:
            header.resizeSection(0, 40); header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            header.resizeSection(1, 150)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        else:
            col_map = {
                'estado': self.COL_PRESENTADO, 'revisado': self.COL_REVISADO, 'adjunto': self.COL_ADJUNTO,
                'codigo': self.COL_CODIGO, 'nombre': self.COL_NOMBRE, 'categoria': self.COL_CATEGORIA,
                'condicion': self.COL_CONDICION, 'responsable': self.COL_RESPONSABLE
            }
            header.resizeSection(col_map['estado'], 40); header.setSectionResizeMode(col_map['estado'], QHeaderView.ResizeMode.Fixed)
            header.resizeSection(col_map['revisado'], 40); header.setSectionResizeMode(col_map['revisado'], QHeaderView.ResizeMode.Fixed)
            header.resizeSection(col_map['adjunto'], 40); header.setSectionResizeMode(col_map['adjunto'], QHeaderView.ResizeMode.Fixed)
            header.resizeSection(col_map['codigo'], 130)
            header.setSectionResizeMode(col_map['nombre'], QHeaderView.ResizeMode.Stretch)
            header.resizeSection(col_map['categoria'], 110)
            header.resizeSection(col_map['condicion'], 110)
            header.resizeSection(col_map['responsable'], 140)

        # Estilo acorde al tema
        self._style_table(table)

        self._setup_context_menu(table)
        table.itemSelectionChanged.connect(self._update_button_states)
        table.doubleClicked.connect(self._edit_document_on_double_click)
        # table.setItemDelegateForColumn(self.COL_PRESENTADO, CenteredCheckboxDelegate(table)) # Opcional

    # ---------- Señales ----------
    def _connect_signals(self):
        """Conecta señales de botones globales y cambio de pestaña."""
        # Grid buttons are connected in _build_ui
        if self.responsable_combo:
            self.responsable_combo.currentTextChanged.connect(self._guardar_responsable_multiple)
        if self.revisado_button:
            self.revisado_button.clicked.connect(self._toggle_estado_revisado)
        if self.subsanable_button:
            self.subsanable_button.clicked.connect(self.cambiar_estado_condicion)
        self.tab_widget.currentChanged.connect(self._update_button_states)

    # ---------- Poblar ----------
    def _populate_all_tabs(self):
        """Llena todas las tablas en todas las pestañas."""
        docs_by_cat: Dict[str, List[Documento]] = {cat: [] for cat in self.categorias}
        docs_subsanables: List[Documento] = []

        for doc in self._documentos_editables:
            cat_raw = getattr(doc, 'categoria', '¡¡ATRIBUTO NO ENCONTRADO!!')
            cat_cleaned = cat_raw.strip() if isinstance(cat_raw, str) else None
            cat_processed = cat_cleaned or "Otros"
            cat = cat_processed
            if cat in docs_by_cat:
                docs_by_cat[cat].append(doc)
            elif "Otros" in docs_by_cat:
                docs_by_cat["Otros"].append(doc)
            if getattr(doc, 'requiere_subsanacion', False):
                docs_subsanables.append(doc)

        for cat_name, table in self._tables.items():
            if "Subsanables" in cat_name:
                continue
            docs_in_cat = docs_by_cat.get(cat_name, [])
            self._populate_table(table, docs_in_cat)

        sub_table = self._tables.get("⚠️ Subsanables")
        if sub_table:
            self._populate_table(sub_table, docs_subsanables)

        self._update_button_states()

    def _populate_table(self, table: QTableWidget, documents: List[Documento]):
        """Llena una tabla específica con una lista de documentos."""
        table.blockSignals(True)
        try:
            current_sort_col = table.horizontalHeader().sortIndicatorSection()
            current_sort_ord = table.horizontalHeader().sortIndicatorOrder()
            table.setSortingEnabled(False)
            table.setRowCount(0)
            is_subsanables_tab = table.columnCount() == 3

            def get_sort_key(doc: Documento) -> int:
                orden = getattr(doc, 'orden_pliego', None)
                if orden is None:
                    return 999999
                try:
                    return int(orden)
                except (ValueError, TypeError):
                    return 999999

            docs_sorted = sorted(
                documents,
                key=lambda d: (get_sort_key(d), str(d.codigo or ""), str(d.nombre or ""))
            )

            for doc in docs_sorted:
                row = table.rowCount()
                table.insertRow(row)
                is_presentado = getattr(doc, 'presentado', False)
                needs_subsanacion = getattr(doc, 'requiere_subsanacion', False)

                # Estado/coloreado de fila (no forzar fondo para OK para respetar alternancia)
                row_brush: Optional[QBrush] = None
                estado_icon = "✅" if is_presentado else "❌"
                if needs_subsanacion:
                    estado_icon = "⚠️"
                    row_brush = QBrush(self._accent_overlay(self.COLOR_DANGER, 58))
                elif not is_presentado:
                    row_brush = QBrush(self._accent_overlay(self.COLOR_WARNING, 46))

                item_estado = QTableWidgetItem(estado_icon)

                if is_subsanables_tab:
                    item_codigo = QTableWidgetItem(doc.codigo or "")
                    item_nombre = QTableWidgetItem(doc.nombre or "")
                    item_nombre.setData(Qt.ItemDataRole.UserRole, doc)
                    table.setItem(row, 0, item_estado)
                    table.setItem(row, 1, item_codigo)
                    table.setItem(row, 2, item_nombre)
                else:
                    revisado_icon = "👁️" if getattr(doc, 'revisado', False) else ""
                    adjunto_icon = "📎" if getattr(doc, 'ruta_archivo', '') else ""
                    condicion = getattr(doc, 'subsanable', 'N/D') or 'N/D'
                    responsable = getattr(doc, 'responsable', 'Sin Asignar') or 'Sin Asignar'
                    item_revisado = QTableWidgetItem(revisado_icon)
                    item_adjunto = QTableWidgetItem(adjunto_icon)
                    item_codigo = QTableWidgetItem(doc.codigo or "")
                    item_nombre = QTableWidgetItem(doc.nombre or "")
                    item_categoria = QTableWidgetItem(doc.categoria or "Otros")
                    item_condicion = QTableWidgetItem(condicion)
                    item_responsable = QTableWidgetItem(responsable)
                    item_nombre.setData(Qt.ItemDataRole.UserRole, doc)
                    item_revisado.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    item_adjunto.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    item_categoria.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    item_condicion.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    item_estado.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    table.setItem(row, self.COL_PRESENTADO, item_estado)
                    table.setItem(row, self.COL_REVISADO, item_revisado)
                    table.setItem(row, self.COL_ADJUNTO, item_adjunto)
                    table.setItem(row, self.COL_CODIGO, item_codigo)
                    table.setItem(row, self.COL_NOMBRE, item_nombre)
                    table.setItem(row, self.COL_CATEGORIA, item_categoria)
                    table.setItem(row, self.COL_CONDICION, item_condicion)
                    table.setItem(row, self.COL_RESPONSABLE, item_responsable)

                # Aplicar fondo solamente si hay estado especial
                if row_brush is not None:
                    for col in range(table.columnCount()):
                        current_item = table.item(row, col)
                        if not current_item:
                            current_item = QTableWidgetItem()
                            table.setItem(row, col, current_item)
                        current_item.setBackground(row_brush)

                # Flags de selección (dejar seleccionables columnas de texto)
                object_column = self.COL_NOMBRE if not is_subsanables_tab else 2
                for col in range(table.columnCount()):
                    current_item = table.item(row, col)
                    if not current_item:
                        current_item = QTableWidgetItem()
                        table.setItem(row, col, current_item)
                    if col == object_column or \
                       (not is_subsanables_tab and col in [self.COL_CODIGO, self.COL_CATEGORIA, self.COL_CONDICION, self.COL_RESPONSABLE]) or \
                       (is_subsanables_tab and col == 1):
                        current_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                    else:
                        current_item.setFlags(Qt.ItemFlag.ItemIsEnabled)

            if not is_subsanables_tab:
                table.resizeColumnsToContents()
                table.horizontalHeader().setSectionResizeMode(self.COL_NOMBRE, QHeaderView.ResizeMode.Stretch)
            else:
                table.resizeColumnsToContents()
                table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        finally:
            table.setSortingEnabled(True)
            if current_sort_col >= 0:
                table.sortByColumn(current_sort_col, current_sort_ord)
            table.blockSignals(False)

    # ---------- Helpers selección ----------
    def _get_active_table(self) -> Optional[QTableWidget]:
        current_widget = self.tab_widget.currentWidget()
        if current_widget:
            return current_widget.findChild(QTableWidget)
        return None

    def _update_button_states(self):
        active_table = self._get_active_table()
        count = 0
        selected_docs = []
        if active_table:
            selected_rows_indices = {item.row() for item in active_table.selectedItems()}
            count = len(selected_rows_indices)
            selected_docs = self._get_selected_documents()

        if self.btn_edit:
            self.btn_edit.setEnabled(count == 1)
        if self.btn_delete:
            self.btn_delete.setEnabled(count > 0)
        if self.btn_attach:
            self.btn_attach.setEnabled(count > 0)
        if self.responsable_combo:
            self.responsable_combo.setEnabled(count > 0)
        if self.revisado_button:
            self.revisado_button.setEnabled(count > 0)
        if self.subsanable_button:
            self.subsanable_button.setEnabled(count == 1)
        if "cambiar_estado" in self.buttons:
            self.buttons["cambiar_estado"].setEnabled(count > 0)

        doc_seleccionado_unico = selected_docs[0] if count == 1 else None
        has_file = bool(doc_seleccionado_unico and doc_seleccionado_unico.ruta_archivo)
        if self.btn_view:
            self.btn_view.setEnabled(count == 1 and has_file)
        if self.btn_remove_attach:
            self.btn_remove_attach.setEnabled(count == 1 and has_file)

        if self.responsable_combo:
            self.responsable_combo.blockSignals(True)
            if doc_seleccionado_unico:
                self.responsable_combo.setCurrentText(doc_seleccionado_unico.responsable or "Sin Asignar")
            elif count == 0:
                self.responsable_combo.setCurrentIndex(0)
            self.responsable_combo.blockSignals(False)

    def _get_selected_documents(self) -> List[Documento]:
        active_table = self._get_active_table()
        if not active_table:
            return []
        docs = []
        selected_rows = sorted(list({item.row() for item in active_table.selectedItems()}))
        object_column = self.COL_NOMBRE if active_table.columnCount() > 3 else 2
        for row in selected_rows:
            item = active_table.item(row, object_column)
            if item:
                doc_data = item.data(Qt.ItemDataRole.UserRole)
                if isinstance(doc_data, Documento):
                    docs.append(doc_data)
        return docs

    def _get_selected_document(self) -> Optional[Documento]:
        docs = self._get_selected_documents()
        return docs[0] if len(docs) == 1 else None

    # --- Acciones CRUD ---
    def _add_document(self):
        """Abre DialogoGestionarDocumento para crear uno nuevo."""
        active_tab_index = self.tab_widget.currentIndex()
        active_tab_name = self.tab_widget.tabText(active_tab_index)
        is_subsanables_active = "Subsanables" in active_tab_name

        initial_cat = None
        if not is_subsanables_active and active_tab_name in self.categorias:
            initial_cat = active_tab_name
        else:
            initial_cat = self.categorias[0] if self.categorias else "Otros"

        dlg = DialogoGestionarDocumento(
            parent=self, title="Añadir Nuevo Documento",
            initial_data={'categoria': initial_cat},  # Pasa un dict
            categories=self.categorias,
            responsables=self.lista_responsables
        )
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.resultado:
            try:
                nuevo_doc = Documento(**dlg.resultado)
                nuevo_doc.id = int(time.time() * -1000 + len(self._documentos_editables))
                if is_subsanables_active:
                    nuevo_doc.requiere_subsanacion = True
                nuevo_doc.orden_pliego = len(self._documentos_editables) + 1
                self._documentos_editables.append(nuevo_doc)
                self._populate_all_tabs()
                print(f"Nuevo documento '{nuevo_doc.nombre}' añadido (temporal).")
            except Exception as e:
                QMessageBox.critical(self, "Error al Crear", f"No se pudo crear objeto:\n{e}")

    def _edit_document(self):
        doc_to_edit = self._get_selected_document()
        if not doc_to_edit:
            QMessageBox.warning(self, "Selección Requerida", "Por favor, selecciona un único documento para editar.")
            return
        self._open_edit_dialog_for_doc(doc_to_edit)

    def _edit_document_on_double_click(self, index: QModelIndex):
        active_table = self._get_active_table()
        if not active_table or not index.isValid():
            return
        object_column = self.COL_NOMBRE if active_table.columnCount() > 3 else 2
        item = active_table.item(index.row(), object_column)
        if not item:
            return
        doc: Documento | None = item.data(Qt.ItemDataRole.UserRole)
        if doc:
            print(f"Doble clic en doc {doc.codigo}. Abriendo editor...")
            self._open_edit_dialog_for_doc(doc)

    def _open_edit_dialog_for_doc(self, doc_to_edit: Documento):
        """Abre el diálogo de edición para un documento específico."""
        dlg = DialogoGestionarDocumento(
            parent=self,
            title=f"Editar Documento - {doc_to_edit.codigo}",
            initial_data=doc_to_edit,  # Pasa el objeto Documento
            categories=self.categorias,
            responsables=self.lista_responsables
        )
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.resultado:
            try:
                updated_data = dlg.resultado
                for key, value in updated_data.items():
                    if hasattr(doc_to_edit, key):
                        setattr(doc_to_edit, key, value)
                self._populate_all_tabs()
                print(f"Documento '{doc_to_edit.nombre}' actualizado (temporal).")
            except Exception as e:
                QMessageBox.critical(self, "Error al Actualizar", f"No se pudo actualizar:\n{e}")

    def _delete_documents(self):
        docs_to_delete = self._get_selected_documents()
        if not docs_to_delete:
            QMessageBox.warning(self, "Selección Requerida", "Selecciona uno o más documentos para eliminar.")
            return

        count = len(docs_to_delete)
        confirm_msg = f"¿Estás seguro de eliminar {count} documento(s)?\n\n"
        confirm_msg += "\n".join([f"- [{d.codigo}] {d.nombre}" for d in docs_to_delete[:5]])
        if count > 5:
            confirm_msg += "\n..."
        confirm_msg += "\n\n(Se eliminarán permanentemente al guardar)"

        reply = QMessageBox.question(
            self, "Confirmar Eliminación", confirm_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            ids_to_remove = {d.id for d in docs_to_delete}
            initial_count = len(self._documentos_editables)
            self._documentos_editables = [doc for doc in self._documentos_editables if doc.id not in ids_to_remove]
            final_count = len(self._documentos_editables)
            if final_count < initial_count:
                self._populate_all_tabs()
                print(f"{initial_count - final_count} documento(s) marcados para eliminar.")

    # --- Acciones Archivos ---
    def _attach_file(self):
        docs_to_attach = self._get_selected_documents()
        if not docs_to_attach:
            QMessageBox.warning(self, "Selección Requerida", "Selecciona uno o más documentos para adjuntarles un archivo.")
            return
        filePath, _ = QFileDialog.getOpenFileName(self, "Seleccionar Archivo Adjunto", "", "Todos los Archivos (*.*)")
        if not filePath:
            return
        path_to_save = filePath
        try:
            dropbox_base = obtener_ruta_dropbox()
            if dropbox_base and os.path.normpath(filePath).startswith(os.path.normpath(dropbox_base)):
                relative_path = os.path.relpath(filePath, dropbox_base).replace(os.sep, '/')
                path_to_save = relative_path
                print(f"Archivo en Dropbox detectado. Guardando ruta relativa: {path_to_save}")
            elif dropbox_base:
                QMessageBox.information(
                    self, "Ruta Absoluta Guardada",
                    "El archivo no está dentro de Dropbox. Se guardará la ruta completa.",
                    QMessageBox.StandardButton.Ok
                )
        except ImportError:
            print("WARN: No se encontró 'obtener_ruta_dropbox'.")
        except Exception as e:
            print(f"Error procesando ruta: {e}.")
        modified_count = 0
        for doc in docs_to_attach:
            doc.ruta_archivo = path_to_save
            doc.presentado = True
            doc.requiere_subsanacion = False
            modified_count += 1
        if modified_count > 0:
            self._populate_all_tabs()
            print(f"Archivo '{os.path.basename(filePath)}' adjuntado a {modified_count} documento(s).")

    def _view_file(self):
        doc = self._get_selected_document()
        if not (doc and doc.ruta_archivo):
            QMessageBox.warning(self, "Sin Archivo / Selección", "Selecciona un único documento con archivo adjunto.")
            return
        try:
            absolute_path = reconstruir_ruta_absoluta(doc.ruta_archivo)
            if absolute_path and os.path.exists(absolute_path):
                if not QDesktopServices.openUrl(QUrl.fromLocalFile(absolute_path)):
                    QMessageBox.warning(self, "Error al Abrir", f"No se pudo abrir:\n{absolute_path}")
            else:
                QMessageBox.warning(self, "Archivo no Encontrado", f"No se encontró:\n{absolute_path}")
        except ImportError:
            QMessageBox.critical(self, "Error", "Falta 'reconstruir_ruta_absoluta'.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir:\n{e}")

    def _remove_attachment(self):
        doc = self._get_selected_document()
        if not (doc and doc.ruta_archivo):
            QMessageBox.warning(self, "Sin Archivo / Selección", "Selecciona un único documento con archivo adjunto.")
            return
        reply = QMessageBox.question(
            self, "Confirmar", f"¿Quitar adjunto de '{doc.nombre}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            doc.ruta_archivo = ""
            doc.presentado = False
            self._populate_all_tabs()
            print(f"Adjunto quitado de '{doc.nombre}'.")

    # --- Acciones de Estado Múltiple ---
    def _guardar_responsable_multiple(self, nuevo_responsable: str):
        if not self.sender() or not self.sender().isEnabled():
            return
        docs = self._get_selected_documents()
        if docs and nuevo_responsable:
            modified = False
            for d in docs:
                if d.responsable != nuevo_responsable:
                    d.responsable = nuevo_responsable
                    modified = True
            if modified:
                self._populate_all_tabs()
                print(f"Responsable '{nuevo_responsable}' asignado a {len(docs)} doc(s).")

    def _toggle_estado_revisado(self):
        docs = self._get_selected_documents()
        if not docs:
            return
        nuevo_estado = not all(getattr(d, "revisado", False) for d in docs)
        for d in docs:
            d.revisado = nuevo_estado
        self._populate_all_tabs()

    def cambiar_estado_presentado(self):
        docs = self._get_selected_documents()
        if not docs:
            return
        nuevo_estado = not all(getattr(d, "presentado", False) for d in docs)
        for d in docs:
            d.presentado = nuevo_estado
        self._populate_all_tabs()

    def cambiar_estado_condicion(self):
        doc = self._get_selected_document()
        if not doc:
            return
        current_condicion = getattr(doc, "subsanable", None) or CONDICIONES[0]
        try:
            current_index = CONDICIONES.index(current_condicion)
            next_index = (current_index + 1) % len(CONDICIONES)
        except ValueError:
            next_index = 1
        doc.subsanable = CONDICIONES[next_index]
        self._populate_all_tabs()

    # --- Acciones de Importación / Plantillas ---
    def importar_desde_licitacion(self):
        """Abre un diálogo para importar documentos desde otra licitación."""
        if not self.db:
            QMessageBox.critical(self, "Error", "Adaptador de base de datos no disponible.")
            return
        try:
            # Reutilizar el diálogo de selección existente
            dlg_select = SelectLicitacionDialog(parent=self, db_adapter=self.db)

            if dlg_select.exec() == QDialog.DialogCode.Accepted and dlg_select.selected_id:
                if dlg_select.selected_id == self.licitacion_original.id:
                    QMessageBox.warning(self, "Acción Inválida", "No puedes importar documentos desde la misma licitación.")
                    return

                lic_origen = self.db.load_licitacion_by_id(dlg_select.selected_id)
                if not lic_origen:
                    QMessageBox.warning(self, "Error", "No se pudo cargar la licitación de origen.")
                    return

                codigos_existentes = {d.codigo for d in self._documentos_editables if d.codigo}
                nuevos_agregados = 0
                docs_para_anadir = []

                for doc_origen in lic_origen.documentos_solicitados:
                    if doc_origen.codigo and doc_origen.codigo not in codigos_existentes:
                        nuevo_doc = Documento(
                            codigo=doc_origen.codigo, nombre=doc_origen.nombre, categoria=doc_origen.categoria,
                            subsanable=getattr(doc_origen, "subsanable", CONDICIONES[0]),
                            comentario=getattr(doc_origen, "comentario", ""),
                            obligatorio=bool(getattr(doc_origen, "obligatorio", False))
                        )
                        nuevo_doc.id = int(time.time() * -1000 + len(self._documentos_editables) + nuevos_agregados)
                        nuevo_doc.orden_pliego = len(self._documentos_editables) + nuevos_agregados + 1

                        docs_para_anadir.append(nuevo_doc)
                        codigos_existentes.add(nuevo_doc.codigo)
                        nuevos_agregados += 1

                if nuevos_agregados > 0:
                    self._documentos_editables.extend(docs_para_anadir)
                    self._populate_all_tabs()
                    QMessageBox.information(self, "Importación Completa", f"Se importaron {nuevos_agregados} documentos nuevos.")
                else:
                    QMessageBox.information(self, "Sin Novedades", "No se encontraron documentos nuevos (por código) en la licitación seleccionada.")

        except Exception as e:
            QMessageBox.critical(self, "Error de Importación", f"Ocurrió un error al importar:\n{e}")

    def agregar_desde_maestro(self):
        """
        Añade documentos desde la lista Maestra Global (anteriormente 'plantilla').
        """
        try:
            # 1. Obtener documentos maestros (globales)
            # Asegúrate que este método exista en tu db_adapter
            documentos_maestros = self.db.get_documentos_maestros()
            if not documentos_maestros:
                QMessageBox.information(self, "Maestro Vacío", "No hay documentos en el maestro global.")
                return
        except AttributeError:
            QMessageBox.critical(self, "Error DB", "El método 'get_documentos_maestros' no existe en el db_adapter.")
            return
        except Exception as e_db:
            QMessageBox.critical(self, "Error DB", f"No se pudieron cargar los documentos maestros:\n{e_db}")
            return

        try:
            # 2. Abrir diálogo de selección
            dlg_seleccion = DialogoSeleccionarDocumentos(
                self, "Seleccionar de Maestro Global",
                documentos_maestros,
                self._documentos_editables  # Pasar docs actuales para filtrar
            )

            if dlg_seleccion.exec() == QDialog.DialogCode.Accepted:
                documentos_a_importar = dlg_seleccion.get_selected_docs()  # Lista de Documentos (maestros)
                if not documentos_a_importar:
                    return  # Usuario aceptó pero no seleccionó nada

                # 3. Abrir diálogo de confirmación y categorización
                dlg_confirmar = DialogoConfirmarImportacion(self, documentos_a_importar, self.categorias)

                if dlg_confirmar.exec() == QDialog.DialogCode.Accepted:
                    nuevos_agregados = 0
                    docs_para_anadir = []
                    codigos_existentes = {d.codigo for d in self._documentos_editables if d.codigo}

                    # Resultado es lista de dicts: {'id_maestro', 'categoria', ...}
                    for doc_data in dlg_confirmar.get_result_data():
                        # Encontrar el objeto maestro original por ID
                        doc_maestro = next((d for d in documentos_maestros if d.id == doc_data['id_maestro']), None)

                        if doc_maestro and (doc_maestro.codigo not in codigos_existentes):
                            nuevo_doc = Documento(
                                codigo=doc_maestro.codigo,
                                nombre=doc_maestro.nombre,
                                categoria=doc_data['categoria'],  # Usar categoría (potencialmente) modificada
                                comentario=doc_maestro.comentario,
                                subsanable=getattr(doc_maestro, "subsanable", CONDICIONES[0]),
                                obligatorio=bool(getattr(doc_maestro, "obligatorio", False)),
                                ruta_archivo=getattr(doc_maestro, "ruta_archivo", "")  # Copiar ruta si es plantilla
                            )
                            # Asignar ID temporal y orden
                            nuevo_doc.id = int(time.time() * -1000 + len(self._documentos_editables) + nuevos_agregados)
                            nuevo_doc.orden_pliego = len(self._documentos_editables) + nuevos_agregados + 1

                            docs_para_anadir.append(nuevo_doc)
                            codigos_existentes.add(nuevo_doc.codigo)  # Asegurar no duplicar en la misma tanda
                            nuevos_agregados += 1

                    # 4. Añadir a la lista y refrescar
                    if nuevos_agregados > 0:
                        self._documentos_editables.extend(docs_para_anadir)
                        self._populate_all_tabs()
                        QMessageBox.information(self, "Éxito", f"Se agregaron {nuevos_agregados} documentos desde el maestro global.")
                    else:
                        QMessageBox.information(self, "Sin Novedades", "No se añadieron documentos (posiblemente ya existían por código).")

        except ImportError as e_imp:
            # Captura si falta DialogoSeleccionarDocumentos o DialogoConfirmarImportacion
            QMessageBox.critical(self, "Error de Archivo", f"Falta un archivo de diálogo necesario:\n{e_imp.name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Ocurrió un error al agregar desde maestro:\n{e}")
            print(f"Error detallado en agregar_desde_maestro: {e}")

    # --- Acciones Subsanación ---
    def iniciar_subsanacion(self):
        """Abre el diálogo para gestionar el proceso de subsanación."""
        if not self.licitacion_original.id:
            QMessageBox.warning(self, "Licitación no Guardada", "La licitación debe guardarse al menos una vez para gestionar subsanaciones.")
            return

        try:
            def guardar_y_refrescar_memoria():
                """Callback para que el diálogo hijo actualice esta UI."""
                print("Callback: Refrescando UI de Gestión de Documentos...")
                self._populate_all_tabs()
                self._actualizar_label_subsanacion()
                print("Callback: UI Refrescada.")
                # (El guardado real en DB lo maneja el diálogo de subsanación)

            # Importar el diálogo aquí para evitar error circular si no se usa
            from .dialogo_gestion_subsanacion import DialogoGestionSubsanacion

            dlg_sub = DialogoGestionSubsanacion(
                parent=self,
                licitacion=self.licitacion_original,
                db_adapter=self.db,  # Pasar el ADAPTER
                callback_guardar_en_memoria=guardar_y_refrescar_memoria,
                documentos_editables=self._documentos_editables
            )
            dlg_sub.exec()

            # Refrescar UI después de CUALQUIER cierre
            self._populate_all_tabs()
            self._actualizar_label_subsanacion()

        except ImportError:
            self._show_not_implemented("Diálogo 'dialogo_gestion_subsanacion.py'")
        except AttributeError as e_attr:
            QMessageBox.critical(self, "Error DB", f"Falta un método en el db_adapter:\n{e_attr}")
        except Exception as e:
            QMessageBox.critical(self, "Error Inesperado", f"No se pudo iniciar la gestión de subsanación:\n{e}")
            print(f"Error detallado en iniciar_subsanacion: {e}")

    def _marcar_subsanables_completados(self):
        """Marca los documentos seleccionados en la pestaña 'Subsanables' como presentados."""
        sub_table = self._tables.get("⚠️ Subsanables")
        if not sub_table:
            return

        selected_rows = sorted(list({item.row() for item in sub_table.selectedItems()}))
        if not selected_rows:
            QMessageBox.warning(self, "Sin Selección", "Selecciona documentos subsanables para marcar.")
            return

        docs_a_marcar_ids: Set[int] = set()
        for row in selected_rows:
            item = sub_table.item(row, 2)  # Object is in Col 2
            if item and isinstance(item.data(Qt.ItemDataRole.UserRole), Documento):
                doc: Documento = item.data(Qt.ItemDataRole.UserRole)
                if doc.id is not None:
                    docs_a_marcar_ids.add(doc.id)

        if not docs_a_marcar_ids:
            return

        modificados = 0
        for doc in self._documentos_editables:  # Modificar la lista interna
            if doc.id in docs_a_marcar_ids:
                doc.presentado = True
                doc.requiere_subsanacion = False
                modificados += 1
                try:
                    if hasattr(self.db, "completar_evento_subsanacion"):
                        self.db.completar_evento_subsanacion(self.licitacion_original.id, doc.id, doc.codigo)
                except Exception as e_db:
                    print(f"WARN: Error DB al completar subsanación: {e_db}")

        if modificados > 0:
            self._populate_all_tabs()
            QMessageBox.information(self, "Éxito", f"{modificados} documento(s) subsanables marcados.")
        else:
            QMessageBox.warning(self, "Error", "No se encontraron documentos para marcar.")

    def _finalizar_proceso_subsanacion(self):
        """Marca el proceso de subsanación como 'Cumplido'."""
        if QMessageBox.question(
            self, "Confirmar Finalización",
            "¿Marcar proceso subsanación como 'Cumplido'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:

            docs_pendientes_antes = [d for d in self._documentos_editables if getattr(d, 'requiere_subsanacion', False) and d.id]

            cronograma = self.licitacion_original.cronograma
            if "Entrega de Subsanaciones" not in cronograma:
                cronograma["Entrega de Subsanaciones"] = {}
            cronograma["Entrega de Subsanaciones"]["estado"] = "Cumplido"

            for doc in self._documentos_editables:
                doc.requiere_subsanacion = False

            try:
                if hasattr(self.db, "completar_evento_subsanacion"):
                    for doc in docs_pendientes_antes:
                        self.db.completar_evento_subsanacion(self.licitacion_original.id, doc.id, doc.codigo)
            except Exception as e_db:
                print(f"WARN: Error DB al finalizar subsanación: {e_db}")

            self._populate_all_tabs()
            self._actualizar_label_subsanacion()
            QMessageBox.information(self, "Proceso Finalizado", "Subsanación marcada como 'Cumplido'.")

    def _actualizar_label_subsanacion(self):
        """Actualiza el texto del QLabel en la pestaña Subsanables."""
        if hasattr(self, 'subsanables_status_label'):
            datos = self.licitacion_original.cronograma.get("Entrega de Subsanaciones", {})
            fecha = datos.get("fecha_limite", "No definida")
            estado = datos.get("estado", "No iniciado")
            self.subsanables_status_label.setText(f"<b>Fecha Límite:</b> {fecha} | <b>Estado:</b> {estado}")

    # --- Menú Contextual ---
    def _setup_context_menu(self, table: QTableWidget):
        """Configura las acciones del menú contextual."""
        if not hasattr(self, "_context_actions"):
            self._context_actions: Dict[str, QAction] = {}
            style = self.style()
            action_defs = [
                ("edit", "✏️ Editar Documento...", self._edit_document, QStyle.StandardPixmap.SP_FileIcon, True),
                ("delete", "🗑️ Eliminar Documento(s)", self._delete_documents, QStyle.StandardPixmap.SP_TrashIcon, False),
                ("separator1", "-", None, None, False),
                ("attach", "📎 Adjuntar Archivo...", self._attach_file, QStyle.StandardPixmap.SP_DriveHDIcon, False),
                ("view", "📂 Ver Archivo Adjunto", self._view_file, QStyle.StandardPixmap.SP_FileDialogContentsView, True),
                ("remove_attach", "❌ Quitar Adjunto", self._remove_attachment, QStyle.StandardPixmap.SP_DialogCloseButton, True),
                ("separator2", "-", None, None, False),
                ("toggle_presentado", "✔️/❌ Cambiar Estado (Presentado)", self.cambiar_estado_presentado, QStyle.StandardPixmap.SP_DialogApplyButton, False),
                ("toggle_revisado", "👁️ Marcar Revisado/No Revisado", self._toggle_estado_revisado, QStyle.StandardPixmap.SP_DialogYesButton, False),
                ("change_condicion", "⚖️ Cambiar Condición", self.cambiar_estado_condicion, QStyle.StandardPixmap.SP_DialogHelpButton, True),
            ]
            for key, text, func, icon_enum, single_only in action_defs:
                if key.startswith("separator"):
                    action = QAction(self)
                    action.setSeparator(True)
                else:
                    action = QAction(text, self)
                    if func:
                        action.triggered.connect(func)
                    if icon_enum:
                        try:
                            icon = style.standardIcon(icon_enum)
                            action.setIcon(icon)
                        except AttributeError:
                            pass
                    action.setProperty("single_selection_only", single_only)
                self._context_actions[key] = action

        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(lambda pos, tbl=table: self._show_context_menu(pos, tbl))

    def _show_context_menu(self, pos, table: QTableWidget):
        """Muestra el menú contextual en la tabla dada."""
        selected_docs = []
        selected_rows = sorted(list({item.row() for item in table.selectedItems()}))
        object_column = self.COL_NOMBRE if table.columnCount() > 3 else 2
        for row in selected_rows:
            item = table.item(row, object_column)
            if item and isinstance(item.data(Qt.ItemDataRole.UserRole), Documento):
                selected_docs.append(item.data(Qt.ItemDataRole.UserRole))

        count = len(selected_docs)
        doc_single = selected_docs[0] if count == 1 else None
        has_file = bool(doc_single and doc_single.ruta_archivo)

        menu = QMenu(self)
        for key, action in self._context_actions.items():
            enabled = True
            if count == 0 and not key.startswith("separator"):
                enabled = False
            elif action.property("single_selection_only") and count != 1:
                enabled = False
            elif key in ["view", "remove_attach"] and not (count == 1 and has_file):
                enabled = False
            action.setEnabled(enabled)
            menu.addAction(action)

        menu.exec(table.viewport().mapToGlobal(pos))

    # --- Accept/Reject ---
    def accept(self):
        print("GestionDocumentosDialog: OK presionado. Actualizando lista original...")
        self.licitacion_original.documentos_solicitados = self._documentos_editables
        super().accept()

    def reject(self):
        print("GestionDocumentosDialog: Cancelado. Cambios descartados.")
        super().reject()

    # --- Placeholder ---
    def _no_implementado(self, feature_name: str = "Esta función"):
        QMessageBox.information(self, "Próximamente", f"{feature_name} aún no está implementada.")