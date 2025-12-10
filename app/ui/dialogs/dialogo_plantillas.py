"""
Diálogo para gestionar plantillas y generar documentos.
"""
from __future__ import annotations
from typing import Optional, Dict, Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QListWidget, QListWidgetItem, QGroupBox, QLineEdit,
    QTextEdit, QFileDialog, QMessageBox, QGridLayout
)

from app.core.template_engine import TemplateEngine


class DialogoPlantillas(QDialog):
    """Diálogo para gestionar plantillas y generar documentos."""
    
    def __init__(self, parent, licitacion_data: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.licitacion_data = licitacion_data or {}
        self.template_engine = TemplateEngine()
        
        self.setWindowTitle("Gestión de Plantillas")
        self.resize(900, 650)
        self.setModal(True)
        
        self._build_ui()
        self._cargar_plantillas()
    
    def _build_ui(self):
        """Construye la interfaz del diálogo."""
        root = QVBoxLayout(self)
        
        # Layout principal dividido
        main_layout = QHBoxLayout()
        
        # Panel izquierdo - Lista de plantillas
        left_panel = QGroupBox("Plantillas Disponibles")
        left_layout = QVBoxLayout(left_panel)
        
        self.list_plantillas = QListWidget()
        self.list_plantillas.itemSelectionChanged.connect(self._plantilla_seleccionada)
        left_layout.addWidget(self.list_plantillas)
        
        btn_cargar = QPushButton("📂 Cargar Plantilla")
        btn_cargar.clicked.connect(self._cargar_plantilla)
        left_layout.addWidget(btn_cargar)
        
        btn_nueva_simple = QPushButton("📄 Nueva Plantilla Simple")
        btn_nueva_simple.clicked.connect(self._nueva_plantilla_simple)
        left_layout.addWidget(btn_nueva_simple)
        
        main_layout.addWidget(left_panel, 1)
        
        # Panel derecho - Variables y generación
        right_panel = QGroupBox("Variables y Generación")
        right_layout = QVBoxLayout(right_panel)
        
        # Variables disponibles
        right_layout.addWidget(QLabel("Variables Disponibles:"))
        self.txt_variables = QTextEdit()
        self.txt_variables.setReadOnly(True)
        self.txt_variables.setMaximumHeight(150)
        self._mostrar_variables_disponibles()
        right_layout.addWidget(self.txt_variables)
        
        # Valores de variables
        vars_group = QGroupBox("Valores para las Variables")
        vars_layout = QGridLayout(vars_group)
        
        row = 0
        self.var_inputs = {}
        
        # Variables comunes
        common_vars = [
            ("razon_social", "Razón Social"),
            ("rnc", "RNC"),
            ("numero_proceso", "Número de Proceso"),
            ("nombre_proceso", "Nombre del Proceso"),
            ("institucion", "Institución"),
            ("monto", "Monto"),
        ]
        
        for var_name, var_label in common_vars:
            vars_layout.addWidget(QLabel(f"{var_label}:"), row, 0)
            input_field = QLineEdit()
            
            # Prellenar con datos de licitación si están disponibles
            if self.licitacion_data:
                if var_name == "numero_proceso":
                    input_field.setText(self.licitacion_data.get("numero_proceso", ""))
                elif var_name == "nombre_proceso":
                    input_field.setText(self.licitacion_data.get("nombre_proceso", ""))
                elif var_name == "institucion":
                    input_field.setText(self.licitacion_data.get("institucion", ""))
            
            vars_layout.addWidget(input_field, row, 1)
            self.var_inputs[var_name] = input_field
            row += 1
        
        right_layout.addWidget(vars_group)
        
        # Botones de generación
        gen_layout = QHBoxLayout()
        
        btn_generar_docx = QPushButton("📝 Generar DOCX")
        btn_generar_docx.clicked.connect(self._generar_docx)
        gen_layout.addWidget(btn_generar_docx)
        
        btn_generar_html = QPushButton("🌐 Generar HTML")
        btn_generar_html.clicked.connect(self._generar_html)
        gen_layout.addWidget(btn_generar_html)
        
        btn_carta_oferta = QPushButton("✉️ Carta de Oferta")
        btn_carta_oferta.clicked.connect(self._generar_carta_oferta)
        gen_layout.addWidget(btn_carta_oferta)
        
        right_layout.addLayout(gen_layout)
        right_layout.addStretch(1)
        
        main_layout.addWidget(right_panel, 2)
        
        root.addLayout(main_layout, 1)
        
        # Botones inferiores
        actions = QHBoxLayout()
        actions.addStretch(1)
        
        btn_ayuda = QPushButton("❓ Ayuda")
        btn_ayuda.clicked.connect(self._mostrar_ayuda)
        actions.addWidget(btn_ayuda)
        
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(self.accept)
        actions.addWidget(btn_cerrar)
        
        root.addLayout(actions)
    
    def _cargar_plantillas(self):
        """Carga la lista de plantillas disponibles."""
        self.list_plantillas.clear()
        plantillas = self.template_engine.list_templates()
        
        if not plantillas:
            item = QListWidgetItem("(No hay plantillas disponibles)")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list_plantillas.addItem(item)
        else:
            for plantilla in plantillas:
                self.list_plantillas.addItem(plantilla)
    
    def _mostrar_variables_disponibles(self):
        """Muestra las variables disponibles para usar en plantillas."""
        variables = self.template_engine.get_available_variables()
        
        text_lines = []
        text_lines.append("Use estas variables en sus plantillas con el formato {{variable}}:\n")
        
        for var_name, var_desc in sorted(variables.items()):
            text_lines.append(f"• {{{{var_name}}}}: {var_desc}")
        
        self.txt_variables.setPlainText("\n".join(text_lines))
    
    def _plantilla_seleccionada(self):
        """Maneja la selección de una plantilla."""
        items = self.list_plantillas.selectedItems()
        if items:
            plantilla = items[0].text()
            # Aquí podríamos mostrar un preview de la plantilla
    
    def _cargar_plantilla(self):
        """Permite cargar una nueva plantilla desde archivo."""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Cargar Plantilla",
            "",
            "Plantillas (*.docx *.html *.txt);;Todos los archivos (*)"
        )
        
        if not filename:
            return
        
        try:
            import shutil
            from pathlib import Path
            
            # Copiar archivo al directorio de plantillas
            dest = Path(self.template_engine.templates_dir) / Path(filename).name
            shutil.copy(filename, dest)
            
            QMessageBox.information(
                self, "Éxito",
                f"Plantilla '{Path(filename).name}' cargada exitosamente"
            )
            
            self._cargar_plantillas()
        
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo cargar la plantilla: {e}")
    
    def _nueva_plantilla_simple(self):
        """Crea una nueva plantilla simple."""
        from PyQt6.QtWidgets import QInputDialog
        
        nombre, ok = QInputDialog.getText(
            self, "Nueva Plantilla",
            "Nombre de la plantilla (sin extensión):"
        )
        
        if not ok or not nombre.strip():
            return
        
        nombre = nombre.strip()
        if not nombre.endswith('.docx'):
            nombre += '.docx'
        
        try:
            from pathlib import Path
            template_path = Path(self.template_engine.templates_dir) / nombre
            
            # Crear plantilla simple
            self.template_engine.create_simple_docx(
                str(template_path),
                titulo="Plantilla: {{nombre_proceso}}",
                contenido="""
Estimados señores de {{institucion}}:

Por medio de la presente, {{razon_social}}, RNC: {{rnc}}, 
presenta su oferta para el proceso:

Número: {{numero_proceso}}
Nombre: {{nombre_proceso}}

Monto ofertado: {{monto}}

Atentamente,
{{razon_social}}
                """.strip()
            )
            
            QMessageBox.information(
                self, "Éxito",
                f"Plantilla '{nombre}' creada exitosamente"
            )
            
            self._cargar_plantillas()
        
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo crear la plantilla: {e}")
    
    def _obtener_variables(self) -> Dict[str, Any]:
        """Obtiene los valores de las variables desde los inputs."""
        import datetime
        
        variables = {
            "fecha": datetime.date.today().strftime("%d/%m/%Y")
        }
        
        for var_name, input_field in self.var_inputs.items():
            variables[var_name] = input_field.text().strip()
        
        return variables
    
    def _generar_docx(self):
        """Genera un documento DOCX desde la plantilla seleccionada."""
        items = self.list_plantillas.selectedItems()
        if not items:
            QMessageBox.warning(self, "Error", "Seleccione una plantilla primero")
            return
        
        plantilla = items[0].text()
        if not plantilla.endswith('.docx'):
            QMessageBox.warning(self, "Error", "La plantilla seleccionada no es un archivo DOCX")
            return
        
        # Pedir ubicación de salida
        output_file, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Documento",
            f"documento_{plantilla}",
            "Word Documents (*.docx)"
        )
        
        if not output_file:
            return
        
        try:
            variables = self._obtener_variables()
            success = self.template_engine.generate_from_docx_template(
                plantilla, variables, output_file
            )
            
            if success:
                QMessageBox.information(
                    self, "Éxito",
                    f"Documento generado exitosamente:\n{output_file}"
                )
            else:
                QMessageBox.warning(self, "Error", "No se pudo generar el documento")
        
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al generar documento: {e}")
    
    def _generar_html(self):
        """Genera un documento HTML desde la plantilla seleccionada."""
        items = self.list_plantillas.selectedItems()
        if not items:
            QMessageBox.warning(self, "Error", "Seleccione una plantilla primero")
            return
        
        plantilla = items[0].text()
        if not plantilla.endswith('.html'):
            QMessageBox.warning(self, "Error", "La plantilla seleccionada no es un archivo HTML")
            return
        
        # Pedir ubicación de salida
        output_file, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Documento",
            f"documento_{plantilla}",
            "HTML Files (*.html)"
        )
        
        if not output_file:
            return
        
        try:
            variables = self._obtener_variables()
            success = self.template_engine.generate_from_html_template(
                plantilla, variables, output_file
            )
            
            if success:
                QMessageBox.information(
                    self, "Éxito",
                    f"Documento generado exitosamente:\n{output_file}"
                )
            else:
                QMessageBox.warning(self, "Error", "No se pudo generar el documento")
        
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al generar documento: {e}")
    
    def _generar_carta_oferta(self):
        """Genera una carta de oferta automática."""
        output_file, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Carta de Oferta",
            "carta_oferta.docx",
            "Word Documents (*.docx)"
        )
        
        if not output_file:
            return
        
        try:
            # Preparar datos
            licitacion_data = {
                "institucion": self.var_inputs["institucion"].text(),
                "numero_proceso": self.var_inputs["numero_proceso"].text(),
                "nombre_proceso": self.var_inputs["nombre_proceso"].text(),
            }
            
            empresa_data = {
                "nombre": self.var_inputs["razon_social"].text(),
                "rnc": self.var_inputs["rnc"].text(),
                "direccion": "",
                "telefono": "",
                "email": "",
            }
            
            success = self.template_engine.generate_carta_oferta(
                licitacion_data, empresa_data, output_file
            )
            
            if success:
                QMessageBox.information(
                    self, "Éxito",
                    f"Carta de oferta generada exitosamente:\n{output_file}"
                )
            else:
                QMessageBox.warning(self, "Error", "No se pudo generar la carta de oferta")
        
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al generar carta: {e}")
    
    def _mostrar_ayuda(self):
        """Muestra ayuda sobre el uso de plantillas."""
        ayuda = """
AYUDA - GESTIÓN DE PLANTILLAS

1. CARGAR PLANTILLAS:
   - Use el botón "Cargar Plantilla" para agregar archivos DOCX o HTML
   - Las plantillas se copian al directorio de plantillas de la aplicación

2. CREAR PLANTILLAS SIMPLES:
   - Use "Nueva Plantilla Simple" para crear una plantilla básica
   - Se generará un archivo DOCX con variables predefinidas

3. USAR VARIABLES:
   - En sus plantillas, use el formato {{nombre_variable}}
   - Ejemplo: {{razon_social}}, {{numero_proceso}}, etc.
   - Las variables disponibles se muestran en el panel derecho

4. GENERAR DOCUMENTOS:
   - Seleccione una plantilla de la lista
   - Complete los valores de las variables
   - Use "Generar DOCX" o "Generar HTML" según el tipo de plantilla
   - Elija dónde guardar el documento generado

5. CARTA DE OFERTA:
   - Use "Carta de Oferta" para generar automáticamente una carta
   - Se usará una plantilla predefinida o se creará una simple
   - Complete los datos básicos de la licitación y empresa

NOTA: Las plantillas DOCX deben crearse con Microsoft Word o LibreOffice
y contener las variables en el formato {{variable}}.
        """.strip()
        
        QMessageBox.information(self, "Ayuda - Plantillas", ayuda)
