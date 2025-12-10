from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QListWidget,
    QListWidgetItem, QPushButton, QCheckBox, QDialogButtonBox, QAbstractItemView,
    QMessageBox, QStyle
)
from PyQt6.QtCore import Qt, QSize
from app.core.models import Documento
from app.core.db_adapter import DatabaseAdapter

CATEGORIAS_EXPEDIENTE = ["Legal", "Técnica", "Financiera", "Sobre B"]

class DialogoOrdenarDocumentos(QDialog):
    def __init__(
        self,
        parent: QWidget,
        documentos_actuales: list,
        licitacion_id: int = None,
        db_adapter: DatabaseAdapter = None
    ):
        super().__init__(parent)
        self.setWindowTitle("Ordenar Documentos del Expediente")
        self.setMinimumSize(950, 600)
        self._documentos_originales = documentos_actuales
        self._categorias_orden = CATEGORIAS_EXPEDIENTE
        self._docs_por_categoria_original = {}
        self._data = {}
        self._list_widgets = {}
        self._include_checkboxes = {}
        self._licitacion_id = licitacion_id
        self._db_adapter = db_adapter

        self.result_incluir = None
        self.result_orden = None

        self._prepare_data()
        self._build_ui()
        self._populate_lists()

    def _prepare_data(self):
        grupos_temp = {cat: [] for cat in self._categorias_orden}
        for doc in self._documentos_originales:
            cat = getattr(doc, "categoria", "Otros")
            if cat in grupos_temp:
                grupos_temp[cat].append(doc)
        for cat in self._categorias_orden:
            docs = grupos_temp.get(cat, [])
            docs_sorted = sorted(docs, key=lambda d: (getattr(d, 'orden_pliego', 99999), str(d.codigo or "")))
            self._docs_por_categoria_original[cat] = list(docs_sorted)
            self._data[cat] = list(docs_sorted)

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        for cat_name in self._categorias_orden:
            tab_content = QWidget()
            tab_layout = QVBoxLayout(tab_content)

            checkbox_layout = QHBoxLayout()
            include_cb = QCheckBox(f"Incluir categoría '{cat_name}' en el expediente")
            include_cb.setChecked(True)
            checkbox_layout.addWidget(include_cb)
            checkbox_layout.addStretch(1)
            tab_layout.addLayout(checkbox_layout)
            self._include_checkboxes[cat_name] = include_cb

            list_button_layout = QHBoxLayout()
            tab_layout.addLayout(list_button_layout)

            list_widget = QListWidget()
            list_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
            list_widget.setDefaultDropAction(Qt.DropAction.MoveAction)
            list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
            list_widget.setStyleSheet("QListWidget::item { padding: 3px; }")
            list_button_layout.addWidget(list_widget, stretch=1)
            self._list_widgets[cat_name] = list_widget

            # DRAG & DROP: persistencia automática
            list_widget.model().rowsMoved.connect(lambda *_, cat=cat_name: self._on_drag_drop(cat))

            button_vlayout = QVBoxLayout()
            button_vlayout.setSpacing(5)
            button_vlayout.setAlignment(Qt.AlignmentFlag.AlignTop)

            btn_up = QPushButton("Subir")
            btn_up.clicked.connect(lambda _, cat=cat_name: self._mover(cat, -1))
            btn_up.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp))
            btn_up.setIconSize(QSize(16,16))

            btn_down = QPushButton("Bajar")
            btn_down.clicked.connect(lambda _, cat=cat_name: self._mover(cat, 1))
            btn_down.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown))
            btn_down.setIconSize(QSize(16,16))

            btn_top = QPushButton("Arriba")
            btn_top.clicked.connect(lambda _, cat=cat_name: self._to_edge(cat, top=True))
            btn_top.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowLeft))
            btn_top.setIconSize(QSize(16,16))

            btn_bottom = QPushButton("Abajo")
            btn_bottom.clicked.connect(lambda _, cat=cat_name: self._to_edge(cat, top=False))
            btn_bottom.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowRight))
            btn_bottom.setIconSize(QSize(16,16))

            btn_reset = QPushButton("Resetear Orden")
            btn_reset.clicked.connect(lambda _, cat=cat_name: self._reset_order(cat))
            btn_reset.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
            btn_reset.setIconSize(QSize(16,16))

            button_vlayout.addWidget(btn_up)
            button_vlayout.addWidget(btn_down)
            button_vlayout.addWidget(btn_top)
            button_vlayout.addWidget(btn_bottom)
            button_vlayout.addWidget(btn_reset)
            list_button_layout.addLayout(button_vlayout)
            self.tab_widget.addTab(tab_content, cat_name)

        dialog_button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            Qt.Orientation.Horizontal
        )
        dialog_button_box.accepted.connect(self._accept)
        dialog_button_box.rejected.connect(self.reject)
        main_layout.addWidget(dialog_button_box)

    def _on_drag_drop(self, cat):
        print(f"[DEBUG] Drag&Drop rowsMoved en {cat}")
        # Actualiza la lista interna
        list_widget = self._list_widgets[cat]
        new_order_docs = []
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            doc = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(doc, Documento):
                new_order_docs.append(doc)
        self._data[cat] = new_order_docs
        self._persist_orden()

    def _populate_lists(self):
        for cat_name in self._categorias_orden:
            self._render_list(cat_name)

    def _render_list(self, category: str):
        list_widget = self._list_widgets.get(category)
        docs_in_cat = self._data.get(category, [])
        list_widget.blockSignals(True)
        list_widget.clear()
        for i, doc in enumerate(docs_in_cat):
            presentado_icon = "✓" if getattr(doc, "presentado", False) else "❌"
            display_text = f"{presentado_icon}  [{doc.codigo or 'S/C'}] {doc.nombre or 'Sin Nombre'}"
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, doc)
            list_widget.addItem(item)
        list_widget.blockSignals(False)

    def _mover(self, cat, delta):
        list_widget = self._list_widgets[cat]
        sel_items = list_widget.selectedItems()
        if not sel_items:
            print(f"[DEBUG] _mover: no items seleccionados para {cat}")
            return
        sel_indices = sorted([list_widget.row(item) for item in sel_items])
        items = self._data[cat]
        if delta < 0:
            for i in sel_indices:
                if i > 0 and (i-1) not in sel_indices:
                    items[i], items[i-1] = items[i-1], items[i]
        else:
            for i in reversed(sel_indices):
                if i < len(items) - 1 and (i+1) not in sel_indices:
                    items[i], items[i+1] = items[i+1], items[i]
        self._render_list(cat)
        nuevos_indices = []
        for i in sel_indices:
            j = i + delta
            if 0 <= j < len(items): nuevos_indices.append(j)
        list_widget.clearSelection()
        for idx in nuevos_indices:
            item = list_widget.item(idx)
            if item: item.setSelected(True)
        print(f"[DEBUG] Mover {cat} delta={delta}: {sel_indices} -> {nuevos_indices}")
        self._persist_orden()

    def _to_edge(self, cat, top=True):
        list_widget = self._list_widgets[cat]
        sel_items = list_widget.selectedItems()
        if not sel_items:
            print(f"[DEBUG] _to_edge: no items seleccionados para {cat}")
            return
        sel_indices = {list_widget.row(item) for item in sel_items}
        items = self._data[cat]
        picked = [item for i, item in enumerate(items) if i in sel_indices]
        rest = [item for i, item in enumerate(items) if i not in sel_indices]
        self._data[cat] = picked + rest if top else rest + picked
        self._render_list(cat)
        if top:
            nuevos = list(range(len(picked)))
        else:
            nuevos = list(range(len(self._data[cat]) - len(picked), len(self._data[cat])))
        list_widget.clearSelection()
        for idx in nuevos:
            item = list_widget.item(idx)
            if item: item.setSelected(True)
        print(f"[DEBUG] ToEdge {cat} top={top}: {list(sel_indices)} -> {nuevos}")
        self._persist_orden()

    def _reset_order(self, category: str):
        original_docs = self._docs_por_categoria_original.get(category)
        if not original_docs:
            print(f"[DEBUG] _reset_order: no originales para {category}")
            return
        self._data[category] = list(original_docs)
        self._render_list(category)
        print(f"[DEBUG] Reset {category}: restaurado a orden original")
        self._persist_orden()

    def _persist_orden(self):
        if not self._db_adapter or not self._licitacion_id:
            print("[DEBUG] _persist_orden: Sin db_adapter o licitacion_id, no se persiste.")
            return
        pares_docid_orden = []
        orden_global = 1
        for cat in self._categorias_orden:
            for d in self._data.get(cat, []):
                try:
                    setattr(d, "orden_pliego", orden_global)
                except Exception:
                    pass
                doc_id = getattr(d, "id", None)
                if doc_id is not None:
                    pares_docid_orden.append((doc_id, orden_global))
                orden_global += 1
        try:
            ok = self._db_adapter.guardar_orden_documentos(self._licitacion_id, pares_docid_orden)
            print(f"[DEBUG] _persist_orden: Guardado en DB: {ok}, pares: {pares_docid_orden}")
        except Exception as e:
            print(f"[ERROR] _persist_orden: fallo al guardar: {e}")

    def _accept(self):
        self.result_incluir = {}
        self.result_orden = {}
        for cat_name in self._categorias_orden:
            include_cb = self._include_checkboxes.get(cat_name)
            self.result_incluir[cat_name] = include_cb.isChecked() if include_cb else False
            self.result_orden[cat_name] = self._data.get(cat_name, [])
        self._persist_orden()
        super().accept()

    def reject(self):
        self.result_incluir = None
        self.result_orden = None
        super().reject()

    def get_orden_documentos(self):
        return self.result_orden

    def get_inclusion_categorias(self):
        return self.result_incluir