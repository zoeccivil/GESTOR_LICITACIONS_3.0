# app/ui/dialogs/gestionar_entidad_dialog.py
from __future__ import annotations
from typing import Dict, Optional, List, Tuple # Añadido List, Tuple
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QDialogButtonBox,
    QWidget,
    QMessageBox, # Añadido para mostrar mensajes de error
    QPushButton, # Añadido para botones personalizados si fuera necesario
    QStyle # Añadido para iconos estándar
)

class DialogoGestionarEntidad(QDialog):
    """
    Editor genérico de entidad (Institución o Empresa).
    entity_type:
      - 'empresa': Muestra todos los campos de empresa.
      - 'institucion': Muestra los campos relevantes para institución.
    """
    def __init__(self, parent: QWidget, title: str, entity_type: str, initial_data: Optional[Dict] = None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.entity_type = entity_type
        self.initial_data = initial_data or {}
        # Cambiamos el nombre del atributo para evitar confusión con el método result() de QDialog
        self.form_data: Optional[Dict] = None

        self._build_ui()
        self._load_initial_data()
        # Conectar la señal accepted del diálogo a nuestro método _on_accept
        self.accepted.connect(self._on_accept)

    def _build_ui(self):
        # Define los campos específicos para cada tipo de entidad
        # fields = [ (Label Text, internal_key), ... ]
        fields: List[Tuple[str, str]] = []
        min_width = 400 # Ancho mínimo por defecto

        if self.entity_type == "empresa":
            fields = [
                ("Nombre (*)", "nombre"), # Marcar Nombre como obligatorio
                ("RNC", "rnc"),
                ("No. RPE", "rpe"),
                ("Teléfono", "telefono"),
                ("Correo", "correo"),
                ("Dirección", "direccion"),
                ("Representante", "representante"),
                ("Cargo del Representante", "cargo_representante"),
            ]
            min_width = 480 # Más ancho para empresas
            min_height = 400
        elif self.entity_type == "institucion":
            fields = [
                ("Nombre (*)", "nombre"), # Marcar Nombre como obligatorio
                ("RNC", "rnc"),
                ("Teléfono", "telefono"),
                ("Correo", "correo"),
                ("Dirección", "direccion")
            ]
            min_height = 320
        else:
            # Tipo no reconocido, podría mostrar un error o campos básicos
             fields = [("Nombre (*)", "nombre")]
             min_height = 150

        self.setMinimumSize(min_width, min_height) # Aplicar tamaño mínimo

        # Layout principal vertical
        vbox = QVBoxLayout(self)

        # Layout de rejilla para etiquetas y campos de entrada
        grid = QGridLayout()
        self._inputs: Dict[str, QLineEdit] = {} # Diccionario para guardar referencia a los QLineEdit

        # Crear etiquetas y campos de entrada para cada field definido
        for row, (label, key) in enumerate(fields):
            grid.addWidget(QLabel(f"{label}:"), row, 0, Qt.AlignmentFlag.AlignTop) # Alinear etiqueta arriba
            edit = QLineEdit(self)
            edit.setPlaceholderText(label.replace(" (*)", "")) # Placeholder sin el asterisco
            grid.addWidget(edit, row, 1)
            self._inputs[key] = edit # Guardar referencia al input

            # Hacer que la columna de inputs (1) se expanda
            grid.setColumnStretch(1, 1)

        # Añadir la rejilla de campos al layout vertical
        vbox.addLayout(grid)
        vbox.addStretch(1) # Añadir espacio flexible para empujar botones hacia abajo

        # Botones estándar OK y Cancelar
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            orientation=Qt.Orientation.Horizontal,
            parent=self,
        )
        # Conectar señales estándar (accepted y rejected)
        # La validación se hará en _on_accept
        buttons.accepted.connect(self.accept) # Conecta OK a accept()
        buttons.rejected.connect(self.reject) # Conecta Cancel a reject()
        vbox.addWidget(buttons)

        # Guardar referencia a los campos para uso posterior si es necesario
        self._fields = fields

    def _load_initial_data(self):
        """Carga los datos iniciales (si existen) en los campos del formulario."""
        for key, widget in self._inputs.items():
            # Obtiene el valor del diccionario initial_data, o usa "" si no existe
            widget.setText(str(self.initial_data.get(key, ""))) # Asegura que sea string

    def _on_accept(self):
        """Se ejecuta cuando se presiona OK. Valida y guarda los datos."""
        # Recolecta los datos de todos los campos, quitando espacios extra
        data = {key: widget.text().strip() for key, widget in self._inputs.items()}

        # Validación: El campo 'nombre' no puede estar vacío
        if not data.get("nombre"):
            QMessageBox.warning(self, "Campo Requerido", "El campo 'Nombre' no puede estar vacío.")
            # IMPORTANTE: Prevenir que el diálogo se cierre si la validación falla
            # No llamamos a self.accept() ni self.done(QDialog.DialogCode.Accepted)
            return # Detiene la ejecución aquí

        # Si la validación pasa, guarda los datos en self.form_data
        self.form_data = data
        # Nota: No necesitamos llamar a self.accept() aquí porque ya está conectado
        #       a la señal 'accepted' del QDialogButtonBox en _build_ui.
        #       Simplemente dejamos que el flujo normal continúe y el diálogo se acepte.

    # Método para obtener los datos guardados (más explícito que acceder a 'result')
    def get_data(self) -> Optional[Dict]:
        """Devuelve el diccionario con los datos del formulario si se aceptó, o None si se canceló o falló la validación."""
        return self.form_data

# --- Fin del archivo ---