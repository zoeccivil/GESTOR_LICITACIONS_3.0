from __future__ import annotations
from typing import Dict, Any, List, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QLabel, QLineEdit,
    QCheckBox, QComboBox, QTableWidget, QTableWidgetItem, QAbstractItemView,
    QHeaderView, QDialogButtonBox, QPushButton, QMessageBox, QStyle, QWidget
)
from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtGui import QIcon, QColor, QBrush, QFont
from typing import Dict, Any, List, Optional, Callable

# Modelos esperados
from app.core.models import Licitacion

from app.ui.dialogs.dialogo_resultados_evaluacion import DialogoResultadosEvaluacion

def _as_float(s: Any, default: float = 0.0) -> float:
    try:
        return float(s)
    except Exception:
        return default

def _as_dict(v: Any) -> Dict[str, Any]:
    return v if isinstance(v, dict) else {}

class DialogoElegirMetodoEvaluacionQt(QDialog):
    """
    Diálogo simple para elegir el método de evaluación.
    """
    def __init__(self, parent: QWidget | None = None, titulo: str = "Seleccionar Método de Evaluación") -> None:
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.setModal(True)
        self.setMinimumWidth(480)
        # Hints ventana
        self.setWindowFlags(self.windowFlags()
                            | Qt.WindowType.WindowSystemMenuHint
                            | Qt.WindowType.WindowMinimizeButtonHint
                            | Qt.WindowType.WindowMaximizeButtonHint)
        self.result: Optional[str] = None

        self.metodos = [
            "Precio Más Bajo (Cumple/No Cumple)",
            "Sistema de Puntos Absolutos (ej: 70 Tec + 30 Eco)",
            "Sistema de Puntos Ponderados (ej: 70% Tec + 30% Eco)"
        ]

        main = QVBoxLayout(self)

        lbl = QLabel("Seleccione el método de evaluación para esta licitación:")
        main.addWidget(lbl)

        self.combo = QComboBox()
        self.combo.addItems(self.metodos)
        main.addWidget(self.combo)

        buttons = QDialogButtonBox()
        btn_next = buttons.addButton("Siguiente", QDialogButtonBox.ButtonRole.AcceptRole)
        btn_cancel = buttons.addButton("Cancelar", QDialogButtonBox.ButtonRole.RejectRole)
        btn_next.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowForward))
        btn_cancel.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        main.addWidget(buttons)

    def accept(self) -> None:
        self.result = self.combo.currentText()
        super().accept()


class DialogoParametrosEvaluacionQt(QDialog):
    """
    Diálogo para definir parámetros y puntajes técnicos (globales o por lote).
    Incluye:
    - Parámetros según método
    - Checkbox 'aplicar_regla_un_lote'
    - Modo por lote con combo de lotes
    - Tabla con: Participante | Puntaje técnico | Descalificado
    - Botones: Guardar, Editar, Calcular, Cerrar
    """
    # Señal opcional si quieres escuchar desde fuera
    saved = pyqtSignal()

    COL_NOMBRE = 0
    COL_PUNTAJE = 1
    COL_DESC = 2

# Dentro de la clase DialogoParametrosEvaluacionQt, reemplaza el inicio de __init__ por este bloque:
    def __init__(self, parent: QWidget, licitacion: Licitacion, metodo_evaluacion: str) -> None:
        super().__init__(parent)
        self.licitacion = licitacion
        # parent (tab), ventana, y db
        self._tab_comp: QWidget = parent
        self._parent_win = getattr(parent, "parent_window", None)
        self._db = getattr(parent, "db", None)

        # Métodos disponibles y método actual (DEFINIR ANTES de _build_ui)
        self.metodos: list[str] = [
            "Precio Más Bajo (Cumple/No Cumple)",
            "Sistema de Puntos Absolutos (ej: 70 Tec + 30 Eco)",
            "Sistema de Puntos Ponderados (ej: 70% Tec + 30% Eco)"
        ]
        pe_in = _as_dict(getattr(self.licitacion, "parametros_evaluacion", {}))
        metodo_guardado = pe_in.get("metodo")
        self.metodo: str = metodo_evaluacion or metodo_guardado or self.metodos[0]

        self.setWindowTitle(f"Definir Parámetros: {self.metodo.split('(')[0].strip()}")
        self.setMinimumSize(900, 650)
        self.setWindowFlags(self.windowFlags()
                            | Qt.WindowType.WindowSystemMenuHint
                            | Qt.WindowType.WindowMinimizeButtonHint
                            | Qt.WindowType.WindowMaximizeButtonHint)
        self.setSizeGripEnabled(True)

        # Cargar parámetros y puntajes existentes desde pe_in
        self.parametros_existentes: Dict[str, Any] = _as_dict(pe_in.get("parametros", {}))
        self.puntajes_existentes: Dict[str, float] = {}
        for k, v in _as_dict(pe_in.get("puntajes_tecnicos", {})).items():
            k_raw = str(k).replace("➡️ ", "")
            self.puntajes_existentes[k_raw] = _as_float(v, 0.0)

        self.aplicar_regla_inicial: bool = bool(pe_in.get("aplicar_regla_un_lote", True))
        self.puntajes_por_lote_exist: Dict[str, Dict[str, float]] = _as_dict(pe_in.get("puntajes_tecnicos_por_lote", {}))

        # Participantes y lotes
        nuestras_empresas_raw = {str(e) for e in getattr(self.licitacion, "empresas_nuestras", []) if str(e).strip()}
        competidores_raw = {getattr(o, "nombre", "") for o in getattr(self.licitacion, "oferentes_participantes", []) if getattr(o, "nombre", "").strip()}
        self.participantes_raw_sorted: List[str] = sorted(
            nuestras_empresas_raw | competidores_raw,
            key=lambda s: ("0" if s in nuestras_empresas_raw else "1") + s.lower()
        )
        self.display_by_raw: Dict[str, str] = {n: (f"➡️ {n}" if n in nuestras_empresas_raw else n) for n in self.participantes_raw_sorted}
        self.lotes_ids: List[str] = [str(getattr(l, "numero", "")) for l in getattr(self.licitacion, "lotes", [])]

        # Estado en memoria
        self.editable: bool = not bool(self.parametros_existentes)
        self.modo_por_lote: bool = False
        self.puntajes_global: Dict[str, float] = {raw: float(self.puntajes_existentes.get(raw, 0.0)) for raw in self.participantes_raw_sorted}
        self.descalificados: Dict[str, bool] = {raw: False for raw in self.participantes_raw_sorted}
        try:
            fallas_inicial = {(f.get("participante_nombre") or "").replace("➡️ ", "") for f in getattr(self.licitacion, "fallas_fase_a", [])}
            for raw in self.participantes_raw_sorted:
                if raw in fallas_inicial:
                    self.descalificados[raw] = True
        except Exception:
            pass
        self.puntajes_por_lote: Dict[str, Dict[str, float]] = {}
        for lote_num, mp in self.puntajes_por_lote_exist.items():
            self.puntajes_por_lote[str(lote_num)] = {str(k).replace("➡️ ", ""): _as_float(v) for k, v in _as_dict(mp).items()}
      
        self._ui_busy: bool = False
        # Construcción UI y estado inicial
        self._build_ui()
        self._apply_editable_state()
        self._refresh_initial_mode()

    # ---------------- UI ----------------
# En _build_ui, añade un guard al inicio para asegurar self.metodo:
    def _build_ui(self) -> None:
        main = QVBoxLayout(self)
        main.setContentsMargins(12, 12, 12, 12)
        main.setSpacing(10)

        # Guard: asegurar que self.metodo existe
        if not hasattr(self, "metodo") or not self.metodo:
            # Si por algún motivo no se inicializó, usa el primero disponible
            self.metodo = self.metodos[0] if hasattr(self, "metodos") and self.metodos else "Precio Más Bajo (Cumple/No Cumple)"
            # 1) Fila superior: Método de Evaluación (permite cambiar y refrescar el diálogo)
        top_row = QHBoxLayout()
        lbl_met = QLabel("Método de Evaluación:")
        self.combo_metodo = QComboBox()
        self.combo_metodo.addItems(self.metodos)
        # Selección inicial coherente con self.metodo
        idx = self.combo_metodo.findText(self.metodo)
        self.combo_metodo.setCurrentIndex(idx if idx >= 0 else 0)
        self.combo_metodo.currentIndexChanged.connect(self._on_metodo_changed)
        top_row.addWidget(lbl_met)
        top_row.addWidget(self.combo_metodo, 1)
        main.addLayout(top_row)

        # 2) Sección: Parámetros (reconstruible según método)
        self.grp_params = QGroupBox("1. Parámetros de Evaluación")
        self.frm_params = QFormLayout(self.grp_params)  # guardamos referencia para reconstruir dinámicamente
        self.frm_params.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        self.inputs_params: Dict[str, QLineEdit] = {}
        self._params_map: Dict[str, str] = {}

        # Checkbox de regla (instancia única, se reubica al final de la sección)
        self.chk_regla = QCheckBox("Aplicar regla de adjudicación a un único lote (por oferente)")
        self.chk_regla.setChecked(self.aplicar_regla_inicial)

        # Población inicial de la sección de parámetros según self.metodo
        self._populate_params_section()
        main.addWidget(self.grp_params)

        # 3) Sección: modo por lote (combo siempre habilitado; cambiar lote activa modo por-lote)
        mode_row = QHBoxLayout()
        self.chk_modo_lote = QCheckBox("Evaluar técnicamente por LOTE")
        self.chk_modo_lote.stateChanged.connect(self._on_toggle_modo_lote)
        mode_row.addWidget(self.chk_modo_lote)

        mode_row.addWidget(QLabel("  Lote:"))
        self.combo_lote = QComboBox()
        # Cargar lista de lotes
        self.combo_lote.addItems(self.lotes_ids)
        # Dejar SIEMPRE habilitado si hay lotes
        self.combo_lote.setEnabled(bool(self.lotes_ids))
        self.combo_lote.setToolTip("Seleccione un lote para asignar puntajes por-lote. Al cambiar de lote se activará el modo por-lote.")
        # Al cambiar de lote, si el modo no está activo, lo activamos automáticamente
        self.combo_lote.currentIndexChanged.connect(self._on_lote_changed)
        mode_row.addWidget(self.combo_lote)
        mode_row.addStretch(1)
        main.addLayout(mode_row)

        # 4) Tabla de puntajes / descalificación
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Participante", "Puntaje Técnico", "Descalificado"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.SelectedClicked)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(self.COL_NOMBRE, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(self.COL_PUNTAJE, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(self.COL_DESC, QHeaderView.ResizeMode.ResizeToContents)
        main.addWidget(self.table, stretch=1)

        # Conexiones de edición de tabla
        self.table.itemChanged.connect(self._on_item_changed)

        # 5) Botonera inferior
        self.btns = QDialogButtonBox()
        self.btn_guardar = self.btns.addButton("Guardar Parámetros", QDialogButtonBox.ButtonRole.ActionRole)
        self.btn_editar = self.btns.addButton("Editar", QDialogButtonBox.ButtonRole.ActionRole)
        self.btn_calcular = self.btns.addButton("Calcular y Ver Resultados", QDialogButtonBox.ButtonRole.ActionRole)
        self.btn_cerrar = self.btns.addButton("Cerrar", QDialogButtonBox.ButtonRole.RejectRole)

        style = self.style()
        self.btn_guardar.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        self.btn_editar.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        self.btn_calcular.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        self.btn_cerrar.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton))

        self.btn_guardar.clicked.connect(self._on_save)
        self.btn_editar.clicked.connect(lambda: self._toggle_edit(True))
        self.btn_calcular.clicked.connect(self._on_calcular)
        self.btns.rejected.connect(self.reject)
        main.addWidget(self.btns)
    # ------------- Tabla y modos -------------
    def _fill_table_global(self) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        for raw in self.participantes_raw_sorted:
            display = self.display_by_raw.get(raw, raw)
            puntaje = self.puntajes_global.get(raw, 0.0)
            desc = self.descalificados.get(raw, False)
            self._append_row(display, puntaje, desc, user_raw=raw)
        self.table.blockSignals(False)

    def _fill_table_lote(self, lote_num: str) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        for p in self._filtrar_participantes_por_lote(lote_num):
            raw = p["raw"]
            display = p["display"]
            # valor por-lote existente o global como fallback
            puntaje = self.puntajes_por_lote.get(lote_num, {}).get(raw, self.puntajes_global.get(raw, 0.0))
            desc = self.descalificados.get(raw, False)
            self._append_row(display, puntaje, desc, user_raw=raw)
        self.table.blockSignals(False)

    def _append_row(self, display: str, puntaje: float, descalificado: bool, user_raw: str) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)

        it_nombre = QTableWidgetItem(display)
        it_nombre.setData(Qt.ItemDataRole.UserRole, user_raw)
        it_nombre.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        self.table.setItem(row, self.COL_NOMBRE, it_nombre)

        it_puntaje = QTableWidgetItem(f"{float(puntaje):.2f}")
        it_puntaje.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        # Editable solo si estado editable
        flags = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        if self.editable:
            flags |= Qt.ItemFlag.ItemIsEditable
        it_puntaje.setFlags(flags)
        self.table.setItem(row, self.COL_PUNTAJE, it_puntaje)

        it_desc = QTableWidgetItem("Sí" if descalificado else "No")
        it_desc.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        it_desc.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        it_desc.setCheckState(Qt.CheckState.Checked if descalificado else Qt.CheckState.Unchecked)
        self.table.setItem(row, self.COL_DESC, it_desc)

        # Color fila si descalificado
        self._apply_row_style(row, descalificado)

    def _apply_row_style(self, row: int, descalificado: bool) -> None:
        bg = QBrush(QColor("#F5F5F5")) if descalificado else QBrush()
        for c in range(self.table.columnCount()):
            it = self.table.item(row, c)
            if it:
                it.setBackground(bg)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if item.column() == self.COL_PUNTAJE:
            raw = self.table.item(item.row(), self.COL_NOMBRE).data(Qt.ItemDataRole.UserRole)
            val = _as_float(item.text(), 0.0)
            if self.modo_por_lote:
                lote = self.combo_lote.currentText()
                self.puntajes_por_lote.setdefault(lote, {})[raw] = val
            else:
                self.puntajes_global[raw] = val
        elif item.column() == self.COL_DESC:
            raw = self.table.item(item.row(), self.COL_NOMBRE).data(Qt.ItemDataRole.UserRole)
            desc = item.checkState() == Qt.CheckState.Checked
            self.descalificados[raw] = desc
            self._apply_row_style(item.row(), desc)

    # ------------ Modo por lote / edición ------------
    def _on_toggle_modo_lote(self, state: int) -> None:
        self.modo_por_lote = state == Qt.CheckState.Checked.value
        self.combo_lote.setEnabled(self.modo_por_lote)
        if self.modo_por_lote:
            self._fill_table_lote(self.combo_lote.currentText() if self.combo_lote.count() else "")
        else:
            self._fill_table_global()

    def _on_lote_changed(self) -> None:
        if self.modo_por_lote:
            self._fill_table_lote(self.combo_lote.currentText())

    def _apply_editable_state(self) -> None:
        """
        Aplica el estado de edición a entradas y tabla.
        Debe llamarse solo después de _build_ui (cuando todos los widgets existen).
        """
        # Entradas de parámetros
        for key, edit in self.inputs_params.items():
            try:
                edit.setReadOnly(not self.editable)
            except Exception:
                pass
        try:
            self.chk_regla.setEnabled(self.editable)
        except Exception:
            pass

        # El check/combobox de modo por lote puede no existir si se llama muy temprano
        chk_modo = getattr(self, "chk_modo_lote", None)
        combo_lote = getattr(self, "combo_lote", None)
        if chk_modo is not None:
            try:
                chk_modo.setEnabled(True)  # siempre visible; la edición va en las celdas
            except Exception:
                pass
        if combo_lote is not None:
            try:
                combo_lote.setEnabled(bool(self.lotes_ids))
            except Exception:
                pass

        # Tabla: habilitar/deshabilitar edición de la columna de puntaje
        if getattr(self, "table", None) is not None:
            for r in range(self.table.rowCount()):
                it = self.table.item(r, self.COL_PUNTAJE)
                if it:
                    flags = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
                    if self.editable:
                        flags |= Qt.ItemFlag.ItemIsEditable
                    it.setFlags(flags)
                itd = self.table.item(r, self.COL_DESC)
                if itd:
                    flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsSelectable
                    if not self.editable:
                        # en no editable, solo lectura (no user check)
                        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
                    itd.setFlags(flags)

        # Botones
        try:
            self.btn_guardar.setEnabled(self.editable)
            self.btn_editar.setEnabled(not self.editable)
            self.btn_calcular.setEnabled(not self.editable)
        except Exception:
            pass

    def _toggle_edit(self, on: bool) -> None:
        self.editable = on
        self._apply_editable_state()

    def _clear_form_layout(self, lay: QFormLayout) -> None:
        """
        Elimina TODAS las filas de un QFormLayout de forma segura:
        - Destruye los widgets (deleteLater)
        - Remueve la fila con removeRow para que rowCount disminuya
        """
        try:
            while lay.rowCount() > 0:
                row = lay.rowCount() - 1
                lbl_item = lay.itemAt(row, QFormLayout.ItemRole.LabelRole)
                fld_item = lay.itemAt(row, QFormLayout.ItemRole.FieldRole)
                if lbl_item:
                    w = lbl_item.widget()
                    if w:
                        w.deleteLater()
                if fld_item:
                    w = fld_item.widget()
                    if w:
                        w.deleteLater()
                lay.removeRow(row)
        except Exception as e:
            print(f"[WARN] _clear_form_layout: {e}")

    def _populate_params_section(self) -> None:
        """
        Reconstruye los campos de parámetros según el método actual (self.metodo).
        Crea SIEMPRE un nuevo checkbox de regla preservando el estado previo.
        """
        # Conservar el estado previo del checkbox (si existía)
        prev_checked = False
        try:
            if hasattr(self, "chk_regla") and self.chk_regla is not None:
                prev_checked = bool(self.chk_regla.isChecked())
            else:
                prev_checked = bool(self.aplicar_regla_inicial)
        except Exception:
            prev_checked = bool(getattr(self, "aplicar_regla_inicial", True))

        # Limpiar layout
        self._clear_form_layout(self.frm_params)
        self.inputs_params.clear()
        self._params_map.clear()

        # Mapas por método y defaults
        defaults: Dict[str, str] = {}
        if "Puntos Absolutos" in self.metodo:
            self._params_map = {
                "Puntaje Técnico Máximo:": "puntaje_tec_max",
                "Puntaje Técnico Mínimo para Calificar:": "puntaje_tec_min",
                "Puntaje Económico Máximo:": "puntaje_eco_max",
            }
            defaults = {"puntaje_tec_max": "70", "puntaje_tec_min": "49", "puntaje_eco_max": "30"}
        elif "Puntos Ponderados" in self.metodo:
            self._params_map = {
                "Puntaje Técnico Mínimo para Calificar (base 100):": "puntaje_tec_min",
                "Ponderación Técnica (%):": "pond_tec",
                "Ponderación Económica (%):": "pond_eco",
            }
            defaults = {"puntaje_tec_min": "70", "pond_tec": "70", "pond_eco": "30"}
        else:
            # Precio Más Bajo
            lbl = QLabel("Este método no requiere parámetros adicionales.")
            self.frm_params.addRow(lbl)

        # Campos si aplican
        for label, key in self._params_map.items():
            val = str(self.parametros_existentes.get(key, defaults.get(key, "")))
            edit = QLineEdit(val)
            edit.setFixedWidth(120)
            self.inputs_params[key] = edit
            self.frm_params.addRow(QLabel(label), edit)

        # Crear un NUEVO checkbox cada vez y reinsertarlo
        self.chk_regla = QCheckBox("Aplicar regla de adjudicación a un único lote (por oferente)")
        self.chk_regla.setChecked(prev_checked)
        self.frm_params.addRow(self.chk_regla)
        # NOTA: _apply_editable_state se invoca fuera (p.ej. al final de _on_metodo_changed)

    def _on_metodo_changed(self) -> None:
        if getattr(self, "_ui_busy", False):
            return
        self._ui_busy = True
        try:
            nuevo = self.combo_metodo.currentText()
            if not nuevo or nuevo == getattr(self, "metodo", ""):
                return

            print(f"[DEBUG] Cambio de método: '{getattr(self, 'metodo', '')}' -> '{nuevo}'")

            # Actualizar estado interno y del modelo
            self.metodo = nuevo
            pe = _as_dict(getattr(self.licitacion, "parametros_evaluacion", {}))
            pe["metodo"] = nuevo
            pe["parametros"] = {}  # resetea solo el bloque de parámetros
            self.licitacion.parametros_evaluacion = pe
            self.parametros_existentes = {}

            # Actualizar título
            self.setWindowTitle(f"Definir Parámetros: {nuevo.split('(')[0].strip()}")

            # Repoblar sección de parámetros y reaplicar editable
            self._populate_params_section()
            self._apply_editable_state()

            # Mantener vista de tabla según modo
            if self.modo_por_lote and getattr(self, "combo_lote", None) and self.combo_lote.count():
                self._fill_table_lote(self.combo_lote.currentText())
            else:
                self._fill_table_global()

        finally:
            self._ui_busy = False
    # --------- Guardar y Calcular ----------
    def _on_save(self) -> None:
        # 1) Validación
        try:
            # validar params
            for key, edit in self.inputs_params.items():
                _ = float(edit.text().strip())
            # validar puntajes
            def _validate_map(mp: Dict[str, float]) -> None:
                for k, v in mp.items():
                    _ = float(v)
            _validate_map(self.puntajes_global)
            if self.modo_por_lote:
                for lote, mp in self.puntajes_por_lote.items():
                    _validate_map(mp)
        except Exception:
            QMessageBox.critical(self, "Error de Validación", "Todos los parámetros y puntajes deben ser numéricos válidos.")
            return

        # 2) Actualizar fallas/descalificados en licitación (manual)
        try:
            existentes = getattr(self.licitacion, "fallas_fase_a", [])
            # Limpiar solo los manuales (documento_id == -1)
            existentes = [f for f in existentes if f.get("documento_id") != -1]
            for raw, estado in self.descalificados.items():
                if estado:
                    existentes.append({
                        "participante_nombre": raw,
                        "documento_id": -1,
                        "comentario": "Descalificado manualmente desde el evaluador.",
                        "es_nuestro": raw in {str(e) for e in getattr(self.licitacion, "empresas_nuestras", [])}
                    })
            self.licitacion.fallas_fase_a = existentes
        except Exception as e:
            print(f"[DialogoParametrosEvaluacionQt] WARN al escribir fallas_fase_a: {e}")

        # 3) Armar parametros_evaluacion
        parametros = {key: float(edit.text().strip()) for key, edit in self.inputs_params.items()}
        pe: Dict[str, Any] = {
            "metodo": self.metodo,
            "parametros": parametros,
            "puntajes_tecnicos": {raw: float(val) for raw, val in self.puntajes_global.items()},
            "aplicar_regla_un_lote": bool(self.chk_regla.isChecked())
        }
        if self.puntajes_por_lote:
            pe["puntajes_tecnicos_por_lote"] = {
                str(lote): {raw: float(val) for raw, val in mp.items()} for lote, mp in self.puntajes_por_lote.items()
            }
        else:
            # conservar si existían en el dict original
            old = _as_dict(getattr(self.licitacion, "parametros_evaluacion", {}))
            if "puntajes_tecnicos_por_lote" in old:
                pe["puntajes_tecnicos_por_lote"] = old["puntajes_tecnicos_por_lote"]

        self.licitacion.parametros_evaluacion = pe

        # 4) Guardar en BD
        try:
            if self._db is None:
                raise RuntimeError("DB adapter no disponible desde el tab.")
            self._db.save_licitacion(self.licitacion)
            self._toggle_edit(False)
            self.saved.emit()
            QMessageBox.information(self, "Guardado", "Parámetros y puntajes guardados. Ahora puede calcular los resultados.")
            print("[DEBUG] parámetros_evaluación guardados:", pe)
        except Exception as e:
            QMessageBox.critical(self, "Error al Guardar", f"No se pudieron guardar cambios:\n{e}")

    def _on_calcular(self) -> None:
        datos = _as_dict(getattr(self.licitacion, "parametros_evaluacion", {}))
        if not datos:
            QMessageBox.warning(self, "Faltan datos", "Primero guarda los parámetros de evaluación.")
            return

        # 1) Intentar encontrar método de cálculo en diferentes contenedores y con nombres alternativos
        calc_names = ["_calcular_resultados_evaluacion", "calcular_resultados_evaluacion"]
        rule_names = ["_aplicar_regla_un_lote_por_oferente", "aplicar_regla_un_lote_por_oferente"]

        contenedores = [self._parent_win, self._tab_comp, self.window()]
        calc_fn = None
        for obj in contenedores:
            calc_fn = self._find_method(obj, calc_names)
            if calc_fn:
                break

        # 2) Calcular resultados
        resultados_por_lote: Dict[str, List[Dict[str, Any]]] = {}
        if calc_fn:
            try:
                resultados_por_lote = calc_fn(datos)  # tipo esperado: Dict[str, List[Dict]]
                print("[DEBUG] _on_calcular: cálculo delegado OK. lotes:", list(resultados_por_lote.keys()))
            except Exception as e:
                QMessageBox.critical(self, "Error de Cálculo", f"Fallo en el método de cálculo:\n{e}")
                return
        else:
            # Fallbacks locales por método cuando no existe el método oficial en la ventana principal
            metodo = str(datos.get("metodo", self.metodo))
            if "Precio Más Bajo" in metodo:
                resultados_por_lote = self._calc_local_precio_mas_bajo(datos)
                if not resultados_por_lote:
                    QMessageBox.information(self, "Sin Datos", "No hay ofertas válidas para evaluar en ningún lote.")
                    return
                print("[DEBUG] _on_calcular: usando fallback local 'Precio Más Bajo'")
            elif "Puntos Absolutos" in metodo:
                resultados_por_lote = self._calc_local_puntos_absolutos(datos)
                if not resultados_por_lote:
                    QMessageBox.information(self, "Sin Datos", "No hay ofertas válidas para evaluar en ningún lote.")
                    return
                print("[DEBUG] _on_calcular: usando fallback local 'Puntos Absolutos'")
            elif "Puntos Ponderados" in metodo:
                resultados_por_lote = self._calc_local_puntos_ponderados(datos)
                if not resultados_por_lote:
                    QMessageBox.information(self, "Sin Datos", "No hay ofertas válidas para evaluar en ningún lote.")
                    return
                print("[DEBUG] _on_calcular: usando fallback local 'Puntos Ponderados'")
            else:
                QMessageBox.information(self, "No Disponible",
                                        "No se encontró el método de cálculo en la ventana principal.")
                return

        if not resultados_por_lote:
            QMessageBox.information(self, "Sin Datos", "No hay ofertas válidas para evaluar en ningún lote.")
            return

        # 3) Regla de 1 lote por oferente
        adjudicados = None
        aplicar_regla = bool(datos.get("aplicar_regla_un_lote", True))
        if aplicar_regla:
            rule_fn = None
            for obj in contenedores:
                rule_fn = self._find_method(obj, rule_names)
                if rule_fn:
                    break
            if rule_fn:
                try:
                    res_rule = rule_fn(resultados_por_lote, lots_min_excepcion=None, campo_cuantia="monto_base_personal")
                    # algunos retornan (adjudicados, resultados_anotados), otros solo resultados
                    if isinstance(res_rule, tuple) and len(res_rule) == 2:
                        adjudicados, resultados_por_lote = res_rule
                    elif isinstance(res_rule, dict):
                        resultados_por_lote = res_rule
                    print("[DEBUG] _on_calcular: regla 1-lote aplicada por método delegado.")
                except Exception as e:
                    print(f"[WARN] Regla delegada falló: {e}. Usando fallback simple.")
                    resultados_por_lote = self._aplicar_regla_un_lote_simple(resultados_por_lote)
            else:
                resultados_por_lote = self._aplicar_regla_un_lote_simple(resultados_por_lote)
                print("[DEBUG] _on_calcular: regla 1-lote aplicada localmente (fallback).")

# Dentro de _on_calcular(), reemplaza el bloque "mostrar resultados" por esto:

        # 4) Mostrar resultados
        dlg_res = DialogoResultadosEvaluacion(
            self,                     # parent (TabCompetitors)
            self.licitacion,
            resultados_por_lote,
            adjudicados=adjudicados,
            metodo=str(datos.get("metodo", self.metodo)),
            datos_param=datos
        )
        dlg_res.exec()
    # ------------- Lógica de filtro por lote (similar a Tk) -------------
    def _filtrar_participantes_por_lote(self, lote_num_str: str) -> List[Dict[str, str]]:
        res: List[Dict[str, str]] = []
        nuestras_empresas_raw = {str(e) for e in getattr(self.licitacion, "empresas_nuestras", [])}

        # Nuestra oferta del lote
        for l in getattr(self.licitacion, "lotes", []):
            if str(getattr(l, "numero", "")) == lote_num_str and getattr(l, "participamos", False) and getattr(l, "fase_A_superada", False) and float(getattr(l, "monto_ofertado", 0) or 0) > 0:
                nombre = f"➡️ {getattr(l, 'empresa_nuestra', None) or 'Nuestra Oferta'}"
                raw = getattr(l, "empresa_nuestra", None) or "Nuestra Oferta"
                res.append({"display": nombre, "raw": raw})

        # Competidores con oferta válida en ese lote
        for of in getattr(self.licitacion, "oferentes_participantes", []):
            for oferta in getattr(of, "ofertas_por_lote", []):
                if str(oferta.get("lote_numero")) == lote_num_str and bool(oferta.get("paso_fase_A", False)):
                    if getattr(of, "nombre", "") not in nuestras_empresas_raw:
                        res.append({"display": getattr(of, "nombre", ""), "raw": getattr(of, "nombre", "")})

        res = [r for r in res if r["display"]]
        res.sort(key=lambda x: x["display"])
        return res
    
    def _find_method(self, obj: Any, candidates: List[str]) -> Optional[Callable]:
        """Devuelve el primer método callable encontrado en 'obj' con alguno de los nombres en candidates."""
        if obj is None:
            return None
        for name in candidates:
            fn = getattr(obj, name, None)
            if callable(fn):
                print(f"[DEBUG] Método encontrado: {type(obj).__name__}.{name}")
                return fn
        return None

    def _calc_local_precio_mas_bajo(self, datos: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fallback local: calcula por lote el ganador a menor precio entre ofertas válidas.
        Respeta 'descalificados' manuales y 'paso_fase_A' si está en la matriz.
        Estructura devuelta: { lote_num: [ {participante, monto, califica_tecnicamente, es_ganador}, ... ] }
        """
        print("[DEBUG] Fallback local: _calc_local_precio_mas_bajo")
        try:
            matriz = self.licitacion.get_matriz_ofertas()
        except Exception as e:
            print(f"[ERROR] Fallback: get_matriz_ofertas falló: {e}")
            return {}

        resultados: Dict[str, List[Dict[str, Any]]] = {}
        for lote_num, ofertas_lote in matriz.items():
            fila: List[Dict[str, Any]] = []
            for participante, d in ofertas_lote.items():
                monto = d.get("monto", 0.0) or 0.0
                pasoA = bool(d.get("paso_fase_A", True))  # si no viene el flag, asumimos True
                # limpiar "➡️ " si venía desde matriz (normalmente no)
                raw = participante.replace("➡️ ", "")
                desc = bool(self.descalificados.get(raw, False))
                califica = pasoA and not desc and isinstance(monto, (int, float)) and monto > 0
                fila.append({
                    "participante": participante,
                    "monto": float(monto) if isinstance(monto, (int, float)) else 0.0,
                    "califica_tecnicamente": califica,
                    "es_ganador": False
                })
            # elegir ganador por menor monto entre los que califican
            calificados = [r for r in fila if r["califica_tecnicamente"] and r["monto"] > 0]
            if calificados:
                ganador = min(calificados, key=lambda r: r["monto"])
                for r in fila:
                    if r is ganador:
                        r["es_ganador"] = True
            # ordenar por monto asc
            fila.sort(key=lambda r: (0 if r["califica_tecnicamente"] else 1, r["monto"]))
            resultados[str(lote_num)] = fila
            print(f"[DEBUG] Fallback: lote {lote_num}, total ofertas={len(fila)}, calificados={len(calificados)}")
        return resultados

    def _aplicar_regla_un_lote_simple(self, resultados_por_lote: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Regla codiciosa simple: a cada lote se le asigna el primer oferente calificado que aún no ha sido adjudicado en otro lote.
        Recorre lotes en orden ascendente.
        """
        print("[DEBUG] Fallback local: _aplicar_regla_un_lote_simple")
        usados: set[str] = set()
        out: Dict[str, List[Dict[str, Any]]] = {}
        for lote_num in sorted(resultados_por_lote.keys(), key=lambda s: int(s) if str(s).isdigit() else str(s)):
            fila = [dict(r) for r in resultados_por_lote[lote_num]]  # copia superficial
            # limpiar marcas previas
            for r in fila:
                r["es_ganador"] = False
            asignado = False
            for r in fila:
                raw = r["participante"].replace("➡️ ", "")
                if r["califica_tecnicamente"] and raw not in usados:
                    r["es_ganador"] = True
                    usados.add(raw)
                    asignado = True
                    break
            if not asignado:
                # si todos usados, dejar al mejor calificado aunque repita (como fallback)
                for r in fila:
                    if r["califica_tecnicamente"]:
                        r["es_ganador"] = True
                        break
            out[lote_num] = fila
        return out
    
# Dentro de la clase DialogoParametrosEvaluacionQt, debajo de _find_method y _calc_local_precio_mas_bajo,
# AÑADE estos helpers de extracción de puntajes y los fallback nuevos:

    def _extract_scores_from_datos(self, datos: Dict[str, Any]) -> tuple[Dict[str, float], Dict[str, Dict[str, float]]]:
        """
        Devuelve (puntajes_global, puntajes_por_lote) a partir de 'datos' (self.licitacion.parametros_evaluacion)
        con fallback a los mapas en memoria del diálogo si no están en 'datos'.
        """
        pe = datos or {}
        glob = {str(k).replace("➡️ ", ""): _as_float(v) for k, v in _as_dict(pe.get("puntajes_tecnicos", {})).items()}
        por_lote_raw = _as_dict(pe.get("puntajes_tecnicos_por_lote", {}))
        por_lote: Dict[str, Dict[str, float]] = {}
        for lote_num, mp in por_lote_raw.items():
            por_lote[str(lote_num)] = {str(k).replace("➡️ ", ""): _as_float(v) for k, v in _as_dict(mp).items()}

        # Fallback a estado del diálogo si no hay info en 'datos'
        if not glob and hasattr(self, "puntajes_global"):
            glob = {str(k): float(v) for k, v in getattr(self, "puntajes_global", {}).items()}
        if not por_lote and hasattr(self, "puntajes_por_lote"):
            por_lote = {str(ln): {str(k): float(v) for k, v in mp.items()} for ln, mp in getattr(self, "puntajes_por_lote", {}).items()}
        return glob, por_lote

    def _get_score_for(self, raw: str, lote: str, glob: Dict[str, float], por_lote: Dict[str, Dict[str, float]]) -> float:
        """Obtiene el puntaje técnico para 'raw' en 'lote' si existe por-lote; si no, global; si no, 0."""
        raw = str(raw)
        if lote in por_lote and raw in por_lote[lote]:
            return float(por_lote[lote][raw])
        return float(glob.get(raw, 0.0))

    def _calc_local_puntos_absolutos(self, datos: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fallback local para 'Sistema de Puntos Absolutos':
        - total = tec_cap + eco
        - tec_cap = min(tec, puntaje_tec_max)
        - eco = puntaje_eco_max * (min_precio_que_califica / precio_oferta), solo si califica (tec >= tec_min y paso A y no descalificado)
        - ganador: mayor total; empate -> menor precio
        """
        print("[DEBUG] Fallback local: _calc_local_puntos_absolutos")
        params = _as_dict(datos.get("parametros", {}))
        tec_max = _as_float(params.get("puntaje_tec_max", 70))
        tec_min = _as_float(params.get("puntaje_tec_min", 49))
        eco_max = _as_float(params.get("puntaje_eco_max", 30))

        glob, por_lote = self._extract_scores_from_datos(datos)

        try:
            matriz = self.licitacion.get_matriz_ofertas()
        except Exception as e:
            print(f"[ERROR] Fallback absolutos: get_matriz_ofertas falló: {e}")
            return {}

        resultados: Dict[str, List[Dict[str, Any]]] = {}
        for lote_num, ofertas_lote in matriz.items():
            lote_key = str(lote_num)
            filas: List[Dict[str, Any]] = []
            # Precalcular calificados y precio mínimo entre calificados
            prelim: List[Dict[str, Any]] = []
            for participante, d in ofertas_lote.items():
                price = float(d.get("monto", 0.0) or 0.0)
                pasoA = bool(d.get("paso_fase_A", True))
                raw = participante.replace("➡️ ", "")
                desc = bool(self.descalificados.get(raw, False))
                tec = self._get_score_for(raw, lote_key, glob, por_lote)
                tec_cap = min(max(tec, 0.0), tec_max)
                califica = pasoA and not desc and tec_cap >= tec_min and price > 0
                prelim.append({
                    "participante": participante,
                    "raw": raw,
                    "monto": price,
                    "tec": tec_cap,
                    "califica_tecnicamente": califica
                })
            calificados = [r for r in prelim if r["califica_tecnicamente"]]
            min_price = min([r["monto"] for r in calificados], default=0.0)

            # Completar filas con eco y total
            for r in prelim:
                eco_pts = (eco_max * (min_price / r["monto"])) if (r["califica_tecnicamente"] and r["monto"] > 0 and min_price > 0) else 0.0
                total = r["tec"] + eco_pts
                filas.append({
                    "participante": r["participante"],
                    "monto": r["monto"],
                    "tec": r["tec"],
                    "eco": eco_pts,
                    "total": total,
                    "califica_tecnicamente": r["califica_tecnicamente"],
                    "es_ganador": False
                })

            # elegir ganador por mayor total; empate: menor precio
            candidatos = [f for f in filas if f["califica_tecnicamente"]]
            if candidatos:
                ganador = sorted(candidatos, key=lambda x: (-x["total"], x["monto"]))[0]
                for f in filas:
                    if f is ganador:
                        f["es_ganador"] = True

            # ordenar por total desc y luego precio
            filas.sort(key=lambda x: (0 if x["califica_tecnicamente"] else 1, -x["total"], x["monto"]))
            resultados[lote_key] = filas
            print(f"[DEBUG] Fallback absolutos: lote {lote_key}, calificados={len(candidatos)}, min_price={min_price}")
        return resultados

    def _calc_local_puntos_ponderados(self, datos: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fallback local para 'Sistema de Puntos Ponderados':
        - Tec%: se asume puntaje técnico en base 100; se trunca a [0, 100]
        - Eco% = 100 * (min_precio_que_califica / precio_oferta) para calificados
        - Total = Tec% * (pond_tec/100) + Eco% * (pond_eco/100)
        - Califica si Tec% >= puntaje_tec_min (base 100), paso A y no descalificado
        """
        print("[DEBUG] Fallback local: _calc_local_puntos_ponderados")
        params = _as_dict(datos.get("parametros", {}))
        tec_min = _as_float(params.get("puntaje_tec_min", 70))
        pond_tec = _as_float(params.get("pond_tec", 70))
        pond_eco = _as_float(params.get("pond_eco", 30))

        glob, por_lote = self._extract_scores_from_datos(datos)

        try:
            matriz = self.licitacion.get_matriz_ofertas()
        except Exception as e:
            print(f"[ERROR] Fallback ponderados: get_matriz_ofertas falló: {e}")
            return {}

        resultados: Dict[str, List[Dict[str, Any]]] = {}
        for lote_num, ofertas_lote in matriz.items():
            lote_key = str(lote_num)
            prelim: List[Dict[str, Any]] = []
            for participante, d in ofertas_lote.items():
                price = float(d.get("monto", 0.0) or 0.0)
                pasoA = bool(d.get("paso_fase_A", True))
                raw = participante.replace("➡️ ", "")
                desc = bool(self.descalificados.get(raw, False))
                tec_pct = self._get_score_for(raw, lote_key, glob, por_lote)
                tec_pct = max(0.0, min(tec_pct, 100.0))
                califica = pasoA and not desc and tec_pct >= tec_min and price > 0
                prelim.append({
                    "participante": participante,
                    "raw": raw,
                    "monto": price,
                    "tec_pct": tec_pct,
                    "califica_tecnicamente": califica
                })
            calificados = [r for r in prelim if r["califica_tecnicamente"]]
            min_price = min([r["monto"] for r in calificados], default=0.0)

            filas: List[Dict[str, Any]] = []
            for r in prelim:
                eco_pct = (100.0 * (min_price / r["monto"])) if (r["califica_tecnicamente"] and r["monto"] > 0 and min_price > 0) else 0.0
                total = (r["tec_pct"] * (pond_tec / 100.0)) + (eco_pct * (pond_eco / 100.0))
                filas.append({
                    "participante": r["participante"],
                    "monto": r["monto"],
                    "tec_pct": r["tec_pct"],
                    "eco_pct": eco_pct,
                    "total": total,
                    "califica_tecnicamente": r["califica_tecnicamente"],
                    "es_ganador": False
                })

            candidatos = [f for f in filas if f["califica_tecnicamente"]]
            if candidatos:
                ganador = sorted(candidatos, key=lambda x: (-x["total"], x["monto"]))[0]
                for f in filas:
                    if f is ganador:
                        f["es_ganador"] = True

            filas.sort(key=lambda x: (0 if x["califica_tecnicamente"] else 1, -x["total"], x["monto"]))
            resultados[lote_key] = filas
            print(f"[DEBUG] Fallback ponderados: lote {lote_key}, calificados={len(candidatos)}, min_price={min_price}")
        return resultados
    
# Añade estos métodos dentro de la clase DialogoParametrosEvaluacionQt

    def _refresh_initial_mode(self) -> None:
        """
        Configura el estado inicial de 'modo por lote':
        - Si ya hay puntajes_por_lote_exist, activar el modo por-lote.
        - Si no, arrancar en global pero permitir elegir lote y auto-activar al cambiar.
        """
        has_per_lote = bool(self.puntajes_por_lote_exist)
        if self.combo_lote.count() > 0 and self.combo_lote.currentIndex() < 0:
            self.combo_lote.setCurrentIndex(0)
        # Activar modo por-lote si existen puntajes guardados por-lote
        self.chk_modo_lote.setChecked(has_per_lote)
        # Forzar refresco de tabla acorde al modo
        if has_per_lote:
            self._on_toggle_modo_lote(self.chk_modo_lote.checkState().value)
        else:
            # Modo global por defecto
            self.modo_por_lote = False
            self.combo_lote.setEnabled(True)  # siempre habilitado
            self._fill_table_global()

    def _on_lote_changed(self) -> None:
        """
        Cuando el usuario cambia el lote en el combo:
        - Si aún no está en modo por-lote, activar el modo por-lote automáticamente.
        - Si ya está en modo por-lote, refrescar la tabla del lote seleccionado.
        """
        if not self.combo_lote.count():
            return
        current_lote = self.combo_lote.currentText()
        if not current_lote:
            return
        if not self.modo_por_lote:
            print("[DEBUG] Activando modo por-lote al cambiar el combo de Lote.")
            # Esto disparará _on_toggle_modo_lote y luego refrescará
            self.chk_modo_lote.setChecked(True)
            return
        # Si ya estamos en modo por-lote, simplemente refrescar tabla del lote actual
        self._fill_table_lote(current_lote)

    def _on_toggle_modo_lote(self, state: int) -> None:
        """
        Activa/desactiva el modo por-lote.
        - El combo de Lote permanece habilitado para permitir cambiar de lote siempre.
        - Al activar, carga la tabla específica del lote seleccionado.
        - Al desactivar, se vuelve a la vista global.
        """
        self.modo_por_lote = (state == Qt.CheckState.Checked.value)
        # Combo SIEMPRE habilitado (requisito), pero aquí aseguramos que haya selección
        if self.combo_lote.count() and self.combo_lote.currentIndex() < 0:
            self.combo_lote.setCurrentIndex(0)

        if self.modo_por_lote:
            current_lote = self.combo_lote.currentText() if self.combo_lote.count() else ""
            print(f"[DEBUG] Modo por-lote ACTIVADO. Lote actual: {current_lote}")
            self._fill_table_lote(current_lote)
        else:
            print("[DEBUG] Modo por-lote DESACTIVADO. Volviendo a puntajes globales.")
            self._fill_table_global()
        # Reaplicar estado editable a celdas según el modo actual
        self._apply_editable_state()