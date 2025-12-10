# app/ui/dialogs/dialogo_gestionar_empresas.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QGroupBox, QPushButton, QLabel, QLineEdit, QMessageBox, QHeaderView, QStyle
)
from PyQt6.QtCore import Qt
# Importamos el formulario de edición/creación genérico
from .gestionar_entidad_dialog import DialogoGestionarEntidad

class DialogoGestionarEmpresas(QDialog):
    """
    Dialogo para gestionar empresas (agregar, editar, eliminar) con aspecto profesional.
    Usa el db_adapter para leer y guardar.
    """
    def __init__(self, parent, db): # Quitamos empresas_registradas, siempre leemos de DB
        super().__init__(parent)
        self.setWindowTitle("Gestor de Empresas")
        self.setMinimumSize(1000, 550) # Un poco más ancho para más columnas
        self.db = db # db ahora es una instancia de DatabaseAdapter

        # Leemos la lista FRESCA de la base de datos al abrir
        try:
            self.empresas = self.db.get_empresas_maestras()
        except Exception as e:
            QMessageBox.critical(self, "Error al Cargar", f"No se pudo cargar la lista de empresas:\n{e}")
            self.empresas = [] # Inicializar como lista vacía en caso de error

        self.empresas.sort(key=lambda x: x.get("nombre", "").upper())

        self.main_layout = QVBoxLayout(self)
        self._crear_panel_empresas()
        self._actualizar_tabla()

    def _crear_panel_empresas(self):
        # Tabla de empresas (con las columnas adicionales)
        group = QGroupBox("Listado de Empresas")
        vbox = QVBoxLayout(group)
        self.table = QTableWidget(0, 8) # 8 columnas ahora
        self.table.setHorizontalHeaderLabels([
            "Nombre", "RNC", "RPE", "Teléfono", "Correo", "Dirección",
            "Representante", "Cargo Repr."
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # Ajustar anchos relativos (ejemplo)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive) # Nombre
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive) # RNC
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive) # RPE
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Interactive) # Representante
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Interactive) # Cargo Repr.
        self.table.setColumnWidth(0, 250); self.table.setColumnWidth(1, 100)
        self.table.setColumnWidth(2, 100); self.table.setColumnWidth(6, 150)
        self.table.setColumnWidth(7, 150)

        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        vbox.addWidget(self.table)
        self.main_layout.addWidget(group)

        # Botones de acciones (igual que instituciones)
        btns = QHBoxLayout()
        self.btn_agregar = QPushButton(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder), "Agregar")
        self.btn_editar = QPushButton(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContents), "Editar")
        self.btn_eliminar = QPushButton(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon), "Eliminar")
        # Estilos de botones
        for btn, base, hover, pressed in [
            (self.btn_agregar, "#43A047", "#66BB6A", "#388E3C"),
            (self.btn_editar, "#FBC02D", "#FFF176", "#F9A825"),
            (self.btn_eliminar, "#D32F2F", "#EF5350", "#B71C1C"),
        ]:
            btn.setStyleSheet(f"""
                QPushButton {{ background-color: {base}; color: white; font-weight: bold; border-radius:6px; padding:8px; }}
                QPushButton:hover {{ background-color: {hover}; }}
                QPushButton:pressed {{ background-color: {pressed}; }}
            """)
        # Conexiones de botones
        self.btn_agregar.clicked.connect(self._agregar_empresa)
        self.btn_editar.clicked.connect(self._editar_empresa)
        self.btn_eliminar.clicked.connect(self._eliminar_empresa)
        # Añadir botones al layout
        btns.addWidget(self.btn_agregar)
        btns.addWidget(self.btn_editar)
        btns.addWidget(self.btn_eliminar)
        self.main_layout.addLayout(btns)

        # Etiqueta de estado
        self.lbl_status = QLabel()
        self.main_layout.addWidget(self.lbl_status)
        self._actualizar_status()

        # Botón Guardar y Cerrar
        btn_guardar = QPushButton(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton), "Guardar y Cerrar")
        btn_guardar.setMinimumWidth(180); btn_guardar.setFixedHeight(36)
        btn_guardar.setStyleSheet("""
            QPushButton { background-color: #1976D2; color: white; font-weight: bold; border-radius:6px; padding:10px; }
            QPushButton:hover { background-color: #64B5F6; }
            QPushButton:pressed { background-color: #1565C0; }
        """)
        btn_guardar.clicked.connect(self._guardar_y_cerrar)
        self.main_layout.addWidget(btn_guardar, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)

    def _actualizar_tabla(self):
        """Llena la tabla con los datos de la lista self.empresas."""
        self.table.setRowCount(0)
        # Usamos self.empresas (la lista en memoria)
        for emp in self.empresas:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(emp.get("nombre", "")))
            self.table.setItem(row, 1, QTableWidgetItem(emp.get("rnc", "")))
            self.table.setItem(row, 2, QTableWidgetItem(emp.get("rpe", ""))) # Nuevo
            self.table.setItem(row, 3, QTableWidgetItem(emp.get("telefono", "")))
            self.table.setItem(row, 4, QTableWidgetItem(emp.get("correo", "")))
            self.table.setItem(row, 5, QTableWidgetItem(emp.get("direccion", "")))
            self.table.setItem(row, 6, QTableWidgetItem(emp.get("representante", ""))) # Nuevo
            self.table.setItem(row, 7, QTableWidgetItem(emp.get("cargo_representante", ""))) # Nuevo
        self._actualizar_status()

    def _actualizar_status(self):
        """Actualiza la etiqueta que muestra el número total de empresas."""
        self.lbl_status.setText(f"Total: {len(self.empresas)} empresas")

    def _agregar_empresa(self):
        """Abre el diálogo para agregar una nueva empresa."""
        # Usamos el diálogo genérico DialogoGestionarEntidad
        dialog = DialogoGestionarEntidad(self, "Agregar Empresa", "empresa", None)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.result:
            nueva = dialog.result
            # Validar duplicados en la lista de memoria (ignorando mayúsculas/minúsculas)
            nombre_nuevo = nueva.get("nombre", "").strip()
            if any(e.get("nombre", "").strip().lower() == nombre_nuevo.lower() for e in self.empresas):
                 QMessageBox.critical(self, "Error", f"Ya existe una empresa con el nombre '{nombre_nuevo}'.")
                 return
            # Añade la nueva empresa a la lista en memoria
            self.empresas.append(nueva)
            self.empresas.sort(key=lambda x: x.get("nombre", "").upper()) # Reordenar
            self._actualizar_tabla() # Refresca la tabla
            QMessageBox.information(self, "Éxito", "Empresa agregada (recuerda Guardar y Cerrar).")

    def _editar_empresa(self):
        """Abre el diálogo para editar la empresa seleccionada."""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Sin Selección", "Selecciona una empresa para editar.")
            return

        # Buscamos por nombre en nuestra lista en memoria para obtener el dict original
        nombre_actual = self.table.item(row, 0).text()
        emp_actual_idx = -1
        for idx, emp in enumerate(self.empresas):
            if emp.get("nombre") == nombre_actual:
                emp_actual_idx = idx
                break

        if emp_actual_idx == -1: return # Seguridad, no debería pasar

        emp_actual = self.empresas[emp_actual_idx]

        # Usamos el diálogo genérico DialogoGestionarEntidad, pasando los datos actuales
        dialog = DialogoGestionarEntidad(self, "Editar Empresa", "empresa", emp_actual)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.result:
            datos_editados = dialog.result
            nombre_editado = datos_editados.get("nombre", "").strip()

             # Validar duplicados (excepto si el nombre no cambió)
            if nombre_editado.lower() != nombre_actual.lower():
                 if any(e.get("nombre", "").strip().lower() == nombre_editado.lower() for e in self.empresas):
                    QMessageBox.critical(self, "Error", f"Ya existe otra empresa con el nombre '{nombre_editado}'.")
                    return

            # Actualiza la empresa en la lista en memoria
            self.empresas[emp_actual_idx] = datos_editados
            self.empresas.sort(key=lambda x: x.get("nombre", "").upper()) # Reordenar
            self._actualizar_tabla() # Refresca la tabla
            QMessageBox.information(self, "Éxito", "Empresa editada (recuerda Guardar y Cerrar).")

    def _eliminar_empresa(self):
        """Elimina la empresa seleccionada de la lista en memoria (si no está en uso)."""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Sin Selección", "Selecciona una empresa para eliminar.")
            return

        nombre = self.table.item(row, 0).text()

        # Verifica que no esté en uso usando el db_adapter
        if self.db.is_empresa_en_uso(nombre):
            QMessageBox.critical(self, "Error", f"La empresa '{nombre}' está en uso en una o más licitaciones (o lotes) y no se puede eliminar.")
            return

        if QMessageBox.question(self, "Confirmar", f"¿Eliminar la empresa '{nombre}' del catálogo?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            # Eliminamos de la lista en memoria
            self.empresas = [emp for emp in self.empresas if emp.get("nombre") != nombre]
            self._actualizar_tabla() # Refresca la tabla
            QMessageBox.information(self, "Eliminada", f"La empresa '{nombre}' fue eliminada (recuerda Guardar y Cerrar).")

    def _guardar_y_cerrar(self):
        """Guarda la lista completa de empresas en la base de datos y cierra el diálogo."""
        # Llama al método del db_adapter para guardar la lista self.empresas
        if self.db.save_empresas_maestras(self.empresas):
            QMessageBox.information(self, "Guardado", "Catálogo de empresas guardado correctamente.")
            self.accept() # Cierra el diálogo con éxito (señal aceptada)
        else:
            QMessageBox.critical(self, "Error", "No se pudo guardar el catálogo en la base de datos.")
            # No cerramos si hubo error al guardar


# Añade al final de la clase SeleccionarEmpresasDialog:

    def get_empresas_seleccionadas(self) -> list[str]:
        """
        Devuelve los nombres de empresas seleccionadas.
        Soporta estados intermedios si el usuario no pulsó Aceptar aún.
        """
        # Intenta usar 'resultado' si existe y es lista; si no, usa el set de selección en memoria.
        val = None
        for cand in ("resultado", "result", "selected_names", "seleccionadas", "nombres_seleccionados"):
            if hasattr(self, cand):
                v = getattr(self, cand)
                try:
                    v = v() if callable(v) else v
                except Exception:
                    pass
                if isinstance(v, list):
                    val = v
                    break
                if isinstance(v, set):
                    val = list(v)
                    break

        if val is None:
            # Fallback a un atributo típico con set() interno
            if hasattr(self, "nombres_seleccionados"):
                ns = getattr(self, "nombres_seleccionados")
                if isinstance(ns, set):
                    val = list(ns)
        # Normaliza a lista de str
        out = []
        if isinstance(val, list):
            for v in val:
                if isinstance(v, str):
                    out.append(v)
                elif isinstance(v, dict):
                    n = v.get("nombre") or v.get("name") or v.get("razon_social")
                    if n: out.append(str(n))
                else:
                    n = getattr(v, "nombre", None) or getattr(v, "name", None)
                    if n: out.append(str(n))
        return out

    # Alias para compatibilidad con otras partes del código
    def get_seleccionados(self) -> list[str]:
        return self.get_empresas_seleccionadas()
# Ya no necesitas DialogoEmpresaForm, DialogoGestionarEntidad lo reemplaza