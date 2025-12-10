from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QGroupBox, QPushButton, QLabel, QLineEdit, QMessageBox, QHeaderView, QStyle
)
from PyQt6.QtCore import Qt

class DialogoGestionarEmpresas(QDialog):
    """
    Dialogo para gestionar empresas (agregar, editar, eliminar) con aspecto profesional.
    Funciona desde el menú principal y desde cualquier ventana que lo requiera.
    """
    def __init__(self, parent, db, empresas_registradas=None):
        super().__init__(parent)
        self.setWindowTitle("Gestor de Empresas")
        self.setMinimumSize(900, 530)
        self.db = db
        # Si viene la lista desde la app principal, úsala; si no, consulta DB
        if empresas_registradas is not None:
            self.empresas = [dict(e) for e in empresas_registradas]
        else:
            self.empresas = self.db._get_master_table('empresas_maestras')
        self.empresas.sort(key=lambda x: x.get("nombre", "").upper())

        self.main_layout = QVBoxLayout(self)
        self._crear_panel_empresas()
        self._actualizar_tabla()

    def _crear_panel_empresas(self):
            # Tabla de empresas (con todas las columnas necesarias)
            group = QGroupBox("Listado de Empresas")
            vbox = QVBoxLayout(group)
            self.table = QTableWidget(0, 8) # 8 columnas ahora
            self.table.setHorizontalHeaderLabels([
                "Nombre", "RNC", "RPE", "Teléfono", "Correo", "Dirección",
                "Representante", "Cargo Repr."
            ])
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            # Ajustar anchos interactivos para columnas clave para mejor visualización
            header = self.table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive) # Nombre
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive) # RNC
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive) # RPE
            header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)     # Dirección toma más espacio
            header.setSectionResizeMode(6, QHeaderView.ResizeMode.Interactive) # Representante
            header.setSectionResizeMode(7, QHeaderView.ResizeMode.Interactive) # Cargo Repr.
            # Definir anchos iniciales
            self.table.setColumnWidth(0, 250); self.table.setColumnWidth(1, 100)
            self.table.setColumnWidth(2, 100); self.table.setColumnWidth(3, 100) # Teléfono
            self.table.setColumnWidth(4, 150) # Correo
            self.table.setColumnWidth(6, 150); self.table.setColumnWidth(7, 150)

            self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows) # Seleccionar filas completas
            self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers) # No permitir editar directamente en la tabla
            vbox.addWidget(self.table)
            self.main_layout.addWidget(group)

            # Botones de acciones (Agregar, Editar, Eliminar)
            btns = QHBoxLayout()
            self.btn_agregar = QPushButton(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder), "Agregar")
            # V V V ESTA ES LA LÍNEA CORREGIDA V V V
            self.btn_editar = QPushButton(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView), "Editar") # <-- CORREGIDO
            # ^ ^ ^ ESTA ES LA LÍNEA CORREGIDA ^ ^ ^
            self.btn_eliminar = QPushButton(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon), "Eliminar")
            # Estilos visuales para los botones
            for btn, base, hover, pressed in [
                (self.btn_agregar, "#43A047", "#66BB6A", "#388E3C"), # Verde
                (self.btn_editar, "#FBC02D", "#FFF176", "#F9A825"),  # Amarillo
                (self.btn_eliminar, "#D32F2F", "#EF5350", "#B71C1C"), # Rojo
            ]:
                btn.setStyleSheet(f"""
                    QPushButton {{ background-color: {base}; color: white; font-weight: bold; border-radius:6px; padding:8px; }}
                    QPushButton:hover {{ background-color: {hover}; }}
                    QPushButton:pressed {{ background-color: {pressed}; }}
                """)
            # Conectar los clics de los botones a las funciones correspondientes
            self.btn_agregar.clicked.connect(self._agregar_empresa)
            self.btn_editar.clicked.connect(self._editar_empresa)
            self.btn_eliminar.clicked.connect(self._eliminar_empresa)
            # Añadir los botones al layout horizontal
            btns.addWidget(self.btn_agregar)
            btns.addWidget(self.btn_editar)
            btns.addWidget(self.btn_eliminar)
            # Añadir el layout de botones al layout principal
            self.main_layout.addLayout(btns)

            # Etiqueta de estado para mostrar el contador
            self.lbl_status = QLabel()
            self.main_layout.addWidget(self.lbl_status)
            self._actualizar_status() # Llama para mostrar el estado inicial

            # Botón para guardar los cambios y cerrar la ventana
            btn_guardar = QPushButton(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton), "Guardar y Cerrar")
            btn_guardar.setMinimumWidth(180) # Ancho mínimo
            btn_guardar.setFixedHeight(36)  # Altura fija
            # Estilos visuales para el botón de guardar
            btn_guardar.setStyleSheet("""
                QPushButton { background-color: #1976D2; color: white; font-weight: bold; border-radius:6px; padding:10px; }
                QPushButton:hover { background-color: #64B5F6; }
                QPushButton:pressed { background-color: #1565C0; }
            """)
            # Conectar clic a la función de guardar y cerrar
            btn_guardar.clicked.connect(self._guardar_y_cerrar)
            # Añadir el botón al layout principal, centrado y abajo
            self.main_layout.addWidget(btn_guardar, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
            
    def _actualizar_tabla(self):
        self.table.setRowCount(0)
        for emp in self.empresas:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(emp.get("nombre", "")))
            self.table.setItem(row, 1, QTableWidgetItem(emp.get("rnc", "")))
            self.table.setItem(row, 2, QTableWidgetItem(emp.get("telefono", "")))
            self.table.setItem(row, 3, QTableWidgetItem(emp.get("correo", "")))
            self.table.setItem(row, 4, QTableWidgetItem(emp.get("direccion", "")))
        self._actualizar_status()

    def _actualizar_status(self):
        self.lbl_status.setText(f"Total: {len(self.empresas)} empresas")

    def _agregar_empresa(self):
        dialog = DialogoEmpresaForm(self, None, self.empresas)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            nueva = dialog.get_empresa()
            self.empresas.append(nueva)
            self._actualizar_tabla()
            QMessageBox.information(self, "Éxito", "Empresa agregada correctamente.")

    def _editar_empresa(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.empresas):
            QMessageBox.warning(self, "Sin Selección", "Selecciona una empresa para editar.")
            return
        emp_actual = self.empresas[row]
        dialog = DialogoEmpresaForm(self, emp_actual, self.empresas)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.empresas[row] = dialog.get_empresa()
            self._actualizar_tabla()
            QMessageBox.information(self, "Éxito", "Empresa editada correctamente.")

    def _eliminar_empresa(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.empresas):
            QMessageBox.warning(self, "Sin Selección", "Selecciona una empresa para eliminar.")
            return
        nombre = self.empresas[row].get("nombre", "")
        # Verifica que no esté en uso (en alguna licitación)
        if self._empresa_en_uso(nombre):
            QMessageBox.critical(self, "Error", f"La empresa '{nombre}' está en uso y no se puede eliminar.")
            return
        if QMessageBox.question(self, "Confirmar", f"¿Eliminar la empresa '{nombre}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self.empresas.pop(row)
            self._actualizar_tabla()
            QMessageBox.information(self, "Eliminada", f"La empresa '{nombre}' fue eliminada.")

    def _empresa_en_uso(self, nombre):
        # Consulta si alguna licitación usa esta empresa
        todas_licitaciones = self.db.get_all_data()[0]  # primer elemento son licitaciones
        for lic in todas_licitaciones:
            empresas_lic = [e.get("nombre", "") for e in lic.get("empresas_nuestras", [])]
            if nombre in empresas_lic:
                return True
        return False

    def _guardar_y_cerrar(self):
        # Guarda en la base de datos y cierra
        try:
            self.db.save_master_lists(
                empresas=self.empresas,
                instituciones=self.db._get_master_table('instituciones_maestras'),
                documentos_maestros=self.db._get_master_table('documentos_maestros'),
                competidores_maestros=self.db._get_master_table('competidores_maestros'),
                responsables_maestros=self.db._get_master_table('responsables_maestros'),
                replace_tables={'empresas_maestras'}
            )
            QMessageBox.information(self, "Guardado", "Catálogo de empresas guardado correctamente.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar.\n{e}")
        self.accept()

class DialogoEmpresaForm(QDialog):
    """
    Formulario para agregar/editar una empresa. Moderno, con validación y feedback visual.
    """
    def __init__(self, parent, empresa_actual, empresas_existentes):
        super().__init__(parent)
        self.setWindowTitle("Agregar Empresa" if empresa_actual is None else "Editar Empresa")
        self.setMinimumSize(400, 380)
        self.result = None
        self.empresas_existentes = empresas_existentes

        vbox = QVBoxLayout(self)
        self.txt_nombre = QLineEdit()
        self.txt_rnc = QLineEdit()
        self.txt_telefono = QLineEdit()
        self.txt_correo = QLineEdit()
        self.txt_direccion = QLineEdit()
        self.txt_rpe = QLineEdit()
        self.txt_representante = QLineEdit()
        self.txt_cargo_representante = QLineEdit()
        if empresa_actual:
            self.txt_nombre.setText(empresa_actual.get("nombre", ""))
            self.txt_rnc.setText(empresa_actual.get("rnc", ""))
            self.txt_telefono.setText(empresa_actual.get("telefono", ""))
            self.txt_correo.setText(empresa_actual.get("correo", ""))
            self.txt_direccion.setText(empresa_actual.get("direccion", ""))
            self.txt_rpe.setText(empresa_actual.get("rpe", ""))
            self.txt_representante.setText(empresa_actual.get("representante", ""))
            self.txt_cargo_representante.setText(empresa_actual.get("cargo_representante", ""))

        vbox.addWidget(QLabel("Nombre:"))
        vbox.addWidget(self.txt_nombre)
        vbox.addWidget(QLabel("RNC:"))
        vbox.addWidget(self.txt_rnc)
        vbox.addWidget(QLabel("Teléfono:"))
        vbox.addWidget(self.txt_telefono)
        vbox.addWidget(QLabel("Correo:"))
        vbox.addWidget(self.txt_correo)
        vbox.addWidget(QLabel("Dirección:"))
        vbox.addWidget(self.txt_direccion)
        vbox.addWidget(QLabel("RPE:"))
        vbox.addWidget(self.txt_rpe)
        vbox.addWidget(QLabel("Representante:"))
        vbox.addWidget(self.txt_representante)
        vbox.addWidget(QLabel("Cargo del Representante:"))
        vbox.addWidget(self.txt_cargo_representante)

        btns = QHBoxLayout()
        btn_ok = QPushButton(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOkButton), "Guardar")
        btn_ok.clicked.connect(self._guardar)
        btn_cancel = QPushButton(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton), "Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_ok)
        btns.addWidget(btn_cancel)
        vbox.addLayout(btns)

    def _guardar(self):
        nombre = self.txt_nombre.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Dato requerido", "El nombre no puede estar vacío.")
            return
        # Validación anti-duplicados (ignora mayúsculas/minúsculas)
        for emp in self.empresas_existentes:
            if emp.get("nombre", "").strip().lower() == nombre.lower():
                # Si está editando, permite si es el mismo registro
                if emp is not self.result:
                    QMessageBox.critical(self, "Error", f"Ya existe una empresa con el nombre '{nombre}'.")
                    return
        self.result = {
            "nombre": nombre,
            "rnc": self.txt_rnc.text().strip(),
            "telefono": self.txt_telefono.text().strip(),
            "correo": self.txt_correo.text().strip(),
            "direccion": self.txt_direccion.text().strip(),
            "rpe": self.txt_rpe.text().strip(),
            "representante": self.txt_representante.text().strip(),
            "cargo_representante": self.txt_cargo_representante.text().strip()
        }
        self.accept()

    def get_empresa(self):
        return self.result if self.result is not None else {}