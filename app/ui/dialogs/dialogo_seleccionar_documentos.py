# app/ui/dialogs/dialogo_seleccionar_documentos.py
from __future__ import annotations
from typing import List, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QDialogButtonBox, QLineEdit,
    QLabel, QComboBox, QWidget, QMessageBox
)
from PyQt6.QtCore import Qt, QModelIndex

from app.core.models import Documento

class DialogoSeleccionarDocumentos(QDialog):
    """
    Diálogo para seleccionar múltiples documentos de una lista maestra,
    con filtros por búsqueda y categoría.
    """
    COL_CHECK = 0
    COL_CODIGO = 1
    COL_NOMBRE = 2
    COL_CATEGORIA = 3

    def __init__(self, parent: QWidget, title: str,
                 documentos_maestros: List[Documento],
                 documentos_actuales: List[Documento]):
        super().__init__(parent)
        
        # Filtrar documentos que ya están en la licitación (por código)
        codigos_actuales = {doc.codigo for doc in documentos_actuales if doc.codigo}
        self.documentos_disponibles = [
            doc for doc in documentos_maestros if doc.codigo not in codigos_actuales
        ]
        self.documentos_disponibles.sort(key=lambda d: (d.categoria or "Z", d.codigo or ""))
        
        # Categorías para el filtro (basadas en los documentos disponibles)
        categorias_unicas = sorted(list(set(doc.categoria for doc in self.documentos_disponibles if doc.categoria)))
        self.categorias_filtro = ["Todas"] + categorias_unicas

        self.selected_docs: List[Documento] = [] # Resultado

        self.setWindowTitle(title)
        self.setMinimumSize(800, 500)
        # Hacer redimensionable y maximizable
        flags = self.windowFlags()
        self.setWindowFlags(flags | Qt.WindowType.WindowMaximizeButtonHint | Qt.WindowType.WindowMinimizeButtonHint)
        
        self._build_ui()
        self._populate_table(self.documentos_disponibles) # Carga inicial

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Panel de Filtros ---
        filter_frame = QWidget()
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(0,0,0,5)
        
        filter_layout.addWidget(QLabel("🔍 Buscar:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Buscar por código o nombre...")
        self.search_edit.textChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.search_edit)

        filter_layout.addWidget(QLabel("Categoría:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems(self.categorias_filtro)
        self.category_combo.currentTextChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.category_combo)
        
        main_layout.addWidget(filter_frame)

        # --- Tabla de Documentos ---
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Sel.", "Código", "Nombre del Documento", "Categoría"])
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setSortingEnabled(False) # El filtrado maneja el orden
        self.table.setAlternatingRowColors(True)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.resizeSection(self.COL_CHECK, 40)
        header.setSectionResizeMode(self.COL_CHECK, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(self.COL_CODIGO, 150)
        header.setSectionResizeMode(self.COL_NOMBRE, QHeaderView.ResizeMode.Stretch)
        header.resizeSection(self.COL_CATEGORIA, 120)
        
        self.table.clicked.connect(self._toggle_checkbox) # Clic en celda
        main_layout.addWidget(self.table)

        # --- Botones OK/Cancel ---
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

    def _populate_table(self, documentos_a_mostrar: List[Documento]):
        """Llena la tabla con los documentos dados."""
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        
        for doc in documentos_a_mostrar:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # Checkbox item (Col 0)
            item_check = QTableWidgetItem()
            item_check.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            check_state = Qt.CheckState.Checked if doc in self.selected_docs else Qt.CheckState.Unchecked
            item_check.setCheckState(check_state)
            item_check.setData(Qt.ItemDataRole.UserRole, doc) # Guardar objeto aquí
            
            # Data items
            item_codigo = QTableWidgetItem(doc.codigo or "")
            item_nombre = QTableWidgetItem(doc.nombre or "")
            item_categoria = QTableWidgetItem(doc.categoria or "")
            # Hacer items no editables
            item_codigo.setFlags(Qt.ItemFlag.ItemIsEnabled)
            item_nombre.setFlags(Qt.ItemFlag.ItemIsEnabled)
            item_categoria.setFlags(Qt.ItemFlag.ItemIsEnabled)

            self.table.setItem(row, self.COL_CHECK, item_check)
            self.table.setItem(row, self.COL_CODIGO, item_codigo)
            self.table.setItem(row, self.COL_NOMBRE, item_nombre)
            self.table.setItem(row, self.COL_CATEGORIA, item_categoria)

        self.table.blockSignals(False)

    def _apply_filters(self):
        """Filtra la lista de documentos basada en los controles de UI."""
        search_term = self.search_edit.text().strip().lower()
        categoria_sel = self.category_combo.currentText()

        documentos_filtrados = []
        for doc in self.documentos_disponibles:
            if categoria_sel != "Todas" and (doc.categoria or "") != categoria_sel:
                continue
            if search_term and (search_term not in (doc.nombre or "").lower()) and \
                             (search_term not in (doc.codigo or "").lower()):
                continue
            documentos_filtrados.append(doc)
            
        self._populate_table(documentos_filtrados)

    def _toggle_checkbox(self, index: QModelIndex):
        """Maneja el clic en cualquier celda para cambiar el checkbox de esa fila."""
        if not index.isValid(): return
        
        item_check = self.table.item(index.row(), self.COL_CHECK)
        if not item_check: return
        
        doc = item_check.data(Qt.ItemDataRole.UserRole)
        if not doc: return

        current_state = item_check.checkState()
        if current_state == Qt.CheckState.Checked:
            item_check.setCheckState(Qt.CheckState.Unchecked)
            if doc in self.selected_docs:
                self.selected_docs.remove(doc)
        else:
            item_check.setCheckState(Qt.CheckState.Checked)
            if doc not in self.selected_docs:
                self.selected_docs.append(doc)
                
    def accept(self):
        """Se llama al presionar OK."""
        if not self.selected_docs:
            QMessageBox.warning(self, "Sin Selección", "No se seleccionó ningún documento.")
            # No cerramos, permitimos al usuario seleccionar
            return 
        
        print(f"DialogoSeleccionarDocumentos: Seleccionados {len(self.selected_docs)} documentos.")
        super().accept()

    def get_selected_docs(self) -> List[Documento]:
        """Devuelve la lista de objetos Documento seleccionados."""
        return self.selected_docs