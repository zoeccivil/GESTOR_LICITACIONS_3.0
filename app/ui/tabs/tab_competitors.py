from __future__ import annotations
import locale
from typing import TYPE_CHECKING, List, Dict, Any, Optional

# --- CORRECCIÓN IMPORTS ---
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QAbstractItemView, QMessageBox, QStyle, QDialog,
    QSplitter, QGroupBox, QGridLayout, QScrollArea, QFormLayout, QLabel,
    QComboBox
)
from PyQt6.QtCore import Qt, QModelIndex  # Added QModelIndex
from PyQt6.QtGui import QIcon, QColor, QBrush, QFont
# --- FIN CORRECCIÓN ---

# Importamos las clases de datos y el adaptador
from app.core.models import Licitacion, Lote, Oferente
from app.core.db_adapter import DatabaseAdapter

# --- Diálogos necesarios ---
# Asegúrate de que estos archivos estén en app/ui/dialogs/
from app.ui.dialogs.gestionar_oferente_dialog import DialogoGestionarOferente
from app.ui.dialogs.dialogo_gestionar_oferta_lote import DialogoGestionarOfertaLote
from app.ui.dialogs.select_licitacion_dialog import SelectLicitacionDialog  # (Comentado si no se usa aquí)
# app/ui/tabs/tab_competitors.py
# ... (otras importaciones)
from app.ui.dialogs.dialogo_seleccionar_competidores import DialogoSeleccionarCompetidores
from app.ui.dialogs.dialogo_analisis_paquetes import DialogoAnalisisPaquetes  # <-- AÑADIR
# Añade el import
from app.ui.dialogs.dialogo_parametros_evaluacion import DialogoElegirMetodoEvaluacionQt, DialogoParametrosEvaluacionQt
# --- Fin de diálogos ---
from app.ui.dialogs.dialogo_parametros_evaluacion import DialogoParametrosEvaluacionQt  # si lo usas en otro flujo
from app.ui.dialogs.dialogo_resultados_evaluacion import DialogoResultadosEvaluacion
from PyQt6.QtWidgets import QMessageBox
from typing import Callable
from app.ui.dialogs.dialogo_fallas_fase_a import DialogoFallasFaseA
from PyQt6.QtWidgets import QMessageBox

if TYPE_CHECKING:
    # Evita importación circular, solo para type hinting
    from app.ui.windows.licitation_details_window import LicitationDetailsWindow

# Configurar la localización para formatos de moneda
try:
    locale.setlocale(locale.LC_ALL, '')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'es_ES.UTF-8')  # Fallback
    except locale.Error:
        print("Advertencia: No se pudo establecer la localización para moneda.")


class TabCompetitors(QWidget):
    """
    Pestaña para gestionar Competidores, sus Ofertas por Lote
    y asignar Ganadores.
    """

    # Índices de columnas (Tabla Ofertas)
    COL_OFERTA_LOTE = 0
    COL_OFERTA_NOMBRE = 1
    COL_OFERTA_MONTO = 2
    COL_OFERTA_ADJUDICADA = 3

    # Titanium Construct colors for offer highlighting
    COLOR_GANADOR = QColor("#D1FAE5")      # Success green for winner
    BRUSH_GANADOR = QBrush(COLOR_GANADOR)
    TEXT_GANADOR = QColor("#065F46")       # Dark green text
    
    COLOR_NUESTRA = QColor("#EEF2FF")      # Indigo for our company
    BRUSH_NUESTRA = QBrush(COLOR_NUESTRA)
    TEXT_NUESTRA = QColor("#4F46E5")       # Indigo text

    def __init__(self, licitacion: Licitacion, db: DatabaseAdapter, parent_window: LicitationDetailsWindow):
        super().__init__(parent_window)
        self.licitacion = licitacion
        self.db = db
        self.parent_window = parent_window
        # En el __init__ de TabCompetitors, después de self.parent_window = parent_window
        # Propagar ReportGenerator (si existe) para que los diálogos hijos lo detecten
        if hasattr(self.parent_window, 'reporter'):
            try:
                self.reporter = getattr(self.parent_window, 'reporter', None)
                if self.reporter:
                    print("[TabCompetitors] Reporter propagado desde ventana padre.")
            except Exception as e:
                print(f"[TabCompetitors] WARN: no se pudo propagar reporter: {e}")
        self.combo_ganador_por_lote: Dict[str, QComboBox] = {}

        self.btn_edit_comp: Optional[QPushButton] = None
        self.btn_del_comp: Optional[QPushButton] = None
        self.btn_add_oferta: Optional[QPushButton] = None
        self.btn_edit_oferta: Optional[QPushButton] = None
        self.btn_del_oferta: Optional[QPushButton] = None

        self._build_ui()
        self._connect_signals()
        self._update_button_states()
        self._loading = False


    def _build_ui(self):
        """Construye la interfaz de la pestaña con QSplitter."""
        main_layout = QHBoxLayout(self)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(main_splitter)

        left_widget = self._build_left_panel()
        right_widget = self._build_right_panel()

        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_widget)
        main_splitter.setSizes([350, 650])

    def _build_left_panel(self) -> QWidget:
        """Construye el panel izquierdo (Lista de competidores y botones)."""
        style = self.style()
        group_competidores = QGroupBox("Competidores")
        layout_competidores = QVBoxLayout(group_competidores)
        layout_competidores.setSpacing(5)

        # Tabla Competidores (sin cambios)
        self.table_competidores = QTableWidget()
        self.table_competidores.setColumnCount(1)
        self.table_competidores.setHorizontalHeaderLabels(["Nombre"])
        self.table_competidores.verticalHeader().setVisible(False)
        self.table_competidores.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_competidores.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_competidores.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table_competidores.setSortingEnabled(True)
        layout_competidores.addWidget(self.table_competidores)

        # Botonera Grid (sin cambios)
        btn_container = QWidget()
        btn_grid_comp = QGridLayout(btn_container)
        btn_grid_comp.setContentsMargins(0, 0, 0, 0)
        btn_grid_comp.setSpacing(5)

        # Iconos (sin cambios)
        icons_left = {}
        icon_map_left = {
            'add': QStyle.StandardPixmap.SP_FileDialogNewFolder,
            'catalog': QStyle.StandardPixmap.SP_DialogOpenButton,
            'import': QStyle.StandardPixmap.SP_ArrowDown,
            'edit': QStyle.StandardPixmap.SP_DialogResetButton,
            'delete': QStyle.StandardPixmap.SP_TrashIcon,
            'analyze_pkg': QStyle.StandardPixmap.SP_FileDialogDetailedView,
            'edit_params': QStyle.StandardPixmap.SP_ComputerIcon,
            'run_eval': QStyle.StandardPixmap.SP_MediaPlay,
            'analyze_fail': QStyle.StandardPixmap.SP_DialogYesButton
        }
        for name, pixmap_enum in icon_map_left.items():
            try:
                icon = style.standardIcon(pixmap_enum)
                if icon.isNull():
                    raise AttributeError(f"Icon {name} is Null")
                icons_left[name] = icon
            except AttributeError as e:
                print(f"WARN [TabCompetitors]: No se pudo cargar icono estándar '{name}' ({e}). Usando icono vacío.")
                icons_left[name] = QIcon()

        # Botones Fila 1 (sin cambios)
        btn_add_manual = QPushButton(" Agregar Manual")
        btn_add_manual.setIcon(icons_left['add'])
        btn_add_catalogo = QPushButton(" Agregar Catálogo...")
        btn_add_catalogo.setIcon(icons_left['catalog'])
        btn_importar = QPushButton(" Importar...")
        btn_importar.setIcon(icons_left['import'])
        btn_grid_comp.addWidget(btn_add_manual, 0, 0)
        btn_grid_comp.addWidget(btn_add_catalogo, 0, 1)
        btn_grid_comp.addWidget(btn_importar, 0, 2)

        # Botones Fila 2 (sin cambios)
        self.btn_edit_comp = QPushButton(" Editar")
        self.btn_edit_comp.setIcon(icons_left['edit'])
        self.btn_del_comp = QPushButton(" Eliminar")
        self.btn_del_comp.setIcon(icons_left['delete'])
        self.btn_del_comp.setProperty("class", "danger")  # Mark as danger action
        btn_analizar_paq = QPushButton(" Analizar Paquetes...")
        btn_analizar_paq.setIcon(icons_left['analyze_pkg'])
        btn_grid_comp.addWidget(self.btn_edit_comp, 1, 0)
        btn_grid_comp.addWidget(self.btn_del_comp, 1, 1)
        btn_grid_comp.addWidget(btn_analizar_paq, 1, 2)

        # Botones Fila 3 (sin cambios)
        btn_edit_params = QPushButton(" Editar Parámetros")
        btn_edit_params.setIcon(icons_left['edit_params'])
        btn_ejecutar_eval = QPushButton(" Ejecutar Evaluación")
        btn_ejecutar_eval.setIcon(icons_left['run_eval'])
        btn_ejecutar_eval.setProperty("class", "primary")  # Mark as primary action
        btn_analizar_fasea = QPushButton(" Análisis de Fallas Fase A…")
        # Usa icono nativo; si manejas un dict icons_left, puedes cambiar esta línea por icons_left['analyze_fail']
        btn_analizar_fasea.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxWarning))
        btn_analizar_fasea.setToolTip("Registrar/gestionar fallas de Fase A por participantes y documentos")
        btn_grid_comp.addWidget(btn_edit_params, 2, 0)
        btn_grid_comp.addWidget(btn_ejecutar_eval, 2, 1)
        btn_grid_comp.addWidget(btn_analizar_fasea, 2, 2)

        layout_competidores.addWidget(btn_container)

        # Conexiones botones (sin cambios)
        btn_add_manual.clicked.connect(self._agregar_competidor)
        self.btn_edit_comp.clicked.connect(self._editar_competidor)
        self.btn_del_comp.clicked.connect(self._eliminar_competidor)
        btn_add_catalogo.clicked.connect(self._agregar_desde_catalogo)
        btn_importar.clicked.connect(self._importar_competidores)
        btn_analizar_paq.clicked.connect(self._abrir_analisis_paquetes)  # Línea NUEVA
        btn_edit_params.clicked.connect(self._abrir_evaluador_ofertas)  # ya creado antes
        btn_ejecutar_eval.clicked.connect(self._ejecutar_evaluacion)
        # Conexión
        btn_analizar_fasea.clicked.connect(self._abrir_analisis_fase_a)

        # Añade el botón al layout donde ubicas el resto (ajusta fila/columna según tu grid)
        btn_grid_comp.addWidget(btn_analizar_fasea, 2, 2)
        return group_competidores

    def _build_right_panel(self) -> QWidget:
        """Construye el panel derecho (Splitter vertical de Ofertas y Ganadores)."""
        style = self.style()
        right_splitter = QSplitter(Qt.Orientation.Vertical)

        # Panel Superior Derecho: Ofertas (sin cambios)
        group_ofertas = QGroupBox("Ofertas por Lote (del competidor seleccionado)")
        layout_ofertas = QVBoxLayout(group_ofertas)
        layout_ofertas.setSpacing(5)

        self.table_ofertas = QTableWidget()
        self.table_ofertas.setColumnCount(4)
        self.table_ofertas.setHorizontalHeaderLabels(["Lote", "Nombre de Lote", "Monto Ofertado", "Adjudicada"])
        self.table_ofertas.verticalHeader().setVisible(False)
        self.table_ofertas.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_ofertas.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_ofertas.horizontalHeader().setSectionResizeMode(self.COL_OFERTA_NOMBRE, QHeaderView.ResizeMode.Stretch)
        self.table_ofertas.setSortingEnabled(True)
        self.table_ofertas.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout_ofertas.addWidget(self.table_ofertas)

        # Botonera Ofertas (sin cambios)
        btn_layout_ofertas = QHBoxLayout()
        btn_layout_ofertas.setContentsMargins(0, 0, 0, 0)

        # Iconos (sin cambios)
        icons_right = {}
        icon_map_right = {
            'add': QStyle.StandardPixmap.SP_FileDialogNewFolder,
            'edit': QStyle.StandardPixmap.SP_DialogResetButton,
            'delete': QStyle.StandardPixmap.SP_TrashIcon
        }
        for name, pixmap_enum in icon_map_right.items():
            try:
                icon = style.standardIcon(pixmap_enum)
                if icon.isNull():
                    raise AttributeError(f"Icon {name} is Null")
                icons_right[name] = icon
            except AttributeError as e:
                print(f"WARN [TabCompetitors]: No se pudo cargar icono estándar '{name}' ({e}). Usando icono vacío.")
                icons_right[name] = QIcon()

        self.btn_add_oferta = QPushButton(" Agregar Oferta")
        self.btn_add_oferta.setIcon(icons_right['add'])
        self.btn_edit_oferta = QPushButton(" Editar Oferta")
        self.btn_edit_oferta.setIcon(icons_right['edit'])
        self.btn_del_oferta = QPushButton(" Eliminar Oferta")
        self.btn_del_oferta.setIcon(icons_right['delete'])
        self.btn_del_oferta.setProperty("class", "danger")  # Mark as danger action

        btn_layout_ofertas.addWidget(self.btn_add_oferta)
        btn_layout_ofertas.addWidget(self.btn_edit_oferta)
        btn_layout_ofertas.addWidget(self.btn_del_oferta)
        btn_layout_ofertas.addStretch(1)
        layout_ofertas.addLayout(btn_layout_ofertas)

        # Conexiones botones Ofertas (sin cambios)
        self.btn_add_oferta.clicked.connect(self._agregar_oferta)
        self.btn_edit_oferta.clicked.connect(self._editar_oferta)
        self.btn_del_oferta.clicked.connect(self._eliminar_oferta)
        self.table_ofertas.doubleClicked.connect(self._editar_oferta_on_double_click)

        right_splitter.addWidget(group_ofertas)

        # Panel Inferior Derecho: Ganadores (sin cambios)
        group_ganadores = QGroupBox("Asignar Ganadores por Lote")
        layout_ganadores = QVBoxLayout(group_ganadores)
        self.scroll_ganadores = QScrollArea()
        self.scroll_ganadores.setWidgetResizable(True)
        self.scroll_ganadores.setMinimumHeight(200)
        self.scroll_content_ganadores = QWidget()
        self.layout_form_ganadores = QFormLayout(self.scroll_content_ganadores)
        self.layout_form_ganadores.setContentsMargins(10, 10, 10, 10)
        self.layout_form_ganadores.setSpacing(10)
        self.layout_form_ganadores.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.scroll_ganadores.setWidget(self.scroll_content_ganadores)
        layout_ganadores.addWidget(self.scroll_ganadores)
        right_splitter.addWidget(group_ganadores)

        right_splitter.setSizes([450, 250])
        return right_splitter

    def _connect_signals(self):
        """Conecta las señales principales de las tablas."""
        self.table_competidores.itemSelectionChanged.connect(self._on_competidor_select)
        self.table_ofertas.itemSelectionChanged.connect(self._on_oferta_select)

    def load_data(self):
        print("TabCompetitors: Cargando datos...")
        self._loading = True
        try:
            self._actualizar_tree_competidores()
            self._rebuild_ganadores_ui()

            if self.table_competidores.rowCount() > 0:
                self.table_competidores.selectRow(0)
                self._on_competidor_select()
            else:
                self._on_competidor_select()
        finally:
            self._loading = False

        print("TabCompetitors: Datos cargados.")

    def collect_data(self) -> bool:
        """Recopila los datos de los ComboBox de Ganadores y los aplica al modelo."""
        print("TabCompetitors: Recolectando datos (aplicando ganadores al modelo)...")
        try:
            self._aplicar_ganadores_al_modelo()
            print("TabCompetitors: Ganadores aplicados al modelo en memoria.")
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error al Recolectar Ganadores",
                                 f"No se pudieron aplicar los ganadores seleccionados:\n{e}")
            print(f"Error detallado en collect_data (TabCompetitors): {e}")
            return False

    # --- Lógica de Actualización de UI ---

    def _actualizar_tree_competidores(self):
        """Rellena la tabla de competidores (panel izquierdo)."""
        self.table_competidores.blockSignals(True)
        try:
            current_selection = self._get_selected_competidor()  # Guardar selección actual
            self.table_competidores.setSortingEnabled(False)
            self.table_competidores.setRowCount(0)

            oferentes = sorted(self.licitacion.oferentes_participantes, key=lambda o: o.nombre)

            restored_row = -1
            for i, oferente in enumerate(oferentes):
                row = self.table_competidores.rowCount()
                self.table_competidores.insertRow(row)

                item = QTableWidgetItem(oferente.nombre)
                item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                item.setData(Qt.ItemDataRole.UserRole, oferente)  # Guardar objeto Oferente

                self.table_competidores.setItem(row, 0, item)
                if current_selection and oferente.nombre == current_selection.nombre:
                    restored_row = row

            if restored_row != -1:
                self.table_competidores.selectRow(restored_row)  # Restaurar selección si es posible

        finally:
            self.table_competidores.setSortingEnabled(True)
            self.table_competidores.blockSignals(False)

    def _actualizar_tree_ofertas(self, competidor: Optional[Oferente]):
        """Rellena la tabla 'Ofertas por Lote' para el competidor seleccionado."""
        self.table_ofertas.blockSignals(True)
        try:
            self.table_ofertas.setSortingEnabled(False)
            self.table_ofertas.setRowCount(0)

            if not competidor:
                # Si no hay competidor, limpiar tabla y salir
                self._on_oferta_select()  # Deshabilitar botones de oferta
                return

            ofertas = sorted(competidor.ofertas_por_lote, key=lambda o: str(o.get("lote_numero", "")))
            bold_font = QFont()
            bold_font.setBold(True)

            for oferta in ofertas:
                lote_num_str = str(oferta.get("lote_numero", ""))
                monto = oferta.get("monto", 0.0) or 0.0

                lote_obj = next((l for l in self.licitacion.lotes if str(l.numero) == lote_num_str), None)
                nombre_lote = lote_obj.nombre if lote_obj else "Lote Desconocido"

                es_ganador = bool(oferta.get("ganador", False))  # 'ganador' se setea en _aplicar_ganadores_al_modelo
                adjudicada_str = "Sí" if es_ganador else "No"

                row = self.table_ofertas.rowCount()
                self.table_ofertas.insertRow(row)

                # Guardar el número de lote (str) como UserRole para identificar la oferta al editar/eliminar
                self._set_oferta_item(row, self.COL_OFERTA_LOTE, lote_num_str, data=lote_num_str, align='center',
                                      is_ganador=es_ganador, bold=bold_font)
                self._set_oferta_item(row, self.COL_OFERTA_NOMBRE, nombre_lote, is_ganador=es_ganador, bold=bold_font)
                try:
                    monto_str = locale.currency(monto, grouping=True)
                except Exception:
                    monto_str = f"{monto:,.2f}"
                self._set_oferta_item(row, self.COL_OFERTA_MONTO, monto_str, align='right', is_ganador=es_ganador,
                                      bold=bold_font)
                self._set_oferta_item(row, self.COL_OFERTA_ADJUDICADA, adjudicada_str, align='center',
                                      is_ganador=es_ganador, bold=bold_font)

            self.table_ofertas.resizeColumnsToContents()
            self.table_ofertas.horizontalHeader().setSectionResizeMode(self.COL_OFERTA_NOMBRE,
                                                                       QHeaderView.ResizeMode.Stretch)

        finally:
            self.table_ofertas.setSortingEnabled(True)
            self.table_ofertas.blockSignals(False)
            self._on_oferta_select()  # Actualizar estado de botones Editar/Eliminar oferta

    def _set_oferta_item(self, row, col, text, data=None, align='left', is_ganador=False, bold=None):
        """Helper para crear y colorear items en la tabla de ofertas."""
        item = QTableWidgetItem(str(text))
        item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)  # No editable directamente

        if align == 'right':
            item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
        elif align == 'center':
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        if data is not None:
            item.setData(Qt.ItemDataRole.UserRole, data)  # Guardar dato asociado (ej: lote_num)

        if is_ganador:
            item.setBackground(self.BRUSH_GANADOR)
            item.setForeground(self.TEXT_GANADOR)
            if bold:
                item.setFont(bold)

        self.table_ofertas.setItem(row, col, item)

    def _rebuild_ganadores_ui(self):
        """Reconstruye el panel de ganadores (un combobox por lote)."""
        # Limpiar layout y diccionario de combos
        self.combo_ganador_por_lote.clear()
        while self.layout_form_ganadores.count():
            item = self.layout_form_ganadores.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # Mapa: lote_num_str -> set(nombres_competidores_que_ofertaron)
        oferentes_por_lote: Dict[str, set[str]] = {}
        for oferente in self.licitacion.oferentes_participantes:
            for oferta in oferente.ofertas_por_lote:
                lote_num_key = str(oferta.get("lote_numero", "")).strip()
                if lote_num_key:
                    oferentes_por_lote.setdefault(lote_num_key, set()).add(oferente.nombre)

        # Lotes ordenados
        lotes = sorted(self.licitacion.lotes, key=lambda l: l.numero)

        if not lotes:
            self.layout_form_ganadores.addRow(QLabel("No hay lotes definidos para esta licitación."))
            return

        # Crear fila (Label + ComboBox) por cada lote
        for lote in lotes:
            lote_num_key = str(lote.numero)
            label_text = f"Lote {lote.numero}:"
            # Añadir nombre del lote al label para claridad
            label = QLabel(f"{label_text} <i style='color:gray'>({lote.nombre})</i>")
            label.setToolTip(lote.nombre)  # Tooltip con nombre completo
            label.setMinimumWidth(120)  # Ancho mínimo para el label

            combo = QComboBox()
            combo.setMinimumWidth(200)  # Ancho mínimo para el combo

            # --- Opciones del ComboBox ---
            opciones: List[tuple[str, str]] = []  # (valor_interno, texto_visible)
            opciones.append(("__NINGUNO__", "— Sin ganador asignado —"))

            # Añadir competidores que ofertaron por este lote
            competidores_ofertan = sorted(list(oferentes_por_lote.get(lote_num_key, set())))
            for comp_name in competidores_ofertan:
                opciones.append((comp_name, comp_name))

            # Añadir nuestra empresa si está asignada a este lote
            emp_lote = (getattr(lote, "empresa_nuestra", None) or "").strip()
            if emp_lote:
                val_nuestra = f"__NUESTRA__::{emp_lote}"
                # Asegurarse de no añadirla dos veces si ya ofertó
                if not any(opt[0] == val_nuestra for opt in opciones):
                    opciones.append((val_nuestra, f"{emp_lote} (Nuestra)"))

            # Llenar el ComboBox
            for val_interno, texto_visible in opciones:
                combo.addItem(texto_visible, val_interno)

            # --- Preselección del ganador (basado en datos del objeto Lote) ---
            pre_val_interno = "__NINGUNO__"
            ganador_nombre_lote = (getattr(lote, "ganador_nombre", "") or "").strip()
            if ganador_nombre_lote:
                es_nuestro_lote = bool(getattr(lote, "ganado_por_nosotros", False))
                if es_nuestro_lote and emp_lote:
                    # Si es nuestro y la empresa_nuestra coincide, usar el valor interno especial
                    if ganador_nombre_lote == emp_lote:
                        pre_val_interno = f"__NUESTRA__::{emp_lote}"
                    else:
                        # Caso raro: ganado_por_nosotros=True pero ganador_nombre no coincide con empresa_nuestra
                        # Se prioriza ganador_nombre si existe como opción, sino se queda "__NINGUNO__"
                        if any(opt[0] == ganador_nombre_lote for opt in opciones):
                            pre_val_interno = ganador_nombre_lote
                elif any(opt[0] == ganador_nombre_lote for opt in opciones):
                    # Si es un competidor y está en las opciones
                    pre_val_interno = ganador_nombre_lote

            # Seleccionar el índice correspondiente al valor interno preseleccionado
            idx_pre = combo.findData(pre_val_interno)
            combo.setCurrentIndex(idx_pre if idx_pre >= 0 else 0)  # Default a "Sin ganador" si no se encuentra

            self.layout_form_ganadores.addRow(label, combo)
            self.combo_ganador_por_lote[lote_num_key] = combo
            combo.currentIndexChanged.connect(
                lambda _, k=lote_num_key, c=combo: self._on_ganador_changed(k, c)
            )
  # Guardar referencia al combo

    def _aplicar_ganadores_al_modelo(self):
        """
        Lee los ComboBox de ganadores y actualiza los atributos
        'ganador_nombre' y 'ganado_por_nosotros' en los objetos Lote
        dentro de self.licitacion.lotes (en memoria).
        También actualiza la bandera 'ganador' en las ofertas de los oferentes.
        """
        if not self.combo_ganador_por_lote:
            return  # Si no se construyó la UI de ganadores

        # 1. Limpiar marcas previas en TODOS los lotes y ofertas
        for lote in self.licitacion.lotes:
            lote.ganador_nombre = ""
            lote.ganado_por_nosotros = False
        for oferente in self.licitacion.oferentes_participantes:
            for oferta in oferente.ofertas_por_lote:
                oferta['ganador'] = False  # Limpiar bandera en todas las ofertas

        # 2. Aplicar la selección actual de cada ComboBox
        for lote_num_key, combo in self.combo_ganador_por_lote.items():
            valor_interno = combo.currentData()  # Obtener el valor interno seleccionado

            if not valor_interno or valor_interno == "__NINGUNO__":
                continue  # Este lote no tiene ganador asignado

            # Encontrar el objeto Lote correspondiente
            lote_obj = next((l for l in self.licitacion.lotes if str(l.numero) == lote_num_key), None)
            if not lote_obj:
                continue  # Lote no encontrado (raro)

            es_nuestro = valor_interno.startswith("__NUESTRA__::")

            if es_nuestro:
                ganador_nombre = valor_interno.split("::", 1)[1]
                lote_obj.ganador_nombre = ganador_nombre
                lote_obj.ganado_por_nosotros = True
                # No marcamos oferta específica aquí, ya que es nuestra
            else:
                # El ganador es un competidor
                ganador_nombre = valor_interno
                lote_obj.ganador_nombre = ganador_nombre
                lote_obj.ganado_por_nosotros = False

                # Marcar la oferta específica del competidor como ganadora
                oferente_ganador = next(
                    (o for o in self.licitacion.oferentes_participantes if o.nombre == ganador_nombre), None)
                if oferente_ganador:
                    for oferta in oferente_ganador.ofertas_por_lote:
                        if str(oferta.get("lote_numero")) == lote_num_key:
                            oferta['ganador'] = True
                            break  # Solo una oferta por lote para un competidor

    # --- Slots de Selección (Habilitar/Deshabilitar Botones) ---

    def _update_button_states(self, competidor_sel=False, oferta_sel=False):
        """Actualiza el estado (enabled/disabled) de los botones."""
        # Botones de Competidor
        if self.btn_edit_comp:
            self.btn_edit_comp.setEnabled(competidor_sel)
        if self.btn_del_comp:
            self.btn_del_comp.setEnabled(competidor_sel)
        # Botón Añadir Oferta (solo necesita competidor seleccionado)
        if self.btn_add_oferta:
            self.btn_add_oferta.setEnabled(competidor_sel)

        # Botones Editar/Eliminar Oferta (necesitan competidor Y oferta seleccionada)
        enable_edit_del_oferta = competidor_sel and oferta_sel
        if self.btn_edit_oferta:
            self.btn_edit_oferta.setEnabled(enable_edit_del_oferta)
        if self.btn_del_oferta:
            self.btn_del_oferta.setEnabled(enable_edit_del_oferta)

    def _on_competidor_select(self):
        """Se activa al seleccionar un competidor."""
        competidor = self._get_selected_competidor()
        self._actualizar_tree_ofertas(competidor)  # Actualiza tabla de ofertas
        # Actualiza estado de botones (oferta_sel=False porque la selección de oferta se reinicia)
        self._update_button_states(competidor_sel=bool(competidor), oferta_sel=False)

    def _on_oferta_select(self):
        """Se activa al seleccionar una oferta."""
        competidor_sel = bool(self._get_selected_competidor())
        oferta_sel = bool(self._get_selected_oferta_num())  # Verifica si hay una oferta seleccionada
        self._update_button_states(competidor_sel=competidor_sel, oferta_sel=oferta_sel)

    # --- Getters de Selección ---

    def _get_selected_competidor(self) -> Optional[Oferente]:
        """Obtiene el objeto Oferente de la fila seleccionada en la tabla de competidores."""
        selected_items = self.table_competidores.selectedItems()
        if not selected_items:
            return None
        # El objeto Oferente se guarda en UserRole del item de la primera columna
        return selected_items[0].data(Qt.ItemDataRole.UserRole)

    def _get_selected_oferta_num(self) -> Optional[str]:
        """Obtiene el número de lote (str) de la oferta seleccionada en la tabla de ofertas."""
        selected_items = self.table_ofertas.selectedItems()
        if not selected_items:
            return None

        # El número de lote (str) se guarda en UserRole del item de la columna COL_OFERTA_LOTE
        selected_row = self.table_ofertas.currentRow()
        if selected_row < 0:
            return None  # No row selected
        item_lote = self.table_ofertas.item(selected_row, self.COL_OFERTA_LOTE)
        if not item_lote:
            return None

        return item_lote.data(Qt.ItemDataRole.UserRole)  # Devuelve el N° de lote (str)

    # --- Lógica de Botones (CRUD Competidores y Ofertas) ---

    def _agregar_competidor(self):
        """Abre diálogo para agregar un nuevo competidor."""
        try:
            # --- SIN try...except ImportError ---
            dialogo = DialogoGestionarOferente(self, title="Agregar Nuevo Competidor")
            if dialogo.exec() == QDialog.DialogCode.Accepted:
                nuevo_oferente = dialogo.get_oferente_object()
                if not nuevo_oferente:
                    return

                nombres_existentes = {o.nombre.lower() for o in self.licitacion.oferentes_participantes}
                if nuevo_oferente.nombre.lower() in nombres_existentes:
                    QMessageBox.warning(self, "Competidor Duplicado",
                                        f"Ya existe un competidor llamado '{nuevo_oferente.nombre}'.")
                    return

                self.licitacion.oferentes_participantes.append(nuevo_oferente)
                if hasattr(self.parent_window, "mark_dirty"):
                    self.parent_window.mark_dirty("TabCompetitors.agregar_competidor")

                self._actualizar_tree_competidores()
                self._rebuild_ganadores_ui()
                print(f"TabCompetitors: Competidor '{nuevo_oferente.nombre}' agregado.")

        except Exception as e:  # Captura cualquier otro error
            QMessageBox.critical(self, "Error", f"No se pudo agregar el competidor:\n{e}")
            print(f"Error detallado en _agregar_competidor: {e}")
            import traceback
            traceback.print_exc()  # Imprimir traceback completo

    def _editar_competidor(self):
        """Edita el competidor seleccionado."""
        competidor = self._get_selected_competidor()
        if not competidor:
            QMessageBox.warning(self, "Sin Selección", "Selecciona un competidor de la lista para editar.")
            return

        try:
            # --- SIN try...except ImportError ---
            dialogo = DialogoGestionarOferente(self, title="Editar Competidor", initial_data=competidor)
            if dialogo.exec() == QDialog.DialogCode.Accepted:
                oferente_actualizado = dialogo.get_oferente_object()
                if not oferente_actualizado:
                    return

                if oferente_actualizado.nombre.lower() != competidor.nombre.lower():
                    nombres_existentes = {o.nombre.lower() for o in self.licitacion.oferentes_participantes if
                                          o != competidor}
                    if oferente_actualizado.nombre.lower() in nombres_existentes:
                        QMessageBox.warning(self, "Nombre Duplicado",
                                            f"Ya existe otro competidor llamado '{oferente_actualizado.nombre}'.")
                        return

                competidor.nombre = oferente_actualizado.nombre
                competidor.comentario = oferente_actualizado.comentario
                if hasattr(self.parent_window, "mark_dirty"):
                    self.parent_window.mark_dirty("TabCompetitors.editar_competidor")


                self._actualizar_tree_competidores()
                self._rebuild_ganadores_ui()
                print(f"TabCompetitors: Competidor '{competidor.nombre}' actualizado.")

        except Exception as e:  # Captura cualquier otro error
            QMessageBox.critical(self, "Error", f"No se pudo editar el competidor:\n{e}")
            print(f"Error detallado en _editar_competidor: {e}")
            import traceback
            traceback.print_exc()

    def _eliminar_competidor(self):
        """Elimina el competidor seleccionado (y sus ofertas asociadas en memoria)."""
        competidor = self._get_selected_competidor()
        if not competidor:
            QMessageBox.warning(self, "Sin Selección", "Selecciona un competidor de la lista para eliminar.")
            return

        reply = QMessageBox.question(
            self, "Confirmar Eliminación",
            f"¿Está seguro de eliminar al competidor '{competidor.nombre}' y todas sus ofertas de ESTA licitación?\n\n"
            "(No se borra del catálogo maestro)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.licitacion.oferentes_participantes.remove(competidor)
                if hasattr(self.parent_window, "mark_dirty"):
                    self.parent_window.mark_dirty("TabCompetitors.eliminar_competidor")

                self._actualizar_tree_competidores()
                # Limpiar la tabla de ofertas ya que el competidor ya no existe
                self._actualizar_tree_ofertas(None)
                # Reconstruir UI de ganadores (el competidor eliminado ya no será opción)
                self._rebuild_ganadores_ui()
                print(f"TabCompetitors: Competidor '{competidor.nombre}' eliminado.")
            except ValueError:
                print(
                    f"TabCompetitors: WARNING - Competidor '{competidor.nombre}' no encontrado en la lista para eliminar.")

    def _agregar_oferta(self):
        """Agrega una oferta para el competidor seleccionado."""
        competidor = self._get_selected_competidor()
        if not competidor:
            QMessageBox.warning(self, "Sin Selección", "Selecciona un competidor primero para agregarle una oferta.")
            return

        numeros_ofertados = {str(o.get('lote_numero', '')) for o in competidor.ofertas_por_lote}
        lotes_disponibles = [lote for lote in self.licitacion.lotes if str(lote.numero) not in numeros_ofertados]

        if not lotes_disponibles:
            QMessageBox.information(self, "Todos los Lotes Ofertados",
                                    f"'{competidor.nombre}' ya tiene ofertas para todos los lotes disponibles.")
            return

        try:
            # --- SIN try...except ImportError ---
            dialogo = DialogoGestionarOfertaLote(self, f"Agregar Oferta para {competidor.nombre}", lotes_disponibles)

            if dialogo.exec() == QDialog.DialogCode.Accepted:
                nueva_oferta_dict = dialogo.get_oferta_dict()
                if nueva_oferta_dict:
                    competidor.ofertas_por_lote.append(nueva_oferta_dict)
                    if hasattr(self.parent_window, "mark_dirty"):
                        self.parent_window.mark_dirty("TabCompetitors.agregar_oferta")

                    self._actualizar_tree_ofertas(competidor)
                    self._rebuild_ganadores_ui()
                    print(f"TabCompetitors: Oferta agregada para lote {nueva_oferta_dict['lote_numero']}.")

        except Exception as e:  # Captura cualquier otro error
            QMessageBox.critical(self, "Error", f"No se pudo agregar la oferta:\n{e}")
            print(f"Error detallado en _agregar_oferta: {e}")
            import traceback
            traceback.print_exc()

    def _editar_oferta(self):
        """Slot para el botón Editar Oferta."""
        competidor = self._get_selected_competidor()
        lote_num_sel = self._get_selected_oferta_num()  # Obtiene el N° de lote (str) de la fila seleccionada

        if not competidor or not lote_num_sel:
            QMessageBox.warning(self, "Sin Selección", "Selecciona un competidor y luego la oferta que deseas editar.")
            return

        self._open_edit_oferta_dialog(competidor, lote_num_sel)

    def _editar_oferta_on_double_click(self, index: QModelIndex):
        """Slot para doble clic en la tabla de ofertas."""
        if not index.isValid():
            return

        competidor = self._get_selected_competidor()
        # Obtener el N° de lote de la fila doble-clickeada
        item_lote = self.table_ofertas.item(index.row(), self.COL_OFERTA_LOTE)
        if not competidor or not item_lote:
            return

        lote_num_sel = item_lote.data(Qt.ItemDataRole.UserRole)  # Obtener N° de lote (str)
        if not lote_num_sel:
            return

        print(f"TabCompetitors: Doble clic detectado en oferta de lote {lote_num_sel}. Abriendo editor...")
        self._open_edit_oferta_dialog(competidor, lote_num_sel)

    def _open_edit_oferta_dialog(self, competidor: Oferente, lote_num_to_edit: str):
        """Función helper para abrir el diálogo de edición de oferta."""
        try:
            oferta_dict_original = next(
                o for o in competidor.ofertas_por_lote if str(o.get('lote_numero')) == lote_num_to_edit)
        except StopIteration:
            QMessageBox.critical(self, "Error Interno",
                                 f"No se encontró la oferta para el lote {lote_num_to_edit} del competidor '{competidor.nombre}'.")
            return

        try:
            # --- SIN try...except ImportError ---
            dialogo = DialogoGestionarOfertaLote(
                self, f"Editar Oferta de {competidor.nombre} - Lote {lote_num_to_edit}",
                self.licitacion.lotes,
                initial_data=oferta_dict_original
            )

            if dialogo.exec() == QDialog.DialogCode.Accepted:
                oferta_actualizada_dict = dialogo.get_oferta_dict()
                if oferta_actualizada_dict:
                    oferta_dict_original.update(oferta_actualizada_dict)
                    if hasattr(self.parent_window, "mark_dirty"):
                        self.parent_window.mark_dirty("TabCompetitors.editar_oferta")

                    self._actualizar_tree_ofertas(competidor)
                    self._rebuild_ganadores_ui()
                    print(f"TabCompetitors: Oferta de lote {lote_num_to_edit} actualizada.")

        except Exception as e:  # Captura cualquier otro error
            QMessageBox.critical(self, "Error", f"No se pudo editar la oferta:\n{e}")
            print(f"Error detallado en _open_edit_oferta_dialog: {e}")
            import traceback
            traceback.print_exc()

    def _eliminar_oferta(self):
        """Elimina la oferta seleccionada."""
        competidor = self._get_selected_competidor()
        lote_num_sel = self._get_selected_oferta_num()  # N° de lote (str)

        if not competidor or not lote_num_sel:
            QMessageBox.warning(self, "Sin Selección", "Selecciona un competidor y luego la oferta a eliminar.")
            return

        # Encontrar nombre del lote para el mensaje
        lote_obj = next((l for l in self.licitacion.lotes if str(l.numero) == lote_num_sel), None)
        nombre_lote_msg = f"Lote {lote_num_sel}" + (f" ({lote_obj.nombre})" if lote_obj else "")

        reply = QMessageBox.question(
            self, "Confirmar Eliminación",
            f"¿Eliminar la oferta de '{competidor.nombre}' para {nombre_lote_msg}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            initial_count = len(competidor.ofertas_por_lote)
            # Filtrar la lista de ofertas del competidor, manteniendo las que NO coinciden
            competidor.ofertas_por_lote = [
                oferta for oferta in competidor.ofertas_por_lote
                if str(oferta.get('lote_numero')) != lote_num_sel
            ]
            final_count = len(competidor.ofertas_por_lote)

            if final_count < initial_count:
                if hasattr(self.parent_window, "mark_dirty"):
                    self.parent_window.mark_dirty("TabCompetitors.eliminar_oferta")
                # Recargar la tabla de ofertas
                self._actualizar_tree_ofertas(competidor)
                # Reconstruir UI ganadores (este competidor ya no será opción para este lote)
                self._rebuild_ganadores_ui()
                print(f"TabCompetitors: Oferta de lote {lote_num_sel} eliminada.")
            else:
                print(
                    f"TabCompetitors: WARNING - No se encontró la oferta de lote {lote_num_sel} para eliminar.")

    def _show_not_implemented(self, feature: str):
        """Muestra un diálogo de 'Función no implementada'."""
        QMessageBox.information(
            self,
            "Próximamente",
            f"La función '{feature}' aún no está implementada en esta versión."
        )

    def _agregar_desde_catalogo(self):
        """ Abre el diálogo para seleccionar competidores del catálogo maestro. """
        if not self.db:
            QMessageBox.warning(self, "Error", "La conexión a la base de datos no está activa.")
            return

        try:
            competidores_maestros = self.db.get_competidores_maestros()
            if not competidores_maestros:
                QMessageBox.information(self, "Catálogo Vacío", "No hay competidores en el catálogo maestro.")
                return

            dialogo = DialogoSeleccionarCompetidores(self,
                                                     competidores_maestros,
                                                     self.licitacion.oferentes_participantes)

            if dialogo.exec() == QDialog.DialogCode.Accepted:
                seleccionados = dialogo.get_seleccionados()  # Obtiene List[Dict]
                if not seleccionados:
                    return  # No seleccionó ninguno

                nuevos_agregados = 0
                nombres_actuales_lower = {o.nombre.lower() for o in self.licitacion.oferentes_participantes}

                for comp_dict in seleccionados:
                    nombre = comp_dict.get('nombre', '')
                    if nombre and nombre.lower() not in nombres_actuales_lower:
                        # Crear Oferente solo con nombre (y comentario vacío por ahora)
                        nuevo_oferente = Oferente(nombre=nombre, comentario="")
                        self.licitacion.oferentes_participantes.append(nuevo_oferente)
                        nombres_actuales_lower.add(nombre.lower())  # Añadir al set para evitar duplicados en la misma tanda
                        nuevos_agregados += 1

                if nuevos_agregados > 0:
                    self._actualizar_tree_competidores()
                    self._rebuild_ganadores_ui()
                    # --- CORRECCIÓN AQUÍ ---
                    QMessageBox.information(self, "Éxito",
                                            f"Se agregaron {nuevos_agregados} competidor(es) desde el catálogo.")
                else:
                    # --- CORRECCIÓN AQUÍ ---
                    QMessageBox.information(self, "Información",
                                            "No se agregaron nuevos competidores (posiblemente ya existían).")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo agregar desde el catálogo:\n{e}")
            print(f"Error detallado en _agregar_desde_catalogo: {e}")
            import traceback
            traceback.print_exc()

    def _importar_competidores(self):
        """ Importa competidores desde otra licitación seleccionada. """
        if not self.db:
            QMessageBox.warning(self, "Error", "La conexión a la base de datos no está activa.")
            return

        try:
            # 1. Obtener lista básica de licitaciones (excluyendo la actual)
            licitaciones_info = self.db.get_all_licitaciones_basic_info()
            if not licitaciones_info:
                QMessageBox.information(self, "Información",
                                        "No hay otras licitaciones en la base de datos para importar.")
                return

            # 2. Abrir diálogo de selección
            dialogo = SelectLicitacionDialog(self, licitaciones_info, exclude_numero=self.licitacion.numero_proceso)

            if dialogo.exec() == QDialog.DialogCode.Accepted:
                selected_id = dialogo.get_selected_id()
                if selected_id is None:
                    return  # No seleccionó o hubo error

                # 3. Cargar la licitación de origen completa
                lic_origen = self.db.load_licitacion_by_id(selected_id)
                if not lic_origen:
                    QMessageBox.warning(self, "Error",
                                        f"No se pudo cargar la licitación de origen con ID {selected_id}.")
                    return

                # 4. Lógica de importación
                nombres_actuales_lower = {o.nombre.lower() for o in self.licitacion.oferentes_participantes}
                nuevos_agregados = 0
                competidores_origen = getattr(lic_origen, "oferentes_participantes", [])

                for comp_origen in competidores_origen:
                    nombre_origen = getattr(comp_origen, "nombre", "")
                    if nombre_origen and nombre_origen.lower() not in nombres_actuales_lower:
                        # Crear nuevo Oferente (copiando nombre y comentario)
                        nuevo_oferente = Oferente(
                            nombre=nombre_origen,
                            comentario=getattr(comp_origen, "comentario", "")
                        )
                        self.licitacion.oferentes_participantes.append(nuevo_oferente)
                        nombres_actuales_lower.add(nombre_origen.lower())
                        nuevos_agregados += 1

                # 5. Actualizar UI y mostrar mensaje
                if nuevos_agregados > 0:
                    self._actualizar_tree_competidores()
                    self._rebuild_ganadores_ui()  # Reconstruir por si afectan las opciones
                    QMessageBox.information(self, "Éxito",
                                            f"Se importaron {nuevos_agregados} nuevo(s) competidor(es) desde '{lic_origen.numero_proceso}'.")
                else:
                    QMessageBox.information(self, "Información",
                                            f"No se encontraron competidores nuevos para importar desde '{lic_origen.numero_proceso}'.")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo importar competidores:\n{e}")
            print(f"Error detallado en _importar_competidores: {e}")
            import traceback
            traceback.print_exc()

    def _abrir_analisis_paquetes(self):
        """ Abre el diálogo de análisis de paquetes/ofertas. """
        try:
            # Pasar la licitación actual al diálogo
            dialogo = DialogoAnalisisPaquetes(self, self.licitacion)
            dialogo.exec()  # Mostrar diálogo modal
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir el análisis de paquetes:\n{e}")
            print(f"Error detallado en _abrir_analisis_paquetes: {e}")
            import traceback
            traceback.print_exc()

    def _abrir_evaluador_ofertas(self, forzar_reconfiguracion: bool = False):
        """
        Abre el diálogo para definir parámetros de evaluación.
        Normaliza self.licitacion.parametros_evaluacion a dict.
        """
        print("[DEBUG] _abrir_evaluador_ofertas: entrando")
        pe = getattr(self.licitacion, "parametros_evaluacion", {})
        if not isinstance(pe, dict):
            pe = {}
        self.licitacion.parametros_evaluacion = pe

        metodo_actual = pe.get("metodo")

        if forzar_reconfiguracion or not metodo_actual:
            dlg_met = DialogoElegirMetodoEvaluacionQt(self)
            if dlg_met.exec() != QDialog.DialogCode.Accepted:
                print("[DEBUG] _abrir_evaluador_ofertas: cancelado en selección de método")
                return
            metodo = dlg_met.result
            if not metodo:
                return
            self.licitacion.parametros_evaluacion = {**pe, "metodo": metodo}
        else:
            metodo = metodo_actual

        print(f"[DEBUG] _abrir_evaluador_ofertas: método='{metodo}'")
        dlg = DialogoParametrosEvaluacionQt(self, self.licitacion, metodo)
        dlg.saved.connect(lambda: print("[DEBUG] parámetros guardados desde diálogo de evaluación."))
        dlg.exec()

    # -------------------------------------------
    # Añade estos métodos dentro de la clase TabCompetitors
    # -------------------------------------------

    # Helpers internos (descubrimiento de métodos oficiales)
    def _find_method(self, obj: object | None, names: list[str]) -> Callable | None:
        if obj is None:
            return None
        for n in names:
            fn = getattr(obj, n, None)
            if callable(fn):
                print(f"[DEBUG][EjecutarEval] Método encontrado: {type(obj).__name__}.{n}")
                return fn
        return None

    # --- Fallbacks de cálculo (idénticos conceptualmente a los del diálogo) ---
    def _extract_scores_from_datos(self, datos: dict) -> tuple[dict[str, float], dict[str, dict[str, float]]]:
        pe = datos or {}
        glob = {
            str(k).replace("➡️ ", ""): float(v or 0)
            for k, v in (pe.get("puntajes_tecnicos") or {}).items()
        } if isinstance(pe.get("puntajes_tecnicos"), dict) else {}
        por_lote = {}
        raw = pe.get("puntajes_tecnicos_por_lote") or {}
        if isinstance(raw, dict):
            for lote_num, mp in raw.items():
                por_lote[str(lote_num)] = {
                    str(k).replace("➡️ ", ""): float(v or 0)
                    for k, v in (mp or {}).items()
                }
        return glob, por_lote

    def _get_score_for_name(self, raw: str, lote: str,
                            glob: dict[str, float],
                            por_lote: dict[str, dict[str, float]]) -> float:
        raw = str(raw)
        return float(por_lote.get(lote, {}).get(raw, glob.get(raw, 0.0)))

    def _calc_local_precio_mas_bajo(self, datos: dict) -> dict[str, list[dict]]:
        print("[DEBUG][EjecutarEval] Fallback: Precio Más Bajo")
        matriz = self.licitacion.get_matriz_ofertas()
        descal_raw = {
            (f.get("participante_nombre") or "").replace("➡️ ", "")
            for f in getattr(self.licitacion, "fallas_fase_a", [])
            if f.get("documento_id") == -1
        }
        out: dict[str, list[dict]] = {}
        for lote_num, ofertas in matriz.items():
            fila = []
            for nombre, d in ofertas.items():
                monto = float(d.get("monto", 0.0) or 0.0)
                paso = bool(d.get("paso_fase_A", True))
                raw = nombre.replace("➡️ ", "")
                cal = (monto > 0 and paso and raw not in descal_raw)
                fila.append({
                    "participante": nombre,
                    "monto": monto,
                    "califica_tecnicamente": cal,
                    "es_ganador": False,
                    "puntaje_tecnico": 100.0 if cal else 0.0,
                    "puntaje_economico": 0.0,
                    "puntaje_final": 0.0
                })
            calif = [r for r in fila if r["califica_tecnicamente"]]
            if calif:
                g = min(calif, key=lambda r: r["monto"])
                g["es_ganador"] = True
            fila.sort(key=lambda r: (0 if r["califica_tecnicamente"] else 1, r["monto"]))
            out[str(lote_num)] = fila
        return out

    def _calc_local_puntos_absolutos(self, datos: dict) -> dict[str, list[dict]]:
        print("[DEBUG][EjecutarEval] Fallback: Puntos Absolutos")
        params = (datos or {}).get("parametros", {}) or {}
        tec_max = float(params.get("puntaje_tec_max", 70) or 70)
        tec_min = float(params.get("puntaje_tec_min", 49) or 49)
        eco_max = float(params.get("puntaje_eco_max", 30) or 30)
        glob, por_lote = self._extract_scores_from_datos(datos)
        matriz = self.licitacion.get_matriz_ofertas()

        descal_raw = {
            (f.get("participante_nombre") or "").replace("➡️ ", "")
            for f in getattr(self.licitacion, "fallas_fase_a", [])
            if f.get("documento_id") == -1
        }
        out: dict[str, list[dict]] = {}
        for lote_num, ofertas in matriz.items():
            lote_key = str(lote_num)
            prelim = []
            for nombre, d in ofertas.items():
                price = float(d.get("monto", 0.0) or 0.0)
                pasoA = bool(d.get("paso_fase_A", True))
                raw = nombre.replace("➡️ ", "")
                tec = min(max(self._get_score_for_name(raw, lote_key, glob, por_lote), 0.0), tec_max)
                cal = pasoA and (raw not in descal_raw) and price > 0 and tec >= tec_min
                prelim.append({
                    "participante": nombre,
                    "raw": raw,
                    "monto": price,
                    "tec": tec,
                    "califica_tecnicamente": cal
                })
            calificados = [r for r in prelim if r["califica_tecnicamente"]]
            min_price = min([r["monto"] for r in calificados], default=0.0)

            filas = []
            for r in prelim:
                eco = (eco_max * (min_price / r["monto"])) if (
                    r["califica_tecnicamente"] and r["monto"] > 0 and min_price > 0
                ) else 0.0
                total = r["tec"] + eco
                filas.append({
                    "participante": r["participante"],
                    "monto": r["monto"],
                    "puntaje_tecnico": r["tec"],
                    "puntaje_economico": eco,
                    "puntaje_final": total,
                    "califica_tecnicamente": r["califica_tecnicamente"],
                    "es_ganador": False
                })
            cand = [f for f in filas if f["califica_tecnicamente"]]
            if cand:
                g = sorted(cand, key=lambda x: (-x["puntaje_final"], x["monto"]))[0]
                g["es_ganador"] = True
            filas.sort(key=lambda x: (
                0 if x["califica_tecnicamente"] else 1,
                -x["puntaje_final"],
                x["monto"]
            ))
            out[lote_key] = filas
        return out

    def _calc_local_puntos_ponderados(self, datos: dict) -> dict[str, list[dict]]:
        print("[DEBUG][EjecutarEval] Fallback: Puntos Ponderados")
        params = (datos or {}).get("parametros", {}) or {}
        tec_min = float(params.get("puntaje_tec_min", 70) or 70)
        pond_tec = float(params.get("pond_tec", 70) or 70)
        pond_eco = float(params.get("pond_eco", 30) or 30)
        glob, por_lote = self._extract_scores_from_datos(datos)
        matriz = self.licitacion.get_matriz_ofertas()

        descal_raw = {
            (f.get("participante_nombre") or "").replace("➡️ ", "")
            for f in getattr(self.licitacion, "fallas_fase_a", [])
            if f.get("documento_id") == -1
        }
        out: dict[str, list[dict]] = {}
        for lote_num, ofertas in matriz.items():
            lote_key = str(lote_num)
            prelim = []
            for nombre, d in ofertas.items():
                price = float(d.get("monto", 0.0) or 0.0)
                pasoA = bool(d.get("paso_fase_A", True))
                raw = nombre.replace("➡️ ", "")
                tec_pct = max(0.0, min(self._get_score_for_name(raw, lote_key, glob, por_lote), 100.0))
                cal = pasoA and (raw not in descal_raw) and price > 0 and tec_pct >= tec_min
                prelim.append({
                    "participante": nombre,
                    "raw": raw,
                    "monto": price,
                    "tec_pct": tec_pct,
                    "califica_tecnicamente": cal
                })
            calificados = [r for r in prelim if r["califica_tecnicamente"]]
            min_price = min([r["monto"] for r in calificados], default=0.0)

            filas = []
            for r in prelim:
                eco_pct = (100.0 * (min_price / r["monto"])) if (
                    r["califica_tecnicamente"] and r["monto"] > 0 and min_price > 0
                ) else 0.0
                total = (r["tec_pct"] * (pond_tec / 100.0)) + (eco_pct * (pond_eco / 100.0))
                filas.append({
                    "participante": r["participante"],
                    "monto": r["monto"],
                    "puntaje_tecnico": r["tec_pct"],
                    "puntaje_economico": eco_pct,
                    "puntaje_final": total,
                    "califica_tecnicamente": r["califica_tecnicamente"],
                    "es_ganador": False
                })
            cand = [f for f in filas if f["califica_tecnicamente"]]
            if cand:
                g = sorted(cand, key=lambda x: (-x["puntaje_final"], x["monto"]))[0]
                g["es_ganador"] = True
            filas.sort(key=lambda x: (
                0 if x["califica_tecnicamente"] else 1,
                -x["puntaje_final"],
                x["monto"]
            ))
            out[lote_key] = filas
        return out

    def _aplicar_regla_un_lote_simple(self, resultados_por_lote: dict[str, list[dict]]) -> dict[str, list[dict]]:
        print("[DEBUG][EjecutarEval] Regla 1-lote (fallback simple)")
        usados: set[str] = set()
        out: dict[str, list[dict]] = {}

        # Clave de ordenación robusta: siempre devuelve una tupla comparable
        def _orden_lote_key(s: object) -> tuple[int, object]:
            """
            Ordena primero por 'es numérico' (0) y luego por valor numérico,
            y después por 'no numérico' (1) y su valor de texto.
            Soporta claves que vienen como str o int.
            """
            s_str = str(s)
            if s_str.isdigit():
                return (0, int(s_str))
            return (1, s_str)

        for lote in sorted(resultados_por_lote.keys(), key=_orden_lote_key):
            fila = [dict(r) for r in resultados_por_lote[lote]]
            for r in fila:
                r["es_ganador"] = False
            asignado = False
            for r in fila:
                raw = r["participante"].replace("➡️ ", "")
                if r.get("califica_tecnicamente") and raw not in usados:
                    r["es_ganador"] = True
                    usados.add(raw)
                    asignado = True
                    break
            if not asignado:
                for r in fila:
                    if r.get("califica_tecnicamente"):
                        r["es_ganador"] = True
                        break
            out[str(lote)] = fila
        return out
    def _sincronizar_ofertas_desde_lotes(self):
        """
        Asegura que las empresas 'nuestras' que tienen monto_ofertado
        en la pestaña de Lotes aparezcan también como ofertas en el
        modelo de competidores (oferentes_participantes/ofertas_por_lote).

        De esta forma, la evaluación usa directamente los datos de TabLotes,
        como hacía la versión SQL antigua.
        """
        # 1) Mapa nombre -> Oferente existente
        oferentes_por_nombre: dict[str, Oferente] = {}
        for of in getattr(self.licitacion, "oferentes_participantes", []) or []:
            nombre = getattr(of, "nombre", "") or ""
            if nombre:
                oferentes_por_nombre[nombre.strip()] = of
            if not hasattr(of, "ofertas_por_lote") or of.ofertas_por_lote is None:
                of.ofertas_por_lote = []

        # 2) Asegurar Oferente para cada empresa_nuestra
        nuestras_empresas_nombres = [
            (e.nombre if hasattr(e, "nombre") else str(e)).strip()
            for e in getattr(self.licitacion, "empresas_nuestras", []) or []
        ]
        for nombre in nuestras_empresas_nombres:
            if not nombre:
                continue
            if nombre not in oferentes_por_nombre:
                nuevo = Oferente(nombre=nombre, comentario="")
                nuevo.ofertas_por_lote = []
                self.licitacion.oferentes_participantes.append(nuevo)
                oferentes_por_nombre[nombre] = nuevo

        # 3) Crear/actualizar ofertas por lote según Lote.empresa_nuestra y Lote.monto_ofertado
        for lote in getattr(self.licitacion, "lotes", []) or []:
            num_lote = str(getattr(lote, "numero", "") or "").strip()
            emp = (getattr(lote, "empresa_nuestra", "") or "").strip()
            monto = float(getattr(lote, "monto_ofertado", 0.0) or 0.0)
            if not num_lote or not emp:
                continue
            # si no quieres filtrar 0, quita este if
            if monto <= 0:
                continue

            ofer = oferentes_por_nombre.get(emp)
            if not ofer:
                # seguridad adicional
                ofer = Oferente(nombre=emp, comentario="")
                ofer.ofertas_por_lote = []
                self.licitacion.oferentes_participantes.append(ofer)
                oferentes_por_nombre[emp] = ofer

            if not hasattr(ofer, "ofertas_por_lote") or ofer.ofertas_por_lote is None:
                ofer.ofertas_por_lote = []

            # Buscar oferta existente para ese lote
            existente = None
            for o in ofer.ofertas_por_lote:
                if str(o.get("lote_numero")) == num_lote:
                    existente = o
                    break

            if existente:
                existente["monto"] = monto
                existente.setdefault("paso_fase_A", True)
            else:
                ofer.ofertas_por_lote.append({
                    "lote_numero": num_lote,
                    "monto": monto,
                    "paso_fase_A": True,
                })

        # 4) Refrescar tablas de competidores/ofertas y combos de ganadores
        self._actualizar_tree_competidores()
        self._rebuild_ganadores_ui()
    # --- Método principal: Ejecutar Evaluación ---

    def _ejecutar_evaluacion(self):
        print("[DEBUG][EjecutarEval] Iniciando ejecución directa...")
        # Sincronizar nuestras ofertas desde los lotes antes de evaluar
        self._sincronizar_ofertas_desde_lotes()

        datos = getattr(self.licitacion, "parametros_evaluacion", {}) or {}
        if not isinstance(datos, dict) or not datos.get("metodo"):
            QMessageBox.information(
                self,
                "Parámetros no definidos",
                "Primero define y guarda los parámetros de evaluación."
            )
            # Opcional: abrir diálogo de parámetros directo
            try:
                self._abrir_evaluador_ofertas()
            except Exception:
                pass
            return

        metodo = str(datos.get("metodo", ""))
        print(f"[DEBUG][EjecutarEval] Método: {metodo}")

        # 1) Intentar métodos oficiales (de la ventana padre o de esta pestaña)
        calc_fn = self._find_method(
            self.parent_window,
            ["_calcular_resultados_evaluacion", "calcular_resultados_evaluacion"]
        ) or self._find_method(
            self,
            ["_calcular_resultados_evaluacion", "calcular_resultados_evaluacion"]
        )

        resultados_por_lote: dict[str, list[dict]] = {}

        if calc_fn:
            try:
                resultados_por_lote = calc_fn(datos)
                print("[DEBUG][EjecutarEval] Cálculo delegado OK. Lotes:", list(resultados_por_lote.keys()))
            except Exception as e:
                QMessageBox.critical(self, "Error de Cálculo", f"Fallo en el método de cálculo:\n{e}")
                return
        else:
            # 2) Fallbacks locales
            if "Precio Más Bajo" in metodo:
                resultados_por_lote = self._calc_local_precio_mas_bajo(datos)
                print("[DEBUG][EjecutarEval] Usando fallback Precio Más Bajo")
            elif "Puntos Absolutos" in metodo:
                resultados_por_lote = self._calc_local_puntos_absolutos(datos)
                print("[DEBUG][EjecutarEval] Usando fallback Puntos Absolutos")
            elif "Puntos Ponderados" in metodo:
                resultados_por_lote = self._calc_local_puntos_ponderados(datos)
                print("[DEBUG][EjecutarEval] Usando fallback Puntos Ponderados")
            else:
                QMessageBox.information(
                    self,
                    "No Disponible",
                    "No se encontró el método de cálculo para el método seleccionado."
                )
                return

        if not resultados_por_lote:
            QMessageBox.information(self, "Sin Datos", "No hay ofertas válidas para evaluar en ningún lote.")
            return

        # 3) Regla 1-lote por oferente (SIEMPRE usando el fallback interno)
        adjudicados = None
        if bool(datos.get("aplicar_regla_un_lote", True)):
            print("[DEBUG][EjecutarEval] Aplicando regla 1-lote simple (interna)")
            resultados_por_lote = self._aplicar_regla_un_lote_simple(resultados_por_lote)

        # 4) Mostrar resultados en el diálogo dedicado
        dlg = DialogoResultadosEvaluacion(
            self,
            self.licitacion,
            resultados_por_lote,
            adjudicados=adjudicados,
            metodo=metodo,
            datos_param=datos
        )
        dlg.exec()
    # En la clase TabCompetitors, añade este método:

    def _abrir_analisis_fase_a(self):
        """
        Abre el Análisis de Fallas Fase A verificando que no haya documentos sin guardar.
        No persiste cambios por sí misma; el guardado global lo realiza la ventana de Detalles.
        """
        # 1) Verificar documentos sin id (no guardados)
        docs = getattr(self.licitacion, "documentos_solicitados", []) or []
        sin_guardar = [d for d in docs if not getattr(d, "id", None)]
        if sin_guardar:
            QMessageBox.information(
                self,
                "Guardar Cambios",
                f"Se han detectado {len(sin_guardar)} documento(s) nuevo(s) que aún no se han guardado en la base de datos.\n\n"
                "Usa el botón 'Guardar y Continuar' en la ventana de Detalles antes de analizar las fallas."
            )
            return

        # 2) Abrir diálogo
        dlg = DialogoFallasFaseA(self, self.licitacion, db_manager=getattr(self, "db", None))
        # Si quieres abrirla maximizada:
        # dlg.setWindowState(dlg.windowState() | Qt.WindowState.WindowMaximized)
        dlg.exec()


    def _on_ganador_changed(self, lote_key: str, combo: QComboBox):
        # Evitar ruido durante carga inicial
        if getattr(self, "_loading", False):
            return

        valor = combo.currentData()

        print(
            f"[CHANGE][TabCompetitors] "
            f"Ganador cambiado en lote {lote_key} -> {valor}"
        )

        # 🧷 Marcar como dirty (NO guardar aquí)
        if hasattr(self.parent_window, "mark_dirty"):
            self.parent_window.mark_dirty(
                f"TabCompetitors.ganador:{lote_key}"
            )
        