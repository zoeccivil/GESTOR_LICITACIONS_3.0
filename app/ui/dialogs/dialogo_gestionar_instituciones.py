# app/ui/dialogs/dialogo_gestionar_instituciones.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QGroupBox, QPushButton, QLabel, QLineEdit, QMessageBox, QHeaderView, QStyle
)
from PyQt6.QtCore import Qt
# Importamos el formulario de edición/creación genérico
from .gestionar_entidad_dialog import DialogoGestionarEntidad

class DialogoGestionarInstituciones(QDialog):
    """
    Dialogo para gestionar instituciones (agregar, editar, eliminar) con aspecto profesional.
    Funciona tanto desde el menú principal como desde la ventana de agregar licitación.
    Usa el db_adapter para leer y guardar.
    """
    def __init__(self, parent, db): # Quitamos instituciones_registradas, siempre leemos de DB
        super().__init__(parent)
        self.setWindowTitle("Gestor de Instituciones")
        self.setMinimumSize(900, 530)
        self.db = db # db ahora es una instancia de DatabaseAdapter

        # Leemos la lista FRESCA de la base de datos al abrir
        try:
            self.instituciones = self.db.get_instituciones_maestras()
        except Exception as e:
            QMessageBox.critical(self, "Error al Cargar", f"No se pudo cargar la lista de instituciones:\n{e}")
            self.instituciones = [] # Inicializar como lista vacía en caso de error

        self.instituciones.sort(key=lambda x: x.get("nombre", "").upper())

        self.main_layout = QVBoxLayout(self)
        self._crear_panel_instituciones() # Llama al método para construir la UI
        self._actualizar_tabla() # Llama al método para poblar la tabla inicialmente

    def _crear_panel_instituciones(self):
            # Tabla de instituciones
            group = QGroupBox("Listado de Instituciones")
            vbox = QVBoxLayout(group)
            self.table = QTableWidget(0, 5) # 5 columnas: Nombre, RNC, Teléfono, Correo, Dirección
            self.table.setHorizontalHeaderLabels(["Nombre", "RNC", "Teléfono", "Correo", "Dirección"])
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            # Ajustar anchos interactivos para columnas clave
            header = self.table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive) # Nombre
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)     # Dirección toma el espacio restante
            self.table.setColumnWidth(0, 250) # Ancho inicial para Nombre
            self.table.setColumnWidth(1, 100) # RNC
            self.table.setColumnWidth(2, 100) # Teléfono
            self.table.setColumnWidth(3, 150) # Correo

            self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows) # Seleccionar filas completas
            self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers) # No editable directamente
            vbox.addWidget(self.table)
            self.main_layout.addWidget(group)

            # Botones de acciones
            btns = QHBoxLayout()
            self.btn_agregar = QPushButton(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder), "Agregar")
            self.btn_editar = QPushButton(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView), "Editar")
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
            # Conectar señales de los botones a las funciones
            self.btn_agregar.clicked.connect(self._agregar_institucion)
            self.btn_editar.clicked.connect(self._editar_institucion)
            self.btn_eliminar.clicked.connect(self._eliminar_institucion)
            # Añadir botones al layout horizontal
            btns.addWidget(self.btn_agregar)
            btns.addWidget(self.btn_editar)
            btns.addWidget(self.btn_eliminar)
            # Añadir layout de botones al principal
            self.main_layout.addLayout(btns)

            # Etiqueta de estado (contador)
            self.lbl_status = QLabel()
            self.main_layout.addWidget(self.lbl_status)
            self._actualizar_status() # Mostrar contador inicial

            # Botón Guardar y Cerrar
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
        """Limpia y rellena la tabla con los datos de la lista self.instituciones."""
        self.table.setRowCount(0)
        # Usamos self.instituciones (la lista en memoria)
        for inst in self.instituciones:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(inst.get("nombre", "")))
            self.table.setItem(row, 1, QTableWidgetItem(inst.get("rnc", "")))
            self.table.setItem(row, 2, QTableWidgetItem(inst.get("telefono", "")))
            self.table.setItem(row, 3, QTableWidgetItem(inst.get("correo", "")))
            self.table.setItem(row, 4, QTableWidgetItem(inst.get("direccion", ""))) # Columna Dirección
        self._actualizar_status() # Actualiza el contador

    def _actualizar_status(self):
        """Actualiza la etiqueta que muestra el número total de instituciones."""
        self.lbl_status.setText(f"Total: {len(self.instituciones)} instituciones")

    def _get_dialog_result(self, dialog):
        """
        Extrae de forma robusta el resultado de un diálogo.
        Soporta:
         - dialog.get_data()
         - dialog.get_result() / dialog.result() (callable o atributo)
         - dialog.resultado / dialog.resultado() / dialog.result (callable o atributo)
        Retorna dict o None.
        """
        # 1) get_data()
        if hasattr(dialog, "get_data") and callable(getattr(dialog, "get_data")):
            try:
                return dialog.get_data()
            except Exception:
                pass
        # 2) buscar nombres comunes
        for name in ("resultado", "result", "get_result", "get_resultado"):
            if hasattr(dialog, name):
                val = getattr(dialog, name)
                try:
                    if callable(val):
                        return val()
                    else:
                        return val
                except Exception:
                    return val
        return None

    def _agregar_institucion(self):
        """Abre el diálogo para agregar una nueva institución."""
        dialog = DialogoGestionarEntidad(self, "Agregar Institución", "institucion", None)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            nueva = self._get_dialog_result(dialog)
            if not isinstance(nueva, dict):
                QMessageBox.warning(self, "Resultado inválido", "El diálogo no devolvió los datos de la institución.")
                return
            # Validar duplicados en la lista de memoria (ignorando mayúsculas/minúsculas)
            nombre_nuevo = nueva.get("nombre", "").strip()
            if any(i.get("nombre", "").strip().lower() == nombre_nuevo.lower() for i in self.instituciones):
                 QMessageBox.critical(self, "Error", f"Ya existe una institución con el nombre '{nombre_nuevo}'.")
                 return # No agregar si está duplicado
            # Añadir a la lista en memoria
            self.instituciones.append(nueva)
            self.instituciones.sort(key=lambda x: x.get("nombre", "").upper()) # Reordenar alfabéticamente
            self._actualizar_tabla() # Refrescar la tabla
            QMessageBox.information(self, "Éxito", "Institución agregada (recuerda Guardar y Cerrar para persistir).")

    def _editar_institucion(self):
        """Abre el diálogo para editar la institución seleccionada."""
        row = self.table.currentRow() # Obtiene la fila seleccionada
        if row < 0: # Si no hay fila seleccionada
            QMessageBox.warning(self, "Sin Selección", "Selecciona una institución de la tabla para editar.")
            return

        # Busca el diccionario correspondiente en la lista en memoria usando el nombre de la fila
        nombre_actual = self.table.item(row, 0).text()
        inst_actual_idx = -1
        for idx, inst in enumerate(self.instituciones):
            if inst.get("nombre") == nombre_actual:
                inst_actual_idx = idx
                break

        if inst_actual_idx == -1: return # Seguridad, no debería pasar si la tabla está sincronizada

        inst_actual = self.instituciones[inst_actual_idx] # El diccionario de la institución a editar

        # Abre el diálogo genérico, pasando los datos actuales para prellenar el formulario
        dialog = DialogoGestionarEntidad(self, "Editar Institución", "institucion", inst_actual)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            datos_editados = self._get_dialog_result(dialog)
            if not isinstance(datos_editados, dict):
                QMessageBox.warning(self, "Resultado inválido", "El diálogo no devolvió los datos editados.")
                return
            nombre_editado = datos_editados.get("nombre", "").strip()

            # Validar duplicados (solo si el nombre cambió y ya existe OTRO con ese nombre)
            if nombre_editado.lower() != nombre_actual.lower():
                 if any(i.get("nombre", "").strip().lower() == nombre_editado.lower() for i in self.instituciones):
                    QMessageBox.critical(self, "Error", f"Ya existe otra institución con el nombre '{nombre_editado}'.")
                    return # No editar si causa duplicado

            # Actualiza el diccionario en la lista en memoria
            self.instituciones[inst_actual_idx] = datos_editados
            self.instituciones.sort(key=lambda x: x.get("nombre", "").upper()) # Reordenar
            self._actualizar_tabla() # Refrescar tabla
            QMessageBox.information(self, "Éxito", "Institución editada (recuerda Guardar y Cerrar).")

    def _eliminar_institucion(self):
        """Elimina la institución seleccionada de la lista en memoria (si no está en uso)."""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Sin Selección", "Selecciona una institución de la tabla para eliminar.")
            return

        nombre = self.table.item(row, 0).text() # Nombre de la institución a eliminar

        # Llama al método del db_adapter para verificar si está en uso en alguna licitación
        try:
            if self.db.is_institucion_en_uso(nombre):
                QMessageBox.critical(self, "Error - En Uso", f"La institución '{nombre}' está asignada a una o más licitaciones y no puede ser eliminada.")
                return # No permitir eliminar si está en uso
        except Exception as e:
             QMessageBox.critical(self, "Error", f"No se pudo verificar el uso de la institución:\n{e}")
             return # No permitir si hay error en la verificación

        # Preguntar confirmación al usuario
        if QMessageBox.question(self, "Confirmar Eliminación", f"¿Estás seguro de que quieres eliminar la institución '{nombre}' del catálogo?\nEsta acción no se puede deshacer.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            # Elimina de la lista en memoria (filtrando por nombre)
            self.instituciones = [inst for inst in self.instituciones if inst.get("nombre") != nombre]
            self._actualizar_tabla() # Refresca la tabla
            QMessageBox.information(self, "Eliminada", f"La institución '{nombre}' fue eliminada de la lista (recuerda Guardar y Cerrar para persistir).")

    def _guardar_y_cerrar(self):
        """Guarda la lista completa de instituciones en la base de datos y cierra el diálogo."""
        # Llama al método del db_adapter para guardar la lista self.instituciones
        try:
            if self.db.save_instituciones_maestras(self.instituciones):
                QMessageBox.information(self, "Guardado", "Catálogo de instituciones guardado correctamente en la base de datos.")
                self.accept() # Cierra el diálogo con éxito (señal aceptada)
            else:
                QMessageBox.critical(self, "Error al Guardar", "No se pudo guardar el catálogo en la base de datos.")
                # No cerramos si hubo error al guardar
        except Exception as e:
             QMessageBox.critical(self, "Error Crítico al Guardar", f"Ocurrió un error inesperado al guardar:\n{e}")

# Ya no necesitas DialogoInstitucionForm, DialogoGestionarEntidad lo reemplaza