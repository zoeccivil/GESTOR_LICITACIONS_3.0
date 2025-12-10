from __future__ import annotations
from typing import Optional, Dict, Any, List, Union
import os
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QPushButton,
    QDialogButtonBox,
    QFileDialog,
    QWidget,QMessageBox
)
from app.core.models import Documento


class DialogoGestionarDocumento(QDialog):
    """
    Editor de Documento.
    Campos: código, nombre, categoría, obligatorio, subsanable, presentado, revisado, responsable, comentario, ruta_archivo
    """
    DEFAULT_CATEGORIES: List[str] = ["Legal", "Técnica", "Financiera", "Sobre B", "Otros"]
    SUBSANABLES: List[str] = ["No Definido", "Subsanable", "No Subsanable"]

    def __init__(
        self,
        parent: QWidget,
        title: str = "Gestionar Documento",
        # Aceptar un Documento (para editar) o un Dict (para añadir con pre-rellenado)
        initial_data: Optional[Union[Documento, Dict[str, Any]]] = None,
        categories: Optional[List[str]] = None,
        responsables: Optional[List[str]] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.initial_data = initial_data
        self.categories = categories or self.DEFAULT_CATEGORIES
        self.responsables = responsables or ["Sin Asignar"]
        self.resultado: Optional[Dict[str, Any]] = None

        self._build_ui()
        self._load_initial_data() # Llamar después de construir la UI

    def _build_ui(self):
        self.setMinimumWidth(580)
        vbox = QVBoxLayout(self)

        grid = QGridLayout()
        grid.setColumnStretch(1, 1) # Permitir que los campos de entrada crezcan

        # Código
        grid.addWidget(QLabel("Código:"), 0, 0)
        self.ed_codigo = QLineEdit(self)
        self.ed_codigo.setPlaceholderText("p.ej. A-01")
        grid.addWidget(self.ed_codigo, 0, 1, 1, 2) # Ocupa 2 columnas

        # Nombre
        grid.addWidget(QLabel("Nombre:"), 1, 0)
        self.ed_nombre = QLineEdit(self)
        self.ed_nombre.setPlaceholderText("Nombre del documento")
        grid.addWidget(self.ed_nombre, 1, 1, 1, 2)

        # Categoría
        grid.addWidget(QLabel("Categoría:"), 2, 0)
        self.cb_categoria = QComboBox(self)
        self.cb_categoria.addItems(self.categories)
        grid.addWidget(self.cb_categoria, 2, 1, 1, 2)

        # Obligatorio
        grid.addWidget(QLabel("Obligatorio:"), 3, 0)
        self.chk_oblig = QCheckBox(self)
        grid.addWidget(self.chk_oblig, 3, 1)

        # Subsanable
        grid.addWidget(QLabel("Condición:"), 4, 0) # Texto cambiado
        self.cb_subsanable = QComboBox(self)
        self.cb_subsanable.addItems(self.SUBSANABLES)
        grid.addWidget(self.cb_subsanable, 4, 1, 1, 2)

        # Presentado
        grid.addWidget(QLabel("Presentado:"), 5, 0)
        self.chk_presentado = QCheckBox(self)
        grid.addWidget(self.chk_presentado, 5, 1)

        # Revisado
        grid.addWidget(QLabel("Revisado:"), 6, 0)
        self.chk_revisado = QCheckBox(self)
        grid.addWidget(self.chk_revisado, 6, 1)

        # Responsable
        grid.addWidget(QLabel("Responsable:"), 7, 0)
        self.cb_responsable = QComboBox(self)
        self.cb_responsable.setEditable(True) # Permitir escribir nombres nuevos
        if self.responsables:
            self.cb_responsable.addItems(self.responsables)
        else:
            self.cb_responsable.addItem("Sin Asignar") # Asegurar al menos una opción
        grid.addWidget(self.cb_responsable, 7, 1, 1, 2)

        # Comentario
        grid.addWidget(QLabel("Comentario:"), 8, 0)
        self.ed_comentario = QLineEdit(self)
        grid.addWidget(self.ed_comentario, 8, 1, 1, 2)

        # Archivo
        grid.addWidget(QLabel("Archivo:"), 9, 0)
        self.ed_archivo = QLineEdit(self)
        self.ed_archivo.setPlaceholderText("Ruta del archivo (opcional)")
        btn_examinar = QPushButton("Examinar…")
        btn_examinar.clicked.connect(self._on_examinar)
        grid.addWidget(self.ed_archivo, 9, 1)
        grid.addWidget(btn_examinar, 9, 2) # Botón en columna 2

        vbox.addLayout(grid)
        vbox.addStretch(1) # Empujar botones hacia abajo

        # Botonera
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            orientation=Qt.Orientation.Horizontal,
            parent=self,
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        vbox.addWidget(buttons)

    # --- MÉTODO CORREGIDO ---
    def _load_initial_data(self):
        """Carga datos iniciales, distinguiendo entre modo Edición (Objeto) y Añadir (Dict)."""
        d = self.initial_data
        if not d:
            # Modo "Añadir" sin datos pre-rellenados, no hacer nada
            print("DialogoGestionarDocumento: Abierto en modo AÑADIR (vacío).")
            return

        if isinstance(d, Documento):
            # --- MODO EDICIÓN (d es un objeto Documento) ---
            print("DialogoGestionarDocumento: Cargando datos en modo EDICIÓN.")
            self.ed_codigo.setText(d.codigo or "")
            self.ed_nombre.setText(d.nombre or "")
            self.cb_categoria.setCurrentText(d.categoria or self.categories[0])
            self.chk_oblig.setChecked(bool(d.obligatorio))
            self.cb_subsanable.setCurrentText(d.subsanable or self.SUBSANABLES[0])
            self.chk_presentado.setChecked(bool(d.presentado))
            self.chk_revisado.setChecked(bool(d.revisado))
            self.cb_responsable.setCurrentText(d.responsable or "Sin Asignar")
            self.ed_comentario.setText(d.comentario or "")
            self.ed_archivo.setText(d.ruta_archivo or "")
        
        elif isinstance(d, dict):
            # --- MODO AÑADIR (d es un diccionario) ---
            # Viene de "Añadir Manual" con datos pre-rellenados
            print("DialogoGestionarDocumento: Cargando datos en modo AÑADIR (desde dict).")
            # Usar .get() para acceder a diccionarios de forma segura
            self.ed_codigo.setText(d.get("codigo", ""))
            self.ed_nombre.setText(d.get("nombre", ""))
            
            categoria_inicial = d.get("categoria")
            if categoria_inicial and categoria_inicial in self.categories:
                self.cb_categoria.setCurrentText(categoria_inicial)
            
            # (El resto de campos se quedan por defecto: vacíos o desmarcados)

    def _on_examinar(self):
        # Iniciar en el directorio del archivo actual, si existe
        start_dir = os.path.dirname(self.ed_archivo.text()) if self.ed_archivo.text() else ""
        
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo", start_dir, "Todos (*.*)")
        if path:
            self.ed_archivo.setText(path)

    # --- MÉTODO CORREGIDO ---
    def _on_accept(self):
        codigo = self.ed_codigo.text().strip()
        nombre = self.ed_nombre.text().strip()
        if not codigo or not nombre:
            QMessageBox.warning(self, "Datos Incompletos", "El Código y el Nombre son obligatorios.")
            return # No cerrar el diálogo

        data = {
            "codigo": codigo,
            "nombre": nombre,
            "categoria": self.cb_categoria.currentText(),
            "obligatorio": self.chk_oblig.isChecked(),
            "subsanable": self.cb_subsanable.currentText(),
            "presentado": self.chk_presentado.isChecked(),
            "revisado": self.chk_revisado.isChecked(),
            "responsable": self.cb_responsable.currentText().strip() or "Sin Asignar",
            "comentario": self.ed_comentario.text().strip(),
            "ruta_archivo": self.ed_archivo.text().strip(),
            # Añadir atributos que no están en el formulario pero deben preservarse/iniciarse
            "requiere_subsanacion": False, # Por defecto al añadir/editar no requiere
            "orden_pliego": None, # El orden se asignará después
        }

        # --- CORRECCIÓN AQUÍ ---
        # Mantener id SÓLO si initial_data era un Documento (modo Edición)
        if isinstance(self.initial_data, Documento):
            if self.initial_data.id is not None:
                data["id"] = self.initial_data.id
            # Preservar el estado de requiere_subsanacion si se estaba editando
            data["requiere_subsanacion"] = self.initial_data.requiere_subsanacion
            # Preservar el orden
            data["orden_pliego"] = self.initial_data.orden_pliego
            # Preservar empresa_nombre (si se usaba)
            if hasattr(self.initial_data, 'empresa_nombre') and self.initial_data.empresa_nombre:
                data["empresa_nombre"] = self.initial_data.empresa_nombre
        # --- FIN CORRECCIÓN ---
        
        # Si estamos en modo Añadir y la categoría es "Otros", asegurarse que se guarde así
        if not isinstance(self.initial_data, Documento) and data["categoria"] not in self.categories:
             data["categoria"] = "Otros"


        self.resultado = data
        self.accept() # Llama al accept() base de QDialog