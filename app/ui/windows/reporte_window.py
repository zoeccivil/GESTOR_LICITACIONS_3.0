from __future__ import annotations
from typing import Optional
from datetime import date, datetime

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QGuiApplication, QPalette, QColor
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QProgressBar,
    QSplitter, QGridLayout, QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QTreeWidget, QTreeWidgetItem, QFileDialog, QMessageBox, QToolBar, QFrame, QStyle
)

# Gráficos (opcional)
try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except Exception:
    MATPLOTLIB_AVAILABLE = False
    FigureCanvas = None
    Figure = None

# ReportGenerator (rutas tolerantes)
REPORT_GENERATOR_AVAILABLE = False
REPORT_GENERATOR_IMPORT_ERROR = ""
try:
    from app.core.reporting import ReportGenerator
    REPORT_GENERATOR_AVAILABLE = True
except Exception as e1:
    REPORT_GENERATOR_IMPORT_ERROR = str(e1)
    try:
        from app.core.reporting.report_generator import ReportGenerator
        REPORT_GENERATOR_AVAILABLE = True
        REPORT_GENERATOR_IMPORT_ERROR = ""
    except Exception as e2:
        REPORT_GENERATOR_IMPORT_ERROR = f"{e1} | {e2}"
        ReportGenerator = None  # type: ignore

# Persistencia JSON para splitters y tabs
from app.core.app_settings import (
    get_splitter_sizes, set_splitter_sizes,
    get_tab_index, set_tab_index,
)

# Dependencias de exportación (mensajes amigables)
try:
    import reportlab  # noqa
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False
try:
    import openpyxl  # noqa
    OPENPYXL_AVAILABLE = True
except Exception:
    OPENPYXL_AVAILABLE = False


def _hex(c: QColor) -> str:
    return c.name() if isinstance(c, QColor) else str(c)


class ReportWindow(QMainWindow):
    """
    Reporte de Licitación (temable):
    - Integra los colores del tema activo (QPalette) en UI y gráficos.
    - Guarda/restaura tamaño del splitter y último tab en JSON (windows.ReportWindow).
    """
    def __init__(self, licitacion, parent: Optional[QWidget] = None, start_maximized: bool = False):
        super().__init__(parent)
        self.licitacion = licitacion

        # Colores derivados del tema activo (QPalette)
        self.ui = self._resolve_theme_colors()

        self._setup_palette()
        self._build_ui()

        self.setWindowTitle(f"Reporte: {getattr(self.licitacion, 'nombre_proceso', '')}")
        self.resize(1100, 850)
        if start_maximized:
            self.showMaximized()

        # Poblar datos
        self._populate_kpis()
        self._populate_cronograma()
        self._populate_financiero()
        self._populate_checklist()
        self._populate_competidores()

        # Restaurar splitters/tabs desde JSON
        self._restore_splitters_and_tabs_json()

        # Conectar para guardar en caliente
        self.split_mid.splitterMoved.connect(self._on_split_mid_moved)
        self.tabs.currentChanged.connect(self._on_tabs_changed)

    # ---------- Tema / Colores ----------
    def _resolve_theme_colors(self) -> dict:
        app = QGuiApplication.instance()
        pal: QPalette = app.palette() if app else QPalette()

        # Roles clave
        accent = pal.highlight().color()
        text = pal.text().color()
        window = pal.window().color()
        base = pal.base().color()
        alt = pal.alternateBase().color()
        button = pal.button().color()

        # No hay "border" en paleta; aproximar con mid() o un gris
        border = pal.mid().color() if pal else QColor("#3A4152")

        # Colores semánticos útiles
        success = QColor("#22C55E")   # verde agradable
        danger = QColor("#EF4444")    # rojo moderno
        warning = QColor("#F59E0B")   # naranja moderno
        info = accent

        # Texto secundario aproximado
        text_sec = pal.placeholderText().color() if hasattr(pal, "placeholderText") else QColor("#B9C0CC")

        return {
            "accent": _hex(accent),
            "accent_soft": f"{_hex(accent)}33",
            "text": _hex(text),
            "text_sec": _hex(text_sec),
            "window": _hex(window),
            "base": _hex(base),
            "alt": _hex(alt),
            "button": _hex(button),
            "border": _hex(border),
            "success": _hex(success),
            "danger": _hex(danger),
            "warning": _hex(warning),
            "info": _hex(info),
        }

    def _setup_palette(self):
        # QSS dinámico (usa colores del tema activo)
        u = self.ui
        self.setStyleSheet(f"""
            QWidget {{
                font-family: 'Segoe UI', 'DejaVu Sans', Arial;
                font-size: 10pt;
                color: {u['text']};
                background: {u['window']};
            }}
            QToolBar {{
                background: {u['window']};
                border: 0;
                border-bottom: 1px solid {u['border']};
            }}
            QStatusBar {{
                background: {u['window']};
                color: {u['text_sec']};
            }}
            QLabel {{
                color: {u['text']};
            }}
            QTabWidget::pane {{
                border: 1px solid {u['border']};
                background: {u['base']};
                border-radius: 6px;
            }}
            QTabBar::tab {{
                background: {u['alt']};
                border: 1px solid {u['border']};
                padding: 6px 12px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
                color: {u['text_sec']};
            }}
            QTabBar::tab:selected {{
                color: {u['text']};
                background: {u['base']};
                border-bottom: 1px solid {u['base']};
            }}
        """)

    def _card_stylesheet(self) -> str:
        u = self.ui
        return (
            f"QGroupBox, QFrame{{"
            f"background:{u['base']};"
            f"border:1px solid {u['border']};"
            f"border-radius:8px;"
            f"padding:8px;"
            f"}}"
            f"QGroupBox::title{{"
            f"left:8px;padding:0 4px;color:{u['text_sec']};font-weight:600;"
            f"}}"
        )

    # ---------- UI ----------
    def _build_toolbar(self):
        tb = QToolBar("Exportar", self)
        tb.setIconSize(tb.iconSize() * 1.1)
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, tb)

        self.act_pdf = QAction(self._icon(QStyle.StandardPixmap.SP_FileIcon, "report"), "Exportar a PDF", self)
        self.act_pdf.setShortcut(QKeySequence("Ctrl+P"))
        self.act_pdf.triggered.connect(lambda: self._export_report("pdf"))
        self.act_pdf.setEnabled(True)

        self.act_xls = QAction(self._icon(QStyle.StandardPixmap.SP_DialogSaveButton, "docs"), "Exportar a Excel", self)
        self.act_xls.setShortcut(QKeySequence("Ctrl+E"))
        self.act_xls.triggered.connect(lambda: self._export_report("excel"))
        self.act_xls.setEnabled(True)

        tb.addAction(self.act_pdf)
        tb.addAction(self.act_xls)

    def _build_ui(self):
        self._build_toolbar()

        central = QWidget(self)
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # KPIs
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(10)
        root.addLayout(kpi_row)

        self.card_estado = self._kpi_card("Estado Actual", self.ui["accent"])
        self.card_docs = self._kpi_card("Progreso Docs", self.ui["success"], with_progress=True)
        self.card_dias = self._kpi_card("Días Restantes", self.ui["warning"])
        self.card_dif = self._kpi_card("Diferencia Oferta", self.ui["danger"])
        for c in (self.card_estado, self.card_docs, self.card_dias, self.card_dif):
            kpi_row.addWidget(c)

        # Splitter Cronograma | Financiero
        self.split_mid = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(self.split_mid, 2)

        # Cronograma
        self.box_crono = QGroupBox("Cronograma")
        self.box_crono.setStyleSheet(self._card_stylesheet())
        v_crono = QVBoxLayout(self.box_crono)
        self.tbl_crono = QTableWidget(0, 3)
        self.tbl_crono.setAlternatingRowColors(True)
        self.tbl_crono.setHorizontalHeaderLabels(["Hito", "Fecha Límite", "Estado"])
        self._tune_table(self.tbl_crono)
        self._tune_cronograma_header()
        v_crono.addWidget(self.tbl_crono)
        self.split_mid.addWidget(self.box_crono)

        # Financiero
        self.box_fin = QGroupBox("Resumen Financiero (Solo Lotes Participados)")
        self.box_fin.setStyleSheet(self._card_stylesheet())
        v_fin = QVBoxLayout(self.box_fin)

        self.grid_fin = QGridLayout()
        self.grid_fin.setVerticalSpacing(8)
        v_fin.addLayout(self.grid_fin)

        if MATPLOTLIB_AVAILABLE:
            self.canvas_fin = self._new_canvas()
            v_fin.addWidget(self._wrap_canvas("Comparativo Oferta vs Base (participados)", self.canvas_fin), 1)
        self.split_mid.addWidget(self.box_fin)

        self.split_mid.setStretchFactor(0, 3)
        self.split_mid.setStretchFactor(1, 2)

        # Tabs inferiores
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 3)

        # Checklist
        self.tab_check = QWidget()
        v_chk = QVBoxLayout(self.tab_check)
        self.tbl_docs = QTableWidget(0, 4)
        self.tbl_docs.setHorizontalHeaderLabels(["✓", "Documento", "Categoría", "Condición"])
        self._tune_table(self.tbl_docs)
        self.tbl_docs.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        v_chk.addWidget(self.tbl_docs)
        self.tabs.addTab(self.tab_check, "Checklist de Documentos")

        # Competidores
        self.tab_comp = QWidget()
        v_comp = QVBoxLayout(self.tab_comp)
        self.tree_comp = QTreeWidget()
        self.tree_comp.setColumnCount(7)
        self.tree_comp.setHeaderLabels([
            "Participante / Lote Ofertado",
            "Monto Ofertado",
            "Monto Habilitado (Fase A)",
            "Estado Fase A",
            "Monto Base Lote",
            "% Diferencia",
            "Ganador",
        ])
        self.tree_comp.setAlternatingRowColors(True)
        v_comp.addWidget(self.tree_comp)
        self.tabs.addTab(self.tab_comp, "Competidores y Resultados")

    # ---------- Persistencia splitters/tabs ----------
    def _restore_splitters_and_tabs_json(self):
        sizes = get_splitter_sizes("ReportWindow", "split_mid")
        if sizes and all(isinstance(s, int) and s > 0 for s in sizes) and len(sizes) == len(self.split_mid.sizes()):
            self.split_mid.setSizes(sizes)
        else:
            self.split_mid.setSizes([700, 400])

        idx = get_tab_index("ReportWindow", "main", default=0)
        if 0 <= idx < self.tabs.count():
            self.tabs.setCurrentIndex(idx)

    def _on_split_mid_moved(self, pos: int, index: int):
        try:
            set_splitter_sizes("ReportWindow", "split_mid", self.split_mid.sizes())
        except Exception:
            pass

    def _on_tabs_changed(self, idx: int):
        try:
            set_tab_index("ReportWindow", "main", int(idx))
        except Exception:
            pass

    # ---------- Cards / tablas / gráficos ----------
    def _kpi_card(self, title: str, accent: str, with_progress: bool = False) -> QFrame:
        card = QFrame()
        card.setStyleSheet(self._card_stylesheet())
        lay = QVBoxLayout(card)

        t = QLabel(title)
        t.setStyleSheet(f"color:{self.ui['text_sec']}; font-weight:600;")
        lay.addWidget(t)

        row = QHBoxLayout()
        v = QLabel("--")
        v.setStyleSheet(f"color:{accent}; font-size:22px; font-weight:700;")
        row.addWidget(v)
        row.addStretch(1)
        lay.addLayout(row)

        pb = None
        if with_progress:
            pb = QProgressBar()
            pb.setRange(0, 100)
            pb.setValue(0)
            pb.setFormat("%p%")
            pb.setStyleSheet(
                f"QProgressBar{{min-height:12px;border-radius:6px;background:{self.ui['alt']};"
                f"border:1px solid {self.ui['border']}; color:{self.ui['text']};}}"
                f"QProgressBar::chunk{{background:{self.ui['accent']}; border-radius:6px;}}"
            )
            lay.addWidget(pb)

        card._value_label = v
        card._progress = pb
        return card

    def _populate_kpis(self):
        estado = getattr(self.licitacion, "estado", "N/D") or "N/D"
        self.card_estado._value_label.setText(estado)
        pct = 0.0
        try:
            if hasattr(self.licitacion, "get_porcentaje_completado"):
                pct = float(self.licitacion.get_porcentaje_completado() or 0.0)
        except Exception:
            pass
        self.card_docs._value_label.setText(f"{pct:.1f}%")
        if self.card_docs._progress:
            self.card_docs._progress.setValue(int(round(pct)))
        dias = "N/D"
        try:
            if hasattr(self.licitacion, "get_dias_restantes"):
                dias = str(self.licitacion.get_dias_restantes())
        except Exception:
            pass
        self.card_dias._value_label.setText(str(dias))
        dif = 0.0
        try:
            if hasattr(self.licitacion, "get_diferencia_porcentual"):
                dif = float(self.licitacion.get_diferencia_porcentual(solo_participados=True) or 0.0)
        except Exception:
            pass
        color = self.ui["danger"] if dif > 0 else self.ui["success"]
        self.card_dif._value_label.setStyleSheet(f"color:{color}; font-size:22px; font-weight:700;")
        self.card_dif._value_label.setText(f"{dif:+.2f}%")

    def _tune_cronograma_header(self):
        h = self.tbl_crono.horizontalHeader()
        h.setVisible(True)
        h.setHighlightSections(False)
        h.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setStretchLastSection(False)
        h.setMinimumSectionSize(80)
        # Header QSS con tema
        self.tbl_crono.setStyleSheet(
            self.tbl_crono.styleSheet()
            + f"QHeaderView::section{{min-height:28px;color:{self.ui['text']};"
              f"background:{self.ui['alt']}; border:1px solid {self.ui['border']}; padding:6px;}}"
        )

    def _populate_cronograma(self):
        self.tbl_crono.setRowCount(0)
        cron = getattr(self.licitacion, "cronograma", {}) or {}
        for evento, datos in sorted(cron.items(), key=lambda x: x[0]):
            r = self.tbl_crono.rowCount()
            self.tbl_crono.insertRow(r)
            fecha = (datos or {}).get("fecha_limite") or (datos or {}).get("fecha") or "N/D"
            estado = (datos or {}).get("estado", "Pendiente")
            self.tbl_crono.setItem(r, 0, QTableWidgetItem(str(evento)))
            self.tbl_crono.setItem(r, 1, QTableWidgetItem(str(fecha)))
            it = QTableWidgetItem(str(estado))
            low = str(estado).lower()
            if low.startswith("cumpl"):
                it.setForeground(QColor(self.ui["success"]))
            elif low.startswith("pend"):
                it.setForeground(QColor(self.ui["warning"]))
            elif low.startswith("incum") or low.startswith("venc"):
                it.setForeground(QColor(self.ui["danger"]))
            self.tbl_crono.setItem(r, 2, it)
        self.tbl_crono.resizeColumnsToContents()
        self.tbl_crono.resizeRowsToContents()

    # ------------------------ Financiero ------------------------
    def _populate_financiero(self):
        while self.grid_fin.count():
            item = self.grid_fin.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        base = 0.0
        ofertado = 0.0
        dif_pct = 0.0
        try:
            if hasattr(self.licitacion, "get_monto_base_total"):
                base = float(self.licitacion.get_monto_base_total(solo_participados=True) or 0.0)
            if hasattr(self.licitacion, "get_oferta_total"):
                ofertado = float(self.licitacion.get_oferta_total(solo_participados=True) or 0.0)
            if hasattr(self.licitacion, "get_diferencia_porcentual"):
                dif_pct = float(self.licitacion.get_diferencia_porcentual(solo_participados=True) or 0.0)
        except Exception:
            pass

        data = [
            ("Monto Base (Presupuesto):", self._money(base), None),
            ("Monto de Nuestra Oferta:", self._money(ofertado), None),
            ("Diferencia Absoluta:", self._money(ofertado - base), self.ui["text"]),
            ("Diferencia Porcentual:", f"{dif_pct:+.2f}%", self.ui["danger"] if dif_pct > 0 else self.ui["success"]),
        ]
        for r, (lbl, val, color) in enumerate(data):
            l = QLabel(lbl)
            l.setStyleSheet(f"font-weight:600; color:{self.ui['text_sec']};")
            v = QLabel(val)
            if color:
                v.setStyleSheet(f"color:{color}; font-weight:700;")
            v.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.grid_fin.addWidget(l, r, 0)
            self.grid_fin.addWidget(v, r, 1)

        if MATPLOTLIB_AVAILABLE:
            ax = self.canvas_fin.figure.subplots()
            ax.clear()

            # Aplicar estilo acorde al tema
            ax.set_facecolor(self.ui["base"])
            ax.tick_params(axis="x", colors=self.ui["text_sec"])
            ax.tick_params(axis="y", colors=self.ui["text_sec"])
            for spine in ("top", "right"):
                ax.spines[spine].set_visible(False)
            ax.spines["left"].set_color(self.ui["border"])
            ax.spines["bottom"].set_color(self.ui["border"])

            labels = ["Base", "Oferta"]
            values = [base, ofertado]
            colors = [self.ui["accent"], self.ui["success"]]

            y_pos = [1, 0]  # "Base" arriba
            bars = ax.barh(y_pos, values, color=colors, height=0.45)
            ax.set_yticks(y_pos, labels, color=self.ui["text"])

            for rect, val in zip(bars, values):
                ax.text(
                    rect.get_width() * 1.01,
                    rect.get_y() + rect.get_height() / 2,
                    f"RD$ {val:,.0f}",
                    va="center",
                    ha="left",
                    fontsize=9,
                    color=self.ui["text"],
                )

            ax.set_xlabel("Monto", color=self.ui["text_sec"])
            max_v = max(values) if values else 1
            ax.set_xlim(0, max_v * 1.25)

            self.canvas_fin.figure.set_facecolor(self.ui["base"])
            self.canvas_fin.figure.tight_layout()
            self.canvas_fin.draw()

    # ------------------------ Checklist documentos ------------------------
    def _populate_checklist(self):
        self.tbl_docs.setRowCount(0)
        docs = getattr(self.licitacion, "documentos_solicitados", []) or []
        docs_sorted = sorted(docs, key=lambda d: ((getattr(d, "categoria", "") or ""), (getattr(d, "nombre", "") or "")))
        for d in docs_sorted:
            row = self.tbl_docs.rowCount()
            self.tbl_docs.insertRow(row)
            ok = "✅" if bool(getattr(d, "presentado", False)) else "❌"
            cat = getattr(d, "categoria", "") or ""
            subs = getattr(d, "subsanable", "") or ""
            vals = [ok, getattr(d, "nombre", "") or "", cat, subs]
            for col, text in enumerate(vals):
                it = QTableWidgetItem(text)
                if col in (0, 3):
                    it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tbl_docs.setItem(row, col, it)
            if (subs == "No Subsanable") and (ok == "❌"):
                for c in range(self.tbl_docs.columnCount()):
                    it = self.tbl_docs.item(row, c)
                    if it:
                        it.setForeground(QColor(self.ui["danger"]))
        self.tbl_docs.resizeRowsToContents()

    # ------------------------ Competidores ------------------------
    def _populate_competidores(self):
        self.tree_comp.clear()

        def _norm(s: str) -> str:
            s = (s or "").strip()
            s = s.replace("➡️", "").replace("(Nuestra Oferta)", "")
            while "  " in s:
                s = s.replace("  ", " ")
            return s.upper()

        cron = getattr(self.licitacion, "cronograma", {}) or {}
        hito_eval = cron.get("Informe de Evaluacion Tecnica", {})
        estado_hito_cumplido = hito_eval.get("estado") == "Cumplido"
        estados_que_implican_fase_A_evaluada = {"Adjudicada", "Descalificado Fase B", "Sobre B Entregado"}
        fase_A_evaluada = estado_hito_cumplido or (getattr(self.licitacion, "estado", "") in estados_que_implican_fase_A_evaluada)

        ganadores_por_lote = {
            str(getattr(l, "numero", "")): (getattr(l, "ganador_nombre", "") or "").strip()
            for l in getattr(self.licitacion, "lotes", [])
        }
        nuestras_empresas = {_norm(str(getattr(e, "nombre", e))) for e in getattr(self.licitacion, "empresas_nuestras", [])}

        participantes = [o.__dict__ for o in getattr(self.licitacion, "oferentes_participantes", [])]
        nuestras = (
            ", ".join(str(getattr(e, "nombre", e)) for e in getattr(self.licitacion, "empresas_nuestras", []))
            or "Nuestras Empresas"
        )
        nuestras_ofertas = [
            {
                "lote_numero": getattr(l, "numero", ""),
                "monto": getattr(l, "monto_ofertado", 0),
                "paso_fase_A": getattr(l, "fase_A_superada", False),
            }
            for l in getattr(self.licitacion, "lotes", [])
            if bool(getattr(l, "participamos", False))
        ]
        participantes.append({"nombre": f"➡️ {nuestras} (Nuestra Oferta)", "es_nuestra": True, "ofertas_por_lote": nuestras_ofertas})

        for p in participantes:
            if fase_A_evaluada:
                p["monto_habilitado"] = sum(o.get("monto", 0) for o in p.get("ofertas_por_lote", []) if o.get("paso_fase_A", True))
            else:
                p["monto_habilitado"] = 0

        participantes_orden = sorted(
            participantes, key=lambda it: it["monto_habilitado"] if it["monto_habilitado"] > 0 else float("inf")
        )

        for p in participantes_orden:
            is_ours = bool(p.get("es_nuestra"))
            nombre = p.get("nombre", "")
            parent = QTreeWidgetItem(self.tree_comp)
            parent.setText(0, nombre)
            parent.setText(1, f"RD$ {sum(o.get('monto', 0) for o in p.get('ofertas_por_lote', [])):,.2f}")
            parent.setText(2, "RD$ {:,.2f}".format(p.get("monto_habilitado", 0) or 0))
            if fase_A_evaluada:
                any_ok = (
                    any(o.get("paso_fase_A", False) for o in p.get("ofertas_por_lote", []))
                    if not is_ours
                    else any(o.get("paso_fase_A", True) for o in p.get("ofertas_por_lote", []))
                )
                parent.setText(3, "Habilitado" if any_ok else "Descalificado")
            else:
                parent.setText(3, "Pendiente")

            nombre_participante_norm = _norm(nombre)
            nombres_en_padre = {x.strip() for x in nombre_participante_norm.split(",") if x.strip()}

            gano_alguno = 0

            for oferta in sorted(p.get("ofertas_por_lote", []), key=lambda o: str(o.get("lote_numero"))):
                lote_num = str(oferta.get("lote_numero"))
                lote_obj = next(
                    (l for l in getattr(self.licitacion, "lotes", []) if str(getattr(l, "numero", "")) == lote_num), None
                )
                lote_nombre = getattr(lote_obj, "nombre", "N/E") if lote_obj else "N/E"
                base = float(getattr(lote_obj, "monto_base", 0) or 0.0) if lote_obj else 0.0
                of_m = float(oferta.get("monto", 0) or 0.0)
                dif_pct = ((of_m - base) / base * 100.0) if base > 0 and of_m > 0 else 0.0

                child = QTreeWidgetItem(parent)
                child.setText(0, f"    ↳ Lote {lote_num}: {lote_nombre}")
                child.setText(1, f"RD$ {of_m:,.2f}")
                child.setText(4, f"RD$ {base:,.2f}" if base > 0 else "N/D")
                child.setText(5, f"{dif_pct:+.2f}%" if base > 0 and of_m > 0 else "N/D")
                if fase_A_evaluada:
                    paso_a = oferta.get("paso_fase_A", True) if is_ours else oferta.get("paso_fase_A", False)
                    child.setText(3, "✅" if paso_a else "❌")
                else:
                    child.setText(3, "⏳")

                ganador_real = (ganadores_por_lote.get(lote_num, "") or "").strip().upper()
                es_ganador = False
                if ganador_real:
                    if is_ours and ganador_real in nuestras_empresas:
                        es_ganador = True
                    elif ganador_real in nombres_en_padre:
                        es_ganador = True
                    elif nombre_participante_norm.startswith(ganador_real):
                        es_ganador = True

                child.setText(6, "Sí" if es_ganador else "No")
                if es_ganador:
                    gano_alguno += 1
                    for c in range(child.columnCount()):
                        child.setForeground(c, QColor(self.ui["success"]))

            if gano_alguno > 0:
                parent.setText(6, f"Sí ({gano_alguno})")
                for c in range(parent.columnCount()):
                    parent.setForeground(c, QColor(self.ui["success"]))

        self.tree_comp.expandAll()
        for i in range(7):
            self.tree_comp.resizeColumnToContents(i)

    # ------------------------ Exportar ------------------------
    def _export_report(self, formato: str):
        # Elegir nombre por extensión; ReportGenerator detecta por file_path
        ext = ".pdf" if formato == "pdf" else ".xlsx"
        title = f"Guardar como {formato.upper()}"
        default_name = f"Reporte_{str(getattr(self.licitacion, 'numero_proceso', 'proceso')).replace(' ', '_')}{ext}"
        path, _ = QFileDialog.getSaveFileName(self, title, default_name, "PDF (*.pdf);;Excel (*.xlsx)")
        if not path:
            return

        # Validaciones de disponibilidad con detalle de import
        if not REPORT_GENERATOR_AVAILABLE or ReportGenerator is None:
            return QMessageBox.warning(
                self,
                "Exportar",
                "ReportGenerator no está disponible en esta instalación.\n\n"
                f"Detalle del import:\n{REPORT_GENERATOR_IMPORT_ERROR}\n\n"
                "Asegúrate de que exista app/core/reporting/report_generator.py y que "
                "app/core/reporting/__init__.py exporte ReportGenerator.",
            )

        # Dependencias (opcionales, el propio ReportGenerator también valida)
        if formato == "pdf" and not REPORTLAB_AVAILABLE:
            return QMessageBox.warning(self, "Exportar", "La librería 'reportlab' no está instalada (pip install reportlab).")
        if formato == "excel" and not OPENPYXL_AVAILABLE:
            return QMessageBox.warning(self, "Exportar", "La librería 'openpyxl' no está instalada (pip install openpyxl).")

        try:
            gen = ReportGenerator()
            # Invocación tolerante: usa el método disponible
            if hasattr(gen, "generate_bid_results_report"):
                gen.generate_bid_results_report(self.licitacion, path)
            elif hasattr(gen, "generate_package_analysis_report"):
                gen.generate_package_analysis_report(self.licitacion, path)
            else:
                raise AttributeError(
                    "ReportGenerator no expone 'generate_bid_results_report' ni 'generate_package_analysis_report'."
                )

            QMessageBox.information(self, "Exportar", f"Reporte guardado en:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Exportar", f"No se pudo exportar el reporte:\n{e}")

    # ------------------------ Utilidades ------------------------
    def _tune_table(self, t: QTableWidget):
        t.setAlternatingRowColors(True)
        t.verticalHeader().setVisible(False)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        t.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        hh = t.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # QSS con tema
        t.setStyleSheet(
            f"QTableWidget{{gridline-color:{self.ui['border']}; background:{self.ui['base']}; "
            f"alternate-background-color:{self.ui['alt']}; selection-background-color:{self.ui['accent']}; "
            f"selection-color:#ffffff;}} "
            f"QHeaderView::section{{background:{self.ui['alt']}; padding:6px; border:1px solid {self.ui['border']}; "
            f"font-weight:600; color:{self.ui['text']}; min-height:28px;}}"
        )

    def _new_canvas(self):
        fig = Figure(figsize=(5.2, 2.8), dpi=100, facecolor=self.ui["base"])
        return FigureCanvas(fig)

    def _wrap_canvas(self, title: str, canvas):
        box = QGroupBox(title)
        box.setStyleSheet(self._card_stylesheet())
        v = QVBoxLayout(box)
        v.addWidget(canvas, 1)
        return box

    def _money(self, v: float) -> str:
        try:
            return "RD$ {:,.2f}".format(float(v or 0.0))
        except Exception:
            return "RD$ 0.00"

    def closeEvent(self, event):
        try:
            # Guardar último estado del splitter y el tab activo en el JSON
            try:
                set_splitter_sizes("ReportWindow", "split_mid", self.split_mid.sizes())
                set_tab_index("ReportWindow", "main", int(self.tabs.currentIndex()))
            except Exception:
                pass
        finally:
            super().closeEvent(event)

    def _icon(self, std: QStyle.StandardPixmap, semantic_name: str = "") -> QIcon:
        """
        Devuelve un icono. Intenta cargar app.ui.icons.icon_loader.get_icon en tiempo de ejecución.
        Si falla o no existe, usa el QStyle nativo como fallback.
        """
        # Cachear el loader en la instancia
        if not hasattr(self, "_icon_loader_func"):
            self._icon_loader_func = None
            try:
                import importlib
                mod = importlib.import_module("app.ui.icons.icon_loader")
                func = getattr(mod, "get_icon", None)
                if callable(func):
                    self._icon_loader_func = func
            except Exception:
                self._icon_loader_func = None

        # 1) Loader opcional (si existe) usando nombre semántico
        if callable(getattr(self, "_icon_loader_func", None)) and semantic_name:
            try:
                return self._icon_loader_func(semantic_name)  # type: ignore[misc]
            except Exception:
                pass

        # 2) Fallback nativo
        return self.style().standardIcon(std)