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
        self.color_perdida = QColor("#FEF2F2")   # Danger red for loss
        self.color_default = QColor(Qt.GlobalColor.white)
        self.color_nuestra = QColor("#EEF2FF")   # Indigo for our company
        self.text_nuestra = QColor("#4F46E5")    # Indigo text

        print("[DEBUG][TabLotes] __init__ - empresas_nuestras en licitación:",
              getattr(self.licitacion, "empresas_nuestras", []))

        self._build_ui()
        self._connect_signals()

    # (métodos _build_ui, _connect_signals, load_data, _set_item, _color_percentage_cell, collect_data, _on_cell_changed
    # exactamente como en tu último código; los omito aquí por brevedad)

    # Helpers de empresas y CRUD (_get_nombres_empresas_actuales, _agregar_lote, _get_selected_lote, _editar_lote,
    # _editar_lote_on_double_click, _open_edit_dialog, _eliminar_lote) también como en tu último envío, con las llamadas
    # a self.db.save_licitacion(self.licitacion) ya añadidas.

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
        print("[DEBUG][TabLotes.load_data] empresas_nuestras en licitación:",
              getattr(self.licitacion, "empresas_nuestras", []))
        self.table_lotes.blockSignals(True)
        try:
            self.table_lotes.setSortingEnabled(False)
            self.table_lotes.setRowCount(0)

            lotes_ordenados = sorted(self.licitacion.lotes, key=lambda l: l.numero or "0")

            for lote in lotes_ordenados:
                print(f"[DEBUG][TabLotes.load_data] Lote {lote.numero} empresa_nuestra={getattr(lote, 'empresa_nuestra', None)}")
                row = self.table_lotes.rowCount()
                self.table_lotes.insertRow(row)

                dif_lic_str, dif_pers_str = "N/D", "N/D"
                dif_lic_val, dif_pers_val = 0.0, 0.0

                try:
                    if lote.monto_base and lote.monto_ofertado and lote.monto_base != 0:
                        dif_lic_val = ((lote.monto_base - lote.monto_ofertado) / lote.monto_base) * 100
                        dif_lic_str = f"{dif_lic_val:.2f}%"
                except Exception as e:
                    print(f"Error calculando dif lic: {e}")

                try:
                    if lote.monto_base_personal and lote.monto_ofertado and lote.monto_base_personal != 0:
                        dif_pers_val = ((lote.monto_base_personal - lote.monto_ofertado) / lote.monto_base_personal) * 100
                        dif_pers_str = f"{dif_pers_val:.2f}%"
                except Exception as e:
                    print(f"Error calculando dif pers: {e}")

                try:
                    monto_base_str = locale.currency(lote.monto_base or 0.0, grouping=True)
                    monto_pers_str = locale.currency(lote.monto_base_personal or 0.0, grouping=True)
                    monto_ofer_str = locale.currency(lote.monto_ofertado or 0.0, grouping=True)
                except Exception:
                    monto_base_str = f"{lote.monto_base or 0.0:,.2f}"
                    monto_pers_str = f"{lote.monto_base_personal or 0.0:,.2f}"
                    monto_ofer_str = f"{lote.monto_ofertado or 0.0:,.2f}"

                item_participar = QTableWidgetItem()
                item_participar.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                item_participar.setCheckState(Qt.CheckState.Checked if lote.participamos else Qt.CheckState.Unchecked)
                self.table_lotes.setItem(row, self.COL_PARTICIPAR, item_participar)

                item_fase_a = QTableWidgetItem()
                item_fase_a.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                item_fase_a.setCheckState(Qt.CheckState.Checked if lote.fase_A_superada else Qt.CheckState.Unchecked)
                self.table_lotes.setItem(row, self.COL_FASE_A, item_fase_a)

                self._set_item(row, self.COL_NUMERO, str(lote.numero or ""), data=lote, align='center')
                self._set_item(row, self.COL_NOMBRE, lote.nombre)
                self._set_item(row, self.COL_MONTO_BASE, monto_base_str, align='right')
                self._set_item(row, self.COL_MONTO_PERSONAL, monto_pers_str, align='right')
                self._set_item(row, self.COL_MONTO_OFERTADO, monto_ofer_str, align='right')

                self._set_item(row, self.COL_DIF_LIC, dif_lic_str, align='right')
                self._color_percentage_cell(self.table_lotes.item(row, self.COL_DIF_LIC), dif_lic_val)

                self._set_item(row, self.COL_DIF_PERS, dif_pers_str, align='right')
                self._color_percentage_cell(self.table_lotes.item(row, self.COL_DIF_PERS), dif_pers_val)

                self._set_item(row, self.COL_EMPRESA, lote.empresa_nuestra or "")
                
                # Highlight rows where we have "our company" assigned
                if lote.empresa_nuestra:
                    font_bold = QFont()
                    font_bold.setBold(True)
                    for c in range(self.table_lotes.columnCount()):
                        if self.table_lotes.item(row, c):
                            self.table_lotes.item(row, c).setBackground(self.color_nuestra)
                            self.table_lotes.item(row, c).setForeground(self.text_nuestra)
                            self.table_lotes.item(row, c).setFont(font_bold)

            self.table_lotes.resizeColumnsToContents()
            self.table_lotes.horizontalHeader().setSectionResizeMode(self.COL_NOMBRE, QHeaderView.ResizeMode.Stretch)

        finally:
            self.table_lotes.setSortingEnabled(True)
            self.table_lotes.blockSignals(False)
        print(f"TabLotes: Datos cargados ({self.table_lotes.rowCount()} filas).")

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

        self.table_lotes.setItem(row, col, item)

    def _color_percentage_cell(self, item: QTableWidgetItem | None, value: float):
        if item is None:
            return
        if value > 0.001:
            item.setBackground(self.color_ahorro)
            item.setToolTip(f"Ahorro del {value:.2f}%")
        elif value < -0.001:
            item.setBackground(self.color_perdida)
            item.setToolTip(f"Sobreprecio del {abs(value):.2f}%")
        else:
            item.setBackground(self.color_default)
            item.setToolTip("Sin diferencia" if value == 0.0 else "")

    def collect_data(self) -> bool:
        print("TabLotes: Collect data (no action needed, model updated by signals).")
        print("[DEBUG][TabLotes.collect_data] empresas_nuestras en licitación al guardar:",
              getattr(self.licitacion, "empresas_nuestras", []))
        for l in self.licitacion.lotes:
            print(f"[DEBUG][TabLotes.collect_data] Lote {l.numero} empresa_nuestra={getattr(l, 'empresa_nuestra', None)}")
        return True

    # ------------------------------------------------------------------ Slots / Señales ------------------------------------------------------------------
    def _on_cell_changed(self, row: int, column: int):
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

        if column == self.COL_PARTICIPAR:
            lote.participamos = is_checked
            print(f"TabLotes: Lote {lote.numero} 'participamos' actualizado a: {is_checked}")
        elif column == self.COL_FASE_A:
            lote.fase_A_superada = is_checked
            print(f"TabLotes: Lote {lote.numero} 'fase_A_superada' actualizado a: {is_checked}")

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
        print("[DEBUG][TabLotes._agregar_lote] empresas_nuestras antes de abrir diálogo:",
              getattr(self.licitacion, "empresas_nuestras", []))
        nombres_empresas = self._get_nombres_empresas_actuales()
        print("[DEBUG][TabLotes._agregar_lote] empresas_participantes que se pasan al diálogo:", nombres_empresas)

        dialogo = DialogoLoteForm(
            parent=self,
            lote_actual=None,
            empresas_participantes=nombres_empresas
        )

        if dialogo.exec() == QDialog.DialogCode.Accepted:
            nuevo_lote = dialogo.get_lote_object()
            print("[DEBUG][TabLotes._agregar_lote] lote devuelto por diálogo:", nuevo_lote)
            if nuevo_lote:
                print(f"[DEBUG][TabLotes._agregar_lote] nuevo_lote.empresa_nuestra={getattr(nuevo_lote, 'empresa_nuestra', None)}")
                if nuevo_lote.id is None:
                    nuevo_lote.id = int(time.time() * -1000 + len(self.licitacion.lotes))
                    print(f"[DEBUG][TabLotes._agregar_lote] Asignado id temporal al nuevo lote: {nuevo_lote.id}")

                nuevo_lote.licitacion_id = self.licitacion.id
                self.licitacion.lotes.append(nuevo_lote)
                print("[DEBUG][TabLotes._agregar_lote] lotes en licitación tras append:",
                      [(l.numero, getattr(l, 'empresa_nuestra', None)) for l in self.licitacion.lotes])

                # Guardar inmediatamente la licitación tras agregar lote
                try:
                    if self.db:
                        print("[DEBUG][TabLotes._agregar_lote] Guardando licitación tras agregar lote")
                        self.db.save_licitacion(self.licitacion)
                except Exception as e:
                    print(f"[ERROR][TabLotes._agregar_lote] Error guardando licitación: {e}")

                self.load_data()
                print(f"TabLotes: Nuevo lote '{nuevo_lote.nombre}' agregado a la lista.")

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
        print(f"[DEBUG][TabLotes._open_edit_dialog] Editando lote {lote_to_edit.numero} empresa_nuestra actual={getattr(lote_to_edit, 'empresa_nuestra', None)}")
        nombres_empresas = self._get_nombres_empresas_actuales()
        print("[DEBUG][TabLotes._open_edit_dialog] empresas_participantes que se pasan al diálogo:", nombres_empresas)

        dialogo = DialogoLoteForm(
            parent=self,
            lote_actual=lote_to_edit,
            empresas_participantes=nombres_empresas
        )

        if dialogo.exec() == QDialog.DialogCode.Accepted:
            lote_actualizado = dialogo.get_lote_object()
            print("[DEBUG][TabLotes._open_edit_dialog] lote devuelto por diálogo:", lote_actualizado)
            if lote_actualizado:
                print(f"[DEBUG][TabLotes._open_edit_dialog] lote_actualizado.empresa_nuestra={getattr(lote_actualizado, 'empresa_nuestra', None)}")
                found = False
                for i, l in enumerate(self.licitacion.lotes):
                    if l.id == lote_to_edit.id:
                        self.licitacion.lotes[i] = lote_actualizado
                        found = True
                        break
                print("[DEBUG][TabLotes._open_edit_dialog] lotes en licitación tras actualización:",
                      [(l.numero, getattr(l, 'empresa_nuestra', None)) for l in self.licitacion.lotes])

                if found:
                    # Guardar inmediatamente la licitación tras actualizar lote
                    try:
                        if self.db:
                            print("[DEBUG][TabLotes._open_edit_dialog] Guardando licitación tras actualizar lote")
                            self.db.save_licitacion(self.licitacion)
                    except Exception as e:
                        print(f"[ERROR][TabLotes._open_edit_dialog] Error guardando licitación: {e}")

                    self.load_data()
                    print(f"TabLotes: Lote {lote_actualizado.numero} actualizado.")
                else:
                    print(f"TabLotes: WARNING - No se encontró el lote original con ID {lote_to_edit.id} para reemplazar.")

    def _eliminar_lote(self):
        lote_a_eliminar = self._get_selected_lote()
        if not lote_a_eliminar:
            QMessageBox.warning(self, "Sin Selección", "Por favor, selecciona un lote de la tabla para eliminar.")
            return

        reply = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Estás seguro de que deseas eliminar el lote:\n\n"
            f"N° {lote_a_eliminar.numero} - {lote_a_eliminar.nombre}?\n\n"
            "Esta acción solo lo quita de la ventana actual. Se eliminará permanentemente al guardar.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            initial_count = len(self.licitacion.lotes)
            self.licitacion.lotes = [l for l in self.licitacion.lotes if l.id != lote_a_eliminar.id]
            final_count = len(self.licitacion.lotes)

            print("[DEBUG][TabLotes._eliminar_lote] lotes en licitación tras eliminar:",
                  [(l.numero, getattr(l, 'empresa_nuestra', None)) for l in self.licitacion.lotes])

            if final_count < initial_count:
                # Guardar inmediatamente la licitación tras eliminar lote
                try:
                    if self.db:
                        print("[DEBUG][TabLotes._eliminar_lote] Guardando licitación tras eliminar lote")
                        self.db.save_licitacion(self.licitacion)
                except Exception as e:
                    print(f"[ERROR][TabLotes._eliminar_lote] Error guardando licitación: {e}")

                self.load_data()
                print(f"TabLotes: Lote {lote_a_eliminar.numero} eliminado de la lista.")
            else:
                print(f"TabLotes: WARNING - No se encontró el lote con ID {lote_a_eliminar.id} para eliminar.")