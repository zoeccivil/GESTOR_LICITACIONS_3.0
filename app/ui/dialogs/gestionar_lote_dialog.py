from __future__ import annotations
from typing import List, Optional, Dict, Any
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QDoubleSpinBox,
    QComboBox,
    QDialogButtonBox,
    QWidget, QMessageBox
)
from app.core.models import Lote

class GestionarLoteDialog(QDialog):
    """
    Editor de Lote en PyQt6.
    Uso:
        dlg = GestionarLoteDialog(parent, initial_data=lote_existente, participating_companies=["EMPRESA A", "EMPRESA B"])
        if dlg.exec() == QDialog.DialogCode.Accepted:
            # Si quieres objeto Lote:
            # nuevo_lote = dlg.get_lote_obj()
            # Si quieres dict:
            datos = dlg.resultado
    """
    def __init__(
        self,
        parent: QWidget,
        title: str = "Gestionar Lote",
        initial_data: Optional[Lote] = None,
        participating_companies: Optional[List[str]] = None,
        licitacion=None,
        db_adapter=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)

        self.initial_data = initial_data
        self.participating_companies = participating_companies or []

        # 🔐 NUEVOS ATRIBUTOS
        self.licitacion = licitacion
        self.db_adapter = db_adapter

        self.resultado: Optional[Dict[str, Any]] = None
        self._lote_obj: Optional[Lote] = None

        self._build_ui()
        self._load_initial_data()

    def _build_ui(self):
        self.setMinimumWidth(520)
        vbox = QVBoxLayout(self)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)

        # Número
        grid.addWidget(QLabel("Número de Lote:"), 0, 0)
        self.numero_edit = QLineEdit(self)
        self.numero_edit.setPlaceholderText("p.ej. 1")
        grid.addWidget(self.numero_edit, 0, 1)

        # Nombre
        grid.addWidget(QLabel("Nombre del Lote:"), 1, 0)
        self.nombre_edit = QLineEdit(self)
        self.nombre_edit.setPlaceholderText("Nombre del lote")
        grid.addWidget(self.nombre_edit, 1, 1)

        # Monto base (licitación)
        grid.addWidget(QLabel("Monto Base (Licitación):"), 2, 0)
        self.monto_base_spin = QDoubleSpinBox(self)
        self.monto_base_spin.setRange(0.0, 1e15)
        self.monto_base_spin.setDecimals(2)
        self.monto_base_spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        grid.addWidget(self.monto_base_spin, 2, 1)

        # Monto base personal
        grid.addWidget(QLabel("Monto Base (Presupuesto Personal):"), 3, 0)
        self.monto_personal_spin = QDoubleSpinBox(self)
        self.monto_personal_spin.setRange(0.0, 1e15)
        self.monto_personal_spin.setDecimals(2)
        self.monto_personal_spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        grid.addWidget(self.monto_personal_spin, 3, 1)

        # Monto ofertado (nuestra oferta)
        grid.addWidget(QLabel("Nuestra Oferta para el Lote:"), 4, 0)
        self.monto_oferta_spin = QDoubleSpinBox(self)
        self.monto_oferta_spin.setRange(0.0, 1e15)
        self.monto_oferta_spin.setDecimals(2)
        self.monto_oferta_spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        grid.addWidget(self.monto_oferta_spin, 4, 1)

        # Empresa
        grid.addWidget(QLabel("Asignar a Empresa:"), 5, 0)
        self.empresa_combo = QComboBox(self)
        self.empresa_combo.addItem("(Sin Asignar)")
        for emp in self.participating_companies:
            self.empresa_combo.addItem(emp)
        grid.addWidget(self.empresa_combo, 5, 1)

        vbox.addLayout(grid)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            orientation=Qt.Orientation.Horizontal,
            parent=self,
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        vbox.addWidget(buttons)

    def _load_initial_data(self):
        if not self.initial_data:
            self.empresa_combo.setCurrentIndex(0)
            return

        # Permitir dict u objeto Lote
        def getv(obj, key):
            if isinstance(obj, dict):
                return obj.get(key)
            return getattr(obj, key, None)

        numero = getv(self.initial_data, "numero")
        nombre = getv(self.initial_data, "nombre")
        monto_base = getv(self.initial_data, "monto_base")
        monto_base_personal = getv(self.initial_data, "monto_base_personal")
        monto_ofertado = getv(self.initial_data, "monto_ofertado")
        empresa_nuestra = getv(self.initial_data, "empresa_nuestra")

        self.numero_edit.setText(str(numero or ""))
        self.nombre_edit.setText(str(nombre or ""))
        try:
            self.monto_base_spin.setValue(float(monto_base or 0.0))
        except Exception:
            self.monto_base_spin.setValue(0.0)
        try:
            self.monto_personal_spin.setValue(float(monto_base_personal or 0.0))
        except Exception:
            self.monto_personal_spin.setValue(0.0)
        try:
            self.monto_oferta_spin.setValue(float(monto_ofertado or 0.0))
        except Exception:
            self.monto_oferta_spin.setValue(0.0)

        emp = (empresa_nuestra or "").strip() or "(Sin Asignar)"
        idx = max(0, self.empresa_combo.findText(emp))
        self.empresa_combo.setCurrentIndex(idx)

    def _on_accept(self):
        numero_txt = self.numero_edit.text().strip()
        nombre_txt = self.nombre_edit.text().strip()

        # Validaciones mínimas
        if not numero_txt:
            QMessageBox.warning(self, "Campo requerido", "El número de lote no puede estar vacío.")
            return
        if not nombre_txt:
            QMessageBox.warning(self, "Campo requerido", "El nombre del lote no puede estar vacío.")
            return

        try:
            lote = Lote(
                numero=numero_txt,
                nombre=nombre_txt,
                monto_base=float(self.monto_base_spin.value()),
                monto_base_personal=float(self.monto_personal_spin.value()),
                monto_ofertado=float(self.monto_oferta_spin.value()),
                empresa_nuestra=(
                    self.empresa_combo.currentText()
                    if self.empresa_combo.currentText() != "(Sin Asignar)"
                    else None
                ),
            )
            if self.initial_data and getattr(self.initial_data, "id", None) is not None:
                lote.id = getattr(self.initial_data, "id")

            self._lote_obj = lote
            self.resultado = lote.to_dict() if hasattr(lote, "to_dict") else {
                "numero": lote.numero,
                "nombre": lote.nombre,
                "monto_base": lote.monto_base,
                "monto_base_personal": getattr(lote, "monto_base_personal", 0.0),
                "monto_ofertado": lote.monto_ofertado,
                "empresa_nuestra": lote.empresa_nuestra,
                "id": getattr(lote, "id", None),
            }

            # 🔐 CANDADO: sincronizar y guardar automáticamente
            try:
                if self.licitacion and hasattr(self.licitacion, "lotes"):
                    for idx, l in enumerate(self.licitacion.lotes):
                        if getattr(l, "id", None) == lote.id:
                            self.licitacion.lotes[idx] = lote
                            break
                    else:
                        # Si no existía, lo agregamos
                        self.licitacion.lotes.append(lote)

                if self.db_adapter:
                    print("[AUTO-SAVE] Guardando licitación en Firebase desde GestionarLoteDialog")
                    self.db_adapter.save_licitacion(self.licitacion)

            except Exception as ex:
                QMessageBox.critical(
                    self,
                    "Error al guardar",
                    f"El lote se guardó localmente, pero falló el guardado en Firebase:\n{ex}",
                )

            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo construir el lote:\n{e}")
            self.resultado = None

    # Métodos auxiliares
    def get_lote_obj(self) -> Optional[Lote]:
        """Devuelve el objeto Lote construido (si se aceptó)."""
        return self._lote_obj

    def get_result_dict(self) -> Optional[Dict[str, Any]]:
        """Devuelve el dict resultado (si se aceptó)."""
        return self.resultado