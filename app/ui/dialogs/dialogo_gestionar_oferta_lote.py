# app/ui/dialogs/dialogo_gestionar_oferta_lote.py
from __future__ import annotations
from typing import Optional, List, Dict, Any

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLabel, QLineEdit, QComboBox,
    QCheckBox, QDialogButtonBox, QMessageBox, QDoubleSpinBox
)
from PyQt6.QtCore import Qt

# Importar el modelo Lote
from app.core.models import Lote

class DialogoGestionarOfertaLote(QDialog):
    """
    Diálogo para agregar o editar la oferta de un competidor para un lote específico.
    """
    def __init__(self, parent, title: str, lotes_disponibles: List[Lote], initial_data: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(450)

        self.lotes_disponibles = lotes_disponibles
        self.initial_data = initial_data or {} # El dict de la oferta
        self.result_oferta_dict: Optional[Dict[str, Any]] = None

        # --- Widgets ---
        self.lote_combo = QComboBox()
        self.monto_spinbox = QDoubleSpinBox() # Usar QDoubleSpinBox para montos
        self.monto_spinbox.setDecimals(2)
        self.monto_spinbox.setMinimum(0.0)
        self.monto_spinbox.setMaximum(999_999_999_999.99) # Límite alto
        self.monto_spinbox.setGroupSeparatorShown(True) # Muestra separador de miles
        
        self.plazo_edit = QLineEdit()
        self.garantia_edit = QLineEdit()
        self.paso_fase_a_check = QCheckBox("Oferta habilitada (Pasó Fase A)")

        # --- Layout ---
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.addRow("Seleccionar Lote:", self.lote_combo)
        form_layout.addRow("Monto Ofertado:", self.monto_spinbox)
        form_layout.addRow("Plazo de Entrega (días):", self.plazo_edit)
        form_layout.addRow("Garantía (meses):", self.garantia_edit)
        form_layout.addRow(self.paso_fase_a_check)
        main_layout.addLayout(form_layout)

        # --- Botones OK/Cancelar ---
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        # --- Llenar ComboBox de Lotes y Cargar Datos Iniciales ---
        self._populate_lote_combo()
        self._load_initial_data()

        # Foco inicial en el monto
        self.monto_spinbox.setFocus()

    def _populate_lote_combo(self):
        """ Llena el ComboBox con los lotes disponibles. """
        self.lote_combo.clear()
        if not self.lotes_disponibles:
            self.lote_combo.addItem("No hay lotes disponibles", None)
            self.lote_combo.setEnabled(False)
            return

        for lote in self.lotes_disponibles:
            # Texto visible: "Numero - Nombre"
            # Dato interno: Numero (como string)
            self.lote_combo.addItem(f"{lote.numero} - {lote.nombre}", str(lote.numero))

    def _load_initial_data(self):
        """ Carga los datos de la oferta si se está editando. """
        if self.initial_data:
            # Modo Edición: Seleccionar lote y deshabilitar combo
            lote_num_inicial = str(self.initial_data.get('lote_numero', ''))
            index = self.lote_combo.findData(lote_num_inicial)
            if index >= 0:
                self.lote_combo.setCurrentIndex(index)
            else:
                 # Si el lote inicial no está en la lista (raro), añadirlo temporalmente
                 print(f"Advertencia: Lote inicial {lote_num_inicial} no encontrado en lotes disponibles.")
                 # Podrías añadirlo aquí si es necesario, pero usualmente no debería pasar.
                 # self.lote_combo.addItem(f"{lote_num_inicial} - Lote Editado", lote_num_inicial)
                 # self.lote_combo.setCurrentIndex(self.lote_combo.count() - 1)
                 pass
            
            self.lote_combo.setEnabled(False) # No se puede cambiar el lote al editar

            # Cargar valores
            self.monto_spinbox.setValue(float(self.initial_data.get('monto', 0.0)))
            self.plazo_edit.setText(str(self.initial_data.get('plazo_entrega', 0)))
            self.garantia_edit.setText(str(self.initial_data.get('garantia_meses', 0)))
            self.paso_fase_a_check.setChecked(bool(self.initial_data.get('paso_fase_A', True)))
        else:
            # Modo Creación: Habilitar combo y poner valores por defecto
            self.lote_combo.setEnabled(True)
            self.lote_combo.setCurrentIndex(0) # Seleccionar el primero
            self.monto_spinbox.setValue(0.0)
            self.plazo_edit.setText('0')
            self.garantia_edit.setText('0')
            self.paso_fase_a_check.setChecked(True) # Por defecto habilitada

    def accept(self):
        """ Sobreescribir accept para validar y guardar. """
        
        lote_numero_data = self.lote_combo.currentData() # Obtiene el dato interno (N° Lote string)
        if lote_numero_data is None:
            QMessageBox.warning(self, "Lote Requerido", "Debes seleccionar un lote.")
            self.lote_combo.setFocus()
            return

        lote_numero = str(lote_numero_data)
        monto = self.monto_spinbox.value()
        paso_fase_a = self.paso_fase_a_check.isChecked()

        # Validar Plazo y Garantía como enteros
        try:
            plazo = int(self.plazo_edit.text() or '0')
            if plazo < 0: raise ValueError("Plazo no puede ser negativo")
        except ValueError:
            QMessageBox.warning(self, "Dato Inválido", "El plazo de entrega debe ser un número entero no negativo.")
            self.plazo_edit.setFocus()
            return

        try:
            garantia = int(self.garantia_edit.text() or '0')
            if garantia < 0: raise ValueError("Garantía no puede ser negativa")
        except ValueError:
            QMessageBox.warning(self, "Dato Inválido", "La garantía debe ser un número entero no negativo.")
            self.garantia_edit.setFocus()
            return

        # Crear el diccionario de resultado
        self.result_oferta_dict = {
            "lote_numero": lote_numero,
            "monto": monto,
            "paso_fase_A": paso_fase_a,
            "plazo_entrega": plazo,
            "garantia_meses": garantia,
            # La bandera 'ganador' NO se gestiona aquí, se aplica después.
            # Se preserva si ya existía en initial_data al editar.
            "ganador": bool(self.initial_data.get('ganador', False)) 
        }

        super().accept() # Cerrar diálogo con éxito

    def get_oferta_dict(self) -> Optional[Dict[str, Any]]:
        """ Devuelve el diccionario con los datos de la oferta. """
        return self.result_oferta_dict