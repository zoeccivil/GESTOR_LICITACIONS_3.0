# app/ui/dialogs/dialogo_confirmar_importacion.py
from __future__ import annotations
from typing import List, Dict, Any, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QDialogButtonBox, QLabel,
    QComboBox, QPushButton, QWidget, QMessageBox
)
from PyQt6.QtCore import Qt, QModelIndex

from app.core.models import Documento

class DialogoConfirmarImportacion(QDialog):
    """
    Diálogo para confirmar la importación de documentos y
    permitir la edición (individual o masiva) de su categoría destino.
    """
    COL_CODIGO = 0
    COL_NOMBRE = 1
    COL_CATEGORIA = 2

    def __init__(self, parent: QWidget,
                 documentos_seleccionados: List[Documento],
                 categorias_disponibles: List[str]):
        super().__init__(parent)
        
        self.documentos = documentos_seleccionados
        self.categorias_disponibles = categorias_disponibles
        self.result_data: List[Dict[str, Any]] = []

        self.setWindowTitle("Confirmar y Categorizar Documentos a Importar")
        self.setMinimumSize(800, 500)
        # Hacer redimensionable y maximizable
        flags = self.windowFlags()
        self.setWindowFlags(flags | Qt.WindowType.WindowMaximizeButtonHint | Qt.WindowType.WindowMinimizeButtonHint)
        
        self._build_ui()
        self._populate_table()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Panel de Acción Masiva ---
        bulk_frame = QWidget()
        bulk_layout = QHBoxLayout(bulk_frame)
        bulk_layout.setContentsMargins(0,0,0,5)
        
        bulk_layout.addWidget(QLabel("Aplicar esta categoría a TODOS:"))
        self.bulk_combo = QComboBox()
        self.bulk_combo.addItems(self.categorias_disponibles)
        bulk_layout.addWidget(self.bulk_combo)
        
        btn_apply_all = QPushButton("Aplicar a Todos")
        btn_apply_all.clicked.connect(self._aplicar_a_todos)
        bulk_layout.addWidget(btn_apply_all)
        bulk_layout.addStretch(1)
        
        main_layout.addWidget(bulk_frame)

        # --- Tabla de Documentos ---
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Código", "Nombre del Documento", "Categoría (Doble Clic para Editar)"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setSortingEnabled(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.resizeSection(self.COL_CODIGO, 150)
        header.setSectionResizeMode(self.COL_NOMBRE, QHeaderView.ResizeMode.Stretch)
        header.resizeSection(self.COL_CATEGORIA, 200)

        self.table.cellDoubleClicked.connect(self._editar_celda_categoria)
        main_layout.addWidget(self.table)

        # --- Botones OK/Cancel ---
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

    def _populate_table(self):
        """Llena la tabla con los documentos seleccionados."""
        self.table.blockSignals(True)
        self.table.setSortingEnabled(False) # Desactivar ordenamiento
        self.table.setRowCount(len(self.documentos))
        
        for row, doc in enumerate(self.documentos):
            item_codigo = QTableWidgetItem(doc.codigo or "")
            item_nombre = QTableWidgetItem(doc.nombre or "")
            item_categoria = QTableWidgetItem(doc.categoria or "")
            
            # Guardar el ID del documento maestro para referencia
            item_codigo.setData(Qt.ItemDataRole.UserRole, doc.id)
            
            # Hacer celdas no editables (solo vía doble clic en categoría)
            item_codigo.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            item_nombre.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            item_categoria.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)

            self.table.setItem(row, self.COL_CODIGO, item_codigo)
            self.table.setItem(row, self.COL_NOMBRE, item_nombre)
            self.table.setItem(row, self.COL_CATEGORIA, item_categoria)
            
        self.table.resizeRowsToContents()
        self.table.setSortingEnabled(True) # Reactivar ordenamiento
        self.table.blockSignals(False)

    def _aplicar_a_todos(self):
        """Aplica la categoría del combo masivo a todas las filas."""
        nueva_categoria = self.bulk_combo.currentText()
        if not nueva_categoria: return
        
        for row in range(self.table.rowCount()):
            item_categoria = self.table.item(row, self.COL_CATEGORIA)
            if item_categoria:
                item_categoria.setText(nueva_categoria)
            else:
                self.table.setItem(row, self.COL_CATEGORIA, QTableWidgetItem(nueva_categoria))
        print(f"Acción masiva: '{nueva_categoria}' aplicada a todas las filas.")

    def _editar_celda_categoria(self, row: int, column: int):
        """Maneja el doble clic para editar la celda de categoría."""
        if column != self.COL_CATEGORIA:
            return # Solo editar la columna de categoría

        # Crear un QComboBox in-place
        combo_editor = QComboBox()
        combo_editor.addItems(self.categorias_disponibles)
        
        valor_actual = self.table.item(row, column).text()
        if valor_actual in self.categorias_disponibles:
            combo_editor.setCurrentText(valor_actual)

        # Función anidada para guardar el valor cuando se cierre el combo
        def on_editor_closed():
            nuevo_valor = combo_editor.currentText()
            # Crear un nuevo item para asegurar que se limpie el widget
            item_nuevo = QTableWidgetItem(nuevo_valor)
            item_nuevo.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(row, column, item_nuevo)
            self.table.removeCellWidget(row, column)
            print(f"Celda ({row}, {column}) actualizada a '{nuevo_valor}'")

        # Conectar señales para cerrar el editor
        combo_editor.activated.connect(on_editor_closed) # Al seleccionar item
        combo_editor.lostFocus.connect(on_editor_closed) # Al perder foco

        # Poner el QComboBox en la celda
        self.table.setCellWidget(row, column, combo_editor)
        combo_editor.setFocus()
        combo_editor.showPopup()

    def accept(self):
        """Se llama al presionar OK. Recopila los datos."""
        self.result_data = []
        for row in range(self.table.rowCount()):
            item_codigo = self.table.item(row, self.COL_CODIGO)
            item_nombre = self.table.item(row, self.COL_NOMBRE)
            item_categoria = self.table.item(row, self.COL_CATEGORIA)
            
            if not item_codigo or not item_categoria: continue
            
            self.result_data.append({
                'id_maestro': item_codigo.data(Qt.ItemDataRole.UserRole), # ID del maestro
                'codigo': item_codigo.text(),
                'nombre': item_nombre.text() if item_nombre else "",
                'categoria': item_categoria.text()
            })
        
        print(f"DialogoConfirmarImportacion: Confirmados {len(self.result_data)} documentos.")
        super().accept()

    def get_result_data(self) -> List[Dict[str, Any]]:
        """Devuelve la lista de diccionarios con los datos confirmados."""
        return self.result_data