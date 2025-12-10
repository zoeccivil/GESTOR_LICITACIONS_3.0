# app/ui/dialogs/seleccionar_institucion_dialog.py
from __future__ import annotations
from typing import List, Optional, Dict, Any

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QDialogButtonBox, QLabel, QMessageBox
)
from PyQt6.QtCore import Qt

from .gestionar_entidad_dialog import DialogoGestionarEntidad
from .dialogo_gestionar_instituciones import DialogoGestionarInstituciones

class SeleccionarInstitucionDialog(QDialog):
    """
    Selector de institución en forma de tabla (Nombre | RNC | Teléfono).
    - Doble clic para seleccionar.
    - Botón para agregar (DialogoGestionarEntidad) y refrescar.
    - Botón para abrir gestor completo y recargar si hubo cambios.
    Devuelve dict seleccionado vía get_selected().
    """
    def __init__(self, parent, db_adapter):
        super().__init__(parent)
        self.setWindowTitle("Seleccionar Institución")
        self.setMinimumSize(640, 420)
        self.db = db_adapter
        try:
            self._instituciones: List[Dict[str, Any]] = list(self.db.get_instituciones_maestras() or [])
        except Exception:
            self._instituciones = []
        self.selected: Optional[Dict[str, Any]] = None
        self._build_ui()
        self._populate_table()

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.addWidget(QLabel("Seleccione una institución (doble clic para elegir)"))

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Nombre", "RNC", "Teléfono"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        main.addWidget(self.table, 1)

        btns_h = QHBoxLayout()
        self.btn_add = QPushButton("➕ Agregar Institución")
        self.btn_add.clicked.connect(self._on_add_institucion)
        btns_h.addWidget(self.btn_add)

        self.btn_manage = QPushButton("Gestionar Instituciones...")
        self.btn_manage.clicked.connect(self._on_manage_instituciones)
        btns_h.addWidget(self.btn_manage)

        btns_h.addStretch(1)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        self.button_box.accepted.connect(self._on_ok)
        self.button_box.rejected.connect(self.reject)
        btns_h.addWidget(self.button_box)

        self.table.currentCellChanged.connect(
            lambda r, c, pr, pc: self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(r is not None and r >= 0)
        )

        main.addLayout(btns_h)

    def _populate_table(self):
        self.table.setRowCount(0)
        for inst in self._instituciones:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(inst.get("nombre", "")))
            self.table.setItem(row, 1, QTableWidgetItem(inst.get("rnc", "")))
            self.table.setItem(row, 2, QTableWidgetItem(inst.get("telefono", "")))

    def _on_cell_double_clicked(self, row: int, col: int):
        self.selected = self._instituciones[row] if 0 <= row < len(self._instituciones) else None
        if self.selected:
            self.accept()

    def _on_ok(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Sin selección", "Por favor selecciona una institución.")
            return
        self.selected = self._instituciones[row]
        self.accept()

    def _on_add_institucion(self):
        dlg = DialogoGestionarEntidad(self, "Agregar Institución", "institucion", None)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            nueva = None
            if hasattr(dlg, "get_data") and callable(getattr(dlg, "get_data")):
                try:
                    nueva = dlg.get_data()
                except Exception:
                    nueva = None
            elif hasattr(dlg, "result"):
                r = getattr(dlg, "result")
                nueva = r() if callable(r) else r
            if not isinstance(nueva, dict):
                QMessageBox.warning(self, "Sin datos", "No se obtuvieron los datos de la nueva institución.")
                return
            # intentar persistir via adapter si existe
            try:
                if hasattr(self.db, "save_instituciones_maestras"):
                    insts = list(self.db.get_instituciones_maestras() or [])
                    insts.append(nueva)
                    self.db.save_instituciones_maestras(insts)
                    self._instituciones = list(self.db.get_instituciones_maestras() or [])
                else:
                    self._instituciones.append(nueva)
            except Exception as e:
                QMessageBox.warning(self, "Aviso", f"No se pudo persistir: {e}\nSe añadirá temporalmente.")
                self._instituciones.append(nueva)

            self._instituciones.sort(key=lambda x: x.get("nombre", "").upper())
            self._populate_table()
            # seleccionar la recién añadida
            target = nueva.get("nombre", "")
            for i in range(self.table.rowCount()):
                if self.table.item(i, 0).text() == target:
                    self.table.selectRow(i)
                    break

    def _on_manage_instituciones(self):
        dlg = DialogoGestionarInstituciones(self, self.db)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                self._instituciones = list(self.db.get_instituciones_maestras() or [])
            except Exception:
                pass
            self._instituciones.sort(key=lambda x: x.get("nombre", "").upper())
            self._populate_table()

    def get_selected(self) -> Optional[Dict[str, Any]]:
        return self.selected