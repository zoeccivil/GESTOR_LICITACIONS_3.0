from __future__ import annotations
from typing import List, Dict, Any, Optional, Set

from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QGroupBox, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView, QMenu, QStyle, QMessageBox
)
from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtGui import QColor, QBrush, QFont
# Añadir import al inicio del archivo
from PyQt6.QtCore import Qt, QPoint, QTimer, QSettings
# Tip: Modelo esperado
# - licitacion.empresas_nuestras: Iterable[str]
# - licitacion.oferentes_participantes: Iterable[obj con .nombre]
# - licitacion.documentos_solicitados: Iterable[obj con .id, .nombre, .codigo]
# - licitacion.fallas_fase_a: List[dict{participante_nombre, documento_id, comentario, es_nuestro}]

FONT_BOLD = QFont()
FONT_BOLD.setBold(True)
BRUSH_OUR = QBrush(QColor("#E8F0FE"))  # azul muy claro para nuestras empresas


class DialogoFallasFaseA(QDialog):
    COL_PART_CHECK = 0
    COL_PART_NAME = 1
    COL_PART_TIPO = 2

    COL_DOC_CHECK = 0
    COL_DOC_NAME = 1
    COL_DOC_CODE = 2

    COL_LIST_PART = 0
    COL_LIST_DOC = 1
    COL_LIST_COMM = 2

    # Reemplaza la firma de __init__ por esta (añade open_maximized=False)
    def __init__(self, parent: QWidget, licitacion, db_manager=None, open_maximized: bool = False) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Análisis de Fallas Fase A - {getattr(licitacion, 'numero_proceso', '')}")
        self.setMinimumSize(1200, 700)
        self.setModal(True)

        # Maximizar/minimizar, grip de tamaño
        self.setWindowFlag(Qt.WindowType.WindowSystemMenuHint, True)
        self.setWindowFlag(Qt.WindowType.WindowMinimizeButtonHint, True)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)
        self.setSizeGripEnabled(True)

        self.licitacion = licitacion
        self.db = db_manager  # DatabaseAdapter recomendado

        self._ui_busy = False  # evita loops por señales

        # caches
        self._docname_by_id: Dict[int, str] = {}
        self._docid_by_name: Dict[str, int] = {}

        # flag preferencia para abrir maximizado (puede forzar si no hay estado guardado)
        self._open_maximized_pref = bool(open_maximized)

        self._build_ui()

        # 1) Restaurar estado UI (geometry / splitters / maximizado) antes de poblar datos
        self._restore_ui_state()

        # 2) Cargar SIEMPRE desde BD si hay adaptador; si no, usar memoria (legacy)
        self._load_fallas_from_db_first()

        # 3) Poblar paneles
        self._load_participants()
        self._load_documents()

        # 4) Refrescar lado derecho tras primer ciclo de eventos
        QTimer.singleShot(0, self._post_init_refresh)

    # ------------------- Helpers de datos/DB -------------------
    def _find_db_method(self, names: List[str]):
        if not self.db:
            return None
        for n in names:
            fn = getattr(self.db, n, None)
            if callable(fn):
                print(f"[DEBUG][FallasA] Método DB encontrado: {type(self.db).__name__}.{n}")
                return fn
        return None

    def _normalize_falla_row(self, row: Any) -> Optional[Dict[str, Any]]:
        """
        Acepta dicts u objetos y devuelve:
        { 'licitacion_id': int, 'participante_nombre': str, 'documento_id': int, 'comentario': str, 'es_nuestro': bool }
        """
        try:
            if isinstance(row, dict):
                lic_id = int(row.get("licitacion_id") or row.get("licitacionId") or row.get("id_licitacion") or 0)
                part = str(row.get("participante_nombre") or row.get("participante") or row.get("oferente") or "")
                doc_id = int(row.get("documento_id") or row.get("doc_id") or row.get("documentoId") or -1)
                comm = str(row.get("comentario") or row.get("nota") or "")
                our = bool(row.get("es_nuestro")) if "es_nuestro" in row else (part.startswith("➡️ "))
            else:
                lic_id = int(getattr(row, "licitacion_id", 0))
                part = str(getattr(row, "participante_nombre", "") or getattr(row, "participante", "") or getattr(row, "oferente", ""))
                doc_id = int(getattr(row, "documento_id", -1) or getattr(row, "doc_id", -1))
                comm = str(getattr(row, "comentario", "") or getattr(row, "nota", ""))
                our = bool(getattr(row, "es_nuestro", part.startswith("➡️ ")))
            if not part:
                return None
            return {
                "licitacion_id": lic_id,
                "participante_nombre": part.replace("➡️ ", ""),  # normalizar
                "documento_id": doc_id,
                "comentario": comm,
                "es_nuestro": our,
            }
        except Exception as e:
            print(f"[WARN][FallasA] No se pudo normalizar fila de falla: {e}")
            return None

    def _ensure_fallas_loaded_from_db_like_legacy(self) -> None:
        """
        Igual que la ventana antigua: usar primero self.licitacion.fallas_fase_a.
        Si está vacío, intentar cargar desde la BD:
          1) Métodos dedicados (si existen): get_fallas_fase_a / load_fallas_fase_a / ...
          2) Caer a get_all_data() y tomar 'fallas_fase_a' del registro de la licitación (como en tu smoketest).
        """
        lic_id = getattr(self.licitacion, "id", None)
        fallas_mem = list(getattr(self.licitacion, "fallas_fase_a", []) or [])
        if fallas_mem:
            # Ya viene cargado (comportamiento antiguo)
            print(f"[DEBUG][FallasA] Fallas en memoria: {len(fallas_mem)}")
            return
        if not lic_id or not self.db:
            return

        # 1) Métodos dedicados si existen
        fn = self._find_db_method([
            "get_fallas_fase_a",
            "load_fallas_fase_a",
            "fetch_fallas_fase_a",
            "read_fallas_fase_a",
            "select_fallas_fase_a",
        ])
        if fn:
            try:
                rows = fn(lic_id) or []
                normalizadas: List[Dict[str, Any]] = []
                for r in rows:
                    n = self._normalize_falla_row(r)
                    if n:
                        normalizadas.append(n)
                if normalizadas:
                    self.licitacion.fallas_fase_a = normalizadas
                    print(f"[DEBUG][FallasA] Fallas cargadas (método dedicado): {len(normalizadas)}")
                    return
            except Exception as e:
                print(f"[WARN][FallasA] Lectura de fallas (método dedicado) falló: {e}")

        # 2) Fallback por get_all_data() (igual que tu prueba _test_fallas_fase_a)
        try:
            all_data = self.db.get_all_data()
            lic_list = all_data[0] if isinstance(all_data, (list, tuple)) and len(all_data) > 0 else []
            if isinstance(lic_list, list):
                lic_row = next((l for l in lic_list if isinstance(l, dict) and l.get('id') == lic_id), None)
                if lic_row and isinstance(lic_row.get('fallas_fase_a'), list):
                    # Normalizar por si viniera con otros nombres
                    normalizadas = []
                    for r in lic_row['fallas_fase_a']:
                        if isinstance(r, dict):
                            normalizadas.append({
                                "licitacion_id": int(r.get("licitacion_id", lic_id)),
                                "participante_nombre": str(r.get("participante_nombre") or r.get("participante") or "").replace("➡️ ", ""),
                                "documento_id": int(r.get("documento_id") or r.get("doc_id") or -1),
                                "comentario": str(r.get("comentario") or r.get("nota") or ""),
                                "es_nuestro": bool(r.get("es_nuestro", False)),
                            })
                    self.licitacion.fallas_fase_a = normalizadas
                    print(f"[DEBUG][FallasA] Fallas cargadas desde get_all_data(): {len(normalizadas)}")
        except Exception as e:
            print(f"[WARN][FallasA] get_all_data() no disponible o falló: {e}")

# Añade estas utilidades bajo el bloque "Helpers de datos/DB"

    def _db_has(self, name: str) -> bool:
        return bool(self.db) and callable(getattr(self.db, name, None))

    def _load_fallas_from_db_first(self) -> None:
        """
        Preferir BD: carga descalificaciones desde 'descalificaciones_fase_a' usando el adaptador.
        Si no hay adaptador o falla, conserva las de memoria (comportamiento legacy).
        """
        try:
            lic_id = int(getattr(self.licitacion, "id", 0) or 0)
        except Exception:
            lic_id = 0
        if not lic_id:
            return

        if self._db_has("get_fallas_fase_a"):
            try:
                rows = self.db.get_fallas_fase_a(lic_id)  # List[dict]
                if isinstance(rows, list):
                    for r in rows:
                        if isinstance(r, dict) and "participante_nombre" in r:
                            r["participante_nombre"] = (r["participante_nombre"] or "").replace("➡️ ", "")
                    self.licitacion.fallas_fase_a = rows
                    print(f"[DEBUG][FallasA] Cargadas {len(rows)} fallas desde BD (descalificaciones_fase_a).")
                    return
            except Exception as e:
                print(f"[WARN][FallasA] get_fallas_fase_a falló: {e}")

        # Fallback: mantener lo que haya en memoria
        fallas_mem = list(getattr(self.licitacion, "fallas_fase_a", []) or [])
        print(f"[DEBUG][FallasA] Usando fallas en memoria (fallback): {len(fallas_mem)}")


    # ------------------- UI -------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        # Splitter principal (ahora como atributos para poder persistir/restaurar tamaños)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setOpaqueResize(True)
        self.splitter.setHandleWidth(8)
        root.addWidget(self.splitter, 1)

        # Izquierda: Splitter vertical con Participantes y Documentos (SOLO UNA VEZ)
        self.left = QSplitter(Qt.Orientation.Vertical)
        self.left.setChildrenCollapsible(False)
        self.left.setOpaqueResize(True)
        self.left.setHandleWidth(6)
        self.splitter.addWidget(self.left)

        # 1) Participantes
        grp_part = QGroupBox("1. Seleccione Participante(s)")
        v1 = QVBoxLayout(grp_part)

        row = QHBoxLayout()
        row.addWidget(QLabel("Buscar:"))
        self.part_search = QLineEdit()
        self.part_search.setPlaceholderText("Escriba para filtrar participantes...")
        self.part_search.textChanged.connect(self._filter_participants)
        row.addWidget(self.part_search, 1)

        btn_sel_all = QPushButton("Seleccionar todo")
        btn_sel_none = QPushButton("Ninguno")
        btn_sel_all.clicked.connect(lambda: self._toggle_all_participants(True))
        btn_sel_none.clicked.connect(lambda: self._toggle_all_participants(False))
        row.addWidget(btn_sel_all)
        row.addWidget(btn_sel_none)
        v1.addLayout(row)

        self.tbl_part = QTableWidget(grp_part)
        self.tbl_part.setColumnCount(3)
        self.tbl_part.setHorizontalHeaderLabels(["Sel.", "Nombre", "Tipo"])
        self.tbl_part.verticalHeader().setVisible(False)
        self.tbl_part.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_part.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.tbl_part.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_part.horizontalHeader().setSectionResizeMode(self.COL_PART_NAME, QHeaderView.ResizeMode.Stretch)
        self.tbl_part.horizontalHeader().setSectionResizeMode(self.COL_PART_TIPO, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_part.setAlternatingRowColors(True)
        self.tbl_part.itemChanged.connect(self._on_part_item_changed)
        v1.addWidget(self.tbl_part, 1)

        self.left.addWidget(grp_part)

        # 2) Documentos
        grp_doc = QGroupBox("2. Marque Documento(s) con Fallas")
        v2 = QVBoxLayout(grp_doc)

        rowd = QHBoxLayout()
        self.doc_filter = QLineEdit()
        self.doc_filter.setPlaceholderText("Filtrar por nombre o código...")
        self.doc_filter.textChanged.connect(self._filter_documents)
        rowd.addWidget(self.doc_filter, 1)
        btn_doc_all = QPushButton("Todos")
        btn_doc_none = QPushButton("Ninguno")
        btn_doc_all.clicked.connect(lambda: self._toggle_all_documents(True))
        btn_doc_none.clicked.connect(lambda: self._toggle_all_documents(False))
        rowd.addWidget(btn_doc_all)
        rowd.addWidget(btn_doc_none)
        v2.addLayout(rowd)

        self.tbl_docs = QTableWidget(grp_doc)
        self.tbl_docs.setColumnCount(3)
        self.tbl_docs.setHorizontalHeaderLabels(["Sel.", "Nombre del Documento", "Código"])
        self.tbl_docs.verticalHeader().setVisible(False)
        self.tbl_docs.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_docs.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.tbl_docs.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_docs.horizontalHeader().setSectionResizeMode(self.COL_DOC_NAME, QHeaderView.ResizeMode.Stretch)
        self.tbl_docs.horizontalHeader().setSectionResizeMode(self.COL_DOC_CODE, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_docs.setAlternatingRowColors(True)
        self.tbl_docs.itemChanged.connect(self._on_doc_item_changed)
        v2.addWidget(self.tbl_docs, 1)

        self.left.addWidget(grp_doc)

        # Proporción vertical del panel izquierdo (similar a la ventana antigua)
        self.left.setStretchFactor(0, 1)
        self.left.setStretchFactor(1, 1)

        # Derecha: Comentario, botón añadir y lista
        right = QWidget()
        vright = QVBoxLayout(right)

        grp_comment = QGroupBox("3. Comentario (Opcional) y Añadir a la Lista")
        vc = QVBoxLayout(grp_comment)
        self.txt_comment = QLineEdit()
        self.txt_comment.setPlaceholderText("Escriba un comentario opcional para las fallas seleccionadas…")
        vc.addWidget(self.txt_comment)

        self.btn_add = QPushButton("Añadir Falla(s) a la Lista")
        try:
            self.btn_add.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown))
        except Exception:
            pass
        self.btn_add.clicked.connect(self._add_fallas)
        vc.addWidget(self.btn_add)
        vright.addWidget(grp_comment)

        grp_list = QGroupBox("Fallas a Registrar (Lista Temporal)")
        vl = QVBoxLayout(grp_list)

        actions = QHBoxLayout()
        self.btn_delete = QPushButton("Eliminar seleccionadas")
        try:
            self.btn_delete.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        except Exception:
            pass
        self.btn_delete.clicked.connect(self._delete_selected)

        self.btn_edit = QPushButton("Editar comentario…")
        try:
            self.btn_edit.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView))
        except Exception:
            pass
        self.btn_edit.clicked.connect(self._edit_comment_selected)

        actions.addWidget(self.btn_delete)
        actions.addWidget(self.btn_edit)
        actions.addStretch(1)
        vl.addLayout(actions)

        self.tbl_list = QTableWidget(grp_list)
        self.tbl_list.setColumnCount(3)
        self.tbl_list.setHorizontalHeaderLabels(["Participante", "Documento Fallido", "Comentario"])
        self.tbl_list.verticalHeader().setVisible(False)
        self.tbl_list.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tbl_list.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_list.horizontalHeader().setSectionResizeMode(self.COL_LIST_PART, QHeaderView.ResizeMode.Stretch)
        self.tbl_list.horizontalHeader().setSectionResizeMode(self.COL_LIST_DOC, QHeaderView.ResizeMode.Stretch)
        self.tbl_list.horizontalHeader().setSectionResizeMode(self.COL_LIST_COMM, QHeaderView.ResizeMode.Stretch)
        self.tbl_list.setAlternatingRowColors(True)
        vl.addWidget(self.tbl_list, 1)

        self.tbl_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tbl_list.customContextMenuRequested.connect(self._open_context_menu)

        vright.addWidget(grp_list, 1)
        # Dar más espacio a la lista que al comentario
        try:
            vright.setStretch(0, 1)
            vright.setStretch(1, 4)
        except Exception:
            pass

        self.splitter.addWidget(right)

        # Proporciones iniciales
        try:
            self.splitter.setStretchFactor(0, 3)
            self.splitter.setStretchFactor(1, 4)
            self.splitter.setSizes([600, 700])
            self.left.setSizes([320, 360])
        except Exception:
            pass

        footer = QHBoxLayout()
        footer.addStretch(1)
        btn_close = QPushButton("Aceptar y Cerrar")
        try:
            btn_close.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        except Exception:
            pass
        btn_close.clicked.connect(self.accept)
        footer.addWidget(btn_close)
        root.addLayout(footer)

    def _post_init_refresh(self) -> None:
        if not self.isVisible():
            return
        self._refresh_list_table()
        self._update_add_button()

    # ------------------- Datos y población -------------------
    def _our_names(self) -> Set[str]:
        try:
            return {str(e).strip() for e in getattr(self.licitacion, "empresas_nuestras", []) if str(e).strip()}
        except Exception:
            return set()

    def _load_participants(self) -> None:
        self._ui_busy = True
        self.tbl_part.setRowCount(0)
        nuestras = self._our_names()
        nombres: Set[str] = set()

        for n in nuestras:
            if not n:
                continue
            nombres.add(n)
            self._append_participant_row(n, "Nuestra", is_our=True)

        for of in getattr(self.licitacion, "oferentes_participantes", []):
            nombre = getattr(of, "nombre", "") or ""
            if not nombre.strip():
                continue
            if nombre in nombres:
                continue
            nombres.add(nombre)
            self._append_participant_row(nombre, "Competidor", is_our=False)

        self._ui_busy = False

    def _append_participant_row(self, nombre: str, tipo: str, is_our: bool) -> None:
        row = self.tbl_part.rowCount()
        self.tbl_part.insertRow(row)

        it_check = QTableWidgetItem("")
        it_check.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        it_check.setCheckState(Qt.CheckState.Unchecked)
        self.tbl_part.setItem(row, self.COL_PART_CHECK, it_check)

        it_name = QTableWidgetItem(nombre)
        it_name.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        if is_our:
            it_name.setBackground(BRUSH_OUR)
            it_name.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
        else:
            it_name.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        self.tbl_part.setItem(row, self.COL_PART_NAME, it_name)

        it_tipo = QTableWidgetItem(tipo)
        it_tipo.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        it_tipo.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        self.tbl_part.setItem(row, self.COL_PART_TIPO, it_tipo)

    def _load_documents(self) -> None:
        self._ui_busy = True
        self.tbl_docs.setRowCount(0)
        docs = sorted(
            [d for d in getattr(self.licitacion, "documentos_solicitados", []) if getattr(d, "id", None)],
            key=lambda d: (getattr(d, "codigo", "") or "", getattr(d, "nombre", "") or "")
        )
        self._docname_by_id = {int(d.id): (d.nombre or f"Doc {d.id}") for d in docs}
        self._docid_by_name = {v: k for k, v in self._docname_by_id.items()}

        for d in docs:
            row = self.tbl_docs.rowCount()
            self.tbl_docs.insertRow(row)

            it_check = QTableWidgetItem("")
            it_check.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            it_check.setCheckState(Qt.CheckState.Unchecked)
            self.tbl_docs.setItem(row, self.COL_DOC_CHECK, it_check)

            it_name = QTableWidgetItem(d.nombre or "")
            it_name.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.tbl_docs.setItem(row, self.COL_DOC_NAME, it_name)

            it_code = QTableWidgetItem(d.codigo or "")
            it_code.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_code.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.tbl_docs.setItem(row, self.COL_DOC_CODE, it_code)
        self._ui_busy = False

    # ------------------- Filtros y toggles -------------------
    def _filter_participants(self, text: str) -> None:
        text = (text or "").strip().lower()
        for r in range(self.tbl_part.rowCount()):
            name = (self.tbl_part.item(r, self.COL_PART_NAME).text() or "").lower()
            self.tbl_part.setRowHidden(r, text not in name)

    def _filter_documents(self, text: str) -> None:
        text = (text or "").strip().lower()
        for r in range(self.tbl_docs.rowCount()):
            name = (self.tbl_docs.item(r, self.COL_DOC_NAME).text() or "").lower()
            code = (self.tbl_docs.item(r, self.COL_DOC_CODE).text() or "").lower()
            self.tbl_docs.setRowHidden(r, (text not in name) and (text not in code))

    def _toggle_all_participants(self, state: bool) -> None:
        self._ui_busy = True
        for r in range(self.tbl_part.rowCount()):
            it = self.tbl_part.item(r, self.COL_PART_CHECK)
            it.setCheckState(Qt.CheckState.Checked if state else Qt.CheckState.Unchecked)
        self._ui_busy = False
        self._update_add_button()

    def _toggle_all_documents(self, state: bool) -> None:
        self._ui_busy = True
        for r in range(self.tbl_docs.rowCount()):
            it = self.tbl_docs.item(r, self.COL_DOC_CHECK)
            it.setCheckState(Qt.CheckState.Checked if state else Qt.CheckState.Unchecked)
        self._ui_busy = False
        self._update_add_button()

    def _on_part_item_changed(self, item: QTableWidgetItem) -> None:
        if self._ui_busy:
            return
        if item.column() != self.COL_PART_CHECK:
            return
        self._update_add_button()

    def _on_doc_item_changed(self, item: QTableWidgetItem) -> None:
        if self._ui_busy:
            return
        if item.column() != self.COL_DOC_CHECK:
            return
        self._update_add_button()

    # ------------------- Acciones principales -------------------
    def _selected_participants(self) -> List[str]:
        res = []
        for r in range(self.tbl_part.rowCount()):
            if self.tbl_part.item(r, self.COL_PART_CHECK).checkState() == Qt.CheckState.Checked:
                res.append(self.tbl_part.item(r, self.COL_PART_NAME).text())
        return res

    def _selected_document_ids(self) -> List[int]:
        res: List[int] = []
        for r in range(self.tbl_docs.rowCount()):
            if self.tbl_docs.item(r, self.COL_DOC_CHECK).checkState() == Qt.CheckState.Checked:
                name = self.tbl_docs.item(r, self.COL_DOC_NAME).text()
                doc_id = self._docid_by_name.get(name)
                if doc_id is not None:
                    res.append(int(doc_id))
        return res

    def _update_add_button(self) -> None:
        p = len(self._selected_participants())
        d = len(self._selected_document_ids())
        self.btn_add.setEnabled(p > 0 and d > 0)
        self.btn_add.setText(f"Añadir Falla(s) a la Lista  •  {p} × {d}")

    def _add_fallas(self) -> None:
        participantes = self._selected_participants()
        doc_ids = self._selected_document_ids()
        comentario = self.txt_comment.text().strip()

        if not participantes or not doc_ids:
            QMessageBox.warning(self, "Datos Faltantes", "Debe seleccionar al menos un participante y un documento.")
            return

        nuestras = self._our_names()
        lic_id = int(getattr(self.licitacion, "id", 0) or 0)
        existentes = getattr(self.licitacion, "fallas_fase_a", [])
        added_mem = 0
        added_db = 0

        for part in participantes:
            es_nuestro = part in nuestras
            for doc_id in doc_ids:
                ya_esta = any(
                    (f.get("participante_nombre") == part and int(f.get("documento_id", -1)) == int(doc_id))
                    for f in existentes
                )
                if ya_esta:
                    continue

                # 1) BD preferida (insertar por IDs si existe el método)
                inserted = False
                if self._db_has("insertar_falla_por_ids"):
                    try:
                        new_id = self.db.insertar_falla_por_ids(licitacion_id=lic_id,
                                                                participante_nombre=part,
                                                                documento_id=int(doc_id),
                                                                es_nuestro=es_nuestro,
                                                                comentario=comentario)
                        if new_id is not None:
                            inserted = True
                            added_db += 1
                    except Exception as e:
                        print(f"[WARN][FallasA] insertar_falla_por_ids falló: {e}")

                # 2) Fallback: agregar a memoria y persistir con save_licitacion si está disponible
                if not inserted:
                    try:
                        existentes.append({
                            "licitacion_id": lic_id,
                            "participante_nombre": part,
                            "documento_id": int(doc_id),
                            "comentario": comentario,
                            "es_nuestro": es_nuestro
                        })
                        added_mem += 1
                    except Exception:
                        pass

        # Si se insertó al menos una en BD, recargar desde BD para mantener IDs y estado
        if added_db > 0 and self._db_has("get_fallas_fase_a"):
            try:
                self.licitacion.fallas_fase_a = self.db.get_fallas_fase_a(lic_id)
            except Exception:
                pass

        # Si solo agregamos a memoria, intenta persistir toda la licitación
        if added_db == 0 and added_mem > 0 and self._db_has("save_licitacion"):
            try:
                self.db.save_licitacion(self.licitacion)
            except Exception as e:
                print(f"[WARN][FallasA] save_licitacion falló al intentar persistir fallas en memoria: {e}")

        self.txt_comment.clear()
        self._toggle_all_documents(False)
        self._refresh_list_table()
        if (added_db + added_mem) > 0:
            QMessageBox.information(self, "Fallas añadidas",
                                    f"Se añadieron {added_db + added_mem} registro(s){' (BD)' if added_db else ''}.")
        else:
            QMessageBox.information(self, "Información", "Las fallas seleccionadas ya existían.")

    def _refresh_list_table(self) -> None:
        if not hasattr(self, "tbl_list") or self.tbl_list is None:
            return

        try:
            self.tbl_list.blockSignals(True)
            self.tbl_list.setRowCount(0)
        except RuntimeError:
            return

        self._docname_by_id = {
            int(d.id): (d.nombre or f"Doc {d.id}")
            for d in getattr(self.licitacion, "documentos_solicitados", [])
            if getattr(d, "id", None)
        }
        self._docid_by_name = {v: k for k, v in self._docname_by_id.items()}

        for f in getattr(self.licitacion, "fallas_fase_a", []):
            part = (f.get("participante_nombre") or "").replace("➡️ ", "")
            doc_id = int(f.get("documento_id") or 0)
            comm = f.get("comentario", "") or ""
            doc_name = self._docname_by_id.get(doc_id, f"ID {doc_id}")

            row = self.tbl_list.rowCount()
            self.tbl_list.insertRow(row)
            self.tbl_list.setItem(row, self.COL_LIST_PART, QTableWidgetItem(part))
            self.tbl_list.setItem(row, self.COL_LIST_DOC, QTableWidgetItem(doc_name))
            self.tbl_list.setItem(row, self.COL_LIST_COMM, QTableWidgetItem(comm))

        try:
            self.tbl_list.blockSignals(False)
        except RuntimeError:
            pass

    def _open_context_menu(self, pos: QPoint) -> None:
        menu = QMenu(self)
        act_edit = menu.addAction(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView), "Editar comentario…")
        act_del = menu.addAction(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon), "Eliminar seleccionadas")
        act = menu.exec(self.tbl_list.mapToGlobal(pos))
        if act == act_edit:
            self._edit_comment_selected()
        elif act == act_del:
            self._delete_selected()

# Reemplaza _delete_selected para preferir borrado por IDs y recargar desde BD

    def _delete_selected(self) -> None:
        rows = sorted({idx.row() for idx in self.tbl_list.selectionModel().selectedRows()}, reverse=True)
        if not rows:
            QMessageBox.information(self, "Eliminar", "Seleccione una o más filas de la lista temporal.")
            return
        if QMessageBox.question(self, "Confirmar", f"¿Eliminar {len(rows)} fila(s)?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return

        lic_id = int(getattr(self.licitacion, "id", 0) or 0)
        exist = list(getattr(self.licitacion, "fallas_fase_a", []))

        deleted_db = 0
        # Intento por IDs (recomendado)
        if self._db_has("eliminar_fallas_por_ids") or self._db_has("eliminar_falla_por_ids"):
            items: list[tuple[str, int]] = []
            for r in rows:
                part = self.tbl_list.item(r, self.COL_LIST_PART).text()
                doc_name = self.tbl_list.item(r, self.COL_LIST_DOC).text()
                doc_id = self._docid_by_name.get(doc_name)
                if doc_id is not None:
                    items.append((part, int(doc_id)))

            if items:
                try:
                    if self._db_has("eliminar_fallas_por_ids"):
                        deleted_db = int(self.db.eliminar_fallas_por_ids(lic_id, items) or 0)
                    else:
                        # iterativo por si no hay bulk
                        for part, did in items:
                            deleted_db += int(self.db.eliminar_falla_por_ids(lic_id, part, did) or 0)
                except Exception as e:
                    print(f"[WARN][FallasA] eliminar_falla(s)_por_ids falló: {e}")

        # Fallback: por nombres (si no se pudo por IDs)
        if deleted_db == 0 and self._db_has("eliminar_falla_por_campos"):
            institucion = getattr(self.licitacion, "institucion", "") or ""
            for r in rows:
                part = self.tbl_list.item(r, self.COL_LIST_PART).text()
                doc_name = self.tbl_list.item(r, self.COL_LIST_DOC).text()
                try:
                    deleted_db += int(self.db.eliminar_falla_por_campos(institucion, part, doc_name) or 0)
                except Exception as e:
                    print(f"[WARN][FallasA] eliminar_falla_por_campos falló: {e}")

        # Actualizar memoria
        for r in rows:
            part = self.tbl_list.item(r, self.COL_LIST_PART).text()
            doc_name = self.tbl_list.item(r, self.COL_LIST_DOC).text()
            doc_id = self._docid_by_name.get(doc_name)
            if doc_id is None:
                continue
            exist = [f for f in exist if not (f.get("participante_nombre") == part and int(f.get("documento_id", -1)) == int(doc_id))]
        self.licitacion.fallas_fase_a = exist

        # Si eliminamos en BD, recargar desde BD para asegurar consistencia
        if deleted_db > 0 and self._db_has("get_fallas_fase_a"):
            try:
                self.licitacion.fallas_fase_a = self.db.get_fallas_fase_a(lic_id)
            except Exception:
                pass
        elif deleted_db == 0 and self._db_has("save_licitacion"):
            # Fallback: persistir todo
            try:
                self.db.save_licitacion(self.licitacion)
            except Exception as e:
                print(f"[WARN][FallasA] save_licitacion (fallback delete) falló: {e}")

        self._refresh_list_table()
        QMessageBox.information(self, "Eliminar", "Falla(s) eliminada(s).")


    def _edit_comment_selected(self) -> None:
        rows = {idx.row() for idx in self.tbl_list.selectionModel().selectedRows()}
        if not rows:
            QMessageBox.information(self, "Editar comentario", "Seleccione una o más filas de la lista temporal.")
            return
        texto, ok = self._prompt_text("Nuevo comentario", f"Ingrese el comentario para {len(rows)} fila(s):")
        if not ok or not texto.strip():
            return
        nuevo = texto.strip()

        lic_id = int(getattr(self.licitacion, "id", 0) or 0)
        exist = getattr(self.licitacion, "fallas_fase_a", [])

        updated_db = 0
        # Intento por IDs (preferido)
        if self._db_has("actualizar_comentarios_por_ids") or self._db_has("actualizar_comentario_falla_por_ids"):
            items_bulk: list[tuple[int, str, str]] = []  # (documento_id, comentario, participante)
            for r in rows:
                part = self.tbl_list.item(r, self.COL_LIST_PART).text()
                doc_name = self.tbl_list.item(r, self.COL_LIST_DOC).text()
                doc_id = self._docid_by_name.get(doc_name)
                if doc_id is not None:
                    items_bulk.append((int(doc_id), nuevo, part))
            try:
                if items_bulk:
                    if self._db_has("actualizar_comentarios_por_ids"):
                        updated_db = int(self.db.actualizar_comentarios_por_ids(lic_id, items_bulk) or 0)
                    else:
                        for did, comentario, part in items_bulk:
                            updated_db += int(self.db.actualizar_comentario_falla_por_ids(lic_id, did, part, comentario) or 0)
            except Exception as e:
                print(f"[WARN][FallasA] actualizar_comentario(s)_por_ids falló: {e}")

        # Fallback por nombres
        if updated_db == 0 and self._db_has("actualizar_comentario_falla"):
            institucion = getattr(self.licitacion, "institucion", "") or ""
            for r in rows:
                part = self.tbl_list.item(r, self.COL_LIST_PART).text()
                doc_name = self.tbl_list.item(r, self.COL_LIST_DOC).text()
                try:
                    updated_db += int(self.db.actualizar_comentario_falla(institucion, part, doc_name, nuevo) or 0)
                except Exception as e:
                    print(f"[WARN][FallasA] actualizar_comentario_falla (por nombres) falló: {e}")

        # Actualizar en memoria
        for r in rows:
            part = self.tbl_list.item(r, self.COL_LIST_PART).text()
            doc_name = self.tbl_list.item(r, self.COL_LIST_DOC).text()
            doc_id = self._docid_by_name.get(doc_name)
            if doc_id is None:
                continue
            for f in exist:
                if f.get("participante_nombre") == part and int(f.get("documento_id", -1)) == int(doc_id):
                    f["comentario"] = nuevo
        self.licitacion.fallas_fase_a = exist

        # Recarga desde BD si hubo updates directos
        if updated_db > 0 and self._db_has("get_fallas_fase_a"):
            try:
                self.licitacion.fallas_fase_a = self.db.get_fallas_fase_a(lic_id)
            except Exception:
                pass
        elif updated_db == 0 and self._db_has("save_licitacion"):
            try:
                self.db.save_licitacion(self.licitacion)
            except Exception as e:
                print(f"[WARN][FallasA] save_licitacion (fallback edit) falló: {e}")

        self._refresh_list_table()
        QMessageBox.information(self, "Editar comentario", "Comentario actualizado.")



    def _prompt_text(self, title: str, msg: str) -> tuple[str, bool]:
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QDialogButtonBox
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        lay = QVBoxLayout(dlg)
        lay.addWidget(QLabel(msg))
        edit = QLineEdit()
        lay.addWidget(edit)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        lay.addWidget(btns)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        ok = dlg.exec() == QDialog.DialogCode.Accepted
        return edit.text(), ok
    
    def _settings_key(self, name: str) -> str:
        return f"DialogoFallasFaseA/{name}"

    def _restore_ui_state(self) -> None:
        """
        Restaura geometry + splitter sizes + maximized flag desde QSettings si existen.
        Si no existen, respeta self._open_maximized_pref para abrir maximizado.
        """
        try:
            settings = QSettings("PROGAIN", "GestorLicitaciones")
            # Maximized?
            is_max = settings.value(self._settings_key("isMaximized"), False, type=bool)
            if is_max:
                self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)
                return  # si estaba maximizado no aplicamos geometry
            # Si no estaba maximizado, revisar geometry
            geom = settings.value(self._settings_key("geometry"), None)
            if isinstance(geom, (bytes, bytearray)):
                try:
                    self.restoreGeometry(geom)
                except Exception:
                    pass
            # splitters
            s_main = settings.value(self._settings_key("splitterSizes"), "")
            if s_main:
                try:
                    sizes = [int(x) for x in str(s_main).split(",") if x.strip()]
                    if sizes and hasattr(self, "splitter"):
                        self.splitter.setSizes(sizes)
                except Exception:
                    pass
            s_left = settings.value(self._settings_key("leftSplitterSizes"), "")
            if s_left:
                try:
                    sizes = [int(x) for x in str(s_left).split(",") if x.strip()]
                    if sizes and hasattr(self, "left"):
                        self.left.setSizes(sizes)
                except Exception:
                    pass
            # Si no había nada guardado y el usuario pidió abrir maximizado por preferencia, aplicarlo
            if self._open_maximized_pref and not is_max:
                self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)
        except Exception as e:
            print(f"[WARN][FallasA] _restore_ui_state fallo: {e}")

    def _save_ui_state(self) -> None:
        """
        Guarda geometry + splitter sizes + maximized flag en QSettings.
        """
        try:
            settings = QSettings("PROGAIN", "GestorLicitaciones")
            is_max = bool(self.windowState() & Qt.WindowState.WindowMaximized)
            settings.setValue(self._settings_key("isMaximized"), is_max)
            if not is_max:
                # Guardar geometry sólo si no está maximizado (guardamos tamaño/restauración)
                try:
                    settings.setValue(self._settings_key("geometry"), self.saveGeometry())
                except Exception:
                    pass
            # splitters
            try:
                if hasattr(self, "splitter"):
                    s = ",".join(str(int(x)) for x in (self.splitter.sizes() or []))
                    settings.setValue(self._settings_key("splitterSizes"), s)
                if hasattr(self, "left"):
                    s2 = ",".join(str(int(x)) for x in (self.left.sizes() or []))
                    settings.setValue(self._settings_key("leftSplitterSizes"), s2)
            except Exception:
                pass
        except Exception as e:
            print(f"[WARN][FallasA] _save_ui_state fallo: {e}")

    def closeEvent(self, event):
        try:
            self._save_ui_state()
        except Exception:
            pass
        super().closeEvent(event)