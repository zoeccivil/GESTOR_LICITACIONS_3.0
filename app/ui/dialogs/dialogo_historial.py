"""
Diálogo para visualizar el historial de auditoría de una entidad.
"""
from __future__ import annotations
from typing import Optional, List, Dict, Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit,
    QGroupBox, QComboBox
)

from app.core.audit_logger import AuditLogger


class DialogoHistorial(QDialog):
    """Diálogo para ver el historial de cambios (auditoría)."""
    
    COL_FECHA = 0
    COL_ACCION = 1
    COL_USUARIO = 2
    COL_RESUMEN = 3
    
    def __init__(self, parent, entity: str, entity_id: str):
        super().__init__(parent)
        self.entity = entity
        self.entity_id = entity_id
        self.audit_logger = AuditLogger()
        
        self.setWindowTitle(f"Historial de Cambios - {entity} #{entity_id}")
        self.resize(900, 600)
        self.setModal(True)
        
        self._build_ui()
        self._load_history()
    
    def _build_ui(self):
        """Construye la interfaz del diálogo."""
        root = QVBoxLayout(self)
        
        # Filtros
        filter_group = QGroupBox("Filtros")
        filter_layout = QHBoxLayout(filter_group)
        
        filter_layout.addWidget(QLabel("Usuario:"))
        self.combo_usuario = QComboBox()
        self.combo_usuario.addItem("Todos", None)
        filter_layout.addWidget(self.combo_usuario)
        
        filter_layout.addWidget(QLabel("Acción:"))
        self.combo_accion = QComboBox()
        self.combo_accion.addItem("Todas", None)
        self.combo_accion.addItem("Crear", "create")
        self.combo_accion.addItem("Actualizar", "update")
        self.combo_accion.addItem("Eliminar", "delete")
        filter_layout.addWidget(self.combo_accion)
        
        btn_filtrar = QPushButton("Aplicar Filtros")
        btn_filtrar.clicked.connect(self._load_history)
        filter_layout.addWidget(btn_filtrar)
        
        filter_layout.addStretch(1)
        root.addWidget(filter_group)
        
        # Tabla de historial
        self.tbl = QTableWidget(0, 4)
        self.tbl.setHorizontalHeaderLabels([
            "Fecha/Hora", "Acción", "Usuario", "Resumen"
        ])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        
        # Configurar anchos de columna
        header = self.tbl.horizontalHeader()
        header.setSectionResizeMode(self.COL_FECHA, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_ACCION, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_USUARIO, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_RESUMEN, QHeaderView.ResizeMode.Stretch)
        
        self.tbl.itemSelectionChanged.connect(self._show_details)
        root.addWidget(self.tbl, 2)
        
        # Panel de detalles
        details_group = QGroupBox("Detalles del Cambio")
        details_layout = QVBoxLayout(details_group)
        
        self.txt_details = QTextEdit()
        self.txt_details.setReadOnly(True)
        self.txt_details.setMaximumHeight(150)
        details_layout.addWidget(self.txt_details)
        
        root.addWidget(details_group, 1)
        
        # Botones
        actions = QHBoxLayout()
        actions.addStretch(1)
        
        btn_refresh = QPushButton("🔄 Actualizar")
        btn_refresh.clicked.connect(self._load_history)
        actions.addWidget(btn_refresh)
        
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.accept)
        actions.addWidget(btn_close)
        
        root.addLayout(actions)
    
    def _load_history(self):
        """Carga el historial de auditoría."""
        # Obtener filtros
        usuario = self.combo_usuario.currentData()
        accion = self.combo_accion.currentData()
        
        # Cargar datos
        history = self.audit_logger.get_entity_history(self.entity, self.entity_id)
        
        # Aplicar filtros adicionales
        if usuario:
            history = [h for h in history if h.get("user_id") == usuario]
        if accion:
            history = [h for h in history if h.get("action") == accion]
        
        # Poblar combo de usuarios (si no se ha hecho)
        if self.combo_usuario.count() == 1:  # Solo tiene "Todos"
            all_history = self.audit_logger.get_entity_history(self.entity, self.entity_id)
            usuarios = set(h.get("user_id", "system") for h in all_history)
            for user in sorted(usuarios):
                self.combo_usuario.addItem(user, user)
        
        # Almacenar para detalles
        self._history_data = history
        
        # Poblar tabla
        self.tbl.setRowCount(0)
        for entry in history:
            row = self.tbl.rowCount()
            self.tbl.insertRow(row)
            
            # Formatear fecha
            timestamp = entry.get("timestamp", "")
            if "T" in timestamp:
                fecha_str = timestamp.split("T")[0]
                hora_str = timestamp.split("T")[1][:8]
                fecha_display = f"{fecha_str} {hora_str}"
            else:
                fecha_display = timestamp
            
            # Acción con emoji
            action = entry.get("action", "")
            action_display = {
                "create": "✨ Crear",
                "update": "✏️ Actualizar",
                "delete": "🗑️ Eliminar",
            }.get(action, action)
            
            self.tbl.setItem(row, self.COL_FECHA, QTableWidgetItem(fecha_display))
            self.tbl.setItem(row, self.COL_ACCION, QTableWidgetItem(action_display))
            self.tbl.setItem(row, self.COL_USUARIO, QTableWidgetItem(entry.get("user_id", "system")))
            self.tbl.setItem(row, self.COL_RESUMEN, QTableWidgetItem(entry.get("changes_summary", "")))
        
        # Actualizar contador
        total = len(history)
        self.setWindowTitle(f"Historial de Cambios - {self.entity} #{self.entity_id} ({total} registros)")
    
    def _show_details(self):
        """Muestra los detalles del cambio seleccionado."""
        row = self.tbl.currentRow()
        if row < 0 or row >= len(self._history_data):
            self.txt_details.clear()
            return
        
        entry = self._history_data[row]
        
        # Generar texto de detalles
        details = []
        details.append(f"Acción: {entry.get('action', 'N/A')}")
        details.append(f"Usuario: {entry.get('user_id', 'system')}")
        details.append(f"Fecha: {entry.get('timestamp', 'N/A')}")
        details.append(f"Resumen: {entry.get('changes_summary', '')}")
        details.append("")
        details.append("Cambios realizados:")
        
        # Mostrar diferencias
        changes = self.audit_logger.get_changes_diff(entry)
        if changes:
            for change in changes:
                details.append(f"  {change}")
        else:
            details.append("  (Sin detalles de cambios)")
        
        self.txt_details.setPlainText("\n".join(details))


class DialogoHistorialCompleto(QDialog):
    """Diálogo para ver todo el historial de auditoría (sin filtrar por entidad)."""
    
    COL_FECHA = 0
    COL_ENTIDAD = 1
    COL_ID = 2
    COL_ACCION = 3
    COL_USUARIO = 4
    COL_RESUMEN = 5
    
    def __init__(self, parent):
        super().__init__(parent)
        self.audit_logger = AuditLogger()
        
        self.setWindowTitle("Historial Completo de Auditoría")
        self.resize(1100, 700)
        self.setModal(True)
        
        self._build_ui()
        self._load_history()
    
    def _build_ui(self):
        """Construye la interfaz del diálogo."""
        root = QVBoxLayout(self)
        
        # Filtros
        filter_group = QGroupBox("Filtros")
        filter_layout = QHBoxLayout(filter_group)
        
        filter_layout.addWidget(QLabel("Entidad:"))
        self.combo_entidad = QComboBox()
        self.combo_entidad.addItem("Todas", None)
        filter_layout.addWidget(self.combo_entidad)
        
        filter_layout.addWidget(QLabel("Usuario:"))
        self.combo_usuario = QComboBox()
        self.combo_usuario.addItem("Todos", None)
        filter_layout.addWidget(self.combo_usuario)
        
        filter_layout.addWidget(QLabel("Acción:"))
        self.combo_accion = QComboBox()
        self.combo_accion.addItem("Todas", None)
        self.combo_accion.addItem("Crear", "create")
        self.combo_accion.addItem("Actualizar", "update")
        self.combo_accion.addItem("Eliminar", "delete")
        filter_layout.addWidget(self.combo_accion)
        
        btn_filtrar = QPushButton("Aplicar Filtros")
        btn_filtrar.clicked.connect(self._load_history)
        filter_layout.addWidget(btn_filtrar)
        
        filter_layout.addStretch(1)
        root.addWidget(filter_group)
        
        # Tabla de historial
        self.tbl = QTableWidget(0, 6)
        self.tbl.setHorizontalHeaderLabels([
            "Fecha/Hora", "Entidad", "ID", "Acción", "Usuario", "Resumen"
        ])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        
        # Configurar anchos de columna
        header = self.tbl.horizontalHeader()
        header.setSectionResizeMode(self.COL_FECHA, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_ENTIDAD, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_ID, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_ACCION, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_USUARIO, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_RESUMEN, QHeaderView.ResizeMode.Stretch)
        
        root.addWidget(self.tbl, 1)
        
        # Botones
        actions = QHBoxLayout()
        actions.addStretch(1)
        
        btn_refresh = QPushButton("🔄 Actualizar")
        btn_refresh.clicked.connect(self._load_history)
        actions.addWidget(btn_refresh)
        
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.accept)
        actions.addWidget(btn_close)
        
        root.addLayout(actions)
    
    def _load_history(self):
        """Carga el historial completo de auditoría."""
        # Obtener filtros
        entidad = self.combo_entidad.currentData()
        usuario = self.combo_usuario.currentData()
        accion = self.combo_accion.currentData()
        
        # Cargar datos
        history = self.audit_logger.get_history(
            entity=entidad,
            user_id=usuario,
            limit=500
        )
        
        # Aplicar filtro de acción
        if accion:
            history = [h for h in history if h.get("action") == accion]
        
        # Poblar combos (si no se ha hecho)
        if self.combo_entidad.count() == 1:  # Solo tiene "Todas"
            all_history = self.audit_logger.get_history(limit=1000)
            entidades = set(h.get("entity", "") for h in all_history)
            for ent in sorted(entidades):
                if ent:
                    self.combo_entidad.addItem(ent, ent)
            
            usuarios = set(h.get("user_id", "system") for h in all_history)
            for user in sorted(usuarios):
                self.combo_usuario.addItem(user, user)
        
        # Poblar tabla
        self.tbl.setRowCount(0)
        for entry in history:
            row = self.tbl.rowCount()
            self.tbl.insertRow(row)
            
            # Formatear fecha
            timestamp = entry.get("timestamp", "")
            if "T" in timestamp:
                fecha_str = timestamp.split("T")[0]
                hora_str = timestamp.split("T")[1][:8]
                fecha_display = f"{fecha_str} {hora_str}"
            else:
                fecha_display = timestamp
            
            # Acción con emoji
            action = entry.get("action", "")
            action_display = {
                "create": "✨ Crear",
                "update": "✏️ Actualizar",
                "delete": "🗑️ Eliminar",
            }.get(action, action)
            
            self.tbl.setItem(row, self.COL_FECHA, QTableWidgetItem(fecha_display))
            self.tbl.setItem(row, self.COL_ENTIDAD, QTableWidgetItem(entry.get("entity", "")))
            self.tbl.setItem(row, self.COL_ID, QTableWidgetItem(str(entry.get("entity_id", ""))))
            self.tbl.setItem(row, self.COL_ACCION, QTableWidgetItem(action_display))
            self.tbl.setItem(row, self.COL_USUARIO, QTableWidgetItem(entry.get("user_id", "system")))
            self.tbl.setItem(row, self.COL_RESUMEN, QTableWidgetItem(entry.get("changes_summary", "")))
        
        # Actualizar contador
        total = len(history)
        self.setWindowTitle(f"Historial Completo de Auditoría ({total} registros)")
