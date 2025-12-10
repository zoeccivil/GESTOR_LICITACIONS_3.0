# app/ui/dialogs/dialogo_gestion_subsanacion.py
from __future__ import annotations
import datetime
from typing import List, Optional, Callable, TYPE_CHECKING

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QDialogButtonBox, QLineEdit,
    QLabel, QComboBox, QWidget, QDateEdit, QGroupBox, QMessageBox
)
from PyQt6.QtCore import Qt, QDate, QModelIndex

from app.core.models import Licitacion, Documento

if TYPE_CHECKING:
    from app.core.db_adapter import DatabaseAdapter

class DialogoGestionSubsanacion(QDialog):
    """
    Diálogo para iniciar o modificar el proceso de subsanación.
    Permite definir una fecha límite y marcar qué documentos requieren subsanación.
    """
    COL_CHECK = 0
    COL_CODIGO = 1
    COL_NOMBRE = 2

    def __init__(self, parent: QWidget,
                    licitacion: Licitacion,
                    # --- CORRECCIÓN DE TIPO ---
                    db_adapter: DatabaseAdapter, # Espera el Adapter
                    # --- FIN CORRECCIÓN ---
                    callback_guardar_en_memoria: Callable,
                    documentos_editables: List[Documento]):
            super().__init__(parent)
            
            self.licitacion = licitacion
            # --- CORRECCIÓN DE ASIGNACIÓN ---
            self.db: DatabaseAdapter = db_adapter # Asigna el Adapter a self.db
            # --- FIN CORRECCIÓN ---
            self.callback_guardar_en_memoria = callback_guardar_en_memoria
            self.documentos_editables = documentos_editables
            
            # El resto del __init__ es igual...
            self.docs_candidatos = [d for d in self.documentos_editables if d.id is not None and d.id > 0]
            self.search_var = ""
            self.categoria_var = "Todas"
            categorias_unicas = sorted(list(set(doc.categoria for doc in self.docs_candidatos if doc.categoria)))
            self.categorias_filtro = ["Todas"] + categorias_unicas

            self.setWindowTitle("Gestionar Proceso de Subsanación")
            self.setMinimumSize(800, 550)
            self._build_ui()
            self._filtrar_y_poblar_tableview()
    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Panel Fecha Límite ---
        fecha_group = QGroupBox("Estado del Proceso de Subsanación")
        fecha_layout = QHBoxLayout(fecha_group)
        fecha_layout.addWidget(QLabel("<b>Fecha Límite para Entrega:</b>"))
        
        self.fecha_entry = QDateEdit()
        self.fecha_entry.setCalendarPopup(True)
        self.fecha_entry.setDisplayFormat("yyyy-MM-dd")
        
        # Cargar fecha y estado actual del cronograma
        datos_evento = self.licitacion.cronograma.get("Entrega de Subsanaciones", {})
        fecha_limite_str = datos_evento.get("fecha_limite")
        if fecha_limite_str:
            self.fecha_entry.setDate(QDate.fromString(fecha_limite_str, "yyyy-MM-dd"))
        else:
            self.fecha_entry.setDate(QDate.currentDate()) # Sugerir hoy
            self.fecha_entry.setSpecialValueText("No definida") # Mostrar si está vacío
        
        estado_actual = datos_evento.get("estado", "No iniciado")
        
        fecha_layout.addWidget(self.fecha_entry)
        fecha_layout.addWidget(QLabel(f"|  <b>Estado Actual:</b> {estado_actual}"))
        fecha_layout.addStretch(1)
        main_layout.addWidget(fecha_group)

        # --- Panel de Filtros ---
        filtros_frame = QWidget()
        filtros_layout = QHBoxLayout(filtros_frame)
        filtros_layout.setContentsMargins(0, 5, 0, 5)
        
        filtros_layout.addWidget(QLabel("Buscar:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Buscar por código o nombre...")
        self.search_edit.textChanged.connect(self._filtrar_y_poblar_tableview)
        filtros_layout.addWidget(self.search_edit)

        filtros_layout.addWidget(QLabel("Categoría:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems(self.categorias_filtro)
        self.category_combo.currentTextChanged.connect(self._filtrar_y_poblar_tableview)
        filtros_layout.addWidget(self.category_combo)
        main_layout.addWidget(filtros_frame)

        # --- Tabla de Documentos ---
        table_group = QGroupBox("Marque los documentos que se deben subsanar")
        table_layout = QVBoxLayout(table_group)
        
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Req.", "Código", "Nombre del Documento"])
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setSortingEnabled(False) # Filtrado maneja el orden

        header = self.table.horizontalHeader()
        header.resizeSection(self.COL_CHECK, 40)
        header.setSectionResizeMode(self.COL_CHECK, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(self.COL_CODIGO, 150)
        header.setSectionResizeMode(self.COL_NOMBRE, QHeaderView.ResizeMode.Stretch)

        self.table.clicked.connect(self._toggle_checkbox)
        table_layout.addWidget(self.table)
        main_layout.addWidget(table_group)

        # --- Botones OK/Cancel ---
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.button(QDialogButtonBox.StandardButton.Save).setText("Guardar Cambios")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

    def _filtrar_y_poblar_tableview(self):
        """Filtra los documentos candidatos y actualiza la tabla."""
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        
        search_term = self.search_edit.text().strip().lower()
        categoria_sel = self.category_combo.currentText()

        for doc in self.docs_candidatos: # Iterar solo sobre los que tienen ID
            # 1. Filtro Categoría
            if categoria_sel != "Todas" and (doc.categoria or "") != categoria_sel:
                continue
            # 2. Filtro Búsqueda
            if search_term and search_term not in (doc.nombre or "").lower() and \
               search_term not in (doc.codigo or "").lower():
                continue
            
            # Si pasa filtros, añadir fila
            row = self.table.rowCount()
            self.table.insertRow(row)

            # Checkbox item (Col 0)
            item_check = QTableWidgetItem()
            item_check.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            # Marcar según el estado actual en la lista editable
            check_state = Qt.CheckState.Checked if getattr(doc, 'requiere_subsanacion', False) else Qt.CheckState.Unchecked
            item_check.setCheckState(check_state)
            item_check.setData(Qt.ItemDataRole.UserRole, doc) # Guardar objeto aquí
            
            # Data items
            item_codigo = QTableWidgetItem(doc.codigo or "")
            item_nombre = QTableWidgetItem(doc.nombre or "")

            self.table.setItem(row, self.COL_CHECK, item_check)
            self.table.setItem(row, self.COL_CODIGO, item_codigo)
            self.table.setItem(row, self.COL_NOMBRE, item_nombre)

        self.table.blockSignals(False)

    def _toggle_checkbox(self, index: QModelIndex):
        """Maneja el clic en cualquier celda para cambiar el checkbox de esa fila."""
        if not index.isValid(): return
        
        item_check = self.table.item(index.row(), self.COL_CHECK)
        if not item_check: return
        
        doc = item_check.data(Qt.ItemDataRole.UserRole)
        if not isinstance(doc, Documento): return

        # Invertir el estado
        current_state = item_check.checkState()
        new_state = Qt.CheckState.Unchecked
        if current_state == Qt.CheckState.Unchecked:
            new_state = Qt.CheckState.Checked
            
        item_check.setCheckState(new_state)
        # --- IMPORTANTE: Modificar el objeto en la lista editable ---
        doc.requiere_subsanacion = (new_state == Qt.CheckState.Checked)

    def accept(self):
            """Muestra confirmación y aplica los cambios."""
            # ... (código para obtener fecha_limite y docs_marcados es igual) ...
            fecha_limite_qdate = self.fecha_entry.date()
            fecha_limite = fecha_limite_qdate.toString("yyyy-MM-dd") if not fecha_limite_qdate.isNull() else None
            docs_marcados = [d for d in self.documentos_editables if getattr(d, 'requiere_subsanacion', False) and d.id]
            ids_docs_marcados = {d.id for d in docs_marcados}

            if not fecha_limite and docs_marcados:
                QMessageBox.warning(self, "Falta Fecha", "Ha marcado documentos pero no ha establecido una fecha límite.")
                return

            # ... (código para construir el mensaje 'msg' es igual) ...
            msg = "Por favor, confirme los cambios a guardar:\n\n"
            if fecha_limite:
                msg += f"FECHA LÍMITE: {fecha_limite}\n"
                msg += "ESTADO PROCESO: Pendiente\n\n"
            else:
                msg += "ACCIÓN: Limpiar proceso de subsanación (quitar fecha y desmarcar todos).\n\n"
            msg += f"DOCUMENTOS MARCADOS PARA SUBSANACIÓN ({len(docs_marcados)}):\n"
            if not docs_marcados: msg += "- Ninguno\n"
            else:
                for doc in docs_marcados[:10]: msg += f"- {doc.nombre}\n"
                if len(docs_marcados) > 10: msg += f"- ... y {len(docs_marcados) - 10} más."

            
            resp = QMessageBox.question(self, "Confirmar Subsanación", msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
            if resp == QMessageBox.StandardButton.Yes:
            # ... tu lógica ...
                try:
                    # 1. Actualizar el objeto licitacion en memoria (el original)
                    if "Entrega de Subsanaciones" not in self.licitacion.cronograma:
                        self.licitacion.cronograma["Entrega de Subsanaciones"] = {}
                    self.licitacion.cronograma["Entrega de Subsanaciones"]["fecha_limite"] = fecha_limite
                    self.licitacion.cronograma["Entrega de Subsanaciones"]["estado"] = "Pendiente" if fecha_limite else "No iniciado"

                    # 2. Registrar eventos en la BD (ahora usando self.db que es el ADAPTER)
                    eventos_para_registrar = []
                    for doc in docs_marcados:
                        # self.db ahora es el DatabaseAdapter
                        if not self.db.existe_evento_subsanacion_pendiente(self.licitacion.id, doc.id):
                            eventos_para_registrar.append((doc.id, fecha_limite, "Solicitud inicial de subsanación."))
                    
                    if eventos_para_registrar:
                        print(f"Registrando {len(eventos_para_registrar)} nuevos eventos de subsanación en BD...")
                        # self.db ahora es el DatabaseAdapter
                        self.db.registrar_eventos_subsanacion(self.licitacion.id, eventos_para_registrar)
                    
                    # 3. Llamar al callback para refrescar la UI padre (GestionDocumentosDialog)
                    print("Llamando al callback para guardar y refrescar...")
                    self.callback_guardar_en_memoria() 
                    
                    QMessageBox.information(self, "Guardado", "Proceso de subsanación actualizado.")
                    super().accept() # Cerrar diálogo
                    
                except Exception as e:
                    QMessageBox.critical(self, "Error al Guardar", f"No se pudieron guardar los cambios:\n{e}")
                    print(f"Error en DialogoGestionSubsanacion.accept: {e}")
            else:
                print("Guardado de subsanación cancelado por usuario.")