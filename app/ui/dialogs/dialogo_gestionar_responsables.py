from __future__ import annotations
from typing import List, Dict, Any, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QInputDialog
)

from app.core.db_adapter import DatabaseAdapter

class DialogoGestionarResponsables(QDialog):
    COL_NOM = 0

    def __init__(self, parent, db: DatabaseAdapter):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Catálogo de Responsables")
        self.resize(560, 480)
        self.setModal(True)

        self._items: List[Dict[str, Any]] = list(self.db.get_responsables_maestros() or [])

        self._build_ui()
        self._populate()

    def _build_ui(self):
        root = QVBoxLayout(self)

        self.tbl = QTableWidget(0, 1)
        self.tbl.setHorizontalHeaderLabels(["Nombre del Responsable o Departamento"])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.setSelectionBehavior(self.tbl.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(self.tbl.SelectionMode.SingleSelection)
        self.tbl.horizontalHeader().setSectionResizeMode(self.COL_NOM, QHeaderView.ResizeMode.Stretch)
        root.addWidget(self.tbl, 1)

        actions = QHBoxLayout()
        self.btn_add = QPushButton("Agregar")
        self.btn_edit = QPushButton("Editar")
        self.btn_del = QPushButton("Eliminar")
        self.btn_close = QPushButton("✅ Guardar y Cerrar")
        self.btn_add.clicked.connect(self._add)
        self.btn_edit.clicked.connect(self._edit)
        self.btn_del.clicked.connect(self._del)
        self.btn_close.clicked.connect(self._save_and_close)
        for b in (self.btn_add, self.btn_edit, self.btn_del):
            actions.addWidget(b)
        actions.addStretch(1)
        actions.addWidget(self.btn_close)
        root.addLayout(actions)

        self.tbl.itemSelectionChanged.connect(self._update_actions)
        self._update_actions()

    def _populate(self):
        self.tbl.setRowCount(0)
        for r in sorted((self._items or []), key=lambda x: (x.get("nombre", "") or "")):
            row = self.tbl.rowCount()
            self.tbl.insertRow(row)
            self.tbl.setItem(row, self.COL_NOM, QTableWidgetItem(r.get("nombre", "") or ""))
        self._update_actions()

    def _current(self) -> Optional[Dict[str, Any]]:
        r = self.tbl.currentRow()
        if r < 0:
            return None
        name = self.tbl.item(r, self.COL_NOM).text()
        for it in self._items:
            if (it.get("nombre", "") or "") == name:
                return it
        return None

    def _update_actions(self):
        has = self._current() is not None
        self.btn_edit.setEnabled(has)
        self.btn_del.setEnabled(has)

    def _add(self):
        nombre, ok = QInputDialog.getText(self, "Agregar Responsable", "Nombre:")
        if not ok or not (nombre or "").strip():
            return
        nombre = nombre.strip()
        if any((r.get("nombre", "") or "").lower() == nombre.lower() for r in self._items):
            QMessageBox.warning(self, "Duplicado", "Ya existe un responsable con ese nombre.")
            return
        self._items.append({"nombre": nombre})
        self._populate()

    def _edit(self):
        item = self._current()
        if not item:
            return
        nuevo, ok = QInputDialog.getText(self, "Editar Responsable", "Nuevo nombre:", text=item.get("nombre", "") or "")
        if not ok or not (nuevo or "").strip():
            return
        nuevo = nuevo.strip()
        if nuevo.lower() != (item.get("nombre", "") or "").lower():
            if any((r.get("nombre", "") or "").lower() == nuevo.lower() for r in self._items):
                QMessageBox.warning(self, "Duplicado", "Ya existe un responsable con ese nombre.")
                return
        item["nombre"] = nuevo
        self._populate()

    def _del(self):
        item = self._current()
        if not item:
            return
        if QMessageBox.question(self, "Confirmar", f"¿Eliminar a '{item.get('nombre','')}' del catálogo?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        self._items = [r for r in self._items if r is not item]
        self._populate()

    def _save_and_close(self):
        ok = self.db.save_responsables_maestros(self._items)
        if ok:
            QMessageBox.information(self, "Guardar", "Cambios guardados.")
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "No se pudieron guardar los cambios.")