# app/ui/dialogs/dialogo_seleccionar_institucion.py
from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict, Any, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QDialogButtonBox, QLineEdit,
    QLabel, QPushButton, QWidget, QMessageBox, QStyle
)
from PyQt6.QtCore import Qt, QModelIndex

# Importar el diálogo para gestionar el catálogo
from .dialogo_gestionar_instituciones import DialogoGestionarInstituciones

if TYPE_CHECKING:
    from app.core.db_adapter import DatabaseAdapter

class DialogoSeleccionarInstitucion(QDialog):
    """
    Diálogo para buscar, seleccionar y (opcionalmente) añadir una institución
    desde el catálogo maestro.
    """
    COL_NOMBRE = 0
    COL_RNC = 1

    def __init__(self, parent: QWidget, db_adapter: DatabaseAdapter):
        super().__init__(parent)
        self.db = db_adapter
        self.lista_instituciones: List[Dict[str, Any]] = [] # Cache de datos
        self.institucion_seleccionada: Optional[Dict[str, Any]] = None

        self.setWindowTitle("Seleccionar Institución")
        self.setMinimumSize(600, 400)
        flags = self.windowFlags()
        self.setWindowFlags(flags | Qt.WindowType.WindowMaximizeButtonHint)

        self._build_ui()
        self.refrescar_lista() # Carga inicial

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        style = self.style()

        # --- Filtro ---
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("🔍 Buscar:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Filtrar por nombre o RNC...")
        self.search_edit.textChanged.connect(self._aplicar_filtro)
        filter_layout.addWidget(self.search_edit)
        main_layout.addLayout(filter_layout)

        # --- Tabla de Instituciones ---
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Nombre", "RNC"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(self.COL_NOMBRE, QHeaderView.ResizeMode.Stretch)
        header.resizeSection(self.COL_RNC, 150)
        
        self.table.doubleClicked.connect(self.accept) # Doble clic para aceptar
        main_layout.addWidget(self.table)

        # --- Botonera Inferior ---
        button_layout = QHBoxLayout()
        
        # Botón para añadir nueva
        self.btn_gestionar = QPushButton(" Gestionar Catálogo...")
        self.btn_gestionar.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder))
        self.btn_gestionar.setToolTip("Añadir, editar o eliminar instituciones del maestro")
        self.btn_gestionar.clicked.connect(self._abrir_gestor_catalogo)
        button_layout.addWidget(self.btn_gestionar)
        
        button_layout.addStretch(1)

        # Botones OK/Cancel
        self.dialog_buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.dialog_buttons.accepted.connect(self.accept)
        self.dialog_buttons.rejected.connect(self.reject)
        button_layout.addWidget(self.dialog_buttons)
        
        main_layout.addLayout(button_layout)

    def refrescar_lista(self, seleccionar_nombre: Optional[str] = None):
        """Recarga la lista de instituciones desde la BD y actualiza la tabla."""
        try:
            self.lista_instituciones = self.db.get_instituciones_maestras()
            self._aplicar_filtro() # Rellena la tabla con los datos (y filtro si hay)

            if seleccionar_nombre:
                self._seleccionar_item_por_nombre(seleccionar_nombre)

        except Exception as e:
            QMessageBox.critical(self, "Error de Carga", f"No se pudo recargar la lista de instituciones:\n{e}")
            self.lista_instituciones = []

    def _aplicar_filtro(self):
        """Filtra y (re)puebla la tabla."""
        self.table.blockSignals(True)
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        
        filtro = self.search_edit.text().strip().lower()
        
        instituciones_filtradas = self.lista_instituciones
        if filtro:
            instituciones_filtradas = [
                inst for inst in self.lista_instituciones
                if filtro in (inst.get('nombre', '') or '').lower() or
                   filtro in (inst.get('rnc', '') or '').lower()
            ]

        for inst_data in instituciones_filtradas:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            nombre = inst_data.get('nombre', '')
            rnc = inst_data.get('rnc', '')
            
            item_nombre = QTableWidgetItem(nombre)
            # Guardar el dict completo en el item para fácil recuperación
            item_nombre.setData(Qt.ItemDataRole.UserRole, inst_data) 
            item_rnc = QTableWidgetItem(rnc)
            
            self.table.setItem(row, self.COL_NOMBRE, item_nombre)
            self.table.setItem(row, self.COL_RNC, item_rnc)

        self.table.setSortingEnabled(True)
        self.table.blockSignals(False)

    def _seleccionar_item_por_nombre(self, nombre: str):
        """Busca y selecciona una fila por el nombre de la institución."""
        for row in range(self.table.rowCount()):
            item_nombre = self.table.item(row, self.COL_NOMBRE)
            if item_nombre and item_nombre.text() == nombre:
                self.table.selectRow(row)
                self.table.scrollToItem(item_nombre, QAbstractItemView.ScrollHint.PositionAtCenter)
                break

    def _abrir_gestor_catalogo(self):
        """
        Abre el gestor de instituciones. Al cerrarse, refresca la lista.
        """
        # Guardamos el nombre de la institución seleccionada actualmente (si hay una)
        nombre_seleccionado_antes = self.get_selected_data().get('nombre') if self.get_selected_data() else None

        dlg_gestor = DialogoGestionarInstituciones(self, self.db)
        dlg_gestor.exec() # Espera a que se cierre

        # --- Refresco automático ---
        print("Refrescando lista de instituciones después de cerrar el gestor...")
        self.refrescar_lista(seleccionar_nombre=nombre_seleccionado_antes)

    def get_selected_data(self) -> Optional[Dict[str, Any]]:
        """Obtiene el diccionario de datos de la fila seleccionada."""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return None
        
        # Obtener el item de la primera columna (Nombre) de la fila seleccionada
        item_nombre = self.table.item(selected_rows[0].row(), self.COL_NOMBRE)
        if not item_nombre:
            return None
        
        # Devolver el diccionario completo que guardamos
        return item_nombre.data(Qt.ItemDataRole.UserRole)

    def accept(self):
        """Al presionar OK, guarda la selección."""
        seleccion = self.get_selected_data()
        if not seleccion:
            QMessageBox.warning(self, "Sin Selección", "Por favor, selecciona una institución de la lista.")
            return # No cerrar

        self.institucion_seleccionada = seleccion
        super().accept()