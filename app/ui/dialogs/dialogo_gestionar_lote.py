from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QGroupBox, QPushButton, QLabel, QLineEdit, QMessageBox, QHeaderView, QComboBox, QStyle
)
from PyQt6.QtCore import Qt
from typing import List, Optional
from app.core.models import Lote


class DialogoGestionarLotes(QDialog):
    """
    Diálogo para gestionar lotes (agregar, editar, eliminar) con aspecto profesional.
    (Esta clase permanece como la proporcionaste, pero no será llamada por TabLotes)
    """
    def __init__(self, parent, empresas_participantes=None, lotes_iniciales=None):
        super().__init__(parent)
        self.setWindowTitle("Gestionar Lotes del Proceso")
        self.setMinimumSize(900, 530)
        self.empresas_participantes = empresas_participantes or []
        self.lotes = [dict(lote) for lote in lotes_iniciales] if lotes_iniciales else []

        self.main_layout = QVBoxLayout(self)
        self._crear_panel_lotes()
        self._actualizar_tabla()

    def _crear_panel_lotes(self):
        group = QGroupBox("Listado de Lotes")
        vbox = QVBoxLayout(group)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["N°", "Nombre Lote", "Monto Base", "Nuestra Oferta", "Empresa Nuestra"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        vbox.addWidget(self.table)
        self.main_layout.addWidget(group)

        btns = QHBoxLayout()
        self.btn_agregar = QPushButton(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder), "Agregar Lote")
        self.btn_editar = QPushButton(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContents), "Editar Lote")
        self.btn_eliminar = QPushButton(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon), "Eliminar Lote")
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
        self.btn_agregar.clicked.connect(self._agregar_lote)
        self.btn_editar.clicked.connect(self._editar_lote)
        self.btn_eliminar.clicked.connect(self._eliminar_lote)
        btns.addWidget(self.btn_agregar)
        btns.addWidget(self.btn_editar)
        btns.addWidget(self.btn_eliminar)
        self.main_layout.addLayout(btns)

        self.lbl_status = QLabel()
        self.main_layout.addWidget(self.lbl_status)
        self._actualizar_status()

        btn_guardar = QPushButton(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton), "Guardar y Cerrar")
        btn_guardar.setMinimumWidth(180)
        btn_guardar.setFixedHeight(36)
        btn_guardar.setStyleSheet("""
            QPushButton { background-color: #1976D2; color: white; font-weight: bold; border-radius:6px; padding:10px; }
            QPushButton:hover { background-color: #64B5F6; }
            QPushButton:pressed { background-color: #1565C0; }
        """)
        btn_guardar.clicked.connect(self._guardar_y_cerrar)
        self.main_layout.addWidget(btn_guardar, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)

    def _actualizar_tabla(self):
        self.table.setRowCount(0)
        for lote in self.lotes:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(lote.get("numero", ""))))
            self.table.setItem(row, 1, QTableWidgetItem(str(lote.get("nombre", ""))))
            self.table.setItem(row, 2, QTableWidgetItem(f'RD$ {lote.get("monto_base", 0):,.2f}'))
            self.table.setItem(row, 3, QTableWidgetItem(f'RD$ {lote.get("monto_ofertado", 0):,.2f}'))
            self.table.setItem(row, 4, QTableWidgetItem(str(lote.get("empresa_nuestra", ""))))
        self._actualizar_status()

    def _actualizar_status(self):
        self.lbl_status.setText(f"Total: {len(self.lotes)} lotes")

    def _agregar_lote(self):
        dialog = DialogoLoteForm(self, None, self.empresas_participantes)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            nuevo = dialog.get_lote()
            self.lotes.append(nuevo)
            self._actualizar_tabla()
            QMessageBox.information(self, "Éxito", "Lote agregado correctamente.")

    def _editar_lote(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.lotes):
            QMessageBox.warning(self, "Sin Selección", "Selecciona un lote para editar.")
            return
        lote_actual = self.lotes[row]
        dialog = DialogoLoteForm(self, lote_actual, self.empresas_participantes)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.lotes[row] = dialog.get_lote()
            self._actualizar_tabla()
            QMessageBox.information(self, "Éxito", "Lote editado correctamente.")

    def _eliminar_lote(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.lotes):
            QMessageBox.warning(self, "Sin Selección", "Selecciona un lote para eliminar.")
            return
        nombre = self.lotes[row].get("nombre", "")
        if QMessageBox.question(self, "Confirmar", f"¿Eliminar el lote '{nombre}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self.lotes.pop(row)
            self._actualizar_tabla()
            QMessageBox.information(self, "Eliminado", f"El lote '{nombre}' fue eliminado.")

    def _guardar_y_cerrar(self):
        self.accept()

    def get_lotes(self):
        return self.lotes

# ---------------------------------------------------------------------------
# --- ESTE ES EL FORMULARIO QUE USAREMOS ---
# ---------------------------------------------------------------------------

class DialogoLoteForm(QDialog):
    """
    Formulario para agregar/editar un lote individual.
    Trabaja directamente con el objeto Lote.
    """
    def __init__(self, parent, lote_actual: Optional[Lote], empresas_participantes: List[str]):
        super().__init__(parent)
        self.setWindowTitle("Editar Lote" if lote_actual else "Agregar Nuevo Lote")
        self.setMinimumSize(400, 380)
        
        self.lote_actual = lote_actual
        self.result_lote: Optional[Lote] = None
        self.empresas_participantes = empresas_participantes or []

        vbox = QVBoxLayout(self)
        vbox.setSpacing(8)

        self.txt_numero = QLineEdit()
        self.txt_nombre = QLineEdit()
        self.txt_monto_base = QLineEdit()
        self.txt_monto_base_personal = QLineEdit()
        self.txt_monto_ofertado = QLineEdit()
        self.combo_empresa_nuestra = QComboBox()
        
        if "" not in self.empresas_participantes:
            self.empresas_participantes.insert(0, "")
        self.combo_empresa_nuestra.addItems([str(e) for e in self.empresas_participantes])

        if self.lote_actual:
            self.txt_numero.setText(str(self.lote_actual.numero or ""))
            self.txt_nombre.setText(self.lote_actual.nombre or "")
            self.txt_monto_base.setText(str(self.lote_actual.monto_base or ""))
            self.txt_monto_base_personal.setText(str(self.lote_actual.monto_base_personal or ""))
            self.txt_monto_ofertado.setText(str(self.lote_actual.monto_ofertado or ""))
            empresa = str(self.lote_actual.empresa_nuestra or "")
            idx = self.combo_empresa_nuestra.findText(empresa)
            if idx >= 0:
                self.combo_empresa_nuestra.setCurrentIndex(idx)

        vbox.addWidget(QLabel("N° Lote:"))
        vbox.addWidget(self.txt_numero)
        vbox.addWidget(QLabel("Nombre Lote:"))
        vbox.addWidget(self.txt_nombre)
        vbox.addWidget(QLabel("Monto Base (Licitación):"))
        vbox.addWidget(self.txt_monto_base)
        vbox.addWidget(QLabel("Monto Base Personal:"))
        vbox.addWidget(self.txt_monto_base_personal)
        vbox.addWidget(QLabel("Nuestra Oferta:"))
        vbox.addWidget(self.txt_monto_ofertado)
        vbox.addWidget(QLabel("Empresa Nuestra:"))
        vbox.addWidget(self.combo_empresa_nuestra)
        vbox.addStretch()

        style = self.style()
        btns = QHBoxLayout()
        btn_ok = QPushButton(style.standardIcon(QStyle.StandardPixmap.SP_DialogOkButton), " Guardar")
        btn_ok.clicked.connect(self._guardar)
        
        btn_cancel = QPushButton(style.standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton), " Cancelar")
        btn_cancel.clicked.connect(self.reject)
        
        btns.addStretch()
        btns.addWidget(btn_ok)
        btns.addWidget(btn_cancel)
        vbox.addLayout(btns)

    def _guardar(self):
        numero = self.txt_numero.text().strip()
        nombre = self.txt_nombre.text().strip()
        empresa_nuestra = self.combo_empresa_nuestra.currentText().strip()

        if not numero or not nombre:
            QMessageBox.warning(self, "Datos Requeridos", "Los campos 'N° Lote' y 'Nombre Lote' son obligatorios.")
            return

        def to_float(s: str) -> float:
            try:
                cleaned_s = s.replace(",", "").replace("RD$", "").replace("$", "").strip()
                if not cleaned_s:
                    return 0.0
                return float(cleaned_s)
            except (ValueError, TypeError):
                return 0.0

        monto_base = to_float(self.txt_monto_base.text())
        monto_base_personal = to_float(self.txt_monto_base_personal.text())
        monto_ofertado = to_float(self.txt_monto_ofertado.text())

        if self.lote_actual:
            lote = self.lote_actual
            lote.numero = numero
            lote.nombre = nombre
            lote.monto_base = monto_base
            lote.monto_base_personal = monto_base_personal
            lote.monto_ofertado = monto_ofertado
            lote.empresa_nuestra = empresa_nuestra
            self.result_lote = lote
        else:
            self.result_lote = Lote(
                id=None,
                numero=numero,
                nombre=nombre,
                monto_base=monto_base,
                monto_base_personal=monto_base_personal,
                monto_ofertado=monto_ofertado,
                empresa_nuestra=empresa_nuestra,
                participamos=True,
                fase_A_superada=False
            )
        print("[DEBUG][DialogoLoteForm._guardar] result_lote:", self.result_lote)
        self.accept()

    def get_lote_object(self) -> Optional[Lote]:
        return self.result_lote