# app/ui/dialogs/gestionar_oferente_dialog.py
from __future__ import annotations
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLabel, QLineEdit, QTextEdit,
    QDialogButtonBox, QMessageBox
)
from PyQt6.QtCore import Qt

# Importar el modelo Oferente
from app.core.models import Oferente

class DialogoGestionarOferente(QDialog):
    """
    Diálogo para agregar o editar un Oferente (Competidor).
    """
    def __init__(self, parent, title="Gestionar Competidor", initial_data: Optional[Oferente] = None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(400)

        self.initial_data = initial_data
        self.result_oferente: Optional[Oferente] = None

        # --- Widgets ---
        self.nombre_edit = QLineEdit()
        self.comentario_edit = QTextEdit()
        self.comentario_edit.setFixedHeight(80) # Altura fija para el comentario

        # --- Layout ---
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.addRow("Nombre del Competidor:", self.nombre_edit)
        form_layout.addRow("Comentario Adicional:", self.comentario_edit)
        main_layout.addLayout(form_layout)

        # --- Botones OK/Cancelar ---
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        # --- Cargar datos iniciales si existen ---
        if self.initial_data:
            self.nombre_edit.setText(self.initial_data.nombre or "")
            self.comentario_edit.setPlainText(self.initial_data.comentario or "")

        # Foco inicial en el nombre
        self.nombre_edit.setFocus()

    def accept(self):
        """ Sobreescribir accept para validar y guardar. """
        nombre = self.nombre_edit.text().strip()
        comentario = self.comentario_edit.toPlainText().strip()

        if not nombre:
            QMessageBox.warning(self, "Campo Requerido", "El nombre del competidor no puede estar vacío.")
            self.nombre_edit.setFocus()
            return # No cerrar el diálogo

        # Crear o actualizar el objeto Oferente
        if self.initial_data:
            # Editando: Modificar el existente (si se pasó como objeto)
            # Nota: Si initial_data fuera un dict, crearíamos uno nuevo aquí.
            # Como pasamos el objeto Oferente, lo modificamos directamente.
            self.initial_data.nombre = nombre
            self.initial_data.comentario = comentario
            self.result_oferente = self.initial_data
        else:
            # Creando: Nuevo objeto Oferente
            # Asume que Oferente solo necesita nombre y comentario en __init__
            # y que ofertas_por_lote se inicializa vacío.
            self.result_oferente = Oferente(nombre=nombre, comentario=comentario)

        super().accept() # Llama al accept() original para cerrar con éxito

    def get_oferente_object(self) -> Optional[Oferente]:
        """ Devuelve el objeto Oferente creado o modificado. """
        return self.result_oferente