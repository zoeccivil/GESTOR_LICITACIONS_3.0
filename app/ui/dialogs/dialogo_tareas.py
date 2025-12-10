"""
Diálogo para gestionar tareas (estilo Kanban).
"""
from __future__ import annotations
from typing import Optional, List, Dict, Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QLineEdit, QTextEdit, QComboBox, QDateEdit, QGroupBox,
    QInputDialog
)
from PyQt6.QtCore import QDate

from app.core.tasks_manager import TasksManager, Task


class DialogoGestionarTareas(QDialog):
    """Diálogo para gestionar tareas con vista Kanban simplificada."""
    
    COL_TITULO = 0
    COL_ESTADO = 1
    COL_RESPONSABLE = 2
    COL_PRIORIDAD = 3
    COL_FECHA_LIMITE = 4
    COL_DESCRIPCION = 5
    
    task_updated = pyqtSignal()
    
    def __init__(self, parent, entity: Optional[str] = None, entity_id: Optional[str] = None):
        super().__init__(parent)
        self.entity = entity
        self.entity_id = entity_id
        self.tasks_manager = TasksManager()
        self.tasks: List[Task] = []
        
        title = "Gestión de Tareas"
        if entity and entity_id:
            title += f" - {entity} #{entity_id}"
        
        self.setWindowTitle(title)
        self.resize(1000, 650)
        self.setModal(True)
        
        self._build_ui()
        self._load_tasks()
    
    def _build_ui(self):
        """Construye la interfaz del diálogo."""
        root = QVBoxLayout(self)
        
        # Filtros y acciones rápidas
        top_bar = QHBoxLayout()
        
        btn_nueva = QPushButton("➕ Nueva Tarea")
        btn_nueva.clicked.connect(self._nueva_tarea)
        top_bar.addWidget(btn_nueva)
        
        top_bar.addWidget(QLabel("Estado:"))
        self.combo_filtro_estado = QComboBox()
        self.combo_filtro_estado.addItem("Todas", None)
        self.combo_filtro_estado.addItem("To-Do", "To-Do")
        self.combo_filtro_estado.addItem("En curso", "En curso")
        self.combo_filtro_estado.addItem("Hecho", "Hecho")
        self.combo_filtro_estado.currentIndexChanged.connect(self._aplicar_filtros)
        top_bar.addWidget(self.combo_filtro_estado)
        
        top_bar.addWidget(QLabel("Prioridad:"))
        self.combo_filtro_prioridad = QComboBox()
        self.combo_filtro_prioridad.addItem("Todas", None)
        self.combo_filtro_prioridad.addItem("Alta", "Alta")
        self.combo_filtro_prioridad.addItem("Media", "Media")
        self.combo_filtro_prioridad.addItem("Baja", "Baja")
        self.combo_filtro_prioridad.currentIndexChanged.connect(self._aplicar_filtros)
        top_bar.addWidget(self.combo_filtro_prioridad)
        
        top_bar.addStretch(1)
        
        btn_vencidas = QPushButton("⚠️ Ver Vencidas")
        btn_vencidas.clicked.connect(self._ver_vencidas)
        top_bar.addWidget(btn_vencidas)
        
        root.addLayout(top_bar)
        
        # Tabla de tareas
        self.tbl = QTableWidget(0, 6)
        self.tbl.setHorizontalHeaderLabels([
            "Título", "Estado", "Responsable", "Prioridad", "Fecha Límite", "Descripción"
        ])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        
        # Configurar anchos de columna
        header = self.tbl.horizontalHeader()
        header.setSectionResizeMode(self.COL_TITULO, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(self.COL_ESTADO, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_RESPONSABLE, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_PRIORIDAD, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_FECHA_LIMITE, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_DESCRIPCION, QHeaderView.ResizeMode.Stretch)
        
        self.tbl.itemSelectionChanged.connect(self._update_actions)
        self.tbl.cellDoubleClicked.connect(self._editar_tarea)
        root.addWidget(self.tbl, 1)
        
        # Acciones
        actions = QHBoxLayout()
        
        self.btn_editar = QPushButton("✏️ Editar")
        self.btn_editar.clicked.connect(self._editar_tarea)
        actions.addWidget(self.btn_editar)
        
        self.btn_cambiar_estado = QPushButton("🔄 Cambiar Estado")
        self.btn_cambiar_estado.clicked.connect(self._cambiar_estado)
        actions.addWidget(self.btn_cambiar_estado)
        
        self.btn_comentario = QPushButton("💬 Agregar Comentario")
        self.btn_comentario.clicked.connect(self._agregar_comentario)
        actions.addWidget(self.btn_comentario)
        
        self.btn_eliminar = QPushButton("🗑️ Eliminar")
        self.btn_eliminar.clicked.connect(self._eliminar_tarea)
        actions.addWidget(self.btn_eliminar)
        
        actions.addStretch(1)
        
        btn_actualizar = QPushButton("🔄 Actualizar")
        btn_actualizar.clicked.connect(self._load_tasks)
        actions.addWidget(btn_actualizar)
        
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(self.accept)
        actions.addWidget(btn_cerrar)
        
        root.addLayout(actions)
        
        self._update_actions()
    
    def _load_tasks(self):
        """Carga las tareas."""
        if self.entity and self.entity_id:
            self.tasks = self.tasks_manager.get_tasks_by_entity(self.entity, self.entity_id)
        else:
            self.tasks = self.tasks_manager.get_all_tasks()
        
        self._aplicar_filtros()
    
    def _aplicar_filtros(self):
        """Aplica los filtros y muestra las tareas."""
        estado_filtro = self.combo_filtro_estado.currentData()
        prioridad_filtro = self.combo_filtro_prioridad.currentData()
        
        tasks_filtradas = self.tasks
        
        if estado_filtro:
            tasks_filtradas = [t for t in tasks_filtradas if t.estado == estado_filtro]
        
        if prioridad_filtro:
            tasks_filtradas = [t for t in tasks_filtradas if t.prioridad == prioridad_filtro]
        
        self._populate_table(tasks_filtradas)
    
    def _populate_table(self, tasks: List[Task]):
        """Pobla la tabla con las tareas."""
        self.tbl.setRowCount(0)
        
        for task in tasks:
            row = self.tbl.rowCount()
            self.tbl.insertRow(row)
            
            # Título
            self.tbl.setItem(row, self.COL_TITULO, QTableWidgetItem(task.titulo))
            
            # Estado con emoji
            estado_emoji = {
                "To-Do": "📋",
                "En curso": "🔄",
                "Hecho": "✅",
            }.get(task.estado, "")
            estado_display = f"{estado_emoji} {task.estado}"
            self.tbl.setItem(row, self.COL_ESTADO, QTableWidgetItem(estado_display))
            
            # Responsable
            self.tbl.setItem(row, self.COL_RESPONSABLE, QTableWidgetItem(task.responsable_nombre or "Sin asignar"))
            
            # Prioridad con color
            prioridad_item = QTableWidgetItem(task.prioridad)
            if task.prioridad == "Alta":
                prioridad_item.setForeground(Qt.GlobalColor.red)
            elif task.prioridad == "Media":
                prioridad_item.setForeground(Qt.GlobalColor.darkYellow)
            self.tbl.setItem(row, self.COL_PRIORIDAD, prioridad_item)
            
            # Fecha límite
            fecha_display = task.fecha_limite or "Sin fecha"
            if task.fecha_limite:
                # Mostrar solo la fecha sin hora
                if "T" in task.fecha_limite:
                    fecha_display = task.fecha_limite.split("T")[0]
            self.tbl.setItem(row, self.COL_FECHA_LIMITE, QTableWidgetItem(fecha_display))
            
            # Descripción (truncada)
            desc = task.descripcion[:50] + "..." if len(task.descripcion) > 50 else task.descripcion
            self.tbl.setItem(row, self.COL_DESCRIPCION, QTableWidgetItem(desc))
        
        self._update_actions()
    
    def _get_selected_task(self) -> Optional[Task]:
        """Obtiene la tarea seleccionada."""
        row = self.tbl.currentRow()
        if row < 0:
            return None
        
        # Buscar por título (podríamos usar un ID oculto, pero esto funciona para el ejemplo)
        titulo = self.tbl.item(row, self.COL_TITULO).text()
        for task in self.tasks:
            if task.titulo == titulo:
                return task
        
        return None
    
    def _update_actions(self):
        """Actualiza el estado de los botones."""
        has_selection = self.tbl.currentRow() >= 0
        self.btn_editar.setEnabled(has_selection)
        self.btn_cambiar_estado.setEnabled(has_selection)
        self.btn_comentario.setEnabled(has_selection)
        self.btn_eliminar.setEnabled(has_selection)
    
    def _nueva_tarea(self):
        """Crea una nueva tarea."""
        dialog = DialogoEditarTarea(self, None, self.entity, self.entity_id)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._load_tasks()
            self.task_updated.emit()
    
    def _editar_tarea(self):
        """Edita la tarea seleccionada."""
        task = self._get_selected_task()
        if not task:
            return
        
        dialog = DialogoEditarTarea(self, task)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._load_tasks()
            self.task_updated.emit()
    
    def _cambiar_estado(self):
        """Cambia el estado de la tarea."""
        task = self._get_selected_task()
        if not task or not task.id:
            return
        
        estados = ["To-Do", "En curso", "Hecho"]
        nuevo_estado, ok = QInputDialog.getItem(
            self, "Cambiar Estado", "Nuevo estado:", 
            estados, estados.index(task.estado), False
        )
        
        if ok and nuevo_estado != task.estado:
            try:
                self.tasks_manager.update_task_estado(task.id, nuevo_estado)
                QMessageBox.information(self, "Éxito", f"Estado actualizado a: {nuevo_estado}")
                self._load_tasks()
                self.task_updated.emit()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"No se pudo actualizar el estado: {e}")
    
    def _agregar_comentario(self):
        """Agrega un comentario a la tarea."""
        task = self._get_selected_task()
        if not task or not task.id:
            return
        
        comentario, ok = QInputDialog.getMultiLineText(
            self, "Agregar Comentario", "Comentario:"
        )
        
        if ok and comentario.strip():
            try:
                self.tasks_manager.add_comentario(task.id, comentario.strip())
                QMessageBox.information(self, "Éxito", "Comentario agregado")
                self._load_tasks()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"No se pudo agregar el comentario: {e}")
    
    def _eliminar_tarea(self):
        """Elimina la tarea seleccionada."""
        task = self._get_selected_task()
        if not task or not task.id:
            return
        
        respuesta = QMessageBox.question(
            self, "Confirmar", 
            f"¿Eliminar la tarea '{task.titulo}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if respuesta == QMessageBox.StandardButton.Yes:
            try:
                self.tasks_manager.delete_task(task.id)
                QMessageBox.information(self, "Éxito", "Tarea eliminada")
                self._load_tasks()
                self.task_updated.emit()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"No se pudo eliminar la tarea: {e}")
    
    def _ver_vencidas(self):
        """Muestra solo las tareas vencidas."""
        vencidas = self.tasks_manager.get_overdue_tasks()
        if not vencidas:
            QMessageBox.information(self, "Tareas Vencidas", "No hay tareas vencidas")
            return
        
        self._populate_table(vencidas)


class DialogoEditarTarea(QDialog):
    """Diálogo para crear/editar una tarea."""
    
    def __init__(self, parent, task: Optional[Task] = None, entity: Optional[str] = None, entity_id: Optional[str] = None):
        super().__init__(parent)
        self.task = task
        self.entity = entity
        self.entity_id = entity_id
        self.tasks_manager = TasksManager()
        
        self.setWindowTitle("Editar Tarea" if task else "Nueva Tarea")
        self.resize(550, 500)
        self.setModal(True)
        
        self._build_ui()
        if task:
            self._load_task_data()
    
    def _build_ui(self):
        """Construye la interfaz del diálogo."""
        root = QVBoxLayout(self)
        
        # Título
        root.addWidget(QLabel("Título:"))
        self.txt_titulo = QLineEdit()
        root.addWidget(self.txt_titulo)
        
        # Descripción
        root.addWidget(QLabel("Descripción:"))
        self.txt_descripcion = QTextEdit()
        self.txt_descripcion.setMaximumHeight(100)
        root.addWidget(self.txt_descripcion)
        
        # Responsable
        root.addWidget(QLabel("Responsable:"))
        self.txt_responsable = QLineEdit()
        root.addWidget(self.txt_responsable)
        
        # Estado y Prioridad
        row1 = QHBoxLayout()
        
        row1.addWidget(QLabel("Estado:"))
        self.combo_estado = QComboBox()
        self.combo_estado.addItems(["To-Do", "En curso", "Hecho"])
        row1.addWidget(self.combo_estado)
        
        row1.addWidget(QLabel("Prioridad:"))
        self.combo_prioridad = QComboBox()
        self.combo_prioridad.addItems(["Alta", "Media", "Baja"])
        self.combo_prioridad.setCurrentText("Media")
        row1.addWidget(self.combo_prioridad)
        
        root.addLayout(row1)
        
        # Fecha límite
        root.addWidget(QLabel("Fecha Límite:"))
        self.date_limite = QDateEdit()
        self.date_limite.setCalendarPopup(True)
        self.date_limite.setDate(QDate.currentDate().addDays(7))
        root.addWidget(self.date_limite)
        
        # Botones
        actions = QHBoxLayout()
        actions.addStretch(1)
        
        btn_guardar = QPushButton("💾 Guardar")
        btn_guardar.clicked.connect(self._guardar)
        actions.addWidget(btn_guardar)
        
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        actions.addWidget(btn_cancelar)
        
        root.addLayout(actions)
    
    def _load_task_data(self):
        """Carga los datos de la tarea en el formulario."""
        if not self.task:
            return
        
        self.txt_titulo.setText(self.task.titulo)
        self.txt_descripcion.setPlainText(self.task.descripcion)
        self.txt_responsable.setText(self.task.responsable_nombre)
        
        self.combo_estado.setCurrentText(self.task.estado)
        self.combo_prioridad.setCurrentText(self.task.prioridad)
        
        if self.task.fecha_limite:
            # Parsear fecha ISO
            fecha_str = self.task.fecha_limite
            if "T" in fecha_str:
                fecha_str = fecha_str.split("T")[0]
            try:
                year, month, day = fecha_str.split("-")
                self.date_limite.setDate(QDate(int(year), int(month), int(day)))
            except (ValueError, IndexError):
                pass
    
    def _guardar(self):
        """Guarda la tarea."""
        titulo = self.txt_titulo.text().strip()
        if not titulo:
            QMessageBox.warning(self, "Error", "El título es obligatorio")
            return
        
        descripcion = self.txt_descripcion.toPlainText().strip()
        responsable = self.txt_responsable.text().strip()
        estado = self.combo_estado.currentText()
        prioridad = self.combo_prioridad.currentText()
        fecha_limite = self.date_limite.date().toString("yyyy-MM-dd")
        
        try:
            if self.task and self.task.id:
                # Actualizar tarea existente
                from app.core import firebase_adapter
                update_data = {
                    "titulo": titulo,
                    "descripcion": descripcion,
                    "responsable_nombre": responsable,
                    "estado": estado,
                    "prioridad": prioridad,
                    "fecha_limite": fecha_limite,
                }
                firebase_adapter.update_doc("tasks", self.task.id, update_data)
            else:
                # Crear nueva tarea
                self.tasks_manager.create_task(
                    entity=self.entity or "",
                    entity_id=self.entity_id or "",
                    titulo=titulo,
                    descripcion=descripcion,
                    responsable_nombre=responsable,
                    fecha_limite=fecha_limite,
                    prioridad=prioridad
                )
            
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo guardar la tarea: {e}")
