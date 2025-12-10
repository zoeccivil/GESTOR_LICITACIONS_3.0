from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QTreeWidget, QTreeWidgetItem,
    QLabel, QPushButton, QAbstractItemView
)
from PyQt6.QtCore import Qt

class SeleccionarEmpresasDialog(QDialog):
    """
    Diálogo para seleccionar múltiples empresas con búsqueda y checkboxes.
    Retorna los nombres seleccionados en self.resultado (lista de str).
    """
    def __init__(self, parent, todas_las_empresas, seleccion_actual=None):
        super().__init__(parent)
        self.setWindowTitle("Seleccionar Empresas Participantes")
        self.resize(500, 400)
        self.todas_las_empresas = sorted(todas_las_empresas, key=lambda x: x['nombre'])
        self.nombres_seleccionados = set(seleccion_actual or [])

        layout = QVBoxLayout(self)

        # Buscador
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("🔍 Buscar:"))
        self.search_edit = QLineEdit()
        self.search_edit.textChanged.connect(self._populate_tree)
        search_layout.addWidget(self.search_edit)
        layout.addLayout(search_layout)

        # TreeWidget con checkboxes
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Nombre de la Empresa"])
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.tree.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.tree, 1)
        self._populate_tree()

        # Botones
        btns = QHBoxLayout()
        btn_ok = QPushButton("Aceptar")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_ok)
        btns.addWidget(btn_cancel)
        layout.addLayout(btns)

        self.setLayout(layout)
        self.resultado = None

    def _populate_tree(self):
        self.tree.blockSignals(True)
        self.tree.clear()
        search_term = self.search_edit.text().lower()
        for empresa in self.todas_las_empresas:
            nombre = empresa['nombre']
            if search_term in nombre.lower():
                item = QTreeWidgetItem([nombre])
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                if nombre in self.nombres_seleccionados:
                    item.setCheckState(0, Qt.CheckState.Checked)
                else:
                    item.setCheckState(0, Qt.CheckState.Unchecked)
                self.tree.addTopLevelItem(item)
        self.tree.blockSignals(False)

    def _on_item_changed(self, item, column):
        nombre = item.text(0)
        if item.checkState(0) == Qt.CheckState.Checked:
            self.nombres_seleccionados.add(nombre)
        else:
            self.nombres_seleccionados.discard(nombre)

    def accept(self):
        # Retorna la lista de nombres seleccionados
        self.resultado = list(self.nombres_seleccionados)
        super().accept()