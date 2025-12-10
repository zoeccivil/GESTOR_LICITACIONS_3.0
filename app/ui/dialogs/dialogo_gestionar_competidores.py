from __future__ import annotations
from typing import List, Dict, Any, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QWidget, QFormLayout
)

from app.core.db_adapter import DatabaseAdapter

class DialogoGestionarCompetidores(QDialog):
    COL_NOM = 0
    COL_RNC = 1
    COL_RPE = 2
    COL_REP = 3

    def __init__(self, parent, db: DatabaseAdapter):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Catálogo de Competidores")
        self.resize(900, 560)
        self.setModal(True)

        self._items: List[Dict[str, Any]] = list(self.db.get_competidores_maestros() or [])
        self._filtered: List[Dict[str, Any]] = list(self._items)

        self._build_ui()
        self._populate()

    def _build_ui(self):
        root = QVBoxLayout(self)

        filt = QGroupBox("Buscar")
        fl = QHBoxLayout(filt)
        fl.addWidget(QLabel("🔍"))
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Buscar por nombre o RNC…")
        self.txt_search.textChanged.connect(self._apply_filter)
        fl.addWidget(self.txt_search, 1)
        root.addWidget(filt)

        self.tbl = QTableWidget(0, 4)
        self.tbl.setHorizontalHeaderLabels(["Nombre", "RNC", "No. RPE", "Representante"])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.setSelectionBehavior(self.tbl.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(self.tbl.SelectionMode.SingleSelection)
        self.tbl.horizontalHeader().setSectionResizeMode(self.COL_NOM, QHeaderView.ResizeMode.Stretch)
        self.tbl.horizontalHeader().setSectionResizeMode(self.COL_RNC, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(self.COL_RPE, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(self.COL_REP, QHeaderView.ResizeMode.Stretch)
        root.addWidget(self.tbl, 1)

        actions = QHBoxLayout()
        self.btn_add = QPushButton("Agregar")
        self.btn_edit = QPushButton("Editar")
        self.btn_del = QPushButton("Eliminar")
        self.btn_close = QPushButton("✅ Guardar Cambios y Cerrar")
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

    def _apply_filter(self):
        term = (self.txt_search.text() or "").strip().lower()
        if not term:
            self._filtered = list(self._items)
        else:
            self._filtered = [
                c for c in self._items
                if term in (c.get("nombre", "") or "").lower() or term in (c.get("rnc", "") or "").lower()
            ]
        self._populate()

    def _populate(self):
        self.tbl.setRowCount(0)
        for c in sorted(self._filtered, key=lambda x: (x.get("nombre", "") or "")):
            row = self.tbl.rowCount()
            self.tbl.insertRow(row)
            vals = (
                c.get("nombre", "") or "",
                c.get("rnc", "") or "",
                c.get("rpe", "") or "",
                c.get("representante", "") or "",
            )
            for col, text in enumerate(vals):
                self.tbl.setItem(row, col, QTableWidgetItem(text))
            self.tbl.setRowHeight(row, 24)
        self._update_actions()

    def _current(self) -> Optional[Dict[str, Any]]:
        r = self.tbl.currentRow()
        if r < 0:
            return None
        name = self.tbl.item(r, self.COL_NOM).text()
        for c in self._items:
            if (c.get("nombre", "") or "") == name:
                return c
        return None

    def _update_actions(self):
        has = self._current() is not None
        self.btn_edit.setEnabled(has)
        self.btn_del.setEnabled(has)

    def _add(self):
        dlg = _CompetidorForm(self, "Agregar Competidor")
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        data = dlg.data()
        if not data.get("nombre"):
            QMessageBox.warning(self, "Datos", "El nombre es obligatorio.")
            return
        if any((c.get("nombre", "") or "").lower() == data["nombre"].lower() for c in self._items):
            QMessageBox.warning(self, "Duplicado", "Ya existe un competidor con ese nombre.")
            return
        if data.get("rnc") and any((c.get("rnc", "") or "").lower() == data["rnc"].lower() and (c.get("rnc", "") or "") for c in self._items):
            QMessageBox.warning(self, "Duplicado", "Ya existe un competidor con ese RNC.")
            return
        self._items.append(data)
        self._apply_filter()

    def _edit(self):
        item = self._current()
        if not item:
            return
        dlg = _CompetidorForm(self, "Editar Competidor", initial=item)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        data = dlg.data()
        # validar duplicados si cambian nombre/rnc
        if data.get("nombre", "").lower() != (item.get("nombre", "") or "").lower():
            if any((c.get("nombre", "") or "").lower() == data["nombre"].lower() for c in self._items):
                QMessageBox.warning(self, "Duplicado", "Ya existe un competidor con ese nombre.")
                return
        if data.get("rnc", "").lower() != (item.get("rnc", "") or "").lower() and data.get("rnc"):
            if any((c.get("rnc", "") or "").lower() == data["rnc"].lower() and (c.get("rnc", "") or "") for c in self._items):
                QMessageBox.warning(self, "Duplicado", "Ya existe un competidor con ese RNC.")
                return
        item.update(data)
        self._apply_filter()

    def _del(self):
        item = self._current()
        if not item:
            return
        if QMessageBox.question(self, "Confirmar", f"¿Eliminar a '{item.get('nombre','')}'?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        self._items = [c for c in self._items if c is not item]
        self._apply_filter()

    def _save_and_close(self):
        ok = self.db.save_competidores_maestros(self._items)
        if ok:
            QMessageBox.information(self, "Guardar", "Cambios guardados.")
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "No se pudieron guardar los cambios.")


class _CompetidorForm(QDialog):
    def __init__(self, parent, titulo: str, initial: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.setModal(True)
        self.resize(520, 200)
        init = initial or {}

        form = QFormLayout(self)
        self.txt_nom = QLineEdit(init.get("nombre", ""))
        form.addRow("Nombre:", self.txt_nom)
        self.txt_rnc = QLineEdit(init.get("rnc", ""))
        form.addRow("RNC:", self.txt_rnc)
        self.txt_rpe = QLineEdit(init.get("rpe", ""))
        form.addRow("No. RPE:", self.txt_rpe)
        self.txt_rep = QLineEdit(init.get("representante", ""))
        form.addRow("Representante:", self.txt_rep)

        btns = QHBoxLayout()
        b_ok = QPushButton("Guardar"); b_cancel = QPushButton("Cancelar")
        b_ok.clicked.connect(self.accept); b_cancel.clicked.connect(self.reject)
        btns.addStretch(1); btns.addWidget(b_ok); btns.addWidget(b_cancel)
        form.addRow(btns)

    def data(self) -> Dict[str, Any]:
        return {
            "nombre": self.txt_nom.text().strip(),
            "rnc": self.txt_rnc.text().strip(),
            "rpe": self.txt_rpe.text().strip(),
            "representante": self.txt_rep.text().strip(),
        }