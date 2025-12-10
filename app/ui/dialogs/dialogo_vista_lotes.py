# app/ui/dialogs/dialogo_vista_lotes.py
from __future__ import annotations
import locale
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QGroupBox, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QAbstractItemView, QLabel, QFormLayout,
    QDialogButtonBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from app.core.models import Licitacion, Lote

if TYPE_CHECKING:
    from app.ui.windows.main_window import MainWindow

# Configurar la localización para formatos de moneda
try:
    locale.setlocale(locale.LC_ALL, '')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'es_ES.UTF-8')
    except locale.Error:
        print("Advertencia: No se pudo establecer la localización para formato de moneda.")

class DialogoVistaLotes(QDialog):
    """
    Una ventana de diálogo de solo lectura para mostrar los detalles 
    de los lotes de una licitación específica.
    """

    def __init__(self, parent: MainWindow, licitacion: Licitacion):
        super().__init__(parent)
        self.licitacion = licitacion

        self.setWindowTitle(f"Detalle de Lotes: {self.licitacion.numero_proceso}")
        self.setMinimumSize(1200, 500)
        self.setModal(True) # Actúa como un Toplevel.grab_set()

        # --- Colores (replicando los tags de Tkinter) ---
        self.color_no_participa = QColor("#888888") # Gris
        self.color_descalificado = QColor("#B00000") # Rojo oscuro

        self._build_ui()
        self._load_data()

    def _build_ui(self):
        """Construye la interfaz de usuario del diálogo."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # --- Tabla de Lotes (Grupo) ---
        group_lotes = QGroupBox(f"Lotes para '{self.licitacion.nombre_proceso}'")
        layout_lotes = QVBoxLayout(group_lotes)

        self.table_lotes = QTableWidget()
        cols = [
            "Participa", "Fase A OK", "N°", "Nombre del Lote",
            "Base Licitación", "Base Personal", "% Dif. Bases",
            "Nuestra Oferta", "% Oferta vs Licit.", "% Oferta vs Pers."
        ]
        self.table_lotes.setColumnCount(len(cols))
        self.table_lotes.setHorizontalHeaderLabels(cols)
        
        # --- Estilo de la Tabla ---
        self.table_lotes.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_lotes.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_lotes.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_lotes.setAlternatingRowColors(True)
        self.table_lotes.verticalHeader().setVisible(False)
        self.table_lotes.setSortingEnabled(True)

        header = self.table_lotes.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        # Columna Nombre Lote se estira
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch) 

        layout_lotes.addWidget(self.table_lotes)
        main_layout.addWidget(group_lotes)

        # --- Resumen Financiero (Grupo) ---
        group_resumen = QGroupBox("Resumen Financiero (Solo lotes donde participamos)")
        # QFormLayout es ideal para pares de Label: Dato
        layout_resumen = QFormLayout(group_resumen)
        layout_resumen.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.lbl_monto_base = QLabel("Calculando...")
        self.lbl_monto_personal = QLabel("Calculando...")
        self.lbl_monto_ofertado = QLabel("Calculando...")
        
        # Añadir etiquetas con negrita
        label_base = QLabel("Monto Base Licitación Total:")
        label_base.setStyleSheet("font-weight: bold;")
        
        label_personal = QLabel("Monto Base Personal Total:")
        label_personal.setStyleSheet("font-weight: bold;")
        
        label_ofertado = QLabel("Monto Ofertado Total:")
        label_ofertado.setStyleSheet("font-weight: bold;")

        layout_resumen.addRow(label_base, self.lbl_monto_base)
        layout_resumen.addRow(label_personal, self.lbl_monto_personal)
        layout_resumen.addRow(label_ofertado, self.lbl_monto_ofertado)

        main_layout.addWidget(group_resumen)

        # --- Botón de Cerrar ---
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.button(QDialogButtonBox.StandardButton.Close).setText("Cerrar")
        button_box.rejected.connect(self.reject) # self.reject() es como self.destroy()

        main_layout.addWidget(button_box, alignment=Qt.AlignmentFlag.AlignRight)

    def _load_data(self):
        """Carga los datos de la licitación en la tabla y el resumen."""
        
        # --- 1. Cargar Resumen Financiero ---
        # ASUNCIÓN: Tu modelo Licitacion tiene estos métodos, 
        # tal como se ve en el código de Tkinter.
        try:
            monto_base_total = self.licitacion.get_monto_base_total()
            monto_personal_total = self.licitacion.get_monto_base_personal_total()
            monto_ofertado_total = self.licitacion.get_oferta_total()
            diferencia_bases = self.licitacion.get_diferencia_bases_porcentual()

            self.lbl_monto_base.setText(f"{locale.currency(monto_base_total, grouping=True)}")
            self.lbl_monto_personal.setText(f"{locale.currency(monto_personal_total, grouping=True)} ({diferencia_bases:.2f}%)")
            self.lbl_monto_ofertado.setText(f"{locale.currency(monto_ofertado_total, grouping=True)}")
        except Exception as e:
            print(f"Error al calcular resumen: {e}")
            self.lbl_monto_base.setText(f"<Error: {e}>")

        # --- 2. Cargar Tabla de Lotes ---
        self.table_lotes.setSortingEnabled(False)
        self.table_lotes.setRowCount(0)
        
        lotes = getattr(self.licitacion, "lotes", []) or []
        lotes_ordenados = sorted(lotes, key=lambda l: getattr(l, "numero", "0"))

        for lote in lotes_ordenados:
            row = self.table_lotes.rowCount()
            self.table_lotes.insertRow(row)

            # --- Valores y Cálculos ---
            participa = bool(getattr(lote, "participamos", True))
            fase_a = bool(getattr(lote, "fase_A_superada", False))
            base = float(getattr(lote, "monto_base", 0.0) or 0.0)
            base_pers = float(getattr(lote, "monto_base_personal", 0.0) or 0.0)
            ofertado = float(getattr(lote, "monto_ofertado", 0.0) or 0.0)

            # % diferencias (replicando la lógica de Tkinter)
            try:
                dif_bases_pct = ((base_pers - base) / base * 100.0) if base > 0 else 0.0
            except ZeroDivisionError: dif_bases_pct = 0.0
            
            try:
                dif_lic_pct = ((ofertado - base) / base * 100.0) if (base > 0 and participa) else 0.0
            except ZeroDivisionError: dif_lic_pct = 0.0

            try:
                dif_pers_pct = ((ofertado - base_pers) / base_pers * 100.0) if (base_pers > 0 and participa) else 0.0
            except ZeroDivisionError: dif_pers_pct = 0.0
            
            # --- Formato de Strings ---
            valores_str = [
                "Sí" if participa else "No",
                "Sí" if fase_a else "No",
                str(getattr(lote, "numero", "")),
                str(getattr(lote, "nombre", "")),
                locale.currency(base, grouping=True),
                locale.currency(base_pers, grouping=True),
                f"{dif_bases_pct:.2f}%",
                locale.currency(ofertado, grouping=True) if participa else "N/A",
                f"{dif_lic_pct:.2f}%" if participa else "N/A",
                f"{dif_pers_pct:.2f}%" if participa else "N/A",
            ]
            
            # --- Determinar color de la fila ---
            tag_color = None
            if not participa:
                tag_color = self.color_no_participa
            elif participa and not fase_a: # Descalificado
                tag_color = self.color_descalificado

            # --- Insertar Items ---
            for col, text in enumerate(valores_str):
                item = QTableWidgetItem(text)
                # Alinear
                if col in [0, 1, 2]: # Participa, Fase A, N°
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                elif col in [4, 5, 6, 7, 8, 9]: # Montos y %
                    item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
                
                # Aplicar color de texto
                if tag_color:
                    item.setForeground(tag_color)
                    
                self.table_lotes.setItem(row, col, item)

        self.table_lotes.setSortingEnabled(True)
        self.table_lotes.resizeColumnsToContents()
        # Restaurar Stretch de la columna nombre
        self.table_lotes.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)