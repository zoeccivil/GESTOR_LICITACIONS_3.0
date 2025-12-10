from __future__ import annotations
from typing import List, Optional, Dict, Any

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QAbstractItemView, QDialogButtonBox, QMessageBox, QLineEdit, QHBoxLayout,
    QWidget, QHeaderView, QStyle
)
try:
    from PyQt6.QtGui import QKeySequence, QShortcut
except Exception:
    try:
        from PyQt6.QtWidgets import QShortcut  # type: ignore
        from PyQt6.QtGui import QKeySequence
    except Exception:
        raise
from PyQt6.QtCore import Qt
import html

"""
SelectLicitacionDialog - Versión tabulada limpia

Cambios principales:
- Sin prints DEBUG.
- Añade columna "Institución".
- Añade método get_selected_row() que devuelve el dict completo del registro seleccionado.
- Normaliza texto (quita saltos de línea) y usa tooltip con el texto completo.
- Desactiva sorting mientras se carga y lo habilita después.
"""

def _get_display_nombre(info: Dict[str, Any]) -> str:
    if not info:
        return ""
    for key in ("nombre_proceso", "nombre", "titulo", "nombre_proyecto", "nombre_proceso_normalizado"):
        val = info.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    nested = info.get("data") or info.get("payload")
    if isinstance(nested, dict):
        for key in ("nombre_proceso", "nombre", "titulo"):
            val = nested.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return ""

def _get_display_codigo(info: Dict[str, Any]) -> str:
    if not info:
        return ""
    for key in ("numero_proceso", "numero", "codigo", "code"):
        val = info.get(key)
        if val is not None:
            return str(val)
    nested = info.get("data") or info.get("payload")
    if isinstance(nested, dict):
        for key in ("numero_proceso", "numero", "codigo"):
            val = nested.get(key)
            if val is not None:
                return str(val)
    return ""

def _get_display_institucion(info: Dict[str, Any]) -> str:
    if not info:
        return ""
    for key in ("institucion", "institucion_proceso", "org", "organizacion"):
        val = info.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    nested = info.get("data") or info.get("payload")
    if isinstance(nested, dict):
        for key in ("institucion", "org"):
            val = nested.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return ""

def _normalize_display_text(s: Optional[str]) -> str:
    if not s:
        return ""
    text = " ".join(line.strip() for line in str(s).splitlines())
    text = " ".join(text.split())
    return text

class SelectLicitacionDialog(QDialog):
    def __init__(self,
                 parent: QWidget,
                 licitaciones_info: Optional[List[Dict[str, Any]]] = None,
                 exclude_numero: Optional[str] = None,
                 db_adapter: Optional[Any] = None,
                 *args,
                 **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.selected_id: Optional[int] = None
        self._current_displayed_list: List[Dict[str, Any]] = []

        # Resolver lista de licitaciones: desde lista pasada o desde adapter
        resolved_info: List[Dict[str, Any]] = []
        if licitaciones_info is not None:
            for x in licitaciones_info:
                if isinstance(x, dict):
                    resolved_info.append(dict(x))
        elif db_adapter is not None:
            try:
                if hasattr(db_adapter, "get_all_licitaciones_basic_info"):
                    resolved_info = db_adapter.get_all_licitaciones_basic_info() or []
                elif hasattr(db_adapter, "list_licitaciones"):
                    objs = db_adapter.list_licitaciones() or []
                    tmp: List[Dict[str, Any]] = []
                    for o in objs:
                        tmp.append({
                            "id": getattr(o, "id", None),
                            "numero_proceso": getattr(o, "numero_proceso", "") or getattr(o, "numero", "") or "",
                            "nombre_proceso": getattr(o, "nombre_proceso", "") or getattr(o, "nombre", "") or "",
                            "institucion": getattr(o, "institucion", "") or "",
                        })
                    resolved_info = tmp
                else:
                    resolved_info = []
            except Exception:
                resolved_info = []
        else:
            resolved_info = []

        # Normalizar: asegurar keys id, numero_proceso, nombre_proceso, institucion
        normalized: List[Dict[str, Any]] = []
        for item in resolved_info:
            if not isinstance(item, dict):
                continue
            nid = item.get("id") or item.get("ID") or item.get("_id")
            codigo = _get_display_codigo(item)
            nombre = _get_display_nombre(item)
            institucion = _get_display_institucion(item)
            normalized.append({
                "id": nid,
                "numero_proceso": codigo,
                "nombre_proceso": nombre,
                "institucion": institucion,
                **{k: v for k, v in item.items() if k not in ("id", "numero_proceso", "nombre_proceso", "institucion")}
            })
        self._all_licitaciones_info = normalized

        # Aplicar exclusión si procede
        if exclude_numero is not None:
            self._all_licitaciones_info = [
                lic for lic in self._all_licitaciones_info if (lic.get("numero_proceso") or "") != exclude_numero
            ]

        # Ordenar
        self._all_licitaciones_info.sort(key=lambda info: (info.get('numero_proceso') or "") or (info.get('nombre_proceso') or ""))

        # UI
        self.setWindowTitle("Seleccionar Licitación de Origen")
        self.setMinimumWidth(800)
        self.setMinimumHeight(440)
        self._build_ui()
        self._populate_table(self._all_licitaciones_info)

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        header_layout = QHBoxLayout()
        icon_label = QLabel()
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton)
        icon_label.setPixmap(icon.pixmap(24, 24))
        header_layout.addWidget(icon_label)
        header_layout.addWidget(QLabel("<b>Seleccione la licitación de origen (doble clic o Enter para confirmar)</b>"))
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filtrar:"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Buscar por código, nombre o institución...")
        self.filter_edit.textChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.filter_edit)
        main_layout.addLayout(filter_layout)

        # Tabla con 3 columnas: Código, Nombre, Institución
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Código", "Nombre", "Institución"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        # Ajuste de filas y wordwrap
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.setWordWrap(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self.accept)
        self.table.setSortingEnabled(False)  # habilitar tras poblar
        main_layout.addWidget(self.table)

        self.status_label = QLabel("")
        main_layout.addWidget(self.status_label)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            Qt.Orientation.Horizontal
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button is not None:
            ok_button.setEnabled(False)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        main_layout.addWidget(self.button_box)

        # Shortcut Enter -> accept when a row is selected
        try:
            QShortcut(QKeySequence(Qt.Key.Key_Return), self, activated=self._on_enter_pressed)
            QShortcut(QKeySequence(Qt.Key.Key_Enter), self, activated=self._on_enter_pressed)
        except Exception:
            pass

        self.filter_edit.setFocus()

    def _populate_table(self, licitaciones_info: List[Dict[str, Any]]):
        # Desactivar sorting durante la carga
        try:
            self.table.setSortingEnabled(False)
        except Exception:
            pass

        self._current_displayed_list = licitaciones_info[:]

        self.table.setRowCount(0)
        if not licitaciones_info:
            self.table.setRowCount(1)
            item = QTableWidgetItem("No se encontraron otras licitaciones.")
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(0, 0, item)
            self.table.setSpan(0, 0, 1, 3)
            self.table.setEnabled(False)
            ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
            if ok_button is not None:
                ok_button.setEnabled(False)
            self.status_label.setText("0 licitaciones disponibles")
            return

        self.table.setEnabled(True)
        self.table.setRowCount(len(licitaciones_info))
        for row, info in enumerate(licitaciones_info):
            codigo = _normalize_display_text(info.get("numero_proceso", "") or "")
            nombre_original = info.get("nombre_proceso", "") or ""
            nombre = _normalize_display_text(nombre_original)
            institucion_original = info.get("institucion", "") or ""
            institucion = _normalize_display_text(institucion_original)
            id_val = info.get("id")

            item_codigo = QTableWidgetItem(codigo)
            item_nombre = QTableWidgetItem(nombre)
            item_institucion = QTableWidgetItem(institucion)

            # Flags y alineación
            item_codigo.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            item_nombre.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            item_institucion.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)

            item_codigo.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            item_nombre.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            item_institucion.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            # Guardar id en UserRole en las celdas
            item_codigo.setData(Qt.ItemDataRole.UserRole, id_val)
            item_nombre.setData(Qt.ItemDataRole.UserRole, id_val)
            item_institucion.setData(Qt.ItemDataRole.UserRole, id_val)

            # Tooltip con texto completo sin normalizar
            if nombre_original:
                item_nombre.setToolTip(html.escape(str(nombre_original)))
            if institucion_original:
                item_institucion.setToolTip(html.escape(str(institucion_original)))

            self.table.setItem(row, 0, item_codigo)
            self.table.setItem(row, 1, item_nombre)
            self.table.setItem(row, 2, item_institucion)

        # Ajustar altura de filas para evitar truncado
        try:
            self.table.resizeRowsToContents()
        except Exception:
            pass

        # Estado
        self.status_label.setText(f"{len(licitaciones_info)} licitaciones disponibles")

        # Habilitar sorting tras poblar
        try:
            self.table.setSortingEnabled(True)
        except Exception:
            pass

        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button is not None:
            ok_button.setEnabled(self.table.currentRow() >= 0)

    def _apply_filter(self):
        txt = self.filter_edit.text().strip().lower()
        if not txt:
            filtered = self._all_licitaciones_info[:]
        else:
            filtered = [
                info for info in self._all_licitaciones_info
                if txt in (info.get("numero_proceso", "") or "").lower()
                or txt in (info.get("nombre_proceso", "") or "").lower()
                or txt in (info.get("institucion", "") or "").lower()
            ]
        self._populate_table(filtered)

    def _on_selection_changed(self):
        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button is not None:
            ok_button.setEnabled(self.table.currentRow() >= 0)

    def _on_enter_pressed(self):
        if self.table.currentRow() >= 0:
            self.accept()

    def accept(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Sin Selección", "Por favor, selecciona una licitación de la tabla.")
            return
        # Obtenemos el dict original mostrado en la fila
        try:
            selected = self._current_displayed_list[row]
        except Exception:
            QMessageBox.critical(self, "Error Interno", "No se pudo obtener la entrada seleccionada.")
            return

        id_val = selected.get("id")
        if id_val is None:
            QMessageBox.critical(self, "Error Interno", "La licitación seleccionada no tiene un ID asociado.")
            return
        try:
            self.selected_id = int(id_val)
        except (ValueError, TypeError):
            QMessageBox.critical(self, "Error Interno", f"El ID '{id_val}' no es un número válido.")
            return

        super().accept()

    def get_selected_id(self) -> Optional[int]:
        """Devuelve el ID entero seleccionado (o None)."""
        return self.selected_id

    def get_selected_row(self) -> Optional[Dict[str, Any]]:
        """Devuelve el dict completo de la fila seleccionada (o None si canceló)."""
        row = self.table.currentRow()
        if row < 0:
            return None
        try:
            return self._current_displayed_list[row]
        except Exception:
            return None