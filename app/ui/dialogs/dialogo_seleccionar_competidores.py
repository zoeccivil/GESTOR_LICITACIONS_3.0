# app/ui/dialogs/dialogo_seleccionar_competidores.py
from __future__ import annotations
from typing import List, Dict, Any, Set

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QTableWidget, QTableWidgetItem,
    QAbstractItemView, QHeaderView, QDialogButtonBox, QLabel, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

# Importar Oferente para type hinting
from app.core.models import Oferente

# Índice de columnas para la tabla
COL_SEL = 0
COL_NOMBRE = 1
COL_RNC = 2

class DialogoSeleccionarCompetidores(QDialog):
    """
    Diálogo para seleccionar múltiples competidores de una lista maestra, con búsqueda.
    """
    def __init__(self, parent,
                 competidores_maestros: List[Dict[str, Any]],
                 oferentes_actuales: List[Oferente]):
        super().__init__(parent)
        self.setWindowTitle("Seleccionar Competidores desde Catálogo")
        self.setMinimumSize(600, 450)

        # 1. Filtrar competidores disponibles
        nombres_actuales_lower = {o.nombre.lower() for o in oferentes_actuales}
        self.competidores_disponibles = sorted(
            [c for c in competidores_maestros if c.get('nombre', '').lower() not in nombres_actuales_lower],
            key=lambda x: x.get('nombre', '')
        )
        self.competidores_filtrados = self.competidores_disponibles[:]

        # 2. Estado de selección (guardamos los nombres seleccionados)
        self.seleccionados: Set[str] = set()
        self.result: List[Dict[str, Any]] = [] # Lista de dicts de competidores seleccionados

        # 3. Timer para debounce de búsqueda
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250) # 250ms delay
        self._search_timer.timeout.connect(self._filtrar_y_poblar)

        # 4. Construir UI
        self._build_ui()
        self._poblar_tabla() # Llenar tabla inicial

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Búsqueda ---
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("🔍 Buscar:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Filtrar por nombre o RNC...")
        # Conectar textChanged al timer
        self.search_edit.textChanged.connect(self._search_timer.start)
        search_layout.addWidget(self.search_edit)
        main_layout.addLayout(search_layout)

        # --- Tabla ---
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Sel.", "Nombre del Competidor", "RNC"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection) # Sin selección de fila
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers) # No editable

        # Ajuste de columnas
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(COL_SEL, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COL_NOMBRE, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(COL_RNC, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(COL_RNC, 120)

        main_layout.addWidget(self.table)

        # Conectar clic en celda para manejar checkboxes
        self.table.cellClicked.connect(self._on_cell_clicked)

        # --- Botones OK/Cancelar ---
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

    def _filtrar_y_poblar(self):
        """ Filtra la lista y actualiza la tabla. """
        termino = self.search_edit.text().strip().lower()
        if not termino:
            self.competidores_filtrados = self.competidores_disponibles[:]
        else:
            self.competidores_filtrados = [
                c for c in self.competidores_disponibles
                if termino in c.get('nombre', '').lower() or termino in (c.get('rnc', '') or '').lower()
            ]
        self._poblar_tabla()

    def _poblar_tabla(self):
        """ Limpia y llena la QTableWidget. """
        self.table.setRowCount(0) # Limpiar tabla
        self.table.setRowCount(len(self.competidores_filtrados))

        for row, comp_dict in enumerate(self.competidores_filtrados):
            nombre = comp_dict.get('nombre', '')
            rnc = comp_dict.get('rnc', '')

            # Item Checkbox (Columna 0)
            item_sel = QTableWidgetItem()
            item_sel.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            # Marcar si el nombre está en nuestro set de seleccionados
            check_state = Qt.CheckState.Checked if nombre in self.seleccionados else Qt.CheckState.Unchecked
            item_sel.setCheckState(check_state)
            # Guardar el nombre en UserRole para identificar la fila al hacer clic
            item_sel.setData(Qt.ItemDataRole.UserRole, nombre)
            self.table.setItem(row, COL_SEL, item_sel)

            # Item Nombre (Columna 1)
            item_nombre = QTableWidgetItem(nombre)
            item_nombre.setFlags(Qt.ItemFlag.ItemIsEnabled) # No seleccionable
            self.table.setItem(row, COL_NOMBRE, item_nombre)

            # Item RNC (Columna 2)
            item_rnc = QTableWidgetItem(rnc)
            item_rnc.setFlags(Qt.ItemFlag.ItemIsEnabled) # No seleccionable
            self.table.setItem(row, COL_RNC, item_rnc)

    def _on_cell_clicked(self, row: int, column: int):
        """ Maneja el clic en cualquier celda para marcar/desmarcar el checkbox de esa fila. """
        item_sel = self.table.item(row, COL_SEL)
        if not item_sel: return

        nombre = item_sel.data(Qt.ItemDataRole.UserRole)
        if not nombre: return

        # Invertir estado actual del checkbox
        current_state = item_sel.checkState()
        new_state = Qt.CheckState.Unchecked if current_state == Qt.CheckState.Checked else Qt.CheckState.Checked
        item_sel.setCheckState(new_state)

        # Actualizar nuestro set de seleccionados
        if new_state == Qt.CheckState.Checked:
            self.seleccionados.add(nombre)
        else:
            self.seleccionados.discard(nombre) # discard no da error si no existe

    def accept(self):
        """ Prepara la lista de resultados antes de cerrar. """
        # Buscar los dicts completos de los nombres seleccionados
        self.result = [
            comp_dict for comp_dict in self.competidores_disponibles # Buscar en disponibles (sin filtro)
            if comp_dict.get('nombre') in self.seleccionados
        ]
        super().accept() # Cerrar el diálogo

    def get_seleccionados(self) -> List[Dict[str, Any]]:
        """ Devuelve la lista de diccionarios de los competidores seleccionados. """
        return self.result