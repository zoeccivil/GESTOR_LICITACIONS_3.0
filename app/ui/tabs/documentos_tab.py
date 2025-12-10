# app/ui/tabs/documentos_tab.py
from __future__ import annotations
from typing import List, Optional
import os
import sys
import subprocess

# --- Importaciones de PyQt6 ---
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QIcon # Añadido QDesktopServices, QIcon
from PyQt6.QtWidgets import (
    QWidget, QDialog,
 
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QMessageBox,
    QHeaderView,
    QFileDialog,
    QStyle # Añadido QStyle
)
# --- Fin Importaciones de PyQt6 ---

from app.core.models import Documento

# --- CORRECCIÓN DE IMPORTACIÓN ---
# La importación debe ser absoluta desde 'app' o relativa (..)
from app.ui.dialogs.gestionar_documento_dialog import DialogoGestionarDocumento
# --- FIN CORRECCIÓN ---


class TabDocumentos(QWidget):
    """
    Pestaña Documentos con QTreeWidget:
    - Añadir, editar, eliminar
    - Adjuntar, Quitar, Abrir archivo
    Columnas: Código, Nombre, Categoría, Oblig., Subsanable, Presentado, Revisado, Responsable, Archivo
    """
    COL_COD = 0
    COL_NOMBRE = 1
    COL_CAT = 2
    COL_OBLIG = 3
    COL_SUBS = 4
    COL_PRES = 5
    COL_REV = 6
    COL_RESP = 7
    COL_FILE = 8

    def __init__(self, parent: QWidget, responsables: Optional[List[str]] = None, categories: Optional[List[str]] = None):
        super().__init__(parent)
        self.responsables = responsables or []
        self.categories = categories or ["Legal", "Técnica", "Financiera", "Sobre B", "Otros"] # Default
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        style = self.style() # Para iconos

        # Barra de acciones
        actions = QHBoxLayout()
        self.btn_add = QPushButton(" Añadir", self)
        self.btn_add.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_ListAdd))
        self.btn_edit = QPushButton(" Editar", self)
        self.btn_edit.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        self.btn_delete = QPushButton(" Eliminar", self)
        self.btn_delete.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        self.btn_attach = QPushButton(" Adjuntar…", self)
        self.btn_attach.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DriveHDIcon))
        self.btn_remove = QPushButton(" Quitar archivo", self)
        self.btn_remove.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton))
        self.btn_open = QPushButton(" Abrir archivo", self)
        self.btn_open.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton))


        for b in (self.btn_add, self.btn_edit, self.btn_delete, self.btn_attach, self.btn_remove, self.btn_open):
            actions.addWidget(b)
        actions.addStretch(1)
        layout.addLayout(actions)

        # Árbol
        self.tree = QTreeWidget(self)
        self.tree.setColumnCount(9)
        self.tree.setHeaderLabels(["Código", "Nombre", "Categoría", "Oblig.", "Subsanable", "Presentado", "Revisado", "Responsable", "Archivo"])
        self.tree.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.tree.header().setSectionResizeMode(self.COL_NOMBRE, QHeaderView.ResizeMode.Stretch) # Estirar nombre
        self.tree.header().setSectionResizeMode(self.COL_FILE, QHeaderView.ResizeMode.Stretch) # Estirar archivo
        self.tree.setSortingEnabled(True)
        self.tree.setAlternatingRowColors(True)
        layout.addWidget(self.tree)

        # Conexiones
        self.btn_add.clicked.connect(self._on_add)
        self.btn_edit.clicked.connect(self._on_edit)
        self.btn_delete.clicked.connect(self._on_delete)
        self.btn_attach.clicked.connect(self._on_attach)
        self.btn_remove.clicked.connect(self._on_remove)
        self.btn_open.clicked.connect(self._on_open)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)

    # Public API
    def load_documentos(self, documentos: List[Documento]):
        self.tree.clear()
        if not documentos:
            return
        for d in documentos:
            self._add_item_for_doc(d)

    def to_documentos(self) -> List[Documento]:
        documentos: List[Documento] = []
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            it = root.child(i)
            doc: Documento = it.data(0, Qt.ItemDataRole.UserRole)  # type: ignore
            if doc:
                documentos.append(doc)
        return documentos

    # Helpers
    def _add_item_for_doc(self, d: Documento):
        it = QTreeWidgetItem(self.tree)
        self._fill_item(it, d)
        self.tree.addTopLevelItem(it)

    def _fill_item(self, it: QTreeWidgetItem, d: Documento):
        it.setText(self.COL_COD, d.codigo or "")
        it.setText(self.COL_NOMBRE, d.nombre or "")
        it.setText(self.COL_CAT, d.categoria or "")
        it.setText(self.COL_OBLIG, "Sí" if d.obligatorio else "No")
        it.setText(self.COL_SUBS, d.subsanable or "Subsanable")
        it.setText(self.COL_PRES, "✓" if d.presentado else "No")
        it.setText(self.COL_REV, "✓" if d.revisado else "No")
        it.setText(self.COL_RESP, d.responsable or "Sin Asignar")
        it.setText(self.COL_FILE, d.ruta_archivo or "")
        # Guardar el objeto Documento en el item
        it.setData(0, Qt.ItemDataRole.UserRole, d)

    def _get_selected_item(self) -> Optional[QTreeWidgetItem]:
        items = self.tree.selectedItems()
        return items[0] if items else None

    def _on_add(self):
        # Asumir que DialogoGestionarDocumento está corregido
        dlg = DialogoGestionarDocumento(self, "Añadir Documento", initial_data=None, categories=self.categories, responsables=self.responsables)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.resultado:
            data = dlg.resultado or {}
            d = Documento(**data) # Crear Documento desde el dict
            self._add_item_for_doc(d)

    def _on_edit(self):
        it = self._get_selected_item()
        if not it:
            QMessageBox.information(self, "Editar", "Selecciona un documento para editar.")
            return
        d: Documento = it.data(0, Qt.ItemDataRole.UserRole)  # type: ignore
        dlg = DialogoGestionarDocumento(self, "Editar Documento", initial_data=d, categories=self.categories, responsables=self.responsables)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.resultado:
            data = dlg.resultado or {}
            # Actualizar el objeto Documento existente
            for key, value in data.items():
                if hasattr(d, key):
                    setattr(d, key, value)
            self._fill_item(it, d) # Refrescar la fila del árbol

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        self._on_edit() # Doble clic es igual a editar

    def _on_delete(self):
        it = self._get_selected_item()
        if not it:
            QMessageBox.information(self, "Eliminar", "Selecciona un documento para eliminar.")
            return
        # Usar botones estándar de PyQt
        res = QMessageBox.question(self, "Confirmar", "¿Eliminar el documento seleccionado?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if res == QMessageBox.StandardButton.Yes:
            idx = self.tree.indexOfTopLevelItem(it)
            self.tree.takeTopLevelItem(idx)

    def _on_attach(self):
        it = self._get_selected_item()
        if not it:
            QMessageBox.information(self, "Adjuntar", "Selecciona un documento.")
            return
        # Usar QFileDialog de PyQt
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo", "", "Todos los Archivos (*.*)")
        if not path:
            return
        d: Documento = it.data(0, Qt.ItemDataRole.UserRole)  # type: ignore
        d.ruta_archivo = path
        d.presentado = True # Marcar como presentado al adjuntar
        self._fill_item(it, d)

    def _on_remove(self):
        it = self._get_selected_item()
        if not it:
            QMessageBox.information(self, "Quitar archivo", "Selecciona un documento.")
            return
        d: Documento = it.data(0, Qt.ItemDataRole.UserRole)  # type: ignore
        d.ruta_archivo = ""
        d.presentado = False # Marcar como no presentado
        self._fill_item(it, d)

    # --- MÉTODO _on_open CORREGIDO Y MODERNIZADO ---
    def _on_open(self):
        it = self._get_selected_item()
        if not it:
            QMessageBox.information(self, "Abrir", "Selecciona un documento.")
            return
        d: Documento = it.data(0, Qt.ItemDataRole.UserRole)  # type: ignore
        
        # Asumir que la ruta puede ser relativa (necesita utils.reconstruir_ruta_absoluta)
        try:
            from app.core.utils import reconstruir_ruta_absoluta
            path = reconstruir_ruta_absoluta((d.ruta_archivo or "").strip())
        except ImportError:
            # Fallback si utils no está listo
            path = (d.ruta_archivo or "").strip()

        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "Abrir", f"El archivo no existe o no hay ruta asignada.\n{path}")
            return
        
        try:
            # Usar QDesktopServices para abrir el archivo de forma multiplataforma
            url = QUrl.fromLocalFile(path)
            if not QDesktopServices.openUrl(url):
                 QMessageBox.critical(self, "Abrir", f"No se pudo abrir el archivo con la aplicación predeterminada.\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Abrir", f"No se pudo abrir el archivo.\n{e}")