from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter, defaultdict
from datetime import date, datetime

from PyQt6.QtCore import Qt, pyqtSignal, QDate
from PyQt6.QtGui import QKeySequence, QShortcut, QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, QComboBox, QLineEdit,
    QPushButton, QDateEdit, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QGroupBox, QSplitter, QFrame
)

# Matplotlib para Qt (PyQt6)
try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib as mpl
    MATPLOTLIB_AVAILABLE = True
except Exception:
    MATPLOTLIB_AVAILABLE = False

from app.core.db_adapter import DatabaseAdapter
from app.core.models import Licitacion, Documento
# 1) Sube este import a tu bloque de imports de QtWidgets (donde están QGroupBox, QSplitter, etc.)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, QComboBox, QLineEdit,
    QPushButton, QDateEdit, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QGroupBox, QSplitter, QMenu, QFrame, QInputDialog  # <-- añade QInputDialog
)

class DashboardWidget(QWidget):
    """
    Dashboard embebido (widget) con pestañas:
    - Resumen General (renovado con tarjetas KPI, gráficos y resumen por empresa)
    - Competencia
    - Fallas Fase A
    """
    edit_licitacion_requested = pyqtSignal(int)

    # Columnas Resumen/Tabla licitaciones (si se usa en otras pestañas)
    COL_LIC_ID = 0
    COL_LIC_NUM = 1
    COL_LIC_NOM = 2
    COL_LIC_INST = 3
    COL_LIC_EST = 4
    COL_LIC_FECHA = 5
    COL_LIC_EMP = 6

    # Competidores
    COL_COMP_NOM = 0
    COL_COMP_RNC = 1
    COL_COMP_PART = 2
    COL_COMP_PCT = 3

    # Fallas: tabla izquierda (impacto)
    COL_FDOC_NOM = 0
    COL_FDOC_CNT = 1
    COL_FDOC_PCT = 2

    # Fallas: detalle
    COL_FDET_EMP = 0
    COL_FDET_RNC = 1
    COL_FDET_INST = 2
    COL_FDET_TIPO = 3

    # Resumen por empresa (tabla lateral)
    COL_EMP_NOM = 0
    COL_EMP_PART = 1
    COL_EMP_WIN = 2
    COL_EMP_ADJ = 3

    def __init__(self, db: DatabaseAdapter, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db

        # Estado
        self._all_licitaciones: List[Licitacion] = []
        self._filtered: List[Licitacion] = []
        self._fallas_dataset: List[Tuple] = []
        self._competidores_maestros: List[Dict[str, Any]] = []
        self._empresas_maestras: List[Dict[str, Any]] = []

        # Paleta moderna (Material/Nord-inspired)
        self._col_blue = "#4F46E5"
        self._col_green = "#16A34A"
        self._col_amber = "#F59E0B"
        self._col_red = "#EF4444"
        self._col_text = "#111827"
        self._col_muted = "#6B7280"
        self._col_card = "#FFFFFF"
        self._col_border = "#E5E7EB"
        self._col_bar1 = "#5E81AC"
        self._col_bar2 = "#2E7D32"

        if MATPLOTLIB_AVAILABLE:
            try:
                mpl.rcParams["font.size"] = 10
                mpl.rcParams["axes.titleweight"] = "bold"
                mpl.rcParams["axes.titlesize"] = 12
                mpl.rcParams["axes.labelsize"] = 10
                mpl.rcParams["legend.fontsize"] = 9
                mpl.rcParams["axes.facecolor"] = "white"
                mpl.rcParams["figure.facecolor"] = "white"
                # Tipografía preferida
                mpl.rcParams["font.sans-serif"] = ["Segoe UI", "DejaVu Sans", "Arial"]
            except Exception:
                pass

        # UI raíz
        root = QVBoxLayout(self)
        self._build_filters_bar(root)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        # Tab Resumen General (make over)
        self.tab_resumen = QWidget()
        self.v_resumen = QVBoxLayout(self.tab_resumen)
        self._build_resumen_tab()
        self.tabs.addTab(self.tab_resumen, "📊 Resumen General")

        # Tab Competencia (sin cambios mayores por ahora)
        self.tab_comp = QWidget()
        self.v_comp = QVBoxLayout(self.tab_comp)
        self._build_competencia_tab()
        self.tabs.addTab(self.tab_comp, "🤺 Competencia")

        # Tab Fallas A (sin cambios mayores por ahora)
        self.tab_fallas = QWidget()
        self.v_fallas = QVBoxLayout(self.tab_fallas)
        self._build_fallas_tab()
        self.tabs.addTab(self.tab_fallas, "🔍 Fallas Fase A")

        # Atajos
        QShortcut(QKeySequence("F5"), self, activated=self.reload_data)

        # Cargar datos iniciales
        self.reload_data()

    # ----------------- Barra de filtros -----------------
    def _build_filters_bar(self, parent_layout: QVBoxLayout):
        box = QGroupBox("Filtros del Dashboard")
        box.setStyleSheet(self._card_stylesheet())
        h = QHBoxLayout(box)

        # Institución
        lbl_inst = QLabel("Institución:")
        self.cmb_inst = QComboBox()
        self.cmb_inst.setMinimumWidth(220)
        h.addWidget(lbl_inst)
        h.addWidget(self.cmb_inst)

        # Código
        lbl_code = QLabel("Código Proceso:")
        self.txt_codigo = QLineEdit()
        self.txt_codigo.setPlaceholderText("ITLA-CCC-CP-2025-0001…")
        h.addWidget(lbl_code)
        h.addWidget(self.txt_codigo)

        # Desde / Hasta (se definirán por defecto desde la primera transacción)
        lbl_desde = QLabel("Desde:")
        self.dt_desde = QDateEdit()
        self.dt_desde.setDisplayFormat("yyyy-MM-dd")
        self.dt_desde.setCalendarPopup(True)

        lbl_hasta = QLabel("Hasta:")
        self.dt_hasta = QDateEdit()
        self.dt_hasta.setDisplayFormat("yyyy-MM-dd")
        self.dt_hasta.setCalendarPopup(True)

        h.addWidget(lbl_desde)
        h.addWidget(self.dt_desde)
        h.addWidget(lbl_hasta)
        h.addWidget(self.dt_hasta)

        # Botones
        self.btn_aplicar = QPushButton("🔍 Aplicar")
        self.btn_limpiar = QPushButton("🧹 Limpiar")
        self.btn_refrescar = QPushButton("↻ Refrescar")

        self.btn_aplicar.clicked.connect(self._apply_filters_and_render)
        self.btn_limpiar.clicked.connect(self._clear_filters)
        self.btn_refrescar.clicked.connect(self.reload_data)

        h.addWidget(self.btn_aplicar)
        h.addWidget(self.btn_limpiar)
        h.addWidget(self.btn_refrescar)
        h.addStretch(1)

        parent_layout.addWidget(box)

    # ----------------- Resumen (make over) -----------------
    def _build_resumen_tab(self):
        # Tarjetas KPI en fila
        kpis = QHBoxLayout()
        self.card_tasa = self._kpi_card("Rendimiento (Finalizadas)", "Tasa de Éxito", accent=self._col_blue)
        self.card_lotes = self._kpi_card("Lotes Ganados (Finalizadas)", "Total de Lotes", accent=self._col_green)
        self.card_fin = self._kpi_card_financiero()
        kpis.addWidget(self.card_tasa)
        kpis.addWidget(self.card_lotes)
        kpis.addWidget(self.card_fin)
        self.v_resumen.addLayout(kpis)

        # Splitter principal vertical:
        #   - Arriba: Splitter horizontal con
        #       izquierda: gráfico Rendimiento por Empresa
        #       derecha: Resumen por Empresa (tabla)
        #   - Abajo: Distribución de Estados
        self.split_v = QSplitter(Qt.Orientation.Vertical)
        self.v_resumen.addWidget(self.split_v, 1)

        split_h = QSplitter(Qt.Orientation.Horizontal)
        self.split_v.addWidget(split_h)

        # Gráfico Rendimiento por Empresa
        if MATPLOTLIB_AVAILABLE:
            self.canvas_rend = self._new_canvas()
            self.box_rend = self._wrap_canvas("Rendimiento por Empresa", self.canvas_rend)
        else:
            self.box_rend = self._placeholder_box("Rendimiento por Empresa", "Matplotlib no está disponible.")
        split_h.addWidget(self.box_rend)

        # Resumen por Empresa (tabla)
        self.box_emp = QGroupBox("Resumen por Empresa")
        self.box_emp.setStyleSheet(self._card_stylesheet())
        v_emp = QVBoxLayout(self.box_emp)

        self.tbl_emp = QTableWidget(0, 4)
        self.tbl_emp.setHorizontalHeaderLabels(["Empresa", "Participa", "Ganadas", "Monto Adjudicado"])
        self.tbl_emp.verticalHeader().setVisible(False)
        self.tbl_emp.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_emp.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_emp.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        hh = self.tbl_emp.horizontalHeader()
        hh.setSectionResizeMode(self.COL_EMP_NOM, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(self.COL_EMP_PART, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(self.COL_EMP_WIN, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(self.COL_EMP_ADJ, QHeaderView.ResizeMode.ResizeToContents)
        v_emp.addWidget(self.tbl_emp, 1)

        split_h.addWidget(self.box_emp)
        split_h.setStretchFactor(0, 3)
        split_h.setStretchFactor(1, 2)

        # Gráfico Distribución de Estados
        if MATPLOTLIB_AVAILABLE:
            self.canvas_estados = self._new_canvas()
            self.box_estados = self._wrap_canvas("Distribución de Estados", self.canvas_estados)
        else:
            self.box_estados = self._placeholder_box("Distribución de Estados", "Matplotlib no está disponible.")
        self.split_v.addWidget(self.box_estados)

        self.split_v.setStretchFactor(0, 3)
        self.split_v.setStretchFactor(1, 2)

    # ---- KPI cards ----
    def _kpi_card(self, titulo: str, sub: str, accent: str = "#4F46E5") -> QFrame:
        card = QFrame()
        card.setStyleSheet(self._card_stylesheet())
        lay = QVBoxLayout(card)
        lbl_title = QLabel(titulo)
        lbl_title.setStyleSheet(f"color:{self._col_muted}; font-weight:600;")
        lay.addWidget(lbl_title)

        row = QHBoxLayout()
        lbl_sub = QLabel(sub + ":")
        lbl_sub.setStyleSheet("font-weight:600;")
        self.lbl_val_main = QLabel("0.0%")
        self.lbl_val_main.setStyleSheet(f"color:{accent}; font-size:20px; font-weight:700;")
        row.addWidget(lbl_sub)
        row.addWidget(self.lbl_val_main)
        row.addStretch(1)
        lay.addLayout(row)

        # Totales inline para ganadas/perdidas en esta tarjeta
        self.lbl_gp = QLabel("Ganadas: 0   |   Perdidas: 0")
        self.lbl_gp.setStyleSheet(f"color:{self._col_muted};")
        lay.addWidget(self.lbl_gp)
        return card

    def _kpi_card_financiero(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet(self._card_stylesheet())
        lay = QVBoxLayout(card)
        lbl_title = QLabel("Análisis Financiero")
        lbl_title.setStyleSheet(f"color:{self._col_muted}; font-weight:600;")
        lay.addWidget(lbl_title)

        def row(lbl: str, val: str, accent: Optional[str] = None):
            h = QHBoxLayout()
            l = QLabel(lbl)
            l.setStyleSheet("font-weight:600;")
            v = QLabel(val)
            if accent:
                v.setStyleSheet(f"color:{accent}; font-weight:700;")
            h.addWidget(l)
            h.addStretch(1)
            h.addWidget(v)
            lay.addLayout(h)

        self._fin_base = QLabel("RD$ 0.00")
        self._fin_ofe = QLabel("RD$ 0.00")
        self._fin_adj = QLabel("RD$ 0.00")
        row("Monto Base Total:", "RD$ 0.00")
        row("Monto Ofertado Total:", "RD$ 0.00")
        row("Monto Adjudicado (Nosotros):", "RD$ 0.00", accent=self._col_green)

        # Guardar referencias en el layout (índices 1,2,3)
        # Más fácil: buscar por hijos al actualizar
        return card

    def _card_stylesheet(self) -> str:
        return f"""
        QGroupBox, QFrame {{
            background: {self._col_card};
            border: 1px solid {self._col_border};
            border-radius: 8px;
            padding: 8px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0px 4px 0px 4px;
            color: {self._col_muted};
            font-weight: 600;
        }}
        """

    def _placeholder_box(self, title: str, text: str) -> QGroupBox:
        box = QGroupBox(title)
        box.setStyleSheet(self._card_stylesheet())
        v = QVBoxLayout(box)
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(lbl, 1)
        return box

    # ----------------- Competencia (básico, sin makeover aún) -----------------
    def _build_competencia_tab(self):
        top = QHBoxLayout()
        top.addWidget(QLabel("🔍 Buscar (Nombre o RNC):"))
        self.txt_comp_search = QLineEdit()
        self.txt_comp_search.textChanged.connect(self._filter_competidores_table)
        top.addWidget(self.txt_comp_search, 1)
        self.v_comp.addLayout(top)

        self.tbl_comp = QTableWidget(0, 4)
        self.tbl_comp.setHorizontalHeaderLabels(["Nombre", "RNC", "# Lotes Ofertados", "% Dif. Promedio"])
        self.tbl_comp.verticalHeader().setVisible(False)
        self.tbl_comp.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_comp.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_comp.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        hh = self.tbl_comp.horizontalHeader()
        hh.setSectionResizeMode(self.COL_COMP_NOM, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(self.COL_COMP_RNC, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(self.COL_COMP_PART, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(self.COL_COMP_PCT, QHeaderView.ResizeMode.ResizeToContents)
        self.v_comp.addWidget(self.tbl_comp, 1)

    # ----------------- Fallas Fase A (básico, sin makeover aún) -----------------
    def _build_fallas_tab(self):
        # Filtros por institución
        filt = QHBoxLayout()
        filt.addWidget(QLabel("Institución:"))
        self.cmb_fallas_inst = QComboBox()
        self.cmb_fallas_inst.currentIndexChanged.connect(self._render_fallas_tab)
        filt.addWidget(self.cmb_fallas_inst, 1)
        self.v_fallas.addLayout(filt)

        # Split: izquierda (impacto + detalle) | derecha (gráfico)
        self.split_fallas = QSplitter(Qt.Orientation.Horizontal)
        self.v_fallas.addWidget(self.split_fallas, 1)

        left = QSplitter(Qt.Orientation.Vertical)
        self.split_fallas.addWidget(left)

        # Impacto por documento
        box_impacto = QGroupBox("Análisis de Impacto por Documento")
        box_impacto.setStyleSheet(self._card_stylesheet())
        vb1 = QVBoxLayout(box_impacto)
        self.tbl_fdoc = QTableWidget(0, 3)
        self.tbl_fdoc.setHorizontalHeaderLabels(["Documento", "N° Fallas", "% del Total"])
        self.tbl_fdoc.verticalHeader().setVisible(False)
        self.tbl_fdoc.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_fdoc.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_fdoc.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        hh = self.tbl_fdoc.horizontalHeader()
        hh.setSectionResizeMode(self.COL_FDOC_NOM, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(self.COL_FDOC_CNT, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(self.COL_FDOC_PCT, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_fdoc.itemSelectionChanged.connect(self._render_fallas_detalle)
        vb1.addWidget(self.tbl_fdoc, 1)
        left.addWidget(box_impacto)

        # Detalle por empresa
        box_det = QGroupBox("Detalle de Fallas por Empresa")
        box_det.setStyleSheet(self._card_stylesheet())
        vb2 = QVBoxLayout(box_det)

        actions = QHBoxLayout()
        self.btn_fdel = QPushButton("🗑 Eliminar seleccionadas")
        self.btn_fedit = QPushButton("✏️ Editar comentario…")
        self.btn_fdel.clicked.connect(self._delete_fallas_selected)
        self.btn_fedit.clicked.connect(self._edit_fallas_comment)
        actions.addWidget(self.btn_fdel)
        actions.addWidget(self.btn_fedit)
        actions.addStretch(1)
        vb2.addLayout(actions)

        self.tbl_fdet = QTableWidget(0, 4)
        self.tbl_fdet.setHorizontalHeaderLabels(["Empresa", "RNC", "Institución", "Tipo"])
        self.tbl_fdet.verticalHeader().setVisible(False)
        self.tbl_fdet.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_fdet.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_fdet.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        hh = self.tbl_fdet.horizontalHeader()
        hh.setSectionResizeMode(self.COL_FDET_EMP, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(self.COL_FDET_RNC, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(self.COL_FDET_INST, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(self.COL_FDET_TIPO, QHeaderView.ResizeMode.ResizeToContents)
        vb2.addWidget(self.tbl_fdet, 1)
        left.addWidget(box_det)

        # Gráfico
        if MATPLOTLIB_AVAILABLE:
            self.canvas_fallas = self._new_canvas()
            self.split_fallas.addWidget(self._wrap_canvas("Top 10 Documentos con Más Fallas", self.canvas_fallas))
        else:
            lbl = QLabel("Matplotlib no está disponible.")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.split_fallas.addWidget(lbl)

        self.split_fallas.setStretchFactor(0, 3)
        self.split_fallas.setStretchFactor(1, 2)

    # ----------------- Helpers gráficos -----------------
    def _new_canvas(self) -> FigureCanvas:
        fig = Figure(figsize=(5.8, 3.2), dpi=100, facecolor="white")
        return FigureCanvas(fig)

    def _wrap_canvas(self, title: str, canvas: FigureCanvas) -> QGroupBox:
        box = QGroupBox(title)
        box.setStyleSheet(self._card_stylesheet())
        v = QVBoxLayout(box)
        v.addWidget(canvas, 1)
        return box

    # ----------------- Datos -----------------
    def reload_data(self):
        """Carga datos desde la BD, fija rangos de fecha (desde la primera transacción) y repuebla UI."""
        try:
            self._all_licitaciones = self.db.load_all_licitaciones() or []
        except Exception as e:
            self._all_licitaciones = []
            QMessageBox.warning(self, "Datos", f"No se pudieron cargar licitaciones:\n{e}")

        # Catálogos auxiliares
        try:
            self._competidores_maestros = self.db.get_competidores_maestros() or []
        except Exception:
            self._competidores_maestros = []

        try:
            self._empresas_maestras = self.db.get_empresas_maestras() or []
        except Exception:
            self._empresas_maestras = []

        # Instituciones (siempre “Todas” + lista)
        insts = sorted({(getattr(b, "institucion", "") or "") for b in self._all_licitaciones if getattr(b, "institucion", "")})
        self.cmb_inst.blockSignals(True)
        self.cmb_inst.clear()
        self.cmb_inst.addItem("Todas")
        self.cmb_inst.addItems(insts)
        self.cmb_inst.blockSignals(False)

        # Fijar rango de fechas por defecto: desde primera transacción a última
        min_d, max_d = self._min_max_dates(self._all_licitaciones)
        if min_d and max_d:
            self.dt_desde.setDate(QDate(min_d.year, min_d.month, min_d.day))
            self.dt_hasta.setDate(QDate(max_d.year, max_d.month, max_d.day))
        else:
            # fallback: hoy
            today = date.today()
            self.dt_desde.setDate(QDate(today.year, today.month, today.day))
            self.dt_hasta.setDate(QDate(today.year, today.month, today.day))

        # Fallas dataset global
        try:
            self._fallas_dataset = self.db.obtener_todas_las_fallas() or []
        except Exception:
            self._fallas_dataset = []

        # Instituciones en fallas
        finsts = sorted({row[0] for row in self._fallas_dataset}) if self._fallas_dataset else []
        # Si existe combo de fallas, popularlo
        if hasattr(self, "cmb_fallas_inst"):
            self.cmb_fallas_inst.blockSignals(True)
            self.cmb_fallas_inst.clear()
            self.cmb_fallas_inst.addItem("Todas")
            self.cmb_fallas_inst.addItems(finsts)
            self.cmb_fallas_inst.blockSignals(False)

        self._apply_filters_and_render()

    def _apply_filters_and_render(self):
        inst = self.cmb_inst.currentText().strip()
        code = (self.txt_codigo.text() or "").strip().lower()

        d_from = self._qdate_to_pydate(self.dt_desde.date())
        d_to = self._qdate_to_pydate(self.dt_hasta.date())

        lst = self._all_licitaciones[:]
        if inst and inst != "Todas":
            lst = [b for b in lst if (getattr(b, "institucion", "") or "") == inst]
        if code:
            lst = [b for b in lst if code in (getattr(b, "numero_proceso", "") or "").lower()]

        if d_from:
            lst = [b for b in lst if self._to_date(getattr(b, "fecha_creacion", None)) >= d_from]
        if d_to:
            lst = [b for b in lst if self._to_date(getattr(b, "fecha_creacion", None)) <= d_to]

        self._filtered = lst

        # Render: KPIs, gráfico rendimiento + tabla empresa, gráfico estados y (en otras pestañas) datos auxiliares
        self._render_resumen_graphs()
        self._render_competencia_tab()
        self._render_fallas_tab()

    def _clear_filters(self):
        # Restablecer a “Todas” y a rango completo (primera a última transacción)
        self.cmb_inst.setCurrentIndex(0)
        self.txt_codigo.clear()
        min_d, max_d = self._min_max_dates(self._all_licitaciones)
        if min_d and max_d:
            self.dt_desde.setDate(QDate(min_d.year, min_d.month, min_d.day))
            self.dt_hasta.setDate(QDate(max_d.year, max_d.month, max_d.day))
        self._apply_filters_and_render()

    # ----------------- Pestaña Resumen: KPIs + gráficos + resumen -----------------
    def _render_resumen_graphs(self):
        # KPIs
        ganadas, perdidas = self._count_win_lose(self._filtered)
        tot_fin = ganadas + perdidas
        tasa = (ganadas / tot_fin * 100.0) if tot_fin > 0 else 0.0

        # Lotes ganados
        lotes_ganados = 0
        for lic in self._filtered:
            if getattr(lic, "estado", "") == "Adjudicada":
                lotes_ganados += sum(1 for l in getattr(lic, "lotes", []) if getattr(l, "ganado_por_nosotros", False))

        # Análisis financiero
        monto_base_total = sum(self._monto_base_total(lic) for lic in self._filtered)
        monto_ofertado_total = sum(self._monto_ofertado_total(lic) for lic in self._filtered)
        monto_adjudicado = self._monto_adjudicado_nuestro(self._filtered)

        # Actualizar tarjetas
        # Card Tasa (toma primer QLabel grande y gp)
        for child in self.card_tasa.findChildren(QLabel):
            if child.text().startswith("Tasa"):
                child.setText(f"Tasa de Éxito")
            # el valor grande:
        # buscar el QLabel grande por estilo no es trivial; mejor recalculemos:
        # volvemos a crear texts directos, buscando por orden: el segundo QLabel del primer HBox
        # Para robustez, seteamos por índices de layout
        # Simplificamos: encontramos todos los labels y seteamos por coincidencia
        # En producción, podrías guardar referencias al crear la tarjeta
        # Aquí, generamos de nuevo los textos por búsqueda heurística:
        def set_text_in_card(frame: QFrame, contains: str, value: str):
            for lb in frame.findChildren(QLabel):
                if contains in lb.text() or lb.text().strip().endswith(":"):
                    # intentaremos encontrar el siguiente QLabel hermano para el valor
                    pass
            # fallback: set first big label by font-size
        # Mejor: almacenamos referencias directas en self al crearlas
        # Reescribimos: al crear _kpi_card guardamos en self.lbl_val_main y self.lbl_gp
        self.lbl_val_main.setText(f"{tasa:.1f}%")
        self.lbl_gp.setText(f"Ganadas: {ganadas}   |   Perdidas: {perdidas}")

        # Card Lotes (texto grande en la segunda card no guardado; lo presentamos como subtítulo)
        # Añadimos/actualizamos dinámicamente un label “total lotes” si no existe
        if not hasattr(self, "_lbl_lotes_total"):
            self._lbl_lotes_total = QLabel(str(lotes_ganados))
            self._lbl_lotes_total.setStyleSheet(f"color:{self._col_green}; font-size:20px; font-weight:700;")
            self.card_lotes.layout().addWidget(self._lbl_lotes_total)
        else:
            self._lbl_lotes_total.setText(str(lotes_ganados))

        # Card Financiero (buscamos y actualizamos por orden visual)
        # Para facilidad, creamos/actualizamos una fila de valores si no existe
        if not hasattr(self, "_lbl_fin_base"):
            self._lbl_fin_base = QLabel(self._money(monto_base_total))
            self._lbl_fin_ofe = QLabel(self._money(monto_ofertado_total))
            self._lbl_fin_adj = QLabel(self._money(monto_adjudicado))
            # Insertar filas en el card_fin (al final)
            lay = self.card_fin.layout()
            def add_line(txt: str, value_lbl: QLabel, accent: Optional[str] = None):
                h = QHBoxLayout()
                l = QLabel(txt)
                l.setStyleSheet("font-weight:600;")
                if accent:
                    value_lbl.setStyleSheet(f"color:{accent}; font-weight:700;")
                h.addWidget(l)
                h.addStretch(1)
                h.addWidget(value_lbl)
                lay.addLayout(h)
            add_line("Monto Base Total:", self._lbl_fin_base, None)
            add_line("Monto Ofertado Total:", self._lbl_fin_ofe, None)
            add_line("Monto Adjudicado (Nosotros):", self._lbl_fin_adj, self._col_green)
        else:
            self._lbl_fin_base.setText(self._money(monto_base_total))
            self._lbl_fin_ofe.setText(self._money(monto_ofertado_total))
            self._lbl_fin_adj.setText(self._money(monto_adjudicado))

        # Gráfico Rendimiento por Empresa + Resumen por Empresa
        stats_emp = defaultdict(lambda: {'participaciones': 0, 'ganadas': 0, 'monto_adj': 0.0})
        for lic in self._filtered:
            empresas = self._our_names_from(lic)
            if not empresas:
                continue
            es_ganada = (getattr(lic, "estado", "") == "Adjudicada") and any(getattr(l, "ganado_por_nosotros", False) for l in getattr(lic, "lotes", []))
            for e in empresas:
                stats_emp[e]['participaciones'] += 1
                if es_ganada:
                    stats_emp[e]['ganadas'] += 1
                    # Monto adjudicado por lote a esa empresa (si coincide empresa_nuestra)
                    for l in getattr(lic, "lotes", []):
                        if getattr(l, "ganado_por_nosotros", False) and (getattr(l, "empresa_nuestra", "") or "") == e:
                            stats_emp[e]['monto_adj'] += float(getattr(l, "monto_ofertado", 0) or 0.0)

        # Tabla lateral
        self._populate_empresa_table(stats_emp)

        # Gráfico rendimiento
        if MATPLOTLIB_AVAILABLE:
            ax = self.canvas_rend.figure.subplots()
            ax.clear()
            if stats_emp:
                data = sorted(stats_emp.items(), key=lambda it: it[1]['participaciones'], reverse=True)
                labels = [k for k, _ in data]
                y = list(range(len(labels)))
                part = [d['participaciones'] for _, d in data]
                wins = [d['ganadas'] for _, d in data]
                height = 0.4
                ax.barh([yy + height/2 for yy in y], part, height=height, color=self._col_bar1, label='Participaciones')
                ax.barh([yy - height/2 for yy in y], wins, height=height, color=self._col_bar2, label='Ganadas')
                ax.set_yticks(y, labels)
                ax.invert_yaxis()
                ax.set_xlabel("Cantidad de Licitaciones")
                ax.legend()
            else:
                ax.text(0.5, 0.5, "Sin datos", ha='center', va='center')
                ax.set_yticks([])
            self.canvas_rend.draw()

        # Gráfico Estados
        if MATPLOTLIB_AVAILABLE:
            ax2 = self.canvas_estados.figure.subplots()
            ax2.clear()
            stats = {"Ganada": 0, "Perdida": 0, "En Proceso": 0}
            for lic in self._filtered:
                estado = getattr(lic, "estado", "")
                if estado == "Adjudicada":
                    if any(getattr(l, "ganado_por_nosotros", False) for l in getattr(lic, "lotes", [])):
                        stats["Ganada"] += 1
                    else:
                        stats["Perdida"] += 1
                elif estado in ["Descalificado Fase A", "Descalificado Fase B", "Desierta", "Cancelada"]:
                    stats["Perdida"] += 1
                else:
                    stats["En Proceso"] += 1
            labels = [f"{k} ({v})" for k, v in stats.items() if v > 0]
            values = [v for v in stats.values() if v > 0]
            colors = [self._col_green, self._col_red, self._col_amber]
            if values:
                bars = ax2.barh(labels, values, color=colors[:len(values)])
                ax2.bar_label(bars, padding=3)
                ax2.set_xlabel("Cantidad de Licitaciones")
                ax2.invert_yaxis()
            else:
                ax2.text(0.5, 0.5, "Sin datos", ha='center', va='center')
                ax2.set_yticks([])
            self.canvas_estados.draw()

    def _populate_empresa_table(self, stats_emp: Dict[str, Dict[str, float]]):
        self.tbl_emp.setRowCount(0)
        data = sorted(stats_emp.items(), key=lambda it: it[1]['participaciones'], reverse=True)
        for emp, d in data:
            row = self.tbl_emp.rowCount()
            self.tbl_emp.insertRow(row)
            vals = (
                emp,
                str(int(d['participaciones'])),
                str(int(d['ganadas'])),
                self._money(d['monto_adj'])
            )
            for col, text in enumerate(vals):
                it = QTableWidgetItem(text)
                if col == self.COL_EMP_ADJ:
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.tbl_emp.setItem(row, col, it)

    # ----------------- Pestaña Competencia: render ---------
    def _render_competencia_tab(self):
        data = self._analizar_competidores_pct(self._filtered)
        self._comp_all = data
        self._filter_competidores_table()

    def _filter_competidores_table(self):
        term = (self.txt_comp_search.text() or "").strip().lower()
        data = getattr(self, "_comp_all", [])
        if term:
            data = [c for c in data if term in (c.get('nombre', '') or '').lower() or term in (c.get('rnc', '') or '').lower()]
        t = self.tbl_comp
        t.setRowCount(0)
        for c in data:
            row = t.rowCount()
            t.insertRow(row)
            vals = (
                c.get('nombre', '') or '',
                c.get('rnc', '') or '',
                str(c.get('participaciones', 0)),
                f"{c.get('pct_promedio', 0.0):.2f}%",
            )
            for col, text in enumerate(vals):
                t.setItem(row, col, QTableWidgetItem(text))

    def _analizar_competidores_pct(self, bids: List[Licitacion]) -> List[Dict[str, Any]]:
        stats: Dict[str, Dict[str, float]] = {}
        base_by_lote: Dict[str, float] = {}
        rnc_map = {c.get('nombre', ''): c.get('rnc', '') for c in (self._competidores_maestros or [])}

        for lic in bids:
            base_by_lote.clear()
            for lote in getattr(lic, 'lotes', []):
                base = getattr(lote, 'monto_base_personal', 0) or getattr(lote, 'monto_base', 0) or 0
                base_by_lote[str(getattr(lote, 'numero', ''))] = float(base) if base else 0.0

            for comp in getattr(lic, 'oferentes_participantes', []):
                nombre = getattr(comp, 'nombre', '').strip() or '—'
                for o in getattr(comp, 'ofertas_por_lote', []):
                    lote_num = str(o.get('lote_numero'))
                    oferta = float(o.get('monto', 0) or 0)
                    base = float(base_by_lote.get(lote_num, 0) or 0)
                    if base > 0 and oferta > 0:
                        pct = (oferta - base) / base * 100.0
                        if nombre not in stats:
                            stats[nombre] = {'sum_pct': 0.0, 'count': 0}
                        stats[nombre]['sum_pct'] += pct
                        stats[nombre]['count'] += 1

        salida: List[Dict[str, Any]] = []
        for nombre, agg in stats.items():
            count = agg['count'] or 0
            pct_prom = (agg['sum_pct'] / count) if count else 0.0
            salida.append({
                'nombre': nombre,
                'rnc': rnc_map.get(nombre, ''),
                'participaciones': count,
                'pct_promedio': pct_prom
            })
        salida.sort(key=lambda x: (-x['participaciones'], x['pct_promedio']))
        return salida

    # ----------------- Pestaña Fallas -----------------
    def _render_fallas_tab(self):
        inst = self.cmb_fallas_inst.currentText() if hasattr(self, "cmb_fallas_inst") and self.cmb_fallas_inst.count() else "Todas"
        datos = self._fallas_dataset if inst == "Todas" else [f for f in self._fallas_dataset if f[0] == inst]

        counter = Counter(item[2] for item in datos)  # doc_nombre
        total = len(datos)
        if hasattr(self, "tbl_fdoc"):
            self.tbl_fdoc.setRowCount(0)
            for doc, cnt in sorted(counter.items(), key=lambda x: x[1], reverse=True):
                pct = (cnt / total * 100.0) if total else 0.0
                row = self.tbl_fdoc.rowCount()
                self.tbl_fdoc.insertRow(row)
                self.tbl_fdoc.setItem(row, self.COL_FDOC_NOM, QTableWidgetItem(doc))
                self.tbl_fdoc.setItem(row, self.COL_FDOC_CNT, QTableWidgetItem(str(cnt)))
                self.tbl_fdoc.setItem(row, self.COL_FDOC_PCT, QTableWidgetItem(f"{pct:.1f}%"))

        if MATPLOTLIB_AVAILABLE and hasattr(self, "canvas_fallas"):
            ax = self.canvas_fallas.figure.subplots()
            ax.clear()
            top_items = counter.most_common(10)
            if not top_items:
                ax.text(0.5, 0.5, "Sin datos", ha='center', va='center')
            else:
                labels = [it[0] for it in top_items][::-1]
                counts = [it[1] for it in top_items][::-1]
                palette = [self._col_bar1, "#81A1C1", "#88C0D0", "#A3BE8C", "#EBCB8B", "#D08770", "#BF616A", "#B48EAD", "#8FBCBB", "#94A3B8"]
                colors = (palette * ((len(counts) // len(palette)) + 1))[:len(counts)][::-1]
                bars = ax.barh(labels, counts, color=colors)
                ax.bar_label(bars, padding=3, fontsize=8, color='black', fmt='%d')
                ax.set_xlabel("Cantidad de Fallas Registradas")
                if counts:
                    ax.set_xlim(right=max(counts) * 1.15)
            self.canvas_fallas.draw()

        if hasattr(self, "tbl_fdet"):
            self.tbl_fdet.setRowCount(0)

    def _render_fallas_detalle(self):
        if not hasattr(self, "tbl_fdoc") or not hasattr(self, "tbl_fdet"):
            return
        self.tbl_fdet.setRowCount(0)
        r = self.tbl_fdoc.currentRow()
        if r < 0:
            return
        doc_sel = self.tbl_fdoc.item(r, self.COL_FDOC_NOM).text()
        inst = self.cmb_fallas_inst.currentText()
        datos = self._fallas_dataset if inst == "Todas" else [f for f in self._fallas_dataset if f[0] == inst]

        rnc_map = {e.get('nombre', ''): e.get('rnc', 'N/D') for e in (self._empresas_maestras or [])}
        rnc_map.update({c.get('nombre', ''): c.get('rnc', 'N/D') for c in (self._competidores_maestros or [])})

        for insti, participante, doc_nombre, es_nuestro, *_ in datos:
            if doc_nombre == doc_sel and (inst == "Todas" or insti == inst):
                tipo = "Nuestra" if es_nuestro else "Competidor"
                rnc = rnc_map.get(participante, "N/D")
                row = self.tbl_fdet.rowCount()
                self.tbl_fdet.insertRow(row)
                self.tbl_fdet.setItem(row, self.COL_FDET_EMP, QTableWidgetItem(participante))
                self.tbl_fdet.setItem(row, self.COL_FDET_RNC, QTableWidgetItem(rnc))
                self.tbl_fdet.setItem(row, self.COL_FDET_INST, QTableWidgetItem(insti))
                self.tbl_fdet.setItem(row, self.COL_FDET_TIPO, QTableWidgetItem(tipo))

    # ----------------- Utilidades -----------------
    def _our_names_from(self, lic: Licitacion) -> List[str]:
        names = set()
        for lote in getattr(lic, "lotes", []):
            n = (getattr(lote, "empresa_nuestra", None) or "").strip()
            if n:
                names.add(n)
        if not names:
            for item in getattr(lic, "empresas_nuestras", []) or []:
                if hasattr(item, "nombre"):
                    n = (getattr(item, "nombre") or "").strip()
                    if n:
                        names.add(n)
                elif isinstance(item, dict) and item.get("nombre"):
                    names.add(item["nombre"].strip())
        return sorted(list(names))

    def _count_win_lose(self, arr: List[Licitacion]) -> Tuple[int, int]:
        gan, per = 0, 0
        perdidas_directas = {"Descalificado Fase A", "Descalificado Fase B", "Desierta", "Cancelada"}
        for lic in arr:
            estado = getattr(lic, "estado", "")
            if estado == "Adjudicada":
                if any(getattr(l, "ganado_por_nosotros", False) for l in getattr(lic, "lotes", [])):
                    gan += 1
                else:
                    per += 1
            elif estado in perdidas_directas:
                per += 1
            else:
                # En proceso: no suma a gan/per (se refleja en gráfico)
                pass
        return gan, per

    def _min_max_dates(self, arr: List[Licitacion]) -> Tuple[Optional[date], Optional[date]]:
        dates: List[date] = []
        for lic in arr:
            d = self._to_date(getattr(lic, "fecha_creacion", None))
            if d:
                dates.append(d)
        if not dates:
            return None, None
        return min(dates), max(dates)

    def _to_date(self, val) -> Optional[date]:
        if isinstance(val, date):
            return val
        if isinstance(val, datetime):
            return val.date()
        if isinstance(val, str) and val:
            try:
                return datetime.strptime(val, "%Y-%m-%d").date()
            except Exception:
                try:
                    return datetime.fromisoformat(val).date()
                except Exception:
                    return None
        return None

    def _qdate_to_pydate(self, qd: QDate) -> Optional[date]:
        if not qd or not qd.isValid():
            return None
        return date(qd.year(), qd.month(), qd.day())

    def _money(self, v: float) -> str:
        try:
            return "RD$ {:,.2f}".format(float(v or 0.0))
        except Exception:
            return "RD$ 0.00"

    def _monto_base_total(self, lic: Licitacion) -> float:
        # Si el modelo expone método, úsalo; si no, suma por lotes
        total = 0.0
        try:
            for l in getattr(lic, "lotes", []) or []:
                total += float(getattr(l, "monto_base_personal", 0) or getattr(l, "monto_base", 0) or 0.0)
        except Exception:
            pass
        return total

    def _monto_ofertado_total(self, lic: Licitacion) -> float:
        try:
            if hasattr(lic, "get_oferta_total"):
                return float(getattr(lic, "get_oferta_total")(solo_participados=True) or 0.0)
        except Exception:
            pass
        # Fallback: suma por lotes
        return sum(float(getattr(l, "monto_ofertado", 0) or 0.0) for l in getattr(lic, "lotes", []) or [])

    def _monto_adjudicado_nuestro(self, bids: List[Licitacion]) -> float:
        total = 0.0
        for lic in bids:
            if getattr(lic, "estado", "") == "Adjudicada":
                for l in getattr(lic, "lotes", []) or []:
                    if getattr(l, "ganado_por_nosotros", False):
                        total += float(getattr(l, "monto_ofertado", 0) or 0.0)
        return total

    # ----------------- Interacción común -----------------
    def get_selected_licitacion_id(self) -> Optional[int]:
        # Este widget ya no muestra tabla de licitaciones aquí,
        # pero mantenemos el método por compatibilidad si se usa en otra pestaña.
        return None

    def _emit_open_selected(self):
        # Compatibilidad si en algún momento se vuelve a mostrar tabla
        lic_id = self.get_selected_licitacion_id()
        if lic_id is not None:
            self.edit_licitacion_requested.emit(lic_id)

# 2) Pega estos dos métodos dentro de la clase DashboardWidget (por ejemplo, debajo de _render_fallas_detalle)

    def _delete_fallas_selected(self):
        """
        Elimina en BD las fallas seleccionadas en la tabla de detalle.
        Usa: institución (col 2), participante (col 0) y el documento actualmente seleccionado.
        """
        # Validar selección en detalle
        if not hasattr(self, "tbl_fdet") or not hasattr(self, "tbl_fdoc"):
            return

        rows = sorted({idx.row() for idx in self.tbl_fdet.selectionModel().selectedRows()}, reverse=True)
        if not rows:
            QMessageBox.information(self, "Eliminar fallas", "Seleccione una o más filas del detalle.")
            return

        # Validar documento seleccionado en la tabla superior de impacto
        r = self.tbl_fdoc.currentRow()
        if r < 0:
            QMessageBox.warning(self, "Eliminar fallas", "Seleccione primero un documento en la tabla superior.")
            return

        doc_sel = self.tbl_fdoc.item(r, self.COL_FDOC_NOM).text().strip()
        if not doc_sel:
            QMessageBox.warning(self, "Eliminar fallas", "No se pudo determinar el documento seleccionado.")
            return

        # Confirmación
        if QMessageBox.question(
            self, "Confirmar",
            f"¿Eliminar {len(rows)} falla(s) del documento '{doc_sel}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return

        eliminadas = 0
        errores = 0
        for rr in rows:
            try:
                empresa = (self.tbl_fdet.item(rr, self.COL_FDET_EMP).text() or "").strip()
                inst = (self.tbl_fdet.item(rr, self.COL_FDET_INST).text() or "").strip()
                if not empresa or not inst:
                    errores += 1
                    continue
                eliminadas += int(self.db.eliminar_falla_por_campos(inst, empresa, doc_sel) or 0)
            except Exception:
                errores += 1

        # Refrescar dataset y vistas
        try:
            self._fallas_dataset = self.db.obtener_todas_las_fallas() or []
        except Exception:
            pass

        self._render_fallas_tab()

        # Re-seleccionar documento si existe
        items = self.tbl_fdoc.findItems(doc_sel, Qt.MatchFlag.MatchExactly)
        if items:
            self.tbl_fdoc.setCurrentItem(items[0])
            self._render_fallas_detalle()

        if errores:
            QMessageBox.warning(self, "Eliminar fallas", f"Se eliminaron {eliminadas} con {errores} error(es).")
        else:
            QMessageBox.information(self, "Eliminar fallas", f"Se eliminaron {eliminadas} fallas.")

    def _edit_fallas_comment(self):
        """
        Edita el comentario de 1..n fallas seleccionadas.
        Requiere: db.actualizar_comentario_falla(institucion, participante, documento, comentario)
        """
        if not hasattr(self, "tbl_fdet") or not hasattr(self, "tbl_fdoc"):
            return

        rows = sorted({idx.row() for idx in self.tbl_fdet.selectionModel().selectedRows()})
        if not rows:
            QMessageBox.information(self, "Editar comentario", "Seleccione una o más filas del detalle.")
            return

        r = self.tbl_fdoc.currentRow()
        if r < 0:
            QMessageBox.warning(self, "Editar comentario", "Seleccione primero un documento en la tabla superior.")
            return

        doc_sel = self.tbl_fdoc.item(r, self.COL_FDOC_NOM).text().strip()
        if not doc_sel:
            QMessageBox.warning(self, "Editar comentario", "No se pudo determinar el documento seleccionado.")
            return

        # Pedir comentario
        texto, ok = QInputDialog.getText(
            self, "Editar comentario",
            f"Nuevo comentario para {len(rows)} falla(s):"
        )
        if not ok:
            return
        comentario = (texto or "").strip()
        if not comentario:
            QMessageBox.information(self, "Editar comentario", "Ingrese un comentario.")
            return

        errores = 0
        for rr in rows:
            try:
                empresa = (self.tbl_fdet.item(rr, self.COL_FDET_EMP).text() or "").strip()
                inst = (self.tbl_fdet.item(rr, self.COL_FDET_INST).text() or "").strip()
                if not empresa or not inst:
                    errores += 1
                    continue
                self.db.actualizar_comentario_falla(inst, empresa, doc_sel, comentario)
            except Exception:
                errores += 1

        # Refrescar dataset y vistas
        try:
            self._fallas_dataset = self.db.obtener_todas_las_fallas() or []
        except Exception:
            pass

        self._render_fallas_tab()

        # Re-seleccionar documento si existe
        items = self.tbl_fdoc.findItems(doc_sel, Qt.MatchFlag.MatchExactly)
        if items:
            self.tbl_fdoc.setCurrentItem(items[0])
            self._render_fallas_detalle()

        if errores:
            QMessageBox.warning(self, "Editar comentario", f"Actualizado con {errores} error(es).")
        else:
            QMessageBox.information(self, "Editar comentario", "Comentario actualizado.")