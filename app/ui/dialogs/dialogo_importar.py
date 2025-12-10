"""
Diálogo asistente para importar datos desde Excel/CSV.
"""
from __future__ import annotations
from typing import Optional, List, Dict, Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QComboBox, QTextEdit, QWizard,
    QWizardPage
)

from app.core.importer import ExcelImporter, ImportResult
from app.core.db_adapter import DatabaseAdapter


class DialogoImportarDatos(QDialog):
    """Diálogo asistente para importar datos desde archivos."""
    
    def __init__(self, parent, db: DatabaseAdapter, entity_type: str = "lotes", entity_id: Optional[str] = None):
        super().__init__(parent)
        self.db = db
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.importer = ExcelImporter()
        self.file_path: Optional[str] = None
        self.preview_data: Optional[Dict[str, Any]] = None
        
        self.setWindowTitle(f"Importar {entity_type.title()}")
        self.resize(950, 700)
        self.setModal(True)
        
        self._build_ui()
    
    def _build_ui(self):
        """Construye la interfaz del diálogo."""
        root = QVBoxLayout(self)
        
        # Paso 1: Selección de archivo
        file_group = QGroupBox("Paso 1: Seleccionar Archivo")
        file_layout = QHBoxLayout(file_group)
        
        file_layout.addWidget(QLabel("Archivo:"))
        self.lbl_file = QLabel("(Ningún archivo seleccionado)")
        file_layout.addWidget(self.lbl_file, 1)
        
        btn_browse = QPushButton("📂 Buscar...")
        btn_browse.clicked.connect(self._seleccionar_archivo)
        file_layout.addWidget(btn_browse)
        
        root.addWidget(file_group)
        
        # Paso 2: Vista previa
        preview_group = QGroupBox("Paso 2: Vista Previa de Datos")
        preview_layout = QVBoxLayout(preview_group)
        
        # Info de mapeo
        self.lbl_mapeo = QLabel("")
        preview_layout.addWidget(self.lbl_mapeo)
        
        # Tabla de preview
        self.tbl_preview = QTableWidget(0, 0)
        self.tbl_preview.verticalHeader().setVisible(False)
        self.tbl_preview.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        preview_layout.addWidget(self.tbl_preview)
        
        # Resumen
        self.txt_resumen = QTextEdit()
        self.txt_resumen.setReadOnly(True)
        self.txt_resumen.setMaximumHeight(100)
        preview_layout.addWidget(self.txt_resumen)
        
        root.addWidget(preview_group, 1)
        
        # Paso 3: Opciones de importación
        options_group = QGroupBox("Paso 3: Opciones de Importación")
        options_layout = QHBoxLayout(options_group)
        
        if self.entity_type in ["lotes", "documentos"]:
            options_layout.addWidget(QLabel("Importar para licitación:"))
            self.combo_licitacion = QComboBox()
            self._cargar_licitaciones()
            options_layout.addWidget(self.combo_licitacion, 1)
        
        options_layout.addStretch(1)
        
        root.addWidget(options_group)
        
        # Botones
        actions = QHBoxLayout()
        
        self.btn_previsualizar = QPushButton("👁️ Previsualizar")
        self.btn_previsualizar.clicked.connect(self._previsualizar)
        self.btn_previsualizar.setEnabled(False)
        actions.addWidget(self.btn_previsualizar)
        
        self.btn_importar = QPushButton("✅ Importar")
        self.btn_importar.clicked.connect(self._importar)
        self.btn_importar.setEnabled(False)
        actions.addWidget(self.btn_importar)
        
        actions.addStretch(1)
        
        btn_ayuda = QPushButton("❓ Ayuda")
        btn_ayuda.clicked.connect(self._mostrar_ayuda)
        actions.addWidget(btn_ayuda)
        
        btn_cerrar = QPushButton("Cancelar")
        btn_cerrar.clicked.connect(self.reject)
        actions.addWidget(btn_cerrar)
        
        root.addLayout(actions)
    
    def _cargar_licitaciones(self):
        """Carga las licitaciones en el combo."""
        try:
            licitaciones = self.db.load_all_licitaciones()
            for lic in licitaciones:
                display = f"{lic.numero_proceso} - {lic.nombre_proceso}"
                self.combo_licitacion.addItem(display, lic.id)
            
            # Seleccionar la licitación actual si se proporcionó
            if self.entity_id:
                for i in range(self.combo_licitacion.count()):
                    if str(self.combo_licitacion.itemData(i)) == str(self.entity_id):
                        self.combo_licitacion.setCurrentIndex(i)
                        break
        except Exception:
            pass
    
    def _seleccionar_archivo(self):
        """Permite seleccionar un archivo para importar."""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar Archivo",
            "",
            "Excel/CSV (*.xlsx *.xls *.csv);;Todos los archivos (*)"
        )
        
        if not filename:
            return
        
        self.file_path = filename
        self.lbl_file.setText(filename)
        self.btn_previsualizar.setEnabled(True)
        
        # Auto-previsualizar
        self._previsualizar()
    
    def _previsualizar(self):
        """Muestra una vista previa de los datos a importar."""
        if not self.file_path:
            QMessageBox.warning(self, "Error", "Seleccione un archivo primero")
            return
        
        try:
            # Obtener preview
            self.preview_data = self.importer.preview_import(
                self.file_path,
                self.entity_type,
                max_rows=10
            )
            
            if not self.preview_data.get("success"):
                QMessageBox.warning(
                    self, "Error",
                    f"No se pudo leer el archivo: {self.preview_data.get('error', 'Error desconocido')}"
                )
                return
            
            # Mostrar mapeo de columnas
            mapping = self.preview_data.get("column_mapping", {})
            mapping_text = "Mapeo de columnas detectado:\n"
            for field, col_idx in sorted(mapping.items()):
                headers = self.preview_data.get("headers", [])
                col_name = headers[col_idx] if col_idx < len(headers) else f"Columna {col_idx}"
                mapping_text += f"  • {field} ← {col_name}\n"
            
            self.lbl_mapeo.setText(mapping_text)
            
            # Mostrar tabla de preview
            headers = self.preview_data.get("headers", [])
            preview_rows = self.preview_data.get("preview_rows", [])
            
            self.tbl_preview.setRowCount(len(preview_rows))
            self.tbl_preview.setColumnCount(len(headers))
            self.tbl_preview.setHorizontalHeaderLabels(headers)
            
            for row_idx, row_data in enumerate(preview_rows):
                for col_idx, cell_value in enumerate(row_data):
                    item = QTableWidgetItem(str(cell_value or ""))
                    self.tbl_preview.setItem(row_idx, col_idx, item)
            
            # Ajustar columnas
            self.tbl_preview.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            
            # Resumen
            total_rows = self.preview_data.get("total_rows", 0)
            resumen = f"""
Archivo: {self.file_path}
Total de filas: {total_rows}
Mostrando: {len(preview_rows)} filas de muestra
Tipo de entidad: {self.entity_type}

Revise los datos y haga clic en "Importar" para continuar.
            """.strip()
            
            self.txt_resumen.setPlainText(resumen)
            
            self.btn_importar.setEnabled(True)
        
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al previsualizar: {e}")
    
    def _importar(self):
        """Realiza la importación de los datos."""
        if not self.file_path:
            QMessageBox.warning(self, "Error", "Seleccione un archivo primero")
            return
        
        # Confirmar
        if not self.preview_data:
            QMessageBox.warning(self, "Error", "Haga una previsualización primero")
            return
        
        total_rows = self.preview_data.get("total_rows", 0)
        respuesta = QMessageBox.question(
            self, "Confirmar Importación",
            f"¿Importar {total_rows} filas de datos?\n\nEsto puede tardar unos momentos.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if respuesta != QMessageBox.StandardButton.Yes:
            return
        
        try:
            result: Optional[ImportResult] = None
            
            # Importar según tipo de entidad
            if self.entity_type == "lotes":
                licitacion_id = self.combo_licitacion.currentData()
                if not licitacion_id:
                    QMessageBox.warning(self, "Error", "Seleccione una licitación")
                    return
                
                result = self.importer.import_lotes(
                    self.file_path,
                    str(licitacion_id),
                    self.db
                )
            
            elif self.entity_type == "documentos":
                licitacion_id = self.combo_licitacion.currentData()
                if not licitacion_id:
                    QMessageBox.warning(self, "Error", "Seleccione una licitación")
                    return
                
                result = self.importer.import_documentos(
                    self.file_path,
                    str(licitacion_id),
                    self.db
                )
            
            # Mostrar resultado
            if result:
                self._mostrar_resultado(result)
                if result.success:
                    self.accept()
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error durante la importación: {e}")
    
    def _mostrar_resultado(self, result: ImportResult):
        """Muestra el resultado de la importación."""
        mensaje = f"""RESULTADO DE LA IMPORTACIÓN

Total de filas procesadas: {result.total_rows}
Filas válidas: {result.valid_rows}
Filas con errores: {result.invalid_rows}

"""
        
        if result.errors:
            mensaje += "ERRORES:\n"
            for error in result.errors[:10]:  # Mostrar max 10 errores
                mensaje += f"  • {error}\n"
            
            if len(result.errors) > 10:
                mensaje += f"  ... y {len(result.errors) - 10} errores más\n"
            mensaje += "\n"
        
        if result.warnings:
            mensaje += "ADVERTENCIAS:\n"
            for warning in result.warnings[:10]:
                mensaje += f"  • {warning}\n"
            
            if len(result.warnings) > 10:
                mensaje += f"  ... y {len(result.warnings) - 10} advertencias más\n"
        
        if result.success:
            mensaje += "\n✅ Importación completada exitosamente"
            QMessageBox.information(self, "Importación Exitosa", mensaje)
        else:
            mensaje += "\n❌ Importación fallida o parcial"
            QMessageBox.warning(self, "Importación con Errores", mensaje)
    
    def _mostrar_ayuda(self):
        """Muestra ayuda sobre la importación."""
        ayuda_map = {
            "lotes": """
AYUDA - IMPORTAR LOTES

El archivo debe tener las siguientes columnas (en cualquier orden):

OBLIGATORIAS:
- numero: Número del lote
- nombre: Nombre o descripción del lote

OPCIONALES:
- monto_base: Monto base del lote
- monto_ofertado: Monto ofertado por nuestra empresa

FORMATO:
- Excel (.xlsx, .xls) o CSV (.csv)
- Primera fila debe contener los encabezados
- Filas vacías serán ignoradas

EJEMPLO:
numero | nombre           | monto_base | monto_ofertado
1      | Obras civiles    | 100000.00  | 95000.00
2      | Equipamiento     | 50000.00   | 48000.00
            """.strip(),
            
            "documentos": """
AYUDA - IMPORTAR DOCUMENTOS

El archivo debe tener las siguientes columnas (en cualquier orden):

OBLIGATORIAS:
- codigo: Código del documento
- nombre: Nombre del documento

OPCIONALES:
- categoria: Categoría del documento (Legal, Técnico, etc.)
- obligatorio: Si es obligatorio (true/false, si/no, 1/0)
- subsanable: Si es subsanable (Subsanable/No Subsanable)

FORMATO:
- Excel (.xlsx, .xls) o CSV (.csv)
- Primera fila debe contener los encabezados
- Filas vacías serán ignoradas

EJEMPLO:
codigo | nombre                    | categoria | obligatorio | subsanable
D001   | Cédula del representante | Legal     | true        | No Subsanable
D002   | RNC de la empresa        | Legal     | true        | Subsanable
            """.strip(),
        }
        
        ayuda = ayuda_map.get(self.entity_type, "No hay ayuda disponible para este tipo de entidad")
        
        QMessageBox.information(self, f"Ayuda - Importar {self.entity_type.title()}", ayuda)
