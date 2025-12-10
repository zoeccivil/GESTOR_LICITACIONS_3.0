# app/ui/dialogs/historial_subsanacion_dialog.py
from __future__ import annotations
import os
import platform
import subprocess
from typing import TYPE_CHECKING, List, Any

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QPushButton, QMessageBox, QStyle,
    QFileDialog, QWidget
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QIcon, QBrush, QColor, QDesktopServices

# Importar modelos y adaptador
from app.core.models import Licitacion
from app.core.db_adapter import DatabaseAdapter
# Asumimos que la lógica de reportes está aquí
# from app.core.logic.reporter import generate_subsanacion_report 

if TYPE_CHECKING:
    pass

# --- Definición de Colores ---
# Puedes ajustar estos colores a tu gusto
COLOR_PENDIENTE = QColor("#FFF9C4")  # Amarillo Claro
COLOR_CUMPLIDO = QColor("#C8E6C9")  # Verde Claro
COLOR_INCUMPLIDO = QColor("#FFCDD2") # Rojo Claro
COLOR_DEFAULT = QColor(Qt.GlobalColor.white) # Blanco

class HistorialSubsanacionDialog(QDialog):
    """
    Muestra el historial de eventos de subsanación de una licitación.
    Permite refrescar y exportar a PDF.
    Es redimensionable y maximizable.
    """
    # Índices de columnas para la tabla
    COL_FECHA_SOL = 0
    COL_CODIGO = 1
    COL_NOMBRE = 2
    COL_FECHA_LIM = 3
    COL_ESTADO = 4
    COL_COMENTARIO = 5

    def __init__(self, parent: QWidget, licitacion: Licitacion, db_adapter: DatabaseAdapter):
        super().__init__(parent)
        self.licitacion = licitacion
        self.db = db_adapter
        self.historial_data: List[Any] = [] # Almacenará los datos crudos para exportar

        self.setWindowTitle(f"Historial de Subsanaciones - {self.licitacion.numero_proceso}")
        self.setMinimumSize(950, 500)

        # --- Hacer Redimensionable/Maximizable ---
        flags = self.windowFlags()
        self.setWindowFlags(flags | Qt.WindowType.WindowMaximizeButtonHint | Qt.WindowType.WindowMinimizeButtonHint)

        self._build_ui()
        self.refrescar_historial() # Cargar datos al iniciar

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # --- Tabla de Historial ---
        self.table_historial = QTableWidget()
        self.table_historial.setColumnCount(6)
        self.table_historial.setHorizontalHeaderLabels([
            "Fecha Solicitud", "Código Doc.", "Documento",
            "Fecha Límite", "Estado", "Comentario"
        ])
        
        # Estilo y comportamiento de la tabla
        self.table_historial.setAlternatingRowColors(True)
        self.table_historial.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_historial.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_historial.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_historial.verticalHeader().setVisible(False)
        self.table_historial.setSortingEnabled(True)

        # Ajuste de columnas
        header = self.table_historial.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive) # Permitir redimensionar
        header.setSectionResizeMode(self.COL_NOMBRE, QHeaderView.ResizeMode.Stretch) # Estirar "Documento"
        header.setSectionResizeMode(self.COL_COMENTARIO, QHeaderView.ResizeMode.Stretch) # Estirar "Comentario"
        header.resizeSection(self.COL_FECHA_SOL, 110)
        header.resizeSection(self.COL_CODIGO, 100)
        header.resizeSection(self.COL_FECHA_LIM, 100)
        header.resizeSection(self.COL_ESTADO, 90)

        main_layout.addWidget(self.table_historial)

        # --- Botonera Inferior ---
        button_layout = QHBoxLayout()
        style = self.style() # Para iconos estándar

        # Botón Refrescar
        self.btn_refrescar = QPushButton(" Refrescar")
        self.btn_refrescar.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.btn_refrescar.clicked.connect(self.refrescar_historial)
        button_layout.addWidget(self.btn_refrescar)

        # Botón Exportar PDF
        self.btn_exportar_pdf = QPushButton(" Exportar a PDF...")
        self.btn_exportar_pdf.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton)) # O SP_DriveFDIcon
        self.btn_exportar_pdf.clicked.connect(self.exportar_pdf)
        button_layout.addWidget(self.btn_exportar_pdf)

        button_layout.addStretch(1) # Espacio

        # Botón Cerrar
        self.btn_cerrar = QPushButton("Cerrar")
        self.btn_cerrar.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton))
        self.btn_cerrar.clicked.connect(self.accept) # 'accept' cierra el QDialog
        button_layout.addWidget(self.btn_cerrar)
        
        main_layout.addLayout(button_layout)

    def refrescar_historial(self):
        """
        Limpia la tabla, vuelve a consultar la base de datos y la rellena
        con los datos actualizados, aplicando colores.
        """
        print("Refrescando historial de subsanaciones...")
        self.table_historial.setSortingEnabled(False) # Desactivar ordenamiento durante la carga
        self.table_historial.setRowCount(0) # Limpiar tabla

        # --- Cargar datos FRESCOS desde la BD ---
        try:
            # Asegúrate de que este método exista en tu db_adapter
            self.historial_data = self.db.obtener_historial_subsanacion(self.licitacion.id)
        except AttributeError:
            QMessageBox.critical(self, "Error", "La función 'obtener_historial_subsanacion' no existe en el adaptador de base de datos.")
            self.historial_data = []
            return
        except Exception as e:
            QMessageBox.critical(self, "Error de Base de Datos", f"No se pudo cargar el historial:\n{e}")
            self.historial_data = []
            return

        if not self.historial_data:
            print("No se encontró historial de subsanación.")
            return

        # --- Poblar la tabla con los nuevos datos ---
        for row_data in self.historial_data:
            row = self.table_historial.rowCount()
            self.table_historial.insertRow(row)

            # Determinar color de la fila basado en el estado (Columna 4)
            estado_str = str(row_data[self.COL_ESTADO]).strip().lower()
            if "cumplido" in estado_str or "completado" in estado_str:
                brush = QBrush(COLOR_CUMPLIDO)
            elif "pendiente" in estado_str:
                brush = QBrush(COLOR_PENDIENTE)
            elif "incumplido" in estado_str or "vencido" in estado_str:
                brush = QBrush(COLOR_INCUMPLIDO)
            else:
                brush = QBrush(COLOR_DEFAULT)

            # Llenar las celdas de la fila
            for col_idx, data in enumerate(row_data):
                item = QTableWidgetItem(str(data) if data is not None else "")
                item.setBackground(brush) # Aplicar color
                # Alinear algunas columnas
                if col_idx in [self.COL_FECHA_SOL, self.COL_FECHA_LIM, self.COL_ESTADO, self.COL_CODIGO]:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                else:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                
                self.table_historial.setItem(row, col_idx, item)

        self.table_historial.setSortingEnabled(True) # Reactivar ordenamiento
        print(f"Historial cargado con {len(self.historial_data)} filas.")

    def exportar_pdf(self):
        """
Example de cómo exportar. Llama a un generador de reportes."""
        if not self.historial_data:
            QMessageBox.warning(self, "Sin Datos", "No hay historial para exportar.")
            return

        # 1. Pedir ruta de guardado
        default_filename = f"Historial_Subsanacion_{self.licitacion.numero_proceso}.pdf"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Historial como PDF",
            default_filename,
            "Archivos PDF (*.pdf);;Todos los archivos (*)"
        )

        if not file_path:
            return # Usuario canceló

        # 2. Llamar a la lógica de generación de reporte
        try:
            # --- ¡IMPORTANTE! ---
            # Necesitas crear este módulo/función basado en tu 'reporter'
            from app.core.logic.reporter import generate_subsanacion_report

            print(f"Generando reporte PDF en: {file_path}...")
            # Pasar la licitación completa y los datos del historial
            generate_subsanacion_report(self.licitacion, self.historial_data, file_path)

            QMessageBox.information(self, "Éxito", f"Reporte guardado exitosamente en:\n{file_path}")

            # 3. Preguntar si desea abrir el archivo
            if QMessageBox.question(self, "Abrir Reporte", "¿Desea abrir el PDF generado?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.Yes) == QMessageBox.StandardButton.Yes:
                if not QDesktopServices.openUrl(QUrl.fromLocalFile(file_path)):
                     QMessageBox.warning(self, "Error al Abrir", f"No se pudo abrir el archivo:\n{file_path}")

        except ImportError:
            QMessageBox.critical(self, "Función Faltante",
                                 "La función 'generate_subsanacion_report' no se encontró en 'app.core.logic.reporter'.\n\n"
                                 "La exportación no está implementada.")
        except Exception as e:
            QMessageBox.critical(self, "Error de Exportación", f"No se pudo generar el reporte PDF:\n{e}")
            print(f"Error detallado exportando PDF de subsanación: {e}")