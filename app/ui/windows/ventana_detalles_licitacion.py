from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget, QGridLayout, QGroupBox,
    QLabel, QLineEdit, QComboBox, QPushButton, QTextEdit, QCheckBox, QHBoxLayout
)
from PyQt6.QtCore import Qt

class LicitationDetailsWindow(QDialog):
    """
    Ventana de detalles de licitación similar a la ficha de la imagen del usuario.
    """
    def __init__(self, parent, licitacion, db=None):
        super().__init__(parent)
        self.licitacion = licitacion
        self.db = db
        self.setWindowTitle(f"Detalles de: {licitacion.nombre_proceso}")
        self.setMinimumSize(950, 700)
        self.setStyleSheet("background: #fafbfc;")

        main_layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Tab principal
        self.tab_general = QWidget()
        self.tabs.addTab(self.tab_general, "Detalles Generales")
        self._crear_tab_general()

        # Resultado de guardado (puedes usar esto si quieres devolver el objeto modificado)
        self.resultado = None

    def _crear_tab_general(self):
        layout = QGridLayout(self.tab_general)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(10)

        # --- Identificación del Proceso ---
        group_id = QGroupBox("Identificación del Proceso")
        grid_id = QGridLayout(group_id)
        lbl_codigo = QLabel("Código:")
        self.txt_codigo = QLineEdit(self.licitacion.numero_proceso)
        self.txt_codigo.setReadOnly(True)
        lbl_nombre = QLabel("Nombre:")
        self.txt_nombre = QLineEdit(self.licitacion.nombre_proceso)
        self.txt_nombre.setReadOnly(True)
        lbl_institucion = QLabel("Institución:")
        self.txt_institucion = QLineEdit(self.licitacion.institucion)
        self.txt_institucion.setReadOnly(True)

        grid_id.addWidget(lbl_codigo, 0, 0)
        grid_id.addWidget(self.txt_codigo, 0, 1)
        grid_id.addWidget(lbl_nombre, 1, 0)
        grid_id.addWidget(self.txt_nombre, 1, 1)
        grid_id.addWidget(lbl_institucion, 2, 0)
        grid_id.addWidget(self.txt_institucion, 2, 1)

        # --- Nuestras Empresas ---
        group_emp = QGroupBox("Nuestras Empresas")
        vbox_emp = QVBoxLayout(group_emp)
        # Mostrar las empresas nuestras separadas por coma
        self.lbl_empresas = QLabel(", ".join([str(e) for e in self.licitacion.empresas_nuestras]))
        vbox_emp.addWidget(self.lbl_empresas)
        btn_seleccionar_emp = QPushButton("Seleccionar...")
        # Aquí puedes conectar la lógica para editar empresas si lo deseas
        vbox_emp.addWidget(btn_seleccionar_emp, alignment=Qt.AlignmentFlag.AlignRight)

        # --- Información General y Estado ---
        group_info = QGroupBox("Información General y Estado")
        grid_info = QGridLayout(group_info)
        lbl_estado = QLabel("Estado:")
        self.combo_estado = QComboBox()
        self.combo_estado.addItems([
            "Iniciada", "Sobre B Entregado", "Adjudicada", "Descalificado Fase A",
            "Descalificado Fase B", "Desierta", "Cancelada"
        ])
        self.combo_estado.setCurrentText(getattr(self.licitacion, "estado", "Iniciada"))
        lbl_adj = QLabel("Adjudicada a:")
        self.txt_adjudicada = QLineEdit(getattr(self.licitacion, "adjudicada_a", ""))
        self.txt_adjudicada.setReadOnly(True)
        lbl_progreso = QLabel("Progreso Docs:")
        self.lbl_progreso = QLabel(f"{getattr(self.licitacion, 'get_porcentaje_completado', lambda: 0.0)():.1f}%")
        self.chk_docs = QCheckBox("Documentación completa (sin requisitos)")
        self.chk_docs.setChecked(getattr(self.licitacion, "docs_completos_manual", False))
        self.chk_faseb = QCheckBox("Fase B (Sobres Económicos) superada")
        self.chk_faseb.setChecked(getattr(self.licitacion, "fase_B_superada", False))
        lbl_motivo = QLabel("Motivo Descalificación / Comentarios:")
        self.txt_motivo = QTextEdit(getattr(self.licitacion, "motivo_descalificacion", ""))

        grid_info.addWidget(lbl_estado, 0, 0)
        grid_info.addWidget(self.combo_estado, 0, 1)
        grid_info.addWidget(lbl_adj, 1, 0)
        grid_info.addWidget(self.txt_adjudicada, 1, 1)
        grid_info.addWidget(lbl_progreso, 2, 0)
        grid_info.addWidget(self.lbl_progreso, 2, 1)
        grid_info.addWidget(self.chk_docs, 3, 0, 1, 2)
        grid_info.addWidget(self.chk_faseb, 4, 0, 1, 2)
        grid_info.addWidget(lbl_motivo, 5, 0, 1, 2)
        grid_info.addWidget(self.txt_motivo, 6, 0, 1, 2)

        # --- Cronograma del Proceso ---
        group_crono = QGroupBox("Cronograma del Proceso")
        grid_crono = QGridLayout(group_crono)
        eventos = [
            "Presentacion de Ofertas",
            "Apertura de Ofertas",
            "Informe de Evaluacion Tecnica",
            "Notificaciones de Subsanables",
            "Entrega de Subsanaciones"
        ]
        for i, evento in enumerate(eventos):
            lbl = QLabel(evento + ":")
            fecha = self.licitacion.cronograma.get(evento, {}).get("fecha_limite", "")
            estado = self.licitacion.cronograma.get(evento, {}).get("estado", "Pendiente")
            date_edit = QLineEdit(fecha)
            date_edit.setReadOnly(True)
            estado_combo = QComboBox()
            estado_combo.addItems(["Pendiente", "Cumplido"])
            estado_combo.setCurrentText(estado)
            grid_crono.addWidget(lbl, i, 0)
            grid_crono.addWidget(date_edit, i, 1)
            grid_crono.addWidget(estado_combo, i, 2)

        # --- Layout total ---
        layout.addWidget(group_id, 0, 0, 2, 2)
        layout.addWidget(group_emp, 0, 2, 2, 1)
        layout.addWidget(group_info, 2, 0, 2, 2)
        layout.addWidget(group_crono, 2, 2, 2, 1)

        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 1)

# Demo de uso
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    class DummyEmpresa:
        def __init__(self, nombre): self.nombre = nombre
        def __str__(self): return self.nombre
    class DummyLicitacion:
        def __init__(self):
            self.numero_proceso = "DGAP-CCC-CP-2025-0004"
            self.nombre_proceso = "READECUACIÓN DE BAÑOS DE LA SEDE CENTRAL"
            self.institucion = "DIRECCION GENERAL DE ADUANAS"
            self.empresas_nuestras = [DummyEmpresa("ZOEC CIVIL")]
            self.estado = "Sobre B Entregado"
            self.adjudicada_a = ""
            self.docs_completos_manual = False
            self.fase_B_superada = False
            self.motivo_descalificacion = ""
            self.cronograma = {
                "Presentacion de Ofertas": {"fecha_limite": "2025-08-11", "estado": "Cumplido"},
                "Apertura de Ofertas": {"fecha_limite": "2025-08-11", "estado": "Cumplido"},
                "Informe de Evaluacion Tecnica": {"fecha_limite": "2025-08-11", "estado": "Cumplido"},
                "Notificaciones de Subsanables": {"fecha_limite": "2025-08-11", "estado": "Cumplido"},
                "Entrega de Subsanaciones": {"fecha_limite": "", "estado": "Pendiente"},
            }
        def get_porcentaje_completado(self): return 100.0
    app = QApplication(sys.argv)
    lic = DummyLicitacion()
    win = LicitationDetailsWindow(None, lic)
    win.show()
    sys.exit(app.exec())