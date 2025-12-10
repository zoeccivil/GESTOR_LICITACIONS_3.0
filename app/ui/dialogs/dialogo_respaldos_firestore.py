"""
Diálogo para gestionar respaldos de Firebase Firestore.
"""
from __future__ import annotations
from typing import Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QGroupBox, QCheckBox, QSpinBox, QProgressDialog
)

from app.core.firestore_backup import FirestoreBackupManager


class BackupThread(QThread):
    """Thread para crear respaldos sin bloquear la UI."""
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, backup_manager, firestore_client):
        super().__init__()
        self.backup_manager = backup_manager
        self.firestore_client = firestore_client
    
    def run(self):
        try:
            backup_file = self.backup_manager.create_backup(self.firestore_client)
            self.finished.emit(backup_file)
        except Exception as e:
            self.error.emit(str(e))


class DialogoRespaldosFirestore(QDialog):
    """Diálogo para gestionar respaldos locales de Firestore."""
    
    COL_FECHA = 0
    COL_ARCHIVO = 1
    COL_TAMANO = 2
    
    def __init__(self, parent, firestore_client=None):
        super().__init__(parent)
        self.firestore_client = firestore_client
        self.backup_manager = FirestoreBackupManager()
        
        self.setWindowTitle("Respaldos Locales de Firebase Firestore")
        self.resize(800, 600)
        self.setModal(True)
        
        self._build_ui()
        self._load_backups()
        self._load_stats()
    
    def _build_ui(self):
        """Construye la interfaz del diálogo."""
        root = QVBoxLayout(self)
        
        # Información superior
        info_group = QGroupBox("Información")
        info_layout = QVBoxLayout(info_group)
        
        self.lbl_info = QLabel(
            "Los respaldos locales permiten trabajar sin conexión y recuperar datos.\n"
            "Se recomienda crear respaldos diarios automáticos."
        )
        self.lbl_info.setWordWrap(True)
        info_layout.addWidget(self.lbl_info)
        
        # Estadísticas
        stats_layout = QHBoxLayout()
        self.lbl_stats = QLabel("Cargando estadísticas...")
        stats_layout.addWidget(self.lbl_stats)
        stats_layout.addStretch(1)
        info_layout.addLayout(stats_layout)
        
        root.addWidget(info_group)
        
        # Configuración de respaldo automático
        auto_group = QGroupBox("Respaldo Automático")
        auto_layout = QHBoxLayout(auto_group)
        
        self.chk_auto_backup = QCheckBox("Activar respaldo automático diario")
        self.chk_auto_backup.setChecked(self.backup_manager.auto_backup_enabled)
        self.chk_auto_backup.stateChanged.connect(self._toggle_auto_backup)
        auto_layout.addWidget(self.chk_auto_backup)
        
        auto_layout.addWidget(QLabel("Intervalo (horas):"))
        self.spin_interval = QSpinBox()
        self.spin_interval.setMinimum(1)
        self.spin_interval.setMaximum(168)  # 1 semana
        self.spin_interval.setValue(24)  # Diario por defecto
        auto_layout.addWidget(self.spin_interval)
        
        auto_layout.addStretch(1)
        
        root.addWidget(auto_group)
        
        # Lista de respaldos
        backups_group = QGroupBox("Respaldos Disponibles")
        backups_layout = QVBoxLayout(backups_group)
        
        self.tbl_backups = QTableWidget(0, 3)
        self.tbl_backups.setHorizontalHeaderLabels([
            "Fecha y Hora", "Archivo", "Tamaño (MB)"
        ])
        self.tbl_backups.verticalHeader().setVisible(False)
        self.tbl_backups.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_backups.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_backups.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        
        # Configurar anchos de columna
        header = self.tbl_backups.horizontalHeader()
        header.setSectionResizeMode(self.COL_FECHA, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_ARCHIVO, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(self.COL_TAMANO, QHeaderView.ResizeMode.ResizeToContents)
        
        self.tbl_backups.itemSelectionChanged.connect(self._update_actions)
        backups_layout.addWidget(self.tbl_backups)
        
        root.addWidget(backups_group, 1)
        
        # Botones de acción
        actions = QHBoxLayout()
        
        self.btn_create_backup = QPushButton("💾 Crear Respaldo Ahora")
        self.btn_create_backup.clicked.connect(self._create_backup)
        actions.addWidget(self.btn_create_backup)
        
        self.btn_restore = QPushButton("⚙️ Restaurar desde Respaldo")
        self.btn_restore.clicked.connect(self._restore_backup)
        self.btn_restore.setEnabled(False)
        actions.addWidget(self.btn_restore)
        
        self.btn_delete = QPushButton("🗑️ Eliminar Respaldo")
        self.btn_delete.clicked.connect(self._delete_backup)
        self.btn_delete.setEnabled(False)
        actions.addWidget(self.btn_delete)
        
        actions.addStretch(1)
        
        btn_refresh = QPushButton("🔄 Actualizar")
        btn_refresh.clicked.connect(self._refresh)
        actions.addWidget(btn_refresh)
        
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.accept)
        actions.addWidget(btn_close)
        
        root.addLayout(actions)
        
        self._update_actions()
    
    def _load_backups(self):
        """Carga la lista de respaldos."""
        self.tbl_backups.setRowCount(0)
        
        backups = self.backup_manager.list_backups()
        
        for backup in backups:
            row = self.tbl_backups.rowCount()
            self.tbl_backups.insertRow(row)
            
            self.tbl_backups.setItem(row, self.COL_FECHA, QTableWidgetItem(backup["created_str"]))
            self.tbl_backups.setItem(row, self.COL_ARCHIVO, QTableWidgetItem(backup["filename"]))
            self.tbl_backups.setItem(row, self.COL_TAMANO, QTableWidgetItem(f"{backup['size_mb']:.2f}"))
        
        if not backups:
            self.lbl_info.setText(
                "No hay respaldos disponibles. Crea el primer respaldo haciendo clic en 'Crear Respaldo Ahora'."
            )
    
    def _load_stats(self):
        """Carga las estadísticas de respaldos."""
        stats = self.backup_manager.get_backup_stats()
        
        if stats["total_backups"] > 0:
            stats_text = (
                f"📊 Estadísticas: {stats['total_backups']} respaldos | "
                f"Tamaño total: {stats['total_size_mb']} MB | "
                f"Más reciente: {stats['newest_backup']}"
            )
        else:
            stats_text = "📊 No hay respaldos disponibles"
        
        self.lbl_stats.setText(stats_text)
    
    def _update_actions(self):
        """Actualiza el estado de los botones."""
        has_selection = self.tbl_backups.currentRow() >= 0
        self.btn_restore.setEnabled(has_selection and self.firestore_client is not None)
        self.btn_delete.setEnabled(has_selection)
        
        # Deshabilitar crear respaldo si no hay cliente Firestore
        self.btn_create_backup.setEnabled(self.firestore_client is not None)
    
    def _create_backup(self):
        """Crea un nuevo respaldo."""
        if not self.firestore_client:
            QMessageBox.warning(
                self, "Error",
                "No hay conexión a Firestore. No se puede crear respaldo."
            )
            return
        
        respuesta = QMessageBox.question(
            self, "Crear Respaldo",
            "¿Crear un respaldo completo de la base de datos?\n\n"
            "Esto puede tardar varios minutos dependiendo del tamaño de los datos.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if respuesta != QMessageBox.StandardButton.Yes:
            return
        
        # Mostrar diálogo de progreso
        progress = QProgressDialog("Creando respaldo...", None, 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
        
        # Crear respaldo en thread separado
        self.backup_thread = BackupThread(self.backup_manager, self.firestore_client)
        self.backup_thread.finished.connect(lambda f: self._on_backup_created(f, progress))
        self.backup_thread.error.connect(lambda e: self._on_backup_error(e, progress))
        self.backup_thread.start()
    
    def _on_backup_created(self, backup_file: str, progress: QProgressDialog):
        """Callback cuando se crea el respaldo."""
        progress.close()
        
        QMessageBox.information(
            self, "Éxito",
            f"Respaldo creado exitosamente:\n{backup_file}"
        )
        
        self._refresh()
    
    def _on_backup_error(self, error: str, progress: QProgressDialog):
        """Callback cuando hay error al crear respaldo."""
        progress.close()
        
        QMessageBox.critical(
            self, "Error",
            f"No se pudo crear el respaldo:\n{error}"
        )
    
    def _restore_backup(self):
        """Restaura desde un respaldo seleccionado."""
        row = self.tbl_backups.currentRow()
        if row < 0:
            return
        
        backups = self.backup_manager.list_backups()
        if row >= len(backups):
            return
        
        backup = backups[row]
        
        respuesta = QMessageBox.warning(
            self, "Restaurar Respaldo",
            f"¿Restaurar respaldo del {backup['created_str']}?\n\n"
            "ADVERTENCIA: Esto mezclará los datos del respaldo con los datos actuales en Firestore.\n"
            "Los datos existentes no se eliminarán, pero se actualizarán con los valores del respaldo.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if respuesta != QMessageBox.StandardButton.Yes:
            return
        
        try:
            progress = QProgressDialog("Restaurando respaldo...", None, 0, 0, self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.show()
            
            stats = self.backup_manager.restore_from_backup(
                self.firestore_client,
                backup["path"],
                merge=True
            )
            
            progress.close()
            
            QMessageBox.information(
                self, "Éxito",
                f"Restauración completada:\n\n"
                f"Colecciones: {stats['collections_restored']}\n"
                f"Documentos: {stats['documents_restored']}\n"
                f"Errores: {stats['errors']}"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self, "Error",
                f"No se pudo restaurar el respaldo:\n{e}"
            )
    
    def _delete_backup(self):
        """Elimina el respaldo seleccionado."""
        row = self.tbl_backups.currentRow()
        if row < 0:
            return
        
        backups = self.backup_manager.list_backups()
        if row >= len(backups):
            return
        
        backup = backups[row]
        
        respuesta = QMessageBox.question(
            self, "Eliminar Respaldo",
            f"¿Eliminar el respaldo del {backup['created_str']}?\n\n"
            f"Archivo: {backup['filename']}\n"
            f"Tamaño: {backup['size_mb']:.2f} MB",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if respuesta == QMessageBox.StandardButton.Yes:
            try:
                import os
                os.remove(backup["path"])
                QMessageBox.information(self, "Éxito", "Respaldo eliminado")
                self._refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo eliminar: {e}")
    
    def _toggle_auto_backup(self, state):
        """Activa o desactiva el respaldo automático."""
        if state == Qt.CheckState.Checked.value:
            if not self.firestore_client:
                QMessageBox.warning(
                    self, "Error",
                    "No hay conexión a Firestore. No se puede activar respaldo automático."
                )
                self.chk_auto_backup.setChecked(False)
                return
            
            interval = self.spin_interval.value()
            self.backup_manager.start_auto_backup(self.firestore_client, interval)
            QMessageBox.information(
                self, "Respaldo Automático",
                f"Respaldo automático activado.\n"
                f"Se creará un respaldo cada {interval} horas."
            )
        else:
            self.backup_manager.stop_auto_backup()
    
    def _refresh(self):
        """Actualiza la vista."""
        self._load_backups()
        self._load_stats()
        self._update_actions()
