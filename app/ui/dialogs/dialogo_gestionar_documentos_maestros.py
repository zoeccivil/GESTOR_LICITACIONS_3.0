from __future__ import annotations
from typing import List, Dict, Any, Optional

import os
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QIcon, QKeySequence, QShortcut, QDesktopServices
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QFileDialog,
    QWidget, QFormLayout
)

from app.core.db_adapter import DatabaseAdapter
from app.core.models import Documento

class DialogoGestionarDocumentosMaestros(QDialog):
    COL_ADJ = 0
    COL_COD = 1
    COL_NOM = 2
    COL_CAT = 3

    def __init__(self, parent, db: DatabaseAdapter):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Gestor de Plantillas de Documentos (Global)")
        self.resize(950, 650)
        self.setModal(True)

        # Lista completa de documentos maestros (global)
        self._docs: List[Documento] = self.db.get_documentos_maestros()

        # Categorías únicas (para filtro)
        self._categorias = sorted({(getattr(d, "categoria", "") or "").strip() for d in self._docs if getattr(d, "categoria", "").strip()})
        self._categorias = ["Todas"] + self._categorias

        self._build_ui()
        self._populate_table()

    def _build_ui(self):
        root = QVBoxLayout(self)

        # Filtros (sin empresa)
        filt = QGroupBox("Filtros")
        fl = QHBoxLayout(filt)

        fl.addWidget(QLabel("Buscar:"))
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Buscar por código o nombre…")
        self.txt_search.textChanged.connect(self._populate_table)
        fl.addWidget(self.txt_search, 1)

        fl.addWidget(QLabel("Categoría:"))
        self.cmb_categoria = QComboBox()
        self.cmb_categoria.addItems(self._categorias)
        self.cmb_categoria.currentIndexChanged.connect(self._populate_table)
        fl.addWidget(self.cmb_categoria, 0)

        root.addWidget(filt)

        # Tabla
        gb = QGroupBox("Plantillas de Documentos (Global)")
        gl = QVBoxLayout(gb)

        self.tbl = QTableWidget(0, 4)
        self.tbl.setHorizontalHeaderLabels(["Adj.", "Código", "Nombre del Documento", "Categoría"])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.setSelectionBehavior(self.tbl.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(self.tbl.SelectionMode.SingleSelection)
        self.tbl.horizontalHeader().setSectionResizeMode(self.COL_NOM, QHeaderView.ResizeMode.Stretch)
        self.tbl.horizontalHeader().setSectionResizeMode(self.COL_COD, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(self.COL_CAT, QHeaderView.ResizeMode.ResizeToContents)
        gl.addWidget(self.tbl, 1)

        # Acciones
        actions = QHBoxLayout()
        self.btn_add = QPushButton("➕ Agregar")
        self.btn_edit = QPushButton("✏️ Editar")
        self.btn_del = QPushButton("🗑 Eliminar")
        self.btn_attach = QPushButton("📎 Adjuntar Plantilla")
        self.btn_open = QPushButton("📂 Ver Plantilla")
        self.btn_remove = QPushButton("❌ Quitar Plantilla")
        self.btn_close = QPushButton("✅ Guardar y Cerrar")

        self.btn_add.clicked.connect(self._add)
        self.btn_edit.clicked.connect(self._edit)
        self.btn_del.clicked.connect(self._delete)
        self.btn_attach.clicked.connect(self._attach)
        self.btn_open.clicked.connect(self._open_file)
        self.btn_remove.clicked.connect(self._remove_file)
        self.btn_close.clicked.connect(self._save_and_close)

        for b in (self.btn_add, self.btn_edit, self.btn_del, self.btn_attach, self.btn_open, self.btn_remove):
            actions.addWidget(b)
        actions.addStretch(1)
        actions.addWidget(self.btn_close)
        gl.addLayout(actions)

        root.addWidget(gb)

        # Atajos
        QShortcut(QKeySequence("Delete"), self, activated=self._delete)
        QShortcut(QKeySequence("Ctrl+N"), self, activated=self._add)
        QShortcut(QKeySequence("Ctrl+E"), self, activated=self._edit)

        self.tbl.itemSelectionChanged.connect(self._update_actions_enabled)
        self._update_actions_enabled()

    def _filtered_docs(self) -> List[Documento]:
        srch = (self.txt_search.text() or "").strip().lower()
        cat = self.cmb_categoria.currentText().strip()
        out: List[Documento] = []
        for d in self._docs:
            if cat and cat != "Todas" and (getattr(d, "categoria", "") or "") != cat:
                continue
            if srch and (srch not in (getattr(d, "nombre", "") or "").lower()) and (srch not in (getattr(d, "codigo", "") or "").lower()):
                continue
            out.append(d)
        return out

    def _populate_table(self):
        docs = self._filtered_docs()
        self.tbl.setRowCount(0)
        for d in sorted(docs, key=lambda x: ((getattr(x, "categoria", "") or ""), (getattr(x, "nombre", "") or ""))):
            row = self.tbl.rowCount()
            self.tbl.insertRow(row)
            adj = "📎" if (getattr(d, "ruta_archivo", "") or "") else ""
            for col, text in (
                (self.COL_ADJ, adj),
                (self.COL_COD, getattr(d, "codigo", "") or ""),
                (self.COL_NOM, getattr(d, "nombre", "") or ""),
                (self.COL_CAT, getattr(d, "categoria", "") or ""),
            ):
                item = QTableWidgetItem(text)
                if col == self.COL_ADJ:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tbl.setItem(row, col, item)
            self.tbl.setRowHeight(row, 24)
        self._update_actions_enabled()

    def _current_doc(self) -> Optional[Documento]:
        r = self.tbl.currentRow()
        if r < 0:
            return None
        cod = self.tbl.item(r, self.COL_COD).text()
        nom = self.tbl.item(r, self.COL_NOM).text()
        # selección por combinación código+nombre (global)
        for d in self._docs:
            if (getattr(d, "codigo", "") or "") == cod and (getattr(d, "nombre", "") or "") == nom:
                return d
        return None

    def _update_actions_enabled(self):
        has = self._current_doc() is not None
        for b in (self.btn_edit, self.btn_del, self.btn_attach, self.btn_open, self.btn_remove):
            b.setEnabled(has)
        d = self._current_doc()
        has_file = bool(d and (getattr(d, "ruta_archivo", "") or ""))
        self.btn_open.setEnabled(has and has_file)
        self.btn_remove.setEnabled(has and has_file)

    # ----- acciones -----
    def _add(self):
        dlg = _DocForm(self, titulo="Nueva Plantilla", categorias=[c for c in self._categorias if c and c != "Todas"])
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        data = dlg.data()
        # Duplicado global por código (case-insensitive)
        if any((getattr(d, "codigo", "") or "").lower() == data["codigo"].lower() for d in self._docs):
            QMessageBox.warning(self, "Duplicado", f"Ya existe un documento con el código '{data['codigo']}'.")
            return
        doc = Documento(
            codigo=data["codigo"], nombre=data["nombre"], categoria=data["categoria"],
            comentario=data.get("comentario", ""), ruta_archivo=""
        )
        # Neutralizar empresa si el modelo aún la tiene
        if hasattr(doc, "empresa_nombre"):
            setattr(doc, "empresa_nombre", None)
        self._docs.append(doc)
        self._populate_table()

    def _edit(self):
        d = self._current_doc()
        if not d:
            return
        init = {
            "codigo": getattr(d, "codigo", "") or "",
            "nombre": getattr(d, "nombre", "") or "",
            "categoria": getattr(d, "categoria", "") or "",
            "comentario": getattr(d, "comentario", "") or "",
        }
        dlg = _DocForm(self, "Editar Plantilla", categorias=[c for c in self._categorias if c and c != "Todas"], initial=init)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        data = dlg.data()
        # Si cambia código, validar duplicado global
        if data["codigo"].lower() != (getattr(d, "codigo", "") or "").lower():
            if any((getattr(x, "codigo", "") or "").lower() == data["codigo"].lower() for x in self._docs):
                QMessageBox.warning(self, "Duplicado", f"Ya existe un documento con el código '{data['codigo']}'.")
                return
        d.codigo = data["codigo"]
        d.nombre = data["nombre"]
        d.categoria = data["categoria"]
        d.comentario = data.get("comentario", "")
        # Neutralizar empresa si existe en el modelo
        if hasattr(d, "empresa_nombre"):
            setattr(d, "empresa_nombre", None)
        self._populate_table()

    def _delete(self):
        d = self._current_doc()
        if not d:
            return
        if QMessageBox.question(self, "Confirmar", f"¿Eliminar la plantilla '{getattr(d, 'nombre', '')}'?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        self._docs = [x for x in self._docs if x is not d]
        self._populate_table()

    def _attach(self):
        d = self._current_doc()
        if not d:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar Archivo de Plantilla", filter="Todos (*.*)")
        if not path:
            return
        d.ruta_archivo = path
        self._populate_table()

    def _open_file(self):
        d = self._current_doc()
        if not d:
            return
        ruta = getattr(d, "ruta_archivo", "") or ""
        if not ruta or not os.path.exists(ruta):
            QMessageBox.warning(self, "Archivo no encontrado", "No hay archivo adjunto o la ruta no existe.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(ruta))

    def _remove_file(self):
        d = self._current_doc()
        if not d:
            return
        d.ruta_archivo = ""
        self._populate_table()

    def _save_and_close(self):
        ok = self.db.save_documentos_maestros(self._docs)
        if ok:
            QMessageBox.information(self, "Guardar", "Cambios guardados.")
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "No se pudieron guardar los cambios.")


class _DocForm(QDialog):
    def __init__(self, parent, titulo: str, categorias: List[str], initial: Optional[Dict[str, str]] = None):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.setModal(True)
        self.resize(500, 200)
        init = initial or {}

        form = QFormLayout(self)

        self.txt_cod = QLineEdit(init.get("codigo", ""))
        form.addRow("Código:", self.txt_cod)

        self.txt_nom = QLineEdit(init.get("nombre", ""))
        form.addRow("Nombre:", self.txt_nom)

        self.cmb_cat = QComboBox()
        self.cmb_cat.setEditable(True)
        self.cmb_cat.addItems([""] + categorias)
        self.cmb_cat.setCurrentText(init.get("categoria", ""))
        form.addRow("Categoría:", self.cmb_cat)

        self.txt_com = QLineEdit(init.get("comentario", ""))
        form.addRow("Comentario:", self.txt_com)

        btns = QHBoxLayout()
        b_ok = QPushButton("Guardar"); b_cancel = QPushButton("Cancelar")
        b_ok.clicked.connect(self.accept); b_cancel.clicked.connect(self.reject)
        btns.addStretch(1); btns.addWidget(b_ok); btns.addWidget(b_cancel)
        form.addRow(btns)

    def data(self) -> Dict[str, str]:
        return {
            "codigo": self.txt_cod.text().strip(),
            "nombre": self.txt_nom.text().strip(),
            "categoria": self.cmb_cat.currentText().strip(),
            "comentario": self.txt_com.text().strip(),
        }