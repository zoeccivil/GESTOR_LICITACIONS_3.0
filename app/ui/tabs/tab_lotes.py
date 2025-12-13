from __future__ import annotations
import locale
import time
from typing import TYPE_CHECKING, List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QAbstractItemView, QMessageBox, QStyle, QDialog,
    QLabel
)
from PyQt6.QtCore import Qt, QModelIndex
from PyQt6.QtGui import QIcon, QColor, QFont

from app.core.models import Licitacion, Lote
from app.core.db_adapter import DatabaseAdapter

from app.ui.dialogs.dialogo_gestionar_lote import DialogoLoteForm

if TYPE_CHECKING:
    from app.ui.windows.licitation_details_window import LicitationDetailsWindow

# Locale
try:
    locale.setlocale(locale.LC_ALL, '')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'es_ES.UTF-8')
    except locale.Error:
        print("Advertencia: No se pudo establecer la localización para formato de moneda.")

from app.core.utils import normalize_lote_numero



class TabLotes(QWidget):
    COL_PARTICIPAR = 0
    COL_FASE_A = 1
    COL_NUMERO = 2
    COL_NOMBRE = 3
    COL_MONTO_BASE = 4
    COL_MONTO_PERSONAL = 5
    COL_MONTO_OFERTADO = 6
    COL_DIF_LIC = 7
    COL_DIF_PERS = 8
    COL_EMPRESA = 9

    def __init__(self, licitacion: Licitacion, db: DatabaseAdapter, parent_window: LicitationDetailsWindow):
        super().__init__(parent_window)
        self.licitacion = licitacion
        self.db = db
        self.parent_window = parent_window

        # Titanium Construct colors for lotes highlighting
        self.color_ahorro = QColor("#D1FAE5")    # Success green for savings
        self.text_ahorro = QColor("#065F46")     # Dark green text
        self.color_perdida = QColor("#FEF2F2")   # Danger red for loss
        self.text_perdida = QColor("#DC2626")    # Red text
        self.color_default = QColor(Qt.GlobalColor.white)
        self.text_default = QColor("#111827")    # Neutral-900
        self.color_nuestra = QColor("#EEF2FF")   # Indigo for our company
        self.text_nuestra = QColor("#4F46E5")    # Indigo text

        print("[DEBUG][TabLotes] __init__ - empresas_nuestras en licitación:",
              getattr(self.licitacion, "empresas_nuestras", []))

        self._build_ui()
        self._connect_signals()
        self._loading = False


    # ------------------------------------------------------------------ UI ------------------------------------------------------------------
    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        self.table_lotes = QTableWidget()
        self.table_lotes.setColumnCount(10)
        self.table_lotes.setHorizontalHeaderLabels([
            "Participar", "Fase A OK", "N°", "Nombre Lote",
            "Base Licitación", "Base Personal", "Nuestra Oferta",
            "% Dif. Licit.", "% Dif. Pers.", "Nuestra Empresa"
        ])

        self.table_lotes.setAlternatingRowColors(True)
        self.table_lotes.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_lotes.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_lotes.verticalHeader().setVisible(False)
        self.table_lotes.setSortingEnabled(True)
        self.table_lotes.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        header = self.table_lotes.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)
        header.setSectionResizeMode(self.COL_NOMBRE, QHeaderView.ResizeMode.Stretch)

        main_layout.addWidget(self.table_lotes)

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)

        style = self.style()
        try:
            icon_add = style.standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder)
            icon_edit = style.standardIcon(QStyle.StandardPixmap.SP_FileIcon)
            icon_del = style.standardIcon(QStyle.StandardPixmap.SP_TrashIcon)

            if icon_add.isNull() or icon_edit.isNull() or icon_del.isNull():
                print("Advertencia: Uno o más iconos estándar no se cargaron correctamente en TabLotes.")
                icon_add, icon_edit, icon_del = QIcon(), QIcon(), QIcon()
        except AttributeError as e:
            print(f"ERROR FATAL: Falló al obtener un icono estándar en TabLotes: {e}. Usando iconos vacíos.")
            icon_add, icon_edit, icon_del = QIcon(), QIcon(), QIcon()

        self.btn_agregar = QPushButton(" Agregar Lote")
        self.btn_agregar.setIcon(icon_add)
        self.btn_agregar.setToolTip("Añadir un nuevo lote a esta licitación")

        self.btn_editar = QPushButton(" Editar Lote")
        self.btn_editar.setIcon(icon_edit)
        self.btn_editar.setToolTip("Editar el lote seleccionado en la tabla (también con doble clic)")

        self.btn_eliminar = QPushButton(" Eliminar Lote")
        self.btn_eliminar.setIcon(icon_del)
        self.btn_eliminar.setToolTip("Eliminar el lote seleccionado de esta licitación")
        self.btn_eliminar.setProperty("class", "danger")  # Mark as danger action

        button_layout.addWidget(self.btn_agregar)
        button_layout.addWidget(self.btn_editar)
        button_layout.addWidget(self.btn_eliminar)
        button_layout.addStretch(1)

        main_layout.addLayout(button_layout)

    def _connect_signals(self):
        self.btn_agregar.clicked.connect(self._agregar_lote)
        self.btn_editar.clicked.connect(self._editar_lote)
        self.btn_eliminar.clicked.connect(self._eliminar_lote)

        self.table_lotes.cellChanged.connect(self._on_cell_changed)
        self.table_lotes.doubleClicked.connect(self._editar_lote_on_double_click)

    # ------------------------------------------------------------------ Carga de datos ------------------------------------------------------------------
    def load_data(self):
        print("TabLotes: Cargando datos...")
        print("[DEBUG][TabLotes.load_data] licitacion id:", id(self.licitacion))
        print("[DEBUG][TabLotes.load_data] empresas_nuestras en licitación:",
            getattr(self.licitacion, "empresas_nuestras", []))

        self._loading = True
        self.table_lotes.blockSignals(True)
        try:
            self.table_lotes.setSortingEnabled(False)
            self.table_lotes.setRowCount(0)
            self.table_lotes.clearContents()

            lotes_ordenados = sorted(self.licitacion.lotes, key=lambda l: str(l.numero or ""))

            for lote in lotes_ordenados:
                print(f"[DEBUG][TabLotes.load_data] Lote {lote.numero} empresa_nuestra={getattr(lote, 'empresa_nuestra', None)}")

                row = self.table_lotes.rowCount()
                self.table_lotes.insertRow(row)

                # -------------------- Cálculos --------------------
                dif_lic_str, dif_pers_str = "N/D", "N/D"
                dif_lic_val, dif_pers_val = 0.0, 0.0

                try:
                    if lote.monto_base and lote.monto_ofertado and lote.monto_base != 0:
                        dif_lic_val = ((lote.monto_base - lote.monto_ofertado) / lote.monto_base) * 100
                        dif_lic_str = f"{dif_lic_val:.2f}%"
                except Exception as e:
                    print(f"[WARN][TabLotes] Error calculando dif lic: {e}")

                try:
                    if lote.monto_base_personal and lote.monto_ofertado and lote.monto_base_personal != 0:
                        dif_pers_val = ((lote.monto_base_personal - lote.monto_ofertado) / lote.monto_base_personal) * 100
                        dif_pers_str = f"{dif_pers_val:.2f}%"
                except Exception as e:
                    print(f"[WARN][TabLotes] Error calculando dif pers: {e}")

                try:
                    monto_base_str = locale.currency(lote.monto_base or 0.0, grouping=True)
                    monto_pers_str = locale.currency(lote.monto_base_personal or 0.0, grouping=True)
                    monto_ofer_str = locale.currency(lote.monto_ofertado or 0.0, grouping=True)
                except Exception:
                    monto_base_str = f"{lote.monto_base or 0.0:,.2f}"
                    monto_pers_str = f"{lote.monto_base_personal or 0.0:,.2f}"
                    monto_ofer_str = f"{lote.monto_ofertado or 0.0:,.2f}"

                # -------------------- Checkboxes --------------------
                item_participar = QTableWidgetItem()
                item_participar.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                item_participar.setCheckState(Qt.CheckState.Checked if lote.participamos else Qt.CheckState.Unchecked)
                self.table_lotes.setItem(row, self.COL_PARTICIPAR, item_participar)

                item_fase_a = QTableWidgetItem()
                item_fase_a.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                item_fase_a.setCheckState(Qt.CheckState.Checked if lote.fase_A_superada else Qt.CheckState.Unchecked)
                self.table_lotes.setItem(row, self.COL_FASE_A, item_fase_a)

                # -------------------- Datos base --------------------
                self._set_item(row, self.COL_NUMERO, str(lote.numero or ""), data=lote, align='center')
                self._set_item(row, self.COL_NOMBRE, lote.nombre)
                self._set_item(row, self.COL_MONTO_BASE, monto_base_str, align='right')
                self._set_item(row, self.COL_MONTO_PERSONAL, monto_pers_str, align='right')
                self._set_item(row, self.COL_MONTO_OFERTADO, monto_ofer_str, align='right')

                # -------------------- % Diferencias --------------------
                self._set_item(row, self.COL_DIF_LIC, dif_lic_str, align='right')
                self._color_percentage_cell(self.table_lotes.item(row, self.COL_DIF_LIC), dif_lic_val)

                self._set_item(row, self.COL_DIF_PERS, dif_pers_str, align='right')
                self._color_percentage_cell(self.table_lotes.item(row, self.COL_DIF_PERS), dif_pers_val)

                # -------------------- Nuestra Empresa (aislada) --------------------
                empresa_item = QTableWidgetItem(lote.empresa_nuestra or "")
                empresa_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                self.table_lotes.setItem(row, self.COL_EMPRESA, empresa_item)

                # -------------------- Resaltado Nuestra Empresa --------------------
                if lote.empresa_nuestra:
                    font_bold = QFont()
                    font_bold.setBold(True)

                    for c in range(self.table_lotes.columnCount()):
                        item = self.table_lotes.item(row, c)
                        if not item:
                            continue

                        # No pisar colores semánticos de % Dif
                        if c in (self.COL_DIF_LIC, self.COL_DIF_PERS):
                            item.setFont(font_bold)
                            continue

                        item.setBackground(self.color_nuestra)
                        item.setForeground(self.text_nuestra)
                        item.setFont(font_bold)

            self.table_lotes.resizeColumnsToContents()
            self.table_lotes.horizontalHeader().setSectionResizeMode(
                self.COL_NOMBRE, QHeaderView.ResizeMode.Stretch
            )

        finally:
            self.table_lotes.setSortingEnabled(True)
            self.table_lotes.blockSignals(False)
            self._loading = False


        print(f"TabLotes: Datos cargados ({self.table_lotes.rowCount()} filas).")


    def set_licitacion(self, licitacion: Licitacion):
        print("[DEBUG][TabLotes] set_licitacion called. id(old) -> id(new):",
            id(getattr(self, "licitacion", None)), "->", id(licitacion))
        self.licitacion = licitacion


    def _set_item(self, row, col, text, data=None, align='left'):
        item = QTableWidgetItem(str(text))
        if col not in (self.COL_PARTICIPAR, self.COL_FASE_A):
            item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)

        if align == 'right':
            item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
        elif align == 'center':
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        if data is not None:
            item.setData(Qt.ItemDataRole.UserRole, data)

        # Color de texto por defecto coherente con Titanium
        item.setForeground(self.text_default)

        self.table_lotes.setItem(row, col, item)

    def _color_percentage_cell(self, item: QTableWidgetItem | None, value: float):
        """
        Aplica colores semánticos Titanium Construct a las celdas de porcentaje,
        garantizando que el texto sea legible incluso sin selección.
        """
        if item is None:
            return

        # Importante: siempre forzamos un color de texto explícito
        if value > 0.001:
            item.setBackground(self.color_ahorro)
            item.setForeground(self.text_ahorro)   # verde oscuro
            item.setToolTip(f"Ahorro del {value:.2f}%")
        elif value < -0.001:
            item.setBackground(self.color_perdida)
            item.setForeground(self.text_perdida)  # rojo
            item.setToolTip(f"Sobreprecio del {abs(value):.2f}%")
        else:
            item.setBackground(self.color_default)
            item.setForeground(self.text_default)  # Neutral-900
            item.setToolTip("Sin diferencia" if abs(value) <= 0.001 else "")

    def collect_data(self) -> bool:
        print("[DEBUG][TabLotes.collect_data] Reafirmando empresa_nuestra desde la tabla")

        # Crear mapa real de lotes actuales por ID
        lotes_by_id = {l.id: l for l in self.licitacion.lotes if l.id is not None}

        for row in range(self.table_lotes.rowCount()):
            num_item = self.table_lotes.item(row, self.COL_NUMERO)
            emp_item = self.table_lotes.item(row, self.COL_EMPRESA)

            if not num_item:
                continue

            lote_ref = num_item.data(Qt.ItemDataRole.UserRole)
            if not lote_ref or lote_ref.id is None:
                continue

            # 🔥 AQUÍ ESTÁ EL FIX
            lote_real = lotes_by_id.get(lote_ref.id)
            if not lote_real:
                continue

            empresa = emp_item.text().strip() if emp_item else None
            lote_real.empresa_nuestra = empresa or None

            print(
                f"[DEBUG][TabLotes.collect_data] "
                f"Lote {lote_real.numero} (id={lote_real.id}) "
                f"empresa_nuestra={lote_real.empresa_nuestra}"
            )

        return True


    # ------------------------------------------------------------------ Slots / Señales ------------------------------------------------------------------
    def _on_cell_changed(self, row: int, column: int):
        if self._loading:
            return

        if column not in (self.COL_PARTICIPAR, self.COL_FASE_A):
            return

        lote_item = self.table_lotes.item(row, self.COL_NUMERO)
        if not lote_item:
            return

        lote: Lote | None = lote_item.data(Qt.ItemDataRole.UserRole)
        if not lote:
            return

        changed_item = self.table_lotes.item(row, column)
        if not changed_item:
            return

        is_checked = (changed_item.checkState() == Qt.CheckState.Checked)
        changed = False

        if column == self.COL_PARTICIPAR and lote.participamos != is_checked:
            lote.participamos = is_checked
            changed = True
            field = "participamos"

        elif column == self.COL_FASE_A and lote.fase_A_superada != is_checked:
            lote.fase_A_superada = is_checked
            changed = True
            field = "fase_A_superada"

        if changed:
            print(f"[CHANGE][TabLotes] Lote {lote.numero} → {field} = {is_checked}")

            if hasattr(self.parent_window, "mark_dirty"):
                self.parent_window.mark_dirty(f"TabLotes.cell:{field}")


    # ------------------------------------------------------------------ Helpers ------------------------------------------------------------------
    def _get_nombres_empresas_actuales(self) -> List[str]:
        print("[DEBUG][TabLotes._get_nombres_empresas_actuales] leyéndolas desde TabGeneral y licitación...")
        try:
            nombres = self.parent_window.tab_general._actualizar_display_empresas()
            print("[DEBUG][TabLotes._get_nombres_empresas_actuales] desde tab_general:", nombres)
            if isinstance(nombres, list):
                return nombres
        except Exception as e:
            print(f"TabLotes: No se pudo obtener empresas de TabGeneral ({e}). Usando fallback.")

        fallback = [str(e) for e in self.licitacion.empresas_nuestras if e]
        print("[DEBUG][TabLotes._get_nombres_empresas_actuales] fallback desde licitación:", fallback)
        return fallback

    # ------------------------------------------------------------------ CRUD Lotes ------------------------------------------------------------------
    def _agregar_lote(self):
        print("[DEBUG][TabLotes._agregar_lote] Abriendo diálogo para nuevo lote")

        nombres_empresas = self._get_nombres_empresas_actuales()

        dialogo = DialogoLoteForm(
            parent=self,
            lote_actual=None,
            empresas_participantes=nombres_empresas
        )

        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return

        nuevo_lote = dialogo.get_lote_object()
        if not nuevo_lote:
            return

        # 🧼 Normalizar número
        nuevo_lote.numero = normalize_lote_numero(nuevo_lote.numero)

        # 🚫 Evitar duplicados
        for l in self.licitacion.lotes:
            if normalize_lote_numero(l.numero) == nuevo_lote.numero:
                QMessageBox.warning(
                    self,
                    "Lote duplicado",
                    f"Ya existe un lote con el número {nuevo_lote.numero}"
                )
                return

        # 🆔 ID temporal ESTABLE (no time-based)
        if nuevo_lote.id is None:
            max_id = max(
                [abs(l.id) for l in self.licitacion.lotes if isinstance(l.id, int)],
                default=0
            )
            nuevo_lote.id = -(max_id + 1)

        nuevo_lote.licitacion_id = self.licitacion.id

        self.licitacion.lotes.append(nuevo_lote)

        # 🧷 Marcar como modificado (NO guardar aquí)
        if hasattr(self.parent_window, "mark_dirty"):
            self.parent_window.mark_dirty("TabLotes.agregar_lote")
            self.parent_window.log_change(f"TabLotes → Lote {nuevo_lote.numero} agregado")


        self.load_data()

        print(f"[OK][TabLotes] Lote {nuevo_lote.numero} agregado (pendiente de guardado)")

    def _get_selected_lote(self) -> Lote | None:
        current_row = self.table_lotes.currentRow()
        if current_row < 0:
            return None
        lote_item = self.table_lotes.item(current_row, self.COL_NUMERO)
        if not lote_item:
            return None
        lote: Lote | None = lote_item.data(Qt.ItemDataRole.UserRole)
        return lote

    def _editar_lote(self):
        lote_seleccionado = self._get_selected_lote()
        if lote_seleccionado:
            self._open_edit_dialog(lote_seleccionado)
        else:
            QMessageBox.warning(self, "Sin Selección", "Por favor, selecciona un lote de la tabla para editar.")

    def _editar_lote_on_double_click(self, index: QModelIndex):
        if not index.isValid():
            return

        lote_item = self.table_lotes.item(index.row(), self.COL_NUMERO)
        if not lote_item:
            return
        lote_a_editar: Lote | None = lote_item.data(Qt.ItemDataRole.UserRole)

        if lote_a_editar:
            print(f"TabLotes: Doble clic detectado en lote {lote_a_editar.numero}. Abriendo editor...")
            self._open_edit_dialog(lote_a_editar)

    def _open_edit_dialog(self, lote_to_edit: Lote):
        print(
            f"[DEBUG][TabLotes._open_edit_dialog] "
            f"Editando lote {lote_to_edit.numero} "
            f"empresa_nuestra actual={getattr(lote_to_edit, 'empresa_nuestra', None)}"
        )

        parent = self.parent()

        # 🔐 Lock de edición (bloquea autosave / guardado global)
        if hasattr(parent, "lock_edit"):
            parent.lock_edit("TabLotes.EditarLote")

        try:
            nombres_empresas = self._get_nombres_empresas_actuales()

            dialogo = DialogoLoteForm(
                parent=self,
                lote_actual=lote_to_edit,
                empresas_participantes=nombres_empresas
            )

            if dialogo.exec() != QDialog.DialogCode.Accepted:
                print("[INFO][TabLotes] Edición cancelada por el usuario")
                return

            lote_actualizado = dialogo.get_lote_object()
            if not lote_actualizado:
                print("[WARN][TabLotes] Diálogo aceptado pero sin lote válido")
                return

            # 🧼 Normalizar número
            lote_actualizado.numero = normalize_lote_numero(lote_actualizado.numero)

            print(
                f"[DEBUG][TabLotes._open_edit_dialog] "
                f"lote_actualizado {lote_actualizado.numero} "
                f"empresa_nuestra={lote_actualizado.empresa_nuestra}"
            )

            # 🔍 Aplicar SOLO cambios reales
            changed_fields: list[str] = []
            lote_real: Lote | None = None

            for l in self.licitacion.lotes:
                if l.id == lote_to_edit.id:
                    lote_real = l
                    break

            if not lote_real:
                print("[ERROR][TabLotes] Lote original no encontrado en licitación")
                return

            def _set(attr: str, new_val):
                nonlocal changed_fields
                old_val = getattr(lote_real, attr, None)
                if old_val != new_val:
                    setattr(lote_real, attr, new_val)
                    changed_fields.append(attr)

            _set("numero", lote_actualizado.numero)
            _set("nombre", lote_actualizado.nombre)
            _set("monto_base", lote_actualizado.monto_base)
            _set("monto_base_personal", lote_actualizado.monto_base_personal)
            _set("monto_ofertado", lote_actualizado.monto_ofertado)
            _set("participamos", lote_actualizado.participamos)
            _set("fase_A_superada", lote_actualizado.fase_A_superada)
            _set("ganador_nombre", lote_actualizado.ganador_nombre)
            _set("ganado_por_nosotros", lote_actualizado.ganado_por_nosotros)
            _set("empresa_nuestra", lote_actualizado.empresa_nuestra)

            if not changed_fields:
                print("[INFO][TabLotes] Edición sin cambios reales")
                self.load_data()  # fuerza coherencia visual
                return

            print(
                f"[CHANGE][TabLotes] Lote {lote_real.numero} "
                f"campos modificados: {', '.join(changed_fields)}"
            )

            # 🧷 Marcar como dirty (NO guardar aquí)
            if hasattr(parent, "mark_dirty"):
                parent.mark_dirty(f"TabLotes.editar_lote:{lote_real.numero}")

            # 🔄 Refrescar UI
            self.load_data()

            print(
                f"[OK][TabLotes] Lote {lote_real.numero} "
                f"actualizado (pendiente de guardado)"
            )

        finally:
            # 🔓 Unlock SIEMPRE
            if hasattr(parent, "unlock_edit"):
                parent.unlock_edit("TabLotes.EditarLote")


    def _eliminar_lote(self):
        lote_a_eliminar = self._get_selected_lote()
        if not lote_a_eliminar:
            QMessageBox.warning(self, "Sin Selección", "Selecciona un lote para eliminar.")
            return

        reply = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Eliminar el lote {lote_a_eliminar.numero} - {lote_a_eliminar.nombre}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        before = len(self.licitacion.lotes)

        self.licitacion.lotes = [
            l for l in self.licitacion.lotes
            if l.id != lote_a_eliminar.id
        ]

        after = len(self.licitacion.lotes)

        if after < before:
            if hasattr(self.parent_window, "mark_dirty"):
                self.parent_window.mark_dirty("TabLotes.eliminar_lote")

            self.load_data()
            print(f"[OK][TabLotes] Lote {lote_a_eliminar.numero} eliminado (pendiente de guardado)")
