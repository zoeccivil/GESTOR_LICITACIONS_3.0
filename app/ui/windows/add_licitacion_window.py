# app/ui/windows/add_licitacion_window.py
from __future__ import annotations
from typing import Optional, Dict, Any

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QLineEdit, QComboBox,
    QPushButton, QListWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QStyle, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# Diálogos
from app.ui.dialogs.gestionar_entidad_dialog import DialogoGestionarEntidad
from app.ui.dialogs.gestionar_lote_dialog import GestionarLoteDialog
from app.ui.dialogs.seleccionar_empresas_dialog import SeleccionarEmpresasDialog
from app.ui.dialogs.dialogo_gestionar_instituciones import DialogoGestionarInstituciones
from app.ui.dialogs.seleccionar_institucion_dialog import SeleccionarInstitucionDialog

# Modelos
from app.core.models import Documento, Licitacion, Lote

class AddLicitacionWindow(QDialog):
    def __init__(self, parent, db, callback_guardar):
        super().__init__(parent)
        self.parent = parent
        self.db = db
        try:
            self.lista_empresas = self.db.get_empresas_maestras()
            # ya no necesitamos cargar instituciones aquí de forma directa; el selector las pedirá al abrirlo
            self.lista_instituciones = list(self.db.get_instituciones_maestras() or [])
        except Exception as e:
             QMessageBox.critical(self, "Error", f"No se pudieron cargar los catálogos: {e}")
             self.lista_empresas = []
             self.lista_instituciones = []

        self.callback_guardar = callback_guardar
        self.institucion_seleccionada: Optional[Dict[str, Any]] = None
        self.empresas_seleccionadas = []
        self.lotes_temp = []
        self.kits_disponibles = []

        self.setWindowTitle("Agregar Nueva Licitación")
        self.setMinimumSize(950, 700)

        # Layout principal
        main_layout = QVBoxLayout(self)
        top_layout = QHBoxLayout()
        main_layout.addLayout(top_layout)

        # --- Panel A: Institución ---
        panelA = QGroupBox("A. Seleccione la Institución")
        vA = QVBoxLayout(panelA)

        fila_inst = QHBoxLayout()

        # Campo read-only que muestra la institución seleccionada (nombre)
        self.institucion_display = QLineEdit()
        self.institucion_display.setReadOnly(True)
        self.institucion_display.setPlaceholderText("Ninguna institución seleccionada")
        self.institucion_display.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        fila_inst.addWidget(self.institucion_display, stretch=1)

        # Botón para abrir el diálogo de selección
        btn_select_inst = QPushButton("Seleccionar Institución...")
        btn_select_inst.setFixedWidth(180)
        btn_select_inst.clicked.connect(self._abrir_selector_institucion)
        fila_inst.addWidget(btn_select_inst)

        # Botón para gestionar catálogo completo (alternativa)
        btn_manage_inst = QPushButton("Gestionar Instituciones…")
        btn_manage_inst.setFixedWidth(180)
        btn_manage_inst.clicked.connect(self._abrir_gestor_instituciones)
        fila_inst.addWidget(btn_manage_inst)

        vA.addLayout(fila_inst)
        top_layout.addWidget(panelA, stretch=1)

        # --- Panel B: Empresas Nuestras ---
        panelB = QGroupBox("B. Seleccione su(s) Empresa(s)")
        vB = QVBoxLayout(panelB)
        self.lbl_empresas_sel = QLabel("Ninguna seleccionada")
        self.lbl_empresas_sel.setStyleSheet("color: red;")
        self.lbl_empresas_sel.setWordWrap(True)
        vB.addWidget(self.lbl_empresas_sel)
        btn_seleccionar_emp = QPushButton("Seleccionar Empresas...")
        btn_seleccionar_emp.clicked.connect(self._abrir_selector_empresas)
        vB.addWidget(btn_seleccionar_emp)
        top_layout.addWidget(panelB, stretch=2)

        # --- Panel C: Detalles Licitación ---
        panelC = QGroupBox("C. Complete los Detalles")
        gridC = QVBoxLayout(panelC)
        self.txt_nombre_lic = QLineEdit()
        self.txt_codigo_lic = QLineEdit()
        self.combo_kit = QComboBox()
        self.combo_kit.addItem(" (Ninguno) ")
        self.combo_kit.setEnabled(False)

        gridC.addWidget(QLabel("Nombre de la Licitación:"))
        gridC.addWidget(self.txt_nombre_lic)
        gridC.addWidget(QLabel("Código del Proceso:"))
        gridC.addWidget(self.txt_codigo_lic)
        gridC.addWidget(QLabel("Aplicar Kit de Requisitos:"))
        gridC.addWidget(self.combo_kit)
        top_layout.addWidget(panelC, stretch=3)

        # --- Panel D: Lotes ---
        panelD = QGroupBox("D. Lotes del Proceso")
        vD = QVBoxLayout(panelD)
        self.tabla_lotes = QTableWidget(0, 5)
        self.tabla_lotes.setHorizontalHeaderLabels(["N°", "Nombre Lote", "Monto Base", "Nuestra Oferta", "Empresa Asignada"])
        self.tabla_lotes.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla_lotes.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_lotes.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        vD.addWidget(self.tabla_lotes)

        lotes_btns_layout = QHBoxLayout()
        btn_add_lote = QPushButton("Agregar Lote")
        btn_edit_lote = QPushButton("Editar Lote")
        btn_del_lote = QPushButton("Eliminar Lote")
        btn_add_lote.clicked.connect(self._agregar_lote)
        btn_edit_lote.clicked.connect(self._editar_lote)
        btn_del_lote.clicked.connect(self._eliminar_lote)
        lotes_btns_layout.addWidget(btn_add_lote)
        lotes_btns_layout.addWidget(btn_edit_lote)
        lotes_btns_layout.addWidget(btn_del_lote)
        lotes_btns_layout.addStretch(1)
        vD.addLayout(lotes_btns_layout)
        main_layout.addWidget(panelD)

        # Guardar
        btn_guardar = QPushButton("Guardar Licitación")
        btn_guardar.setStyleSheet("padding: 10px; font-weight: bold;")
        btn_guardar.clicked.connect(self._guardar_licitacion)
        main_layout.addWidget(btn_guardar, alignment=Qt.AlignmentFlag.AlignCenter)

        # (No hay combo: la lista se obtiene desde el selector al abrirlo)
        # mantengo lista local por si alguna función la necesita
        self.lista_instituciones = list(self.lista_instituciones or [])

    # --- Nuevos métodos para selector modal ---
    def _abrir_selector_institucion(self):
        dlg = SeleccionarInstitucionDialog(self, self.db)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            selected = dlg.get_selected()
            if selected:
                self._set_selected_institucion(selected)

    def _set_selected_institucion(self, inst: Dict[str, Any]):
        """Actualiza UI y estado interno con la institución seleccionada (dict completo)."""
        self.institucion_seleccionada = inst
        nombre = inst.get("nombre") or ""
        self.institucion_display.setText(nombre)
        # habilitar carga de kits si aplica
        self._cargar_kits_institucion()

    # --- Reutilizo el gestor completo (si el usuario quiere abrirlo directamente) ---
    def _abrir_gestor_instituciones(self):
        dlg = DialogoGestionarInstituciones(self, self.db)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            # recargar lista local
            try:
                self.lista_instituciones = list(self.db.get_instituciones_maestras() or [])
            except Exception:
                pass

    # --- Resto de métodos (empresas, lotes, guardado) iguales a antes ---
    def _abrir_selector_empresas(self):
        dlg = SeleccionarEmpresasDialog(self, self.lista_empresas, self.empresas_seleccionadas)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.empresas_seleccionadas = dlg.get_empresas_seleccionadas()
            self._actualizar_display_empresas()

    def _actualizar_display_empresas(self):
        if not self.empresas_seleccionadas:
            self.lbl_empresas_sel.setText("Ninguna seleccionada")
            self.lbl_empresas_sel.setStyleSheet("color: red;")
        else:
            texto = ", ".join(sorted(self.empresas_seleccionadas))
            self.lbl_empresas_sel.setText(texto)
            self.lbl_empresas_sel.setStyleSheet("color: black;")

    def _actualizar_tabla_lotes(self):
        self.tabla_lotes.setRowCount(0)
        for lote in self.lotes_temp:
            row = self.tabla_lotes.rowCount()
            self.tabla_lotes.insertRow(row)
            self.tabla_lotes.setItem(row, 0, QTableWidgetItem(str(lote.numero)))
            self.tabla_lotes.setItem(row, 1, QTableWidgetItem(lote.nombre))
            self.tabla_lotes.setItem(row, 2, QTableWidgetItem(f"{float(lote.monto_base or 0):,.2f}"))
            self.tabla_lotes.setItem(row, 3, QTableWidgetItem(f"{float(lote.monto_ofertado or 0):,.2f}"))
            empresa_asignada = lote.empresa_nuestra if lote.empresa_nuestra else ""
            self.tabla_lotes.setItem(row, 4, QTableWidgetItem(empresa_asignada))

    def _agregar_lote(self):
        dialog = GestionarLoteDialog(self, None, self.empresas_seleccionadas)
        if dialog.exec() == QDialog.DialogCode.Accepted and getattr(dialog, "resultado", None):
            data = dialog.resultado
            nuevo = Lote(
                numero=data.get("numero"),
                nombre=data.get("nombre"),
                monto_base=float(data.get("monto_base", 0) or 0),
                monto_base_personal=float(data.get("monto_base_personal", 0) or 0),
                monto_ofertado=float(data.get("monto_ofertado", 0) or 0),
                empresa_nuestra=data.get("empresa_nuestra") or None,
            )
            if any(str(l.numero) == str(nuevo.numero) for l in self.lotes_temp):
                QMessageBox.warning(self, "Lote Duplicado", f"Ya existe un lote con el número '{nuevo.numero}'.")
                return
            self.lotes_temp.append(nuevo)
            self._actualizar_tabla_lotes()

    def _editar_lote(self):
        selected_rows = self.tabla_lotes.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Sin Selección", "Selecciona un lote de la tabla para editar.")
            return
        row_index = selected_rows[0].row()
        lote_a_editar = self.lotes_temp[row_index]
        dialog = GestionarLoteDialog(self, lote_a_editar, self.empresas_seleccionadas)
        if dialog.exec() == QDialog.DialogCode.Accepted and getattr(dialog, "resultado", None):
            data = dialog.resultado
            editado = Lote(
                numero=data.get("numero"),
                nombre=data.get("nombre"),
                monto_base=float(data.get("monto_base", 0) or 0),
                monto_base_personal=float(data.get("monto_base_personal", 0) or 0),
                monto_ofertado=float(data.get("monto_ofertado", 0) or 0),
                empresa_nuestra=data.get("empresa_nuestra") or None,
            )
            if any((str(l.numero) == str(editado.numero) and l is not lote_a_editar) for l in self.lotes_temp):
                QMessageBox.warning(self, "Lote Duplicado", f"Ya existe otro lote con el número '{editado.numero}'.")
                return
            self.lotes_temp[row_index] = editado
            self._actualizar_tabla_lotes()

    def _eliminar_lote(self):
        selected_rows = self.tabla_lotes.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Sin Selección", "Selecciona un lote de la tabla para eliminar.")
            return
        row_index = selected_rows[0].row()
        nombre_lote = self.lotes_temp[row_index].nombre
        if QMessageBox.question(self, "Confirmar Eliminación", f"¿Eliminar el lote '{nombre_lote}'?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            del self.lotes_temp[row_index]
            self._actualizar_tabla_lotes()

    def _guardar_licitacion(self):
        if not self.institucion_seleccionada:
            QMessageBox.warning(self, "Campo Requerido", "Debe seleccionar una institución.")
            return
        if not self.empresas_seleccionadas:
            QMessageBox.warning(self, "Campo Requerido", "Debe seleccionar al menos una empresa participante.")
            return
        nombre_lic = self.txt_nombre_lic.text().strip()
        codigo_lic = self.txt_codigo_lic.text().strip()
        if not nombre_lic or not codigo_lic:
            QMessageBox.warning(self, "Campos Requeridos", "El Nombre y el Código de la licitación no pueden estar vacíos.")
            return
        if not self.lotes_temp:
            QMessageBox.warning(self, "Lotes Requeridos", "Debe agregar al menos un lote a la licitación.")
            return

        empresas_obj_o_nombres = self.empresas_seleccionadas

        try:
            nueva_licitacion = Licitacion(
                nombre_proceso=nombre_lic,
                numero_proceso=codigo_lic,
                institucion=self.institucion_seleccionada,
                empresas_nuestras=empresas_obj_o_nombres,
                lotes=self.lotes_temp,
                documentos_solicitados=[]
            )

            kit_seleccionado = self.combo_kit.currentText()
            if kit_seleccionado and kit_seleccionado.strip() != "(Ninguno)":
                print(f"Aplicando kit: {kit_seleccionado}")

            if self.callback_guardar:
                ok = self.callback_guardar(nueva_licitacion)
                if ok:
                    QMessageBox.information(self, "Éxito", "Licitación agregada correctamente.")
                    self.accept()
                else:
                    QMessageBox.critical(self, "Error", "No se pudo guardar la licitación (callback falló).")
            else:
                QMessageBox.warning(self, "Error", "No se definió una función para guardar.")

        except Exception as e:
            QMessageBox.critical(self, "Error al Crear Licitación", f"Ocurrió un error:\n{e}")