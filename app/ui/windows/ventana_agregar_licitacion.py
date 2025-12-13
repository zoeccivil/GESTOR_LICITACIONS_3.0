from __future__ import annotations

from typing import Optional, Dict, Any, List, Tuple, Callable

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QLineEdit, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QStyle, QDialogButtonBox, QFormLayout, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSettings, QEvent
from PyQt6.QtGui import QIcon, QFont, QPalette, QKeySequence, QShortcut

# Diálogos
from app.ui.dialogs.gestionar_lote_dialog import GestionarLoteDialog
from app.ui.dialogs.seleccionar_empresas_dialog import SeleccionarEmpresasDialog
from app.ui.dialogs.dialogo_seleccionar_institucion import DialogoSeleccionarInstitucion

# Modelos
from app.core.models import Documento, Licitacion, Lote, Empresa


class AddLicitacionWindow(QDialog):
    """
    Diálogo para crear o editar una Licitación.
    Funciona en modo creación (por defecto) o edición si se pasa 'licitacion_existente'.
    - Selección de institución mediante diálogo separate.
    - Selección de empresas propias.
    - Gestión de lotes (agregar / editar / eliminar).
    - Carga opcional de Kit de requisitos (placeholder adaptable).
    - Persistencia de geometría y anchos de columnas vía QSettings.
    - Atajos: Ctrl+N (Agregar lote), Ctrl+E (Editar), Del (Eliminar), Ctrl+S (Guardar).
    Señales:
        saved(Licitacion) -> emitida cuando la licitación se guarda (creada o actualizada) correctamente.
    """

    saved = pyqtSignal(object)

    SETTINGS_GEOM_KEY = "add_licitacion_window/geometry"
    SETTINGS_TABLE_COLS_KEY = "add_licitacion_window/lotes_col_widths"

    def __init__(
        self,
        parent=None,
        db=None,
        callback_guardar: Optional[Callable[[Licitacion], bool]] = None,
        licitacion_existente: Optional[Licitacion] = None,
        **kwargs
    ):
        """
        Parámetros:
            db: Adaptador de base de datos.
            callback_guardar: función para persistir (creación); debe retornar bool.
            licitacion_existente: si se provee, el diálogo entra en modo edición.
            on_saved: (alias) alternativa para callback_guardar.
        """
        super().__init__(parent)
        if callback_guardar is None and "on_saved" in kwargs:
            callback_guardar = kwargs.get("on_saved")

        self.db = db
        self._on_saved_cb = callback_guardar
        self.modo_edicion = licitacion_existente is not None
        self.licitacion_existente = licitacion_existente

        # Catálogos
        try:
            self.lista_empresas = self.db.get_empresas_maestras() if self.db else []
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar las empresas maestras:\n{e}")
            self.lista_empresas = []

        # Estado interno
        self.institucion_seleccionada: Optional[Dict[str, Any]] = None
        self.empresas_seleccionadas: List[str] = []
        self.lotes_temp: List[Lote] = []
        self.kits_disponibles: List[Dict[str, Any]] = []

        # Configuración ventana
        self.setWindowTitle("Editar Licitación" if self.modo_edicion else "Agregar Nueva Licitación")
        self.setMinimumSize(950, 700)
        flags = self.windowFlags()
        self.setWindowFlags(flags | Qt.WindowType.WindowMaximizeButtonHint | Qt.WindowType.WindowMinimizeButtonHint)

        # Construcción de UI
        self._build_ui()

        # Atajos de teclado
        self._registrar_atajos()

        # Cargar datos si estamos en edición
        if self.modo_edicion:
            self._cargar_licitacion_existente()

        # Tema / persistencia
        self._apply_theme()
        self._restore_ui_state()

    # ---------- UI ----------
    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        top_layout = QHBoxLayout()
        main_layout.addLayout(top_layout)

        style = self.style()

        # Panel A: Institución
        panelA = QGroupBox("A. Seleccione la Institución")
        vA = QVBoxLayout(panelA)
        fila_inst = QHBoxLayout()
        self.txt_institucion_sel = QLineEdit()
        self.txt_institucion_sel.setPlaceholderText("Ninguna seleccionada...")
        self.txt_institucion_sel.setReadOnly(True)
        self.txt_institucion_sel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        fila_inst.addWidget(self.txt_institucion_sel, stretch=1)

        self.btn_seleccionar_inst = QPushButton(" Seleccionar...")
        self.btn_seleccionar_inst.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton))
        self.btn_seleccionar_inst.clicked.connect(self._abrir_selector_institucion)
        fila_inst.addWidget(self.btn_seleccionar_inst)
        vA.addLayout(fila_inst)
        top_layout.addWidget(panelA, stretch=2)

        # Panel B: Empresas propias
        panelB = QGroupBox("B. Seleccione su(s) Empresa(s)")
        vB = QVBoxLayout(panelB)
        self.lbl_empresas_sel = QLabel("Ninguna seleccionada")
        self.lbl_empresas_sel.setWordWrap(True)
        vB.addWidget(self.lbl_empresas_sel, stretch=1)

        btn_seleccionar_emp = QPushButton(" Seleccionar Empresas...")
        btn_seleccionar_emp.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        btn_seleccionar_emp.clicked.connect(self._abrir_selector_empresas)
        vB.addWidget(btn_seleccionar_emp, alignment=Qt.AlignmentFlag.AlignRight)
        top_layout.addWidget(panelB, stretch=2)

        # Panel C: Detalles de licitación
        panelC = QGroupBox("C. Complete los Detalles")
        formC = QFormLayout(panelC)
        formC.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.txt_nombre_lic = QLineEdit()
        self.txt_codigo_lic = QLineEdit()
        self.combo_kit = QComboBox()
        self.combo_kit.addItem(" (Ninguno) ")
        self.combo_kit.setEnabled(False)

        formC.addRow("Nombre Licitación:", self.txt_nombre_lic)
        formC.addRow("Código Proceso:", self.txt_codigo_lic)
        formC.addRow("Aplicar Kit Requisitos:", self.combo_kit)
        top_layout.addWidget(panelC, stretch=3)

        # Panel D: Lotes
        panelD = QGroupBox("D. Lotes del Proceso")
        vD = QVBoxLayout(panelD)
        self.tabla_lotes = QTableWidget(0, 5)
        self.tabla_lotes.setHorizontalHeaderLabels(["N°", "Nombre Lote", "Monto Base", "Nuestra Oferta", "Empresa Asignada"])
        header = self.tabla_lotes.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)
        header.resizeSection(0, 80)
        header.resizeSection(1, 260)
        header.resizeSection(2, 120)
        header.resizeSection(3, 120)
        header.resizeSection(4, 160)
        self.tabla_lotes.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_lotes.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_lotes.setAlternatingRowColors(True)
        self.tabla_lotes.setSortingEnabled(True)
        self.tabla_lotes.verticalHeader().setDefaultSectionSize(24)
        self.tabla_lotes.doubleClicked.connect(self._editar_lote)
        vD.addWidget(self.tabla_lotes)

        lotes_btns_layout = QHBoxLayout()
        btn_add_lote = QPushButton(" Agregar Lote")
        btn_add_lote.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder))
        btn_edit_lote = QPushButton(" Editar Lote")
        btn_edit_lote.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        btn_del_lote = QPushButton(" Eliminar Lote")
        btn_del_lote.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_TrashIcon))

        btn_add_lote.clicked.connect(self._agregar_lote)
        btn_edit_lote.clicked.connect(self._editar_lote)
        btn_del_lote.clicked.connect(self._eliminar_lote)

        lotes_btns_layout.addWidget(btn_add_lote)
        lotes_btns_layout.addWidget(btn_edit_lote)
        lotes_btns_layout.addWidget(btn_del_lote)
        lotes_btns_layout.addStretch(1)
        vD.addLayout(lotes_btns_layout)
        main_layout.addWidget(panelD, stretch=1)

        # Botonera Guardar / Cancelar
        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self._button_box.button(QDialogButtonBox.StandardButton.Save).setText(
            "Guardar Cambios" if self.modo_edicion else "Crear Licitación"
        )
        self._button_box.accepted.connect(self._guardar_licitacion)
        self._button_box.rejected.connect(self.reject)
        main_layout.addWidget(self._button_box)

    def _registrar_atajos(self):
        QShortcut(QKeySequence("Ctrl+N"), self).activated.connect(self._agregar_lote)
        QShortcut(QKeySequence("Ctrl+E"), self).activated.connect(self._editar_lote)
        QShortcut(QKeySequence("Del"), self).activated.connect(self._eliminar_lote)
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self._guardar_licitacion)

    # ---------- Tema / Persistencia ----------
    def _apply_theme(self):
        pal: QPalette = self.palette()
        col_text = pal.color(QPalette.ColorRole.WindowText).name()
        col_warn = pal.color(QPalette.ColorRole.LinkVisited).name()
        col_readonly_bg = pal.color(QPalette.ColorRole.AlternateBase).name()

        self.txt_institucion_sel.setStyleSheet(
            f"QLineEdit:read-only {{ background-color: {col_readonly_bg}; color: {col_text}; }}"
        )

        if not self.empresas_seleccionadas:
            self.lbl_empresas_sel.setStyleSheet(f"color: {col_warn}; font-weight: 600;")
        else:
            self.lbl_empresas_sel.setStyleSheet(f"color: {col_text};")

    def changeEvent(self, event: QEvent) -> None:
        if event.type() in (QEvent.Type.PaletteChange, QEvent.Type.ApplicationPaletteChange):
            self._apply_theme()
        super().changeEvent(event)

    def _save_ui_state(self):
        try:
            s = QSettings()
            s.setValue(self.SETTINGS_GEOM_KEY, self.saveGeometry())
            col_widths = [self.tabla_lotes.columnWidth(i) for i in range(self.tabla_lotes.columnCount())]
            s.setValue(self.SETTINGS_TABLE_COLS_KEY, col_widths)
        except Exception:
            pass

    def _restore_ui_state(self):
        try:
            s = QSettings()
            g = s.value(self.SETTINGS_GEOM_KEY, None)
            if g is not None:
                self.restoreGeometry(g)
            widths = s.value(self.SETTINGS_TABLE_COLS_KEY, None)
            if isinstance(widths, list) and len(widths) == self.tabla_lotes.columnCount():
                for i, w in enumerate(widths):
                    try:
                        self.tabla_lotes.setColumnWidth(i, int(w))
                    except Exception:
                        pass
        except Exception:
            pass

    def closeEvent(self, e):
        self._save_ui_state()
        super().closeEvent(e)

    # ---------- Cargar licitación existente ----------
    def _cargar_licitacion_existente(self):
        lic = self.licitacion_existente
        if not lic:
            return
        self.txt_nombre_lic.setText(lic.nombre_proceso or "")
        self.txt_codigo_lic.setText(lic.numero_proceso or "")

        institucion_nombre = getattr(lic, "institucion", "") or ""
        if institucion_nombre:
            self.institucion_seleccionada = {"nombre": institucion_nombre}
            self.txt_institucion_sel.setText(institucion_nombre)
            self._cargar_kits_institucion()

        self.empresas_seleccionadas = [
            e.nombre if isinstance(e, Empresa) else (e if isinstance(e, str) else "")
            for e in getattr(lic, "empresas_nuestras", [])
            if e
        ]
        self._actualizar_display_empresas()

        self.lotes_temp = []
        for l in getattr(lic, "lotes", []):
            if isinstance(l, Lote):
                self.lotes_temp.append(l)
            elif isinstance(l, dict):
                try:
                    self.lotes_temp.append(
                        Lote(
                            numero=l.get("numero"),
                            nombre=l.get("nombre"),
                            monto_base=float(l.get("monto_base", 0) or 0),
                            monto_base_personal=float(l.get("monto_base_personal", 0) or 0),
                            monto_ofertado=float(l.get("monto_ofertado", 0) or 0),
                            empresa_nuestra=l.get("empresa_nuestra"),
                        )
                    )
                except Exception:
                    pass
        self._actualizar_tabla_lotes()

    # ---------- Institución ----------
    def _abrir_selector_institucion(self):
        try:
            dlg = DialogoSeleccionarInstitucion(self, self.db)
            if self.institucion_seleccionada:
                try:
                    dlg._seleccionar_item_por_nombre(self.institucion_seleccionada.get('nombre', ''))
                except Exception:
                    pass
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self.institucion_seleccionada = dlg.institucion_seleccionada
                if self.institucion_seleccionada:
                    self.txt_institucion_sel.setText(self.institucion_seleccionada.get('nombre', ''))
                    self._cargar_kits_institucion()
                else:
                    self.txt_institucion_sel.clear()
                    self._on_institucion_changed()
        except ImportError:
            QMessageBox.critical(self, "Error", "Falta el archivo 'dialogo_seleccionar_institucion.py'.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir el selector de instituciones:\n{e}")

    def _on_institucion_changed(self):
        if self.institucion_seleccionada:
            self._cargar_kits_institucion()
        else:
            self.combo_kit.clear()
            self.combo_kit.addItem(" (Ninguno) ")
            self.combo_kit.setEnabled(False)

    def _cargar_kits_institucion(self):
        if not self.institucion_seleccionada:
            return
        nombre_inst = self.institucion_seleccionada.get('nombre', '').strip()
        nombres_kits = [f"Kit A {nombre_inst}", f"Kit B {nombre_inst}"] if nombre_inst else []
        self.combo_kit.clear()
        self.combo_kit.addItem(" (Ninguno) ")
        if nombres_kits:
            self.combo_kit.addItems(nombres_kits)
            self.combo_kit.setEnabled(True)
        else:
            self.combo_kit.setEnabled(False)
        self.combo_kit.setCurrentIndex(0)

    # ---------- Empresas ----------
    def _abrir_selector_empresas(self):
        dlg = SeleccionarEmpresasDialog(self, self.lista_empresas, self.empresas_seleccionadas)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            seleccion = self._get_empresas_desde_dialog(dlg)
            if seleccion is None:
                QMessageBox.warning(self, "Aviso", "No se pudo obtener la selección de empresas del diálogo.")
                return
            self.empresas_seleccionadas = seleccion
            self._actualizar_display_empresas()
            self._apply_theme()

    def _get_empresas_desde_dialog(self, dlg) -> List[str] | None:
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

        # 1) Métodos típicos
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

        # 2) Atributos comunes
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

    def _actualizar_display_empresas(self):
        pal: QPalette = self.palette()
        col_text = pal.color(QPalette.ColorRole.WindowText).name()
        col_warn = pal.color(QPalette.ColorRole.LinkVisited).name()

        if not self.empresas_seleccionadas:
            self.lbl_empresas_sel.setText("Ninguna seleccionada")
            self.lbl_empresas_sel.setStyleSheet(f"color: {col_warn}; font-weight: 600;")
        else:
            texto = ", ".join(sorted(self.empresas_seleccionadas))
            self.lbl_empresas_sel.setText(texto)
            self.lbl_empresas_sel.setStyleSheet(f"color: {col_text};")

    # ---------- Lotes ----------
    def _actualizar_tabla_lotes(self):
        self.tabla_lotes.setSortingEnabled(False)
        self.tabla_lotes.setRowCount(0)
        for i, lote in enumerate(self.lotes_temp):
            row = self.tabla_lotes.rowCount()
            self.tabla_lotes.insertRow(row)

            item_num = QTableWidgetItem(str(lote.numero))
            item_num.setData(Qt.ItemDataRole.UserRole, i)
            item_num.setFlags(item_num.flags() & ~Qt.ItemFlag.ItemIsEditable)

            item_nombre = QTableWidgetItem(lote.nombre)

            item_monto_base = QTableWidgetItem(f"{float(lote.monto_base or 0):,.2f}")
            item_monto_base.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            item_monto_ofer = QTableWidgetItem(f"{float(lote.monto_ofertado or 0):,.2f}")
            item_monto_ofer.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            empresa_asignada = lote.empresa_nuestra if lote.empresa_nuestra else ""
            item_empresa = QTableWidgetItem(empresa_asignada)

            self.tabla_lotes.setItem(row, 0, item_num)
            self.tabla_lotes.setItem(row, 1, item_nombre)
            self.tabla_lotes.setItem(row, 2, item_monto_base)
            self.tabla_lotes.setItem(row, 3, item_monto_ofer)
            self.tabla_lotes.setItem(row, 4, item_empresa)

        self.tabla_lotes.setSortingEnabled(True)

    def _get_selected_lote_index_and_obj(self) -> Tuple[Optional[int], Optional[Lote]]:
        sel = self.tabla_lotes.selectionModel().selectedRows()
        if not sel:
            return None, None
        row_visual = sel[0].row()
        item_num = self.tabla_lotes.item(row_visual, 0)
        if not item_num:
            return None, None
        idx = item_num.data(Qt.ItemDataRole.UserRole)
        try:
            idx = int(idx)
            if 0 <= idx < len(self.lotes_temp):
                return idx, self.lotes_temp[idx]
        except Exception:
            pass
        return None, None

    def _agregar_lote(self):
        if not self.empresas_seleccionadas:
            QMessageBox.warning(
                self,
                "Empresas Requeridas",
                "Seleccione al menos una empresa antes de agregar lotes."
            )
            return

        dialog = GestionarLoteDialog(
            parent=self,
            title="Agregar Lote",
            initial_data=None,
            participating_companies=self.empresas_seleccionadas,
        )

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        lote = dialog.get_lote_obj()
        if not lote:
            QMessageBox.warning(self, "Aviso", "No se obtuvo un lote válido del diálogo.")
            return

        # Evitar duplicados
        if any(str(x.numero) == str(lote.numero) for x in self.lotes_temp):
            QMessageBox.warning(
                self,
                "Lote Duplicado",
                f"Ya existe un lote con el número '{lote.numero}'."
            )
            return

        # 1️⃣ Agregar al modelo en memoria
        self.lotes_temp.append(lote)
        self.licitacion.lotes = list(self.lotes_temp)

        # 2️⃣ GUARDADO AUTOMÁTICO (candado)
        try:
            self.db_adapter.save_licitacion(self.licitacion)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error al Guardar",
                f"No se pudo guardar el lote en Firebase:\n{e}"
            )
            return

        # 3️⃣ Refrescar UI
        self._actualizar_tabla_lotes()
        self.tabla_lotes.selectRow(len(self.lotes_temp) - 1)


    def _editar_lote(self):
        idx, lote_actual = self._get_selected_lote_index_and_obj()
        if lote_actual is None or idx is None:
            QMessageBox.warning(self, "Sin Selección", "Selecciona un lote para editar.")
            return

        dialog = GestionarLoteDialog(
            parent=self,
            title="Editar Lote",
            initial_data=lote_actual,
            participating_companies=self.empresas_seleccionadas,
        )

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        editado = dialog.get_lote_obj()
        if not editado:
            QMessageBox.warning(self, "Aviso", "No se obtuvo un lote válido del diálogo.")
            return

        # Evitar duplicados por número
        if any(
            str(x.numero) == str(editado.numero) and i != idx
            for i, x in enumerate(self.lotes_temp)
        ):
            QMessageBox.warning(
                self,
                "Lote Duplicado",
                f"Ya existe otro lote con el número '{editado.numero}'."
            )
            return

        # 🔐 Preservar ID del lote
        if getattr(lote_actual, "id", None) is not None:
            editado.id = lote_actual.id

        # 1️⃣ Actualizar en memoria
        self.lotes_temp[idx] = editado
        self.licitacion.lotes = list(self.lotes_temp)

        # 2️⃣ GUARDADO AUTOMÁTICO (candado)
        try:
            self.db_adapter.save_licitacion(self.licitacion)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error al Guardar",
                f"No se pudo guardar el lote editado en Firebase:\n{e}"
            )
            return

        # 3️⃣ Refrescar UI
        self._actualizar_tabla_lotes()
        self.tabla_lotes.selectRow(idx)



    def _eliminar_lote(self):
        lote_index, lote_a_eliminar = self._get_selected_lote_index_and_obj()
        if lote_a_eliminar is None or lote_index is None:
            QMessageBox.warning(self, "Sin Selección", "Selecciona un lote para eliminar.")
            return
        nombre_lote = lote_a_eliminar.nombre
        if QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Eliminar el lote '{nombre_lote}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            del self.lotes_temp[lote_index]
            self._actualizar_tabla_lotes()

    # ---------- Guardado ----------
    def _guardar_licitacion(self):
        if not self.institucion_seleccionada:
            QMessageBox.warning(self, "Campo Requerido", "Debe seleccionar una institución (Panel A).")
            return
        if not self.empresas_seleccionadas:
            QMessageBox.warning(self, "Campo Requerido", "Debe seleccionar al menos una empresa (Panel B).")
            return
        nombre_lic = self.txt_nombre_lic.text().strip()
        codigo_lic = self.txt_codigo_lic.text().strip()
        if not nombre_lic or not codigo_lic:
            QMessageBox.warning(self, "Campos Requeridos", "Nombre y Código no pueden estar vacíos (Panel C).")
            return
        if not self.lotes_temp:
            QMessageBox.warning(self, "Lotes Requeridos", "Agregue al menos un lote (Panel D).")
            return

        empresas_obj = [Empresa(nombre=n) for n in self.empresas_seleccionadas]

        try:
            if self.modo_edicion and self.licitacion_existente:
                lic = self.licitacion_existente
                lic.nombre_proceso = nombre_lic
                lic.numero_proceso = codigo_lic
                lic.institucion = self.institucion_seleccionada.get('nombre', '')
                lic.empresas_nuestras = empresas_obj
                lic.lotes = self.lotes_temp
                self._aplicar_kit_a_licitacion(lic)
                ok = self._persistir_licitacion(lic, nuevo=False)
                if ok:
                    self.saved.emit(lic)
                    QMessageBox.information(self, "Éxito", f"Licitación '{lic.nombre_proceso}' actualizada.")
                    self.accept()
                return

            nueva = Licitacion(
                nombre_proceso=nombre_lic,
                numero_proceso=codigo_lic,
                institucion=self.institucion_seleccionada.get('nombre', ''),
                empresas_nuestras=empresas_obj,
                lotes=self.lotes_temp,
                documentos_solicitados=[]
            )
            self._aplicar_kit_a_licitacion(nueva)
            ok = self._persistir_licitacion(nueva, nuevo=True)
            if ok:
                self.saved.emit(nueva)
                QMessageBox.information(self, "Éxito", f"Licitación '{nombre_lic}' creada.")
                self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al guardar la licitación:\n{e}")

    def _aplicar_kit_a_licitacion(self, lic: Licitacion):
        kit_seleccionado = self.combo_kit.currentText()
        if kit_seleccionado and kit_seleccionado.strip() not in {"(Ninguno)", " (Ninguno) "}:
            if self.db and hasattr(self.db, "get_documentos_de_kit"):
                try:
                    documentos_kit_dict = self.db.get_documentos_de_kit(
                        kit_seleccionado,
                        self.institucion_seleccionada.get('nombre', '')
                    )
                    lic.documentos_solicitados = [Documento(**d) for d in documentos_kit_dict]
                except Exception as e_kit:
                    QMessageBox.warning(self, "Kit", f"No se pudieron cargar documentos del kit:\n{e_kit}")

    def _persistir_licitacion(self, lic: Licitacion, nuevo: bool) -> bool:
        if not self.db:
            return True  # modo sin persistencia
        try:
            if nuevo:
                for method in ("save_licitacion", "crear_licitacion", "add_licitacion"):
                    if hasattr(self.db, method):
                        new_id = getattr(self.db, method)(lic)
                        if new_id:
                            lic.id = new_id
                        return True
                return False
            else:
                for method in ("update_licitacion", "actualizar_licitacion", "save_licitacion"):
                    if hasattr(self.db, method):
                        getattr(self.db, method)(lic)
                        return True
                return False
        except Exception as e:
            QMessageBox.critical(self, "Persistencia", f"Error al persistir en la base de datos:\n{e}")
            return False

    # ---------- Helper lote ----------
    def _lote_desde_dialog(self, dialog) -> Optional[Lote]:
        for cand in ("get_lote_obj", "lote_result"):
            if hasattr(dialog, cand):
                val = getattr(dialog, cand)
                try:
                    lote_obj = val() if callable(val) else val
                except Exception:
                    lote_obj = val
                if isinstance(lote_obj, Lote):
                    return lote_obj

        data = None
        for cand in ("resultado", "result", "get_result"):
            if hasattr(dialog, cand):
                val = getattr(dialog, cand)
                try:
                    data = val() if callable(val) else val
                except Exception:
                    data = val
                break

        if isinstance(data, dict):
            try:
                return Lote(
                    numero=data.get("numero"),
                    nombre=data.get("nombre"),
                    monto_base=float(data.get("monto_base", 0) or 0),
                    monto_base_personal=float(data.get("monto_base_personal", 0) or 0),
                    monto_ofertado=float(data.get("monto_ofertado", 0) or 0),
                    empresa_nuestra=data.get("empresa_nuestra") or None,
                )
            except Exception:
                return None
        return None