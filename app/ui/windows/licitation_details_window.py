
# app/ui/windows/licitation_details_window.py
from __future__ import annotations
import sys
import re
import json
from typing import Optional, Callable, Any, List
from collections import deque
from datetime import datetime
from PyQt6.QtWidgets import QListWidget, QGroupBox, QVBoxLayout
from PyQt6.QtWidgets import (
    QGroupBox, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QSizePolicy, QListWidget
)
from PyQt6.QtWidgets import QStyle



from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QDialogButtonBox, QMessageBox, QWidget,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QStyle, QSizePolicy,
    QTableWidget, QDateEdit, QDateTimeEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QSettings, QEvent, QTimer, QDate
from PyQt6.QtGui import QShortcut, QKeySequence, QPalette, QBrush, QColor

# Modelos y DB
from app.core.models import Licitacion, Empresa, Lote, Documento
from app.core.db_adapter import DatabaseAdapter

# Pestañas
from app.core.utils import normalize_lote_numero
from app.ui.tabs.tab_details_general import TabDetailsGeneral
from app.ui.tabs.tab_lotes import TabLotes
from app.ui.tabs.tab_competitors import TabCompetitors  # Import correcto (sin alias extraño)

# Diálogos
from app.ui.dialogs.dialogo_seleccionar_institucion import DialogoSeleccionarInstitucion
from app.ui.dialogs.dialogo_gestionar_instituciones import DialogoGestionarInstituciones
from app.ui.dialogs.seleccionar_empresas_dialog import SeleccionarEmpresasDialog
from app.core.log_utils import get_logger
logger = get_logger("licitation_details_window")
from app.core.utils import normalize_lote_numero


class LicitationDetailsWindow(QDialog):
    """
    Ventana MODAL para ver/editar Licitación con panel superior (Datos Iniciales).

    Reglas clave:
    - Edición (licitacion.id): panel 'Datos Iniciales' deshabilitado; en el tab 'Detalles Generales'
      la Institución es editable y Nuestras Empresas también es editable.
    - Creación: seleccionar Institución en panel A la refleja y bloquea en el tab; seleccionar Empresas en panel B
      deshabilita el selector del tab pero muestra las empresas elegidas.
    - Tab Lotes: columnas de diferencias muestran color en el texto, no en el fondo.
    - Fechas: en creación, QDateEdit/QDateTimeEdit con 2000-01-01 se ajustan a la fecha actual.
    """
    saved = pyqtSignal(object)
    deleted = pyqtSignal(int)  # emite el ID cuando se elimina la licitación

    SETTINGS_GEOMETRY_KEY = "windows/LicitationDetailsWindow/geometry"
    SETTINGS_TAB_INDEX_KEY = "windows/LicitationDetailsWindow/tab_index"

    def __init__(self, parent: QWidget, licitacion: Licitacion, db_adapter: DatabaseAdapter, refresh_callback: Optional[Callable] = None):
        super().__init__(parent)
        self.licitacion = licitacion
        self.db = db_adapter
        self.refresh_callback = refresh_callback

        self.setWindowTitle(f"Detalles Licitación: {self.licitacion.numero_proceso or ''} - {self.licitacion.nombre_proceso or ''}")
        self.resize(1000, 700)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint | Qt.WindowType.WindowMinimizeButtonHint)

        # Estado del panel superior
        self._institucion_seleccionada: Optional[dict] = None
        self._empresas_nuestras_nombres: List[str] = []
        self._kits_actuales: List[str] = []
        self._lock_initial_on_open: bool = bool(getattr(self.licitacion, "id", None))  # bloquea Datos Iniciales si es edición

        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Panel superior: Datos Iniciales
        self._build_header_panel(main_layout)

        # Pestañas
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        self.tab_general = TabDetailsGeneral(self.licitacion, self.db, self)
        self.tab_lotes = TabLotes(self.licitacion, self.db, self)
        self.tab_competitors = TabCompetitors(self.licitacion, self.db, self)

        self.tab_widget.addTab(self.tab_general, "Detalles Generales")
        self.tab_widget.addTab(self.tab_lotes, "Lotes del Proceso")
        self.tab_widget.addTab(self.tab_competitors, "Competidores y Ofertas")

        # Botonera inferior
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            Qt.Orientation.Horizontal
        )
        btn_ok = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if btn_ok:
            btn_ok.setText("Guardar y Cerrar")
        self.btn_save_continue = self.button_box.addButton("Guardar y Continuar", QDialogButtonBox.ButtonRole.ActionRole)

        # Botón Eliminar (solo visible si existe id)
        self.btn_delete = self.button_box.addButton("Eliminar", QDialogButtonBox.ButtonRole.DestructiveRole)
        self.btn_delete.setVisible(bool(getattr(self.licitacion, "id", None)))
        if self.btn_delete.isVisible():
            self.btn_delete.setToolTip("Eliminar esta licitación definitivamente.")

        main_layout.addWidget(self.button_box)

        # Conexiones
        self.button_box.accepted.connect(self._save_and_close)
        self.btn_save_continue.clicked.connect(self._save_and_continue)
        self.button_box.rejected.connect(self.reject)
        self.btn_delete.clicked.connect(self._confirm_and_delete)
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        # Atajos globales
        self._register_shortcuts()

        # Carga inicial (modelo -> UI)
        self._load_header_from_model()
        self._load_data_into_tabs()

        # Edición: bloquear 'Datos Iniciales' y asegurar edición en pestañas
        self._set_initial_data_enabled(not self._lock_initial_on_open)
        if self._lock_initial_on_open:
            # Campo Institución editable en tab + Empresas editables en tab
            self._set_tab_general_institucion_enabled(True)
            self._set_tab_general_empresas_edit_enabled(True)

        # Tema y persistencia
        self._apply_theme()
        self._restore_ui_state()
        self._dirty = False
        self._saving = False

        # 🔒 lock de edición por contador (no booleano)
        self._edit_locks: dict[str, int] = {}

        # ⏱️ autosave con debounce
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.timeout.connect(self._autosave_if_needed)

        # ⏱️ delay recomendado (7 segundos)
        self._autosave_delay_ms = 7000

        # 🔁 snapshot hash
        self._last_snapshot = self._snapshot_model()


        self._change_log = deque(maxlen=200)





    def mark_dirty(self, source: str = ""):
        if self._saving:
            return

        if not self._dirty:
            print(f"[DIRTY] Cambios detectados ({source})")

        self._dirty = True
        self._enable_save_continue_button()

        # ⏱️ reiniciar debounce de autosave
        self._autosave_timer.start(self._autosave_delay_ms)



# -------------------- UI: Header --------------------
    def _build_header_panel(self, parent_layout: QVBoxLayout):
        from PyQt6.QtWidgets import QGridLayout

        self.group_header = QGroupBox("Datos Iniciales")

        # 🔒 Header compacto (no estira la ventana)
        self.group_header.setMaximumHeight(180)
        self.group_header.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )

        h = QGridLayout(self.group_header)
        h.setContentsMargins(8, 8, 8, 8)
        h.setHorizontalSpacing(10)
        h.setVerticalSpacing(6)

        style = self.style()

        # =========================================================
        # A. Institución
        # =========================================================
        self.boxA = QGroupBox("A. Institución")
        la = QHBoxLayout(self.boxA)
        la.setContentsMargins(6, 6, 6, 6)

        self.txt_institucion = QLineEdit()
        self.txt_institucion.setPlaceholderText("Ninguna seleccionada…")
        self.txt_institucion.setReadOnly(True)
        self.txt_institucion.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )
        la.addWidget(self.txt_institucion)

        self.btn_sel_inst = QPushButton(" Seleccionar…")
        self.btn_sel_inst.setIcon(
            style.standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton)
        )
        self.btn_sel_inst.clicked.connect(self._abrir_selector_institucion)
        la.addWidget(self.btn_sel_inst)

        self.btn_gestionar_inst = QPushButton(" Gestionar…")
        self.btn_gestionar_inst.setIcon(
            style.standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)
        )
        self.btn_gestionar_inst.clicked.connect(self._abrir_gestionar_instituciones)
        la.addWidget(self.btn_gestionar_inst)

        # =========================================================
        # B. Empresas Propias
        # =========================================================
        self.boxB = QGroupBox("B. Empresas Propias")
        lb = QHBoxLayout(self.boxB)
        lb.setContentsMargins(6, 6, 6, 6)

        self.lbl_empresas = QLabel("Ninguna seleccionada")
        self.lbl_empresas.setWordWrap(True)
        self.lbl_empresas.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred
        )
        lb.addWidget(self.lbl_empresas)

        self.btn_sel_empresas = QPushButton(" Seleccionar…")
        self.btn_sel_empresas.setIcon(
            style.standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton)
        )
        self.btn_sel_empresas.clicked.connect(self._abrir_selector_empresas)
        lb.addWidget(self.btn_sel_empresas)

        # =========================================================
        # C. Kit de Requisitos
        # =========================================================
        self.boxC = QGroupBox("C. Kit de Requisitos")
        lc = QHBoxLayout(self.boxC)
        lc.setContentsMargins(6, 6, 6, 6)

        self.combo_kit = QComboBox()
        self.combo_kit.addItem(" (Ninguno) ")
        self.combo_kit.setEnabled(False)
        self.combo_kit.setMinimumWidth(150)
        self.combo_kit.setMaximumWidth(220)
        lc.addWidget(self.combo_kit)

        # =========================================================
        # D. Cambios Pendientes (Logger Visual)
        # =========================================================
        self.boxD = QGroupBox("D. Cambios Pendientes")
        self.boxD.setMaximumWidth(300)

        ld = QVBoxLayout(self.boxD)
        ld.setContentsMargins(6, 6, 6, 6)
        ld.setSpacing(4)

        self.list_change_log = QListWidget()
        self.list_change_log.setMinimumHeight(90)
        self.list_change_log.setMinimumWidth(220)
        self.list_change_log.setMaximumWidth(260)
        self.list_change_log.setToolTip(
            "Cambios realizados que aún no se han guardado en la base de datos"
        )

        ld.addWidget(self.list_change_log)

        # =========================================================
        # Layout compacto (GRID)
        # =========================================================
        h.addWidget(self.boxA, 0, 0)
        h.addWidget(self.boxB, 0, 1)
        h.addWidget(self.boxC, 0, 2)
        h.addWidget(self.boxD, 0, 3)

        # 🔧 Control fino de anchuras
        h.setColumnStretch(0, 2)  # Institución
        h.setColumnStretch(1, 2)  # Empresas
        h.setColumnStretch(2, 1)  # Kit
        h.setColumnStretch(3, 1)  # Logger

        # =========================================================
        # Insertar header en layout padre
        # =========================================================
        parent_layout.addWidget(self.group_header)


    def _set_initial_data_enabled(self, enabled: bool):
        self.group_header.setEnabled(enabled)
        if not enabled:
            self.group_header.setToolTip("Datos Iniciales bloqueados en modo edición para evitar confusiones.")
        else:
            self.group_header.setToolTip("")

    # -------------------- Atajos --------------------
    def _register_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+N"), self).activated.connect(lambda: self._trigger_tab_lotes_action("add"))
        QShortcut(QKeySequence("Ctrl+E"), self).activated.connect(lambda: self._trigger_tab_lotes_action("edit"))
        QShortcut(QKeySequence("Del"), self).activated.connect(lambda: self._trigger_tab_lotes_action("delete"))
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self._save_and_continue)
        # Atajo para eliminar (solo si existe ID)
        if getattr(self.licitacion, "id", None):
            QShortcut(QKeySequence("Ctrl+Shift+D"), self).activated.connect(self._confirm_and_delete)

    def _trigger_tab_lotes_action(self, action: str):
        tab = self.tab_lotes
        try_names = []
        if action == "add":
            try_names = ["agregar_lote", "add_lote", "nuevo_lote", "on_add_clicked"]
        elif action == "edit":
            try_names = ["editar_lote", "edit_lote", "on_edit_clicked"]
        elif action == "delete":
            try_names = ["eliminar_lote", "delete_lote", "remove_lote", "on_delete_clicked"]
        for name in try_names:
            if hasattr(tab, name):
                try:
                    getattr(tab, name)()
                    return
                except Exception:
                    pass

    # -------------------- Tema / Persistencia --------------------
    def changeEvent(self, event: QEvent) -> None:
        if event.type() in (QEvent.Type.PaletteChange, QEvent.Type.ApplicationPaletteChange):
            self._apply_theme()
        super().changeEvent(event)

    def _apply_theme(self):
        pal: QPalette = self.palette()
        col_text = pal.color(QPalette.ColorRole.WindowText).name()
        col_warn = pal.color(QPalette.ColorRole.LinkVisited).name()
        col_readonly_bg = pal.color(QPalette.ColorRole.AlternateBase).name()
        self.txt_institucion.setStyleSheet(f"QLineEdit:read-only {{ background-color: {col_readonly_bg}; color: {col_text}; }}")
        if not self._empresas_nuestras_nombres:
            self.lbl_empresas.setStyleSheet(f"color: {col_warn}; font-weight: 600;")
        else:
            self.lbl_empresas.setStyleSheet(f"color: {col_text};")

    def _save_ui_state(self):
        try:
            s = QSettings()
            s.setValue(self.SETTINGS_GEOMETRY_KEY, self.saveGeometry())
            s.setValue(self.SETTINGS_TAB_INDEX_KEY, self.tab_widget.currentIndex())
        except Exception:
            pass

    def _restore_ui_state(self):
        try:
            s = QSettings()
            g = s.value(self.SETTINGS_GEOMETRY_KEY, None)
            if g is not None:
                self.restoreGeometry(g)
            idx = s.value(self.SETTINGS_TAB_INDEX_KEY, None)
            if idx is not None:
                try:
                    self.tab_widget.setCurrentIndex(int(idx))
                except Exception:
                    pass
        except Exception:
            pass

    def closeEvent(self, e):
        self._save_ui_state()
        super().closeEvent(e)

    # -------------------- Carga inicial --------------------
    def _load_header_from_model(self):
        # Institución
        inst_name = getattr(self.licitacion, "institucion", "") or ""
        if inst_name:
            self._set_institucion_seleccionada({"nombre": inst_name})
        else:
            self._set_institucion_seleccionada(None)

        # Empresas propias
        empresas = getattr(self.licitacion, "empresas_nuestras", []) or []
        nombres = []
        for e in empresas:
            if isinstance(e, Empresa):
                if e.nombre:
                    nombres.append(e.nombre)
            elif isinstance(e, dict):
                n = e.get("nombre") or e.get("razon_social") or e.get("name")
                if n:
                    nombres.append(str(n))
            elif isinstance(e, str):
                if e:
                    nombres.append(e)
        self._empresas_nuestras_nombres = sorted(set([n for n in nombres if n]))
        self._refresh_empresas_label()
        # Si hay empresas en B y estamos en creación, deshabilitar selector de empresas en la pestaña; en edición siempre habilitado
        self._sync_empresas_editability()
        self._tab_general_set_empresas_label_text(", ".join(self._empresas_nuestras_nombres) if self._empresas_nuestras_nombres else None)

        # Kit: si hay institución, cargar kits disponibles
        if self._institucion_seleccionada:
            self._cargar_kits_para_institucion(self._institucion_seleccionada.get("nombre", ""))

        # Sincronizar lock/valor de institución en pestaña según modo
        self._sync_institucion_lock_state()

    def _refresh_empresas_label(self):
        if not self._empresas_nuestras_nombres:
            self.lbl_empresas.setText("Ninguna seleccionada")
        else:
            self.lbl_empresas.setText(", ".join(self._empresas_nuestras_nombres))
        self._apply_theme()

    # -------------------- Header Actions --------------------
    def _abrir_selector_institucion(self):
        try:
            dlg = DialogoSeleccionarInstitucion(self, self.db)
            # Intentar preseleccionar
            if self._institucion_seleccionada:
                try:
                    if hasattr(dlg, "_seleccionar_item_por_nombre"):
                        dlg._seleccionar_item_por_nombre(self._institucion_seleccionada.get("nombre", ""))
                except Exception:
                    pass
            if dlg.exec() == QDialog.DialogCode.Accepted:
                # Obtener resultado de forma robusta
                inst = None
                for attr in ("institucion_seleccionada", "resultado", "result_data", "selected"):
                    if hasattr(dlg, attr):
                        val = getattr(dlg, attr)
                        if callable(val):
                            try:
                                val = val()
                            except Exception:
                                pass
                        if isinstance(val, dict) and (val.get("nombre") or val.get("name")):
                            inst = val
                            break
                        if isinstance(val, (str,)):
                            inst = {"nombre": val}
                            break
                self._set_institucion_seleccionada(inst)
        except ImportError:
            QMessageBox.critical(self, "Error", "Falta el archivo 'dialogo_seleccionar_institucion.py'.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir el selector de instituciones:\n{e}")

    def _abrir_gestionar_instituciones(self):
        try:
            dlg = DialogoGestionarInstituciones(self, self.db)
        except ImportError:
            QMessageBox.critical(self, "Error", "Falta el archivo 'dialogo_gestionar_instituciones.py'.")
            return
        try:
            if dlg.exec() == QDialog.DialogCode.Accepted:
                inst = None
                for attr in ("institucion_creada", "institucion_seleccionada", "resultado", "result_data"):
                    if hasattr(dlg, attr):
                        val = getattr(dlg, attr)
                        if callable(val):
                            try:
                                val = val()
                            except Exception:
                                pass
                        if isinstance(val, dict) and (val.get("nombre") or val.get("name")):
                            inst = val
                            break
                        if isinstance(val, (str,)):
                            inst = {"nombre": val}
                            break
                if inst:
                    self._set_institucion_seleccionada(inst)
                else:
                    if self._institucion_seleccionada:
                        self._cargar_kits_para_institucion(self._institucion_seleccionada.get("nombre", ""))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir 'Gestionar Instituciones':\n{e}")

    def _abrir_selector_empresas(self):
        try:
            # Cargar catálogo de empresas maestras
            try:
                lista_empresas = self.db.get_empresas_maestras()
            except Exception:
                lista_empresas = []
            dlg = SeleccionarEmpresasDialog(self, lista_empresas, self._empresas_nuestras_nombres)
        except ImportError:
            QMessageBox.critical(self, "Error", "Falta el archivo 'seleccionar_empresas_dialog.py'.")
            return
        try:
            if dlg.exec() == QDialog.DialogCode.Accepted:
                nombres = self._get_empresas_desde_dialog(dlg)
                self._empresas_nuestras_nombres = sorted(set(nombres))
                self._refresh_empresas_label()
                # Desactivar selector en el tab General cuando estamos en creación; en edición, mantenerlo habilitado
                self._sync_empresas_editability()
                self._tab_general_set_empresas_label_text(", ".join(self._empresas_nuestras_nombres) if self._empresas_nuestras_nombres else None)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir el selector de empresas:\n{e}")

    def _get_empresas_desde_dialog(self, dlg) -> List[str]:
        def normalize(value) -> List[str]:
            if value is None:
                return []
            if isinstance(value, list):
                out = []
                for v in value:
                    if isinstance(v, str):
                        out.append(v)
                    elif isinstance(v, dict):
                        n = v.get("nombre") or v.get("name") or v.get("razon_social")
                        if n:
                            out.append(str(n))
                    else:
                        n = getattr(v, "nombre", None) or getattr(v, "name", None) or getattr(v, "razon_social", None)
                        if n:
                            out.append(str(n))
                return out
            return []
        # Métodos
        for m in ("get_empresas_seleccionadas", "get_seleccionados", "get_selected", "get_selected_names"):
            if hasattr(dlg, m):
                try:
                    val = getattr(dlg, m)
                    val = val() if callable(val) else val
                    names = normalize(val)
                    if names:
                        return names
                except Exception:
                    pass
        # Atributos
        for a in ("resultado", "seleccionadas", "selected", "selected_names", "nombres_seleccionados"):
            if hasattr(dlg, a):
                val = getattr(dlg, a)
                try:
                    if callable(val):
                        val = val()
                except Exception:
                    pass
                names = normalize(val)
                if names:
                    return names
        return []

    # -------------------- Header helpers --------------------
    def _set_institucion_seleccionada(self, dict_inst: Optional[dict]):
        self._institucion_seleccionada = dict_inst
        if dict_inst and (dict_inst.get("nombre") or dict_inst.get("name")):
            nombre = dict_inst.get("nombre") or dict_inst.get("name")
            self.txt_institucion.setText(str(nombre))
            # Actualizar en el modelo
            self.licitacion.institucion = str(nombre)
            # Cargar kits
            self._cargar_kits_para_institucion(str(nombre))
        else:
            self.txt_institucion.clear()
            self.licitacion.institucion = ""
            self.combo_kit.clear()
            self.combo_kit.addItem(" (Ninguno) ")
            self.combo_kit.setEnabled(False)
            self._kits_actuales = []
        # Sincronizar lock/valor de institución en pestaña según modo
        self._sync_institucion_lock_state()

    def _sync_institucion_lock_state(self):
        """
        - En creación (no id): empuja la institución del header al campo de la pestaña y lo deshabilita.
        - En edición (id): deja editable el campo de la pestaña (y el header está bloqueado).
        """
        if self._lock_initial_on_open:
            # Edición: asegurar editable en pestaña
            self._set_tab_general_institucion_enabled(True)
            return

        # Creación: si hay institución en header, reflejar y bloquear en pestaña
        inst_name = (self._institucion_seleccionada or {}).get("nombre") or (self._institucion_seleccionada or {}).get("name") or ""
        self._set_tab_general_institucion_text(inst_name)
        self._set_tab_general_institucion_enabled(False if inst_name else True)

    def _cargar_kits_para_institucion(self, nombre_institucion: str):
        self.combo_kit.clear()
        self.combo_kit.addItem(" (Ninguno) ")
        self.combo_kit.setEnabled(False)
        self._kits_actuales = []
        if not nombre_institucion:
            return
        kits: List[str] = []
        try_methods = [
            "get_kits_de_institucion",
            "get_kits_para_institucion",
            "get_kits_por_institucion",
            "listar_kits_institucion"
        ]
        for m in try_methods:
            if hasattr(self.db, m):
                try:
                    res = getattr(self.db, m)(nombre_institucion)
                    if isinstance(res, list):
                        for item in res:
                            if isinstance(item, str):
                                kits.append(item)
                            elif isinstance(item, dict):
                                n = item.get("nombre") or item.get("name") or item.get("titulo")
                                if n:
                                    kits.append(str(n))
                    break
                except Exception:
                    pass
        if kits:
            kits = sorted(set([k for k in kits if k and k.strip()]))
            self.combo_kit.addItems(kits)
            self.combo_kit.setEnabled(True)
            self._kits_actuales = kits
        else:
            self.combo_kit.setEnabled(False)

    # -------------------- Tabs load/collect --------------------
    # -------------------- Tabs load/collect --------------------
    def _load_data_into_tabs(self):
        """
        Carga el modelo en las pestañas.

        Nota: la lógica de colores de diferencias (% Dif. Licit. / % Dif. Pers.)
        ahora vive dentro de TabLotes, por lo que no se aplica ningún
        post-proceso adicional aquí.
        """
        try:
            self.tab_general.load_data()

            # 🔴 CLAVE: reinyectar el modelo actual
            self.tab_lotes.set_licitacion(self.licitacion)
            self.tab_lotes.load_data()

            self.tab_competitors.load_data()

            # Post-procesos tras cargar (solo fechas por defecto, etc.)
            self._fix_default_dates_if_needed()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error al Cargar Pestañas",
                f"No se pudieron cargar completamente los datos en las pestañas:\n{e}",
            )

    def _collect_data_from_header(self):
        # Empresas -> modelo (el header debe prevalecer en creación; en edición no bloquea el tab)
        empresas_objs = [Empresa(nombre=n) for n in self._empresas_nuestras_nombres]
        self.licitacion.empresas_nuestras = empresas_objs

        # Aplicar kit seleccionado -> documentos_solicitados
        kit_sel = (self.combo_kit.currentText() or "").strip()
        if kit_sel and kit_sel not in {"(Ninguno)", " (Ninguno) "} and self.combo_kit.isEnabled():
            if hasattr(self.db, "get_documentos_de_kit"):
                try:
                    documentos_kit = self.db.get_documentos_de_kit(kit_sel, self.licitacion.institucion or "")
                    if isinstance(documentos_kit, list):
                        docs = []
                        for d in documentos_kit:
                            if isinstance(d, Documento):
                                docs.append(d)
                            elif isinstance(d, dict):
                                try:
                                    docs.append(Documento(**d))
                                except Exception:
                                    pass
                        self.licitacion.documentos_solicitados = docs
                except Exception as e:
                    # No es bloqueante
                    QMessageBox.warning(self, "Kit", f"No se pudieron cargar documentos del kit:\n{e}")

    def _collect_data_from_tabs(self) -> bool:
        try:
            if not self.tab_general.collect_data():
                return False
            if not self.tab_lotes.collect_data():
                return False
            if not self.tab_competitors.collect_data():
                return False
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error al Recolectar Datos",
                                 f"No se pudieron obtener los datos actualizados de las pestañas:\n{e}")
            return False

    # -------------------- Evitar duplicidad de selección de empresas --------------------
    def _set_tab_general_empresas_edit_enabled(self, enabled: bool):
        # API pública (si existe)
        for m in ("set_empresas_selector_enabled", "set_empresas_edit_enabled", "habilitar_edicion_empresas", "set_empresas_button_enabled"):
            if hasattr(self.tab_general, m):
                try:
                    getattr(self.tab_general, m)(enabled)
                    return
                except Exception:
                    pass
        # Heurística: deshabilitar el grupo "Nuestras Empresas" o el botón "Seleccionar…"
        try:
            from PyQt6.QtWidgets import QGroupBox, QPushButton
            grupos = [g for g in self.tab_general.findChildren(QGroupBox) if "empresa" in (g.title() or "").lower()]
            if grupos:
                grupos[0].setEnabled(enabled)
            for btn in self.tab_general.findChildren(QPushButton):
                txt = (btn.text() or "").lower().replace("&", "")
                if "seleccionar" in txt:
                    btn.setEnabled(enabled)
        except Exception:
            pass

    def _find_tab_general_empresas_group(self):
        try:
            from PyQt6.QtWidgets import QGroupBox
            grupos = [g for g in self.tab_general.findChildren(QGroupBox)]
            for g in grupos:
                title = (g.title() or "").lower()
                name = (g.objectName() or "").lower()
                if "empresa" in title or "empresa" in name:
                    return g
        except Exception:
            pass
        return None

    def _tab_general_set_empresas_label_text(self, text: Optional[str]):
        # API pública si existe
        for m in ("set_empresas_label_text", "set_empresas_texto", "set_nuestras_empresas_text"):
            if hasattr(self.tab_general, m):
                try:
                    getattr(self.tab_general, m)(text or "Ninguna empresa seleccionada")
                    return
                except Exception:
                    pass
        # Heurística: buscar QLabel en el grupo de empresas
        try:
            group = self._find_tab_general_empresas_group()
            if group:
                labels = group.findChildren(QLabel)
                target = labels[0] if labels else None
                if target:
                    target.setText(text or "Ninguna empresa seleccionada")
                    return
            # Fallback: buscar por nombre
            for cand in ("lbl_empresas", "label_empresas", "lblNuestrasEmpresas", "lbl_empresas_sel"):
                if hasattr(self.tab_general, cand):
                    obj = getattr(self.tab_general, cand)
                    if isinstance(obj, QLabel):
                        obj.setText(text or "Ninguna empresa seleccionada")
                        return
        except Exception:
            pass

    def _sync_empresas_editability(self):
        # En edición: siempre habilitado en el tab
        if self._lock_initial_on_open:
            self._set_tab_general_empresas_edit_enabled(True)
            return
        # En creación: si hay empresas en B, deshabilitar el selector del tab; si no, habilitar
        enabled_in_tab = not bool(self._empresas_nuestras_nombres)
        self._set_tab_general_empresas_edit_enabled(enabled_in_tab)

    # -------------------- Helpers de Institución en Tab General --------------------
    def _set_tab_general_institucion_text(self, nombre: str):
        if nombre is None:
            return
        # API pública
        for m in ("set_institucion_value", "set_institucion", "set_institucion_text", "set_institucion_display"):
            if hasattr(self.tab_general, m):
                try:
                    getattr(self.tab_general, m)(nombre)
                    return
                except Exception:
                    pass
        # Heurística
        try:
            for cand in ("combo_institucion", "cbo_institucion", "institucion_combo", "inst_combo", "cb_institucion", "cmbInstitucion", "cmb_institucion", "comboInstitucion"):
                if hasattr(self.tab_general, cand):
                    w = getattr(self.tab_general, cand)
                    if isinstance(w, QComboBox):
                        w.setCurrentText(nombre)
                        return
                    if isinstance(w, QLineEdit):
                        w.setText(nombre)
                        return
            for w in self.tab_general.findChildren(QComboBox):
                nm = (w.objectName() or "").lower()
                if "institu" in nm or "institucion" in nm or "institution" in nm:
                    w.setCurrentText(nombre)
                    return
            for w in self.tab_general.findChildren(QLineEdit):
                nm = (w.objectName() or "").lower()
                if "institu" in nm or "institucion" in nm or "institution" in nm:
                    w.setText(nombre)
                    return
        except Exception:
            pass

    def _set_tab_general_institucion_enabled(self, enabled: bool):
        # API pública
        for m in ("set_institucion_enabled", "habilitar_institucion", "set_institucion_edit_enabled"):
            if hasattr(self.tab_general, m):
                try:
                    getattr(self.tab_general, m)(enabled)
                    return
                except Exception:
                    pass
        # Heurística
        try:
            for cand in ("combo_institucion", "cbo_institucion", "institucion_combo", "inst_combo", "cb_institucion", "cmbInstitucion", "cmb_institucion", "comboInstitucion"):
                if hasattr(self.tab_general, cand):
                    w = getattr(self.tab_general, cand)
                    if isinstance(w, (QComboBox, QLineEdit)):
                        w.setEnabled(enabled)
                        return
            for w in self.tab_general.findChildren(QComboBox):
                nm = (w.objectName() or "").lower()
                if "institu" in nm or "institucion" in nm or "institution" in nm:
                    w.setEnabled(enabled)
                    return
            for w in self.tab_general.findChildren(QLineEdit):
                nm = (w.objectName() or "").lower()
                if "institu" in nm or "institucion" in nm or "institution" in nm:
                    w.setEnabled(enabled)
                    return
        except Exception:
            pass

    # -------------------- Fechas por defecto en creación --------------------
    def _fix_default_dates_if_needed(self):
        if self._lock_initial_on_open:
            return  # Solo en creación
        sentinel = QDate(2000, 1, 1)
        today = QDate.currentDate()
        # QDateEdit
        for de in self.tab_general.findChildren(QDateEdit):
            try:
                if de.date() == sentinel:
                    de.setDate(today)
            except Exception:
                pass
        # QDateTimeEdit
        for dte in self.tab_general.findChildren(QDateTimeEdit):
            try:
                d = dte.date()
                if d == sentinel:
                    dt = dte.dateTime()
                    dt.setDate(today)
                    dte.setDateTime(dt)
            except Exception:
                pass

    # -------------------- Lotes: colorear texto en % Dif --------------------

    def _on_tab_changed(self, idx: int):
        """
        Maneja cambios de pestaña.

        Antes se reaplicaba un post-proceso de colores sobre la tabla de lotes
        (_postprocess_lotes_diff_colors), pero esa lógica ahora está contenida
        íntegramente dentro de TabLotes, para evitar conflictos con el tema
        Titanium Construct.
        """
        # Si en el futuro necesitas lógica al cambiar de pestaña, colócala aquí.
        _ = self.tab_widget.widget(idx)
        return


    def _ensure_empresa_nuestra_consistency(self):
        nombres = {e.nombre for e in self.licitacion.empresas_nuestras}

        for lote in self.licitacion.lotes:
            if lote.empresa_nuestra and lote.empresa_nuestra not in nombres:
                self.licitacion.empresas_nuestras.append(
                    Empresa(nombre=lote.empresa_nuestra)
                )

    # -------------------- Validación / Normalización --------------------
    def _normalize_model(self):
        """
        Normaliza el modelo antes de guardar, sin perder información de los lotes.
        - Asegura que empresas_nuestras sean objetos Empresa.
        - Asegura que lotes sean instancias de Lote, preservando todos los campos relevantes.
        """
        from app.core.log_utils import get_logger
        logger = get_logger("licitation_details_window")

        # DEBUG antes de normalizar
        logger.debug(
            "_normalize_model: Inicio normalización para licitación ID=%s numero=%s",
            getattr(self.licitacion, "id", None),
            getattr(self.licitacion, "numero_proceso", None),
        )
        for l in getattr(self.licitacion, "lotes", []) or []:
            logger.debug(
                "_normalize_model BEFORE: numero=%r empresa_nuestra=%r monto_base=%r monto_base_personal=%r monto_ofertado=%r participamos=%r fase_A_superada=%r ganador_nombre=%r ganado_por_nosotros=%r",
                getattr(l, "numero", None),
                getattr(l, "empresa_nuestra", None),
                getattr(l, "monto_base", None),
                getattr(l, "monto_base_personal", None),
                getattr(l, "monto_ofertado", None),
                getattr(l, "participamos", None),
                getattr(l, "fase_A_superada", None),
                getattr(l, "ganador_nombre", None),
                getattr(l, "ganado_por_nosotros", None),
            )

        # --- Normalizar empresas_nuestras ---
        empresas_norm: List[Empresa] = []
        for e in getattr(self.licitacion, "empresas_nuestras", []) or []:
            if isinstance(e, Empresa):
                empresas_norm.append(e)
            elif isinstance(e, dict):
                n = e.get("nombre") or e.get("razon_social") or e.get("name")
                if n:
                    empresas_norm.append(Empresa(nombre=str(n)))
            elif isinstance(e, str):
                if e.strip():
                    empresas_norm.append(Empresa(nombre=e.strip()))
        self.licitacion.empresas_nuestras = empresas_norm

        # --- Normalizar lotes ---
        lotes_norm: List[Lote] = []
        for l in getattr(self.licitacion, "lotes", []) or []:
            if isinstance(l, Lote):
                # Ya es un objeto Lote completo, no lo toques
                lotes_norm.append(l)
            elif isinstance(l, dict):
                try:
                    lotes_norm.append(
                        Lote(
                            id=l.get("id"),
                            numero=normalize_lote_numero(l.get("numero")),
                            nombre=l.get("nombre", ""),
                            monto_base=float(l.get("monto_base", 0.0) or 0.0),
                            monto_base_personal=float(l.get("monto_base_personal", 0.0) or 0.0),
                            monto_ofertado=float(l.get("monto_ofertado", 0.0) or 0.0),
                            participamos=bool(l.get("participamos", True)),
                            fase_A_superada=bool(l.get("fase_A_superada", True)),
                            ganador_nombre=l.get("ganador_nombre", ""),
                            ganado_por_nosotros=bool(l.get("ganado_por_nosotros", False)),
                            empresa_nuestra=l.get("empresa_nuestra") or None,
                        )
                    )
                except Exception as ex:
                    print("[WARN][LicitationDetailsWindow._normalize_model] "
                          f"No se pudo normalizar lote desde dict {l!r}: {ex}")
                    logger.warning(
                        "_normalize_model: No se pudo normalizar lote desde dict %r: %s",
                        l, ex
                    )
            else:
                # Tipo inesperado; intenta leer atributos por reflexión
                try:
                    lotes_norm.append(
                        Lote(
                            id=getattr(l, "id", None),
                            numero=str(getattr(l, "numero", "") or ""),
                            nombre=getattr(l, "nombre", "") or "",
                            monto_base=float(getattr(l, "monto_base", 0.0) or 0.0),
                            monto_base_personal=float(getattr(l, "monto_base_personal", 0.0) or 0.0),
                            monto_ofertado=float(getattr(l, "monto_ofertado", 0.0) or 0.0),
                            participamos=bool(getattr(l, "participamos", True)),
                            fase_A_superada=bool(getattr(l, "fase_A_superada", True)),
                            ganador_nombre=getattr(l, "ganador_nombre", "") or "",
                            ganado_por_nosotros=bool(getattr(l, "ganado_por_nosotros", False)),
                            empresa_nuestra=getattr(l, "empresa_nuestra", None),
                        )
                    )
                except Exception as ex:
                    print("[WARN][LicitationDetailsWindow._normalize_model] "
                          f"Tipo de lote inesperado {type(l)}: {ex}")
                    logger.warning(
                        "_normalize_model: Tipo de lote inesperado %s: %s",
                        type(l), ex
                    )
        self.licitacion.lotes = lotes_norm

        # DEBUG después de normalizar
        logger.debug("_normalize_model: Lotes normalizados para licitación ID=%s", getattr(self.licitacion, "id", None))
        for l in self.licitacion.lotes:
            logger.debug(
                "_normalize_model AFTER: numero=%r empresa_nuestra=%r monto_base=%r monto_base_personal=%r monto_ofertado=%r participamos=%r fase_A_superada=%r ganador_nombre=%r ganado_por_nosotros=%r",
                l.numero,
                l.empresa_nuestra,
                l.monto_base,
                l.monto_base_personal,
                l.monto_ofertado,
                l.participamos,
                l.fase_A_superada,
                l.ganador_nombre,
                l.ganado_por_nosotros,
            )

        # También puedes dejar el print de depuración si quieres ver algo en consola
        print("[DEBUG][LicitationDetailsWindow._normalize_model] Lotes normalizados:")
        for l in self.licitacion.lotes:
            print(f"   numero={l.numero!r}, empresa_nuestra={l.empresa_nuestra!r}, "
                  f"monto_ofertado={l.monto_ofertado}, participamos={l.participamos}, "
                  f"fase_A_superada={l.fase_A_superada}, ganador={l.ganador_nombre}, "
                  f"ganado_por_nosotros={l.ganado_por_nosotros}")            
                        
    def _validate_before_save(self) -> bool:
        # Institución
        if not (self.licitacion.institucion and str(self.licitacion.institucion).strip()):
            QMessageBox.warning(self, "Campo Requerido", "Debe seleccionar una Institución.")
            self.tab_widget.setCurrentWidget(self.tab_general)
            return False
        # Empresas propias
        if not getattr(self.licitacion, "empresas_nuestras", []):
            QMessageBox.warning(self, "Campo Requerido", "Debe seleccionar al menos una empresa propia.")
            return False
        # Nombre y código
        nombre_lic = (self.licitacion.nombre_proceso or "").strip()
        codigo_lic = (self.licitacion.numero_proceso or "").strip()
        if not nombre_lic or not codigo_lic:
            QMessageBox.warning(self, "Campos Requeridos", "Nombre y Código del proceso no pueden estar vacíos.")
            self.tab_widget.setCurrentWidget(self.tab_general)
            return False
        # Lotes
        if not getattr(self.licitacion, "lotes", []):
            QMessageBox.warning(self, "Lotes Requeridos", "Agregue al menos un lote.")
            self.tab_widget.setCurrentWidget(self.tab_lotes)
            return False
        return True

    # -------------------- Guardado --------------------
    def _ensure_licitacion_id_after_save(self, save_return: Any):
        if isinstance(save_return, int) and save_return > 0:
            self.licitacion.id = save_return
        if getattr(self.licitacion, "id", None):
            return
        codigo = (self.licitacion.numero_proceso or "").strip()
        try_methods = [
            "get_licitacion_por_codigo",
            "get_licitacion_by_codigo",
            "buscar_licitacion_por_codigo",
            "get_licitacion_por_numero",
            "get_licitacion_by_numero",
            "find_licitacion_by_code",
        ]
        for m in try_methods:
            if hasattr(self.db, m):
                try:
                    res = getattr(self.db, m)(codigo)
                    if isinstance(res, Licitacion) and getattr(res, "id", None):
                        self.licitacion.id = res.id
                        return
                    if isinstance(res, dict):
                        rid = res.get("id") or res.get("pk") or res.get("licitacion_id")
                        if rid:
                            self.licitacion.id = int(rid)
                            return
                except Exception:
                    pass
        for cand in ("last_inserted_id", "get_last_inserted_id", "lastrowid"):
            if hasattr(self.db, cand):
                try:
                    val = getattr(self.db, cand)
                    val = val() if callable(val) else val
                    if isinstance(val, int) and val > 0:
                        self.licitacion.id = val
                        return
                except Exception:
                    pass

    def _persistir_ganadores_por_lote(self):
        if not self.licitacion.id or not hasattr(self.db, "marcar_ganador_lote"):
            if not hasattr(self.db, "marcar_ganador_lote"):
                print("Advertencia: No se persistirán ganadores (db_adapter no tiene 'marcar_ganador_lote').")
            return
        try:
            for lote in self.licitacion.lotes:
                nombre_ganador = (getattr(lote, 'ganador_nombre', '') or '').strip()
                lote_num_str = str(lote.numero)
                if nombre_ganador:
                    es_nuestro = bool(getattr(lote, 'ganado_por_nosotros', False))
                    emp_nuestra_lote = (getattr(lote, 'empresa_nuestra', '') or '').strip()
                    empresa_nuestra_arg = emp_nuestra_lote if (es_nuestro or emp_nuestra_lote == nombre_ganador) else None
                    self.db.marcar_ganador_lote(
                        self.licitacion.id,
                        lote_num_str,
                        nombre_ganador,
                        empresa_nuestra_arg
                    )
                elif hasattr(self.db, "borrar_ganador_lote"):
                    self.db.borrar_ganador_lote(self.licitacion.id, lote_num_str)
        except Exception as e:
            QMessageBox.warning(self, "Error Parcial al Guardar",
                                f"Los cambios principales se guardaron, pero ocurrió un error al persistir los ganadores de los lotes:\n{e}")

    def _save_changes(self) -> bool:
        try:
            save_return = self.db.save_licitacion(self.licitacion)
            success = bool(save_return) if not isinstance(save_return, int) else True
            if not success:
                QMessageBox.warning(self, "Error al Guardar", "La operación de guardado principal falló.")
                return False

            self._ensure_licitacion_id_after_save(save_return)
            self._persistir_ganadores_por_lote()

            if self.refresh_callback:
                try:
                    self.refresh_callback()
                except Exception:
                    pass
            try:
                self.saved.emit(self.licitacion)
            except Exception:
                pass
            return True

        except ValueError as ve:
            # Mensaje proveniente del adaptador cuando faltan mínimos (p.ej. sin lotes)
            QMessageBox.warning(self, "Validación", str(ve))
            return False
        except getattr(sys.modules.get('app.core.db_manager'), 'ConcurrencyException', Exception) as ce:
            QMessageBox.critical(self, "Error de Concurrencia",
                                f"Los datos han sido modificados por otro usuario.\n{ce}\n\n"
                                "Cierra y vuelve a abrir para ver cambios.")
            return False
        except Exception as e:
            QMessageBox.critical(self, "Error Crítico al Guardar",
                                f"Ocurrió un error inesperado al guardar:\n{e}")
            return False

    # -------------------- Eliminación --------------------
    def _confirm_and_delete(self):
        lic_id = getattr(self.licitacion, "id", None)
        if not lic_id:
            QMessageBox.information(self, "Eliminar", "Esta licitación aún no tiene ID; no se puede eliminar.")
            return
        codigo = self.licitacion.numero_proceso or "(sin código)"
        nombre = (self.licitacion.nombre_proceso or "").strip() or "(sin nombre)"
        msg = (f"¿Seguro que deseas eliminar la licitación?\n\n"
               f"Código: {codigo}\nNombre: {nombre}\n\n"
               "Esta acción es permanente.")
        resp = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if resp == QMessageBox.StandardButton.Yes:
            self._delete_licitacion(lic_id)

    def _delete_licitacion(self, lic_id: int):
        try:
            # Borrado principal
            self.db.delete_licitacion(lic_id)
            try:
                self.deleted.emit(int(lic_id))
            except Exception:
                pass
            # Feedback
            QMessageBox.information(self, "Eliminado", "La licitación fue eliminada correctamente.")
            # Refrescar caller si corresponde
            if self.refresh_callback:
                try:
                    self.refresh_callback()
                except Exception:
                    pass
            # Limpiar/Deshabilitar UI y cerrar
            self._after_deletion_cleanup()
        except Exception as e:
            QMessageBox.critical(self, "Error al Eliminar", f"No se pudo eliminar la licitación:\n{e}")

    def _after_deletion_cleanup(self):
        # Marcar como eliminada y desactivar controles
        self.licitacion.id = None
        self.setWindowTitle("Licitación eliminada")
        self.group_header.setEnabled(False)
        self.tab_widget.setEnabled(False)
        self.btn_save_continue.setEnabled(False)
        ok_btn = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setEnabled(False)
        if self.btn_delete:
            self.btn_delete.setEnabled(False)
            self.btn_delete.setVisible(False)
        # Cerrar luego de breve pausa
        QTimer.singleShot(900, self.accept)

    # -------------------- Botones Guardar --------------------
    def _save_and_continue(self):
        print("[DEBUG][LicitationDetailsWindow] Save & Continue")

        if self._perform_save(close_after=False):
            self._load_data_into_tabs()




    def _enable_save_continue_button(self):
        if self._edit_lock or self._saving:
            self.btn_save_continue.setEnabled(False)
            return
        self.btn_save_continue.setText("Guardar y Continuar")
        self.btn_save_continue.setEnabled(True)

    def _save_and_close(self):
        print("[DEBUG][LicitationDetailsWindow] Save & Close iniciado")

        tabs = [
            self.tab_general,
            self.tab_lotes,
            self.tab_competitors,
        ]

        for tab in tabs:
            if hasattr(tab, "collect_data"):
                print(f"[DEBUG] collect_data() -> {tab.__class__.__name__}")
                tab.collect_data()

        self._normalize_model()

        self.db.save_licitacion(self.licitacion)
        self._change_log.clear()
        self._refresh_change_logger()


        self.close()


    def _snapshot_model(self) -> int:
        """
        Snapshot rápido basado en hash.
        Suficiente para detectar cambios reales.
        """
        try:
            parts = []

            parts.append(self.licitacion.numero_proceso or "")
            parts.append(self.licitacion.nombre_proceso or "")
            parts.append(self.licitacion.institucion or "")

            for e in getattr(self.licitacion, "empresas_nuestras", []) or []:
                parts.append(getattr(e, "nombre", str(e)))

            for l in getattr(self.licitacion, "lotes", []) or []:
                parts.extend([
                    str(l.id),
                    str(l.numero),
                    l.nombre or "",
                    str(l.monto_base),
                    str(l.monto_base_personal),
                    str(l.monto_ofertado),
                    str(l.participamos),
                    str(l.fase_A_superada),
                    l.ganador_nombre or "",
                    str(l.ganado_por_nosotros),
                    l.empresa_nuestra or "",
                ])

            return hash("|".join(parts))

        except Exception as e:
            print("[WARN] Snapshot falló:", e)
            return 0


    def lock_edit(self, source: str = ""):
        self._edit_locks[source] = self._edit_locks.get(source, 0) + 1
        print(f"[LOCK] {source} → {self._edit_locks[source]}")

    def unlock_edit(self, source: str = ""):
        if source in self._edit_locks:
            self._edit_locks[source] -= 1
            if self._edit_locks[source] <= 0:
                del self._edit_locks[source]
            print(f"[UNLOCK] {source}")



    # -------------------- Resultado property --------------------
    @property
    def resultado(self) -> Licitacion | None:
        return getattr(self, "_resultado_guardado", None)

    @resultado.setter
    def resultado(self, value: Licitacion | None):
        self._resultado_guardado = value

    def reject(self):
        self.resultado = None
        super().reject()



    def _autosave_if_needed(self):
        """
        Autosave diferido. Solo guarda si:
        - hay cambios (_dirty)
        - no se está guardando
        - no hay locks activos
        """
        if not self._dirty:
            return

        if self._saving:
            print("[AUTOSAVE] Guardado en progreso, se omite")
            return

        if self._edit_locks:
            print("[AUTOSAVE] Locks activos, se omite:", self._edit_locks)
            return

        print("[AUTOSAVE] Ejecutando autosave…")
        self._perform_save(close_after=False)



    def _perform_save(self, close_after: bool = False) -> bool:
        if self._saving:
            print("[LOCK] Guardado ya en progreso")
            return False

        if self._edit_lock:
            print("[LOCK] Edición bloqueada, no se guarda")
            return False

        # 1. Recolectar datos
        tabs = [self.tab_general, self.tab_lotes, self.tab_competitors]
        for tab in tabs:
            if hasattr(tab, "collect_data"):
                if tab.collect_data() is False:
                    return False

        # 2. Normalizar
        self._normalize_model()

        # 3. Validar
        if not self._validate_before_save():
            return False

        # 4. Snapshot
        new_snapshot = self._snapshot_model()
        if new_snapshot == self._last_snapshot:
            print("[INFO] No hay cambios reales, se omite guardado")
            self._dirty = False
            return True

        # 5. Guardar
        try:
            self._saving = True
            save_return = self.db.save_licitacion(self.licitacion)
            self._ensure_licitacion_id_after_save(save_return)
            self._persistir_ganadores_por_lote()

            self._last_snapshot = new_snapshot
            self._dirty = False

            if self.refresh_callback:
                try:
                    self.refresh_callback()
                except Exception:
                    pass

            try:
                self.saved.emit(self.licitacion)
            except Exception:
                pass

            print("[OK] Guardado exitoso")
            return True

        finally:
            self._saving = False


    def log_change(self, message: str):
        ts = datetime.now().strftime("%H:%M:%S")
        entry = f"[{ts}] {message}"

        self._change_log.append(entry)

        print(f"[LOGGER] {entry}")

        # Refrescar UI si existe
        if hasattr(self, "_refresh_change_logger"):
            self._refresh_change_logger()


    def _refresh_change_logger(self):
        if not hasattr(self, "list_change_log"):
            return

        self.list_change_log.clear()
        for entry in reversed(self._change_log):
            self.list_change_log.addItem(entry)
