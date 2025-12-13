from __future__ import annotations
from typing import Dict, Any, List, Optional, Callable
import copy
import traceback  # DEBUG: para imprimir stack

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget, QTableWidgetItem,
    QAbstractItemView, QHeaderView, QDialogButtonBox, QPushButton, QMessageBox,
    QFileDialog, QWidget, QLabel, QStyle, QCheckBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush, QFont, QIcon

from app.core.models import Licitacion
from app.core.reporting.report_generator import ReportGenerator, REPORTLAB_AVAILABLE, OPENPYXL_AVAILABLE

# Titanium Construct color palette for evaluation results
GREEN_BG = QBrush(QColor("#D1FAE5"))      # Success background (winner)
GREEN_TEXT = QColor("#065F46")             # Success text (winner)
INDIGO_BG = QBrush(QColor("#EEF2FF"))     # Info background (our company)
INDIGO_TEXT = QColor("#4F46E5")            # Info text (our company)
RED_BG = QBrush(QColor("#FEF2F2"))        # Danger background (disqualified)
RED_TEXT = QColor("#DC2626")               # Danger text (disqualified)

FONT_BOLD = QFont()
FONT_BOLD.setBold(True)


class DialogoResultadosEvaluacion(QDialog):
    COL_NUM = 0
    COL_POS = 1
    COL_PART = 2
    COL_CALIF = 3
    COL_PTEC = 4
    COL_MONTO = 5
    COL_PECO = 6
    COL_PFIN = 7
    COL_DESC = 8

    def __init__(self,
                 parent: QWidget,
                 licitacion: Licitacion,
                 resultados_por_lote: Dict[str, List[Dict[str, Any]]],
                 adjudicados: Optional[Dict[str, str]] = None,
                 metodo: Optional[str] = None,
                 datos_param: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Resultados de la Evaluación de Ofertas")
        self.setModal(True)
        self.setMinimumSize(1100, 620)
        self.setWindowFlags(self.windowFlags()
                            | Qt.WindowType.WindowSystemMenuHint
                            | Qt.WindowType.WindowMinimizeButtonHint
                            | Qt.WindowType.WindowMaximizeButtonHint)
        self.setSizeGripEnabled(True)

        self.licitacion = licitacion
        self.resultados_por_lote = resultados_por_lote or {}
        self.adjudicados = adjudicados or self._inferir_adjudicados_de_flags(self.resultados_por_lote)
        self.metodo = metodo or ""
        self.datos_param = datos_param or {}

        self._parent_tab = parent
        self._parent_win = getattr(parent, "parent_window", None)
        self._db = getattr(parent, "db", None)

        # Reporter
        self.reporter: Optional[ReportGenerator] = None
        self._resolve_reporter()

        # Banner/Simulación
        self._fallas_base = copy.deepcopy(getattr(self.licitacion, "fallas_fase_a", []))
        self._sim_desc_raw: set[str] = set()  # nombres "raw" simulados
        self._ui_busy = False

        print("[DEBUG][DialogoResultados] __init__ - resultados_por_lote keys:",
              list(self.resultados_por_lote.keys()))

        # Mapa Nº global
        todos = sorted(list({
            r.get("participante", "")
            for lst in self.resultados_por_lote.values() for r in lst
        }))
        self.participante_map = {n: i for i, n in enumerate(todos, start=1)}

        self._build_ui()
        self._populate_tabs()

    # ---------- utilidades ----------
    def _resolve_reporter(self):
        for obj in [self._parent_tab, self.window()]:
            rep = getattr(obj, "reporter", None)
            if rep is not None:
                self.reporter = rep
                break
        if self.reporter is None:
            try:
                self.reporter = ReportGenerator()
            except Exception:
                self.reporter = None

    def _find_method(self, obj: Any, candidates: List[str]) -> Optional[Callable]:
        if obj is None:
            return None
        for name in candidates:
            fn = getattr(obj, name, None)
            if callable(fn):
                print(f"[DEBUG][Resultados] Método encontrado: {type(obj).__name__}.{name}")
                return fn
        return None

    def _inferir_adjudicados_de_flags(self, resultados_por_lote: Dict[str, List[Dict[str, Any]]]) -> Dict[str, str]:
        adj = {}
        for lote, lista in resultados_por_lote.items():
            ganador = next((r.get("participante") for r in lista if r.get("es_ganador")), None)
            if ganador:
                adj[str(lote)] = ganador
        return adj

    # ---------- UI ----------
    def _build_ui(self):
        main = QVBoxLayout(self)

        banner = QLabel("Evaluación preliminar (no adjudica ni aplica ganadores). Use Exportar para compartir.")
        banner.setStyleSheet(
            "background:#FFF3CD; color:#7A5E00; border:1px solid #FFE69C; padding:6px; border-radius:4px;")
        main.addWidget(banner)

        self.tabs = QTabWidget()
        main.addWidget(self.tabs, stretch=1)

        btns = QDialogButtonBox()
        self.btn_export_pdf = btns.addButton("Exportar a PDF", QDialogButtonBox.ButtonRole.ActionRole)
        self.btn_export_pdf.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        self.btn_export_pdf.setProperty("class", "primary")
        self.btn_export_xlsx: Optional[QPushButton] = None
        if OPENPYXL_AVAILABLE:
            self.btn_export_xlsx = btns.addButton("Exportar a Excel", QDialogButtonBox.ButtonRole.ActionRole)
            self.btn_export_xlsx.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
            self.btn_export_xlsx.setProperty("class", "primary")
            self.btn_export_xlsx.clicked.connect(lambda: self._exportar("xlsx"))
        close_btn = btns.addButton("Cerrar", QDialogButtonBox.ButtonRole.RejectRole)
        close_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton))
        self.btn_export_pdf.clicked.connect(lambda: self._exportar("pdf"))
        btns.rejected.connect(self.reject)

        self.chk_simul = QCheckBox("Modo simulación (no guardar descalificaciones)")
        self.chk_simul.setChecked(True)

        footer = QHBoxLayout()
        footer.addWidget(self.chk_simul)
        footer.addStretch(1)
        footer.addWidget(btns)
        main.addLayout(footer)

        exp_enabled = self.reporter is not None and ((REPORTLAB_AVAILABLE) or (OPENPYXL_AVAILABLE))
        self.btn_export_pdf.setEnabled(exp_enabled and REPORTLAB_AVAILABLE)
        if self.btn_export_xlsx:
            self.btn_export_xlsx.setEnabled(exp_enabled and OPENPYXL_AVAILABLE)
        if not exp_enabled:
            tip = "Exportación no disponible."
            if not self.reporter:
                tip += " (ReportGenerator no disponible)"
            if not REPORTLAB_AVAILABLE:
                tip += " (reportlab no instalado)"
            self.btn_export_pdf.setToolTip(tip)

    def _make_tab_title(self, lote_num: str) -> str:
        lote_obj = next((l for l in getattr(self.licitacion, "lotes", [])
                         if str(getattr(l, "numero", "")) == lote_num), None)
        texto = f"Lote {lote_num}"
        if lote_obj:
            nom = getattr(lote_obj, "nombre", "")
            if nom:
                texto += f": {nom[:30]}"
        return texto

    def _get_field(self, res: Dict[str, Any], names: List[str], default: float = 0.0) -> float:
        for n in names:
            if n in res:
                try:
                    return float(res[n] or 0.0)
                except Exception:
                    return default
        return default

    def _populate_tabs(self):
        print("[DEBUG][DialogoResultados] _populate_tabs - keys antes de ordenar:",
              list(self.resultados_por_lote.keys()))
        self.tabs.clear()

        def _orden_lote_key(v: Any) -> tuple[int, Any]:
            s = str(v)
            if s.isdigit():
                return (0, int(s))
            return (1, s)

        try:
            ordenados = sorted(self.resultados_por_lote.keys(), key=_orden_lote_key)
            print("[DEBUG][DialogoResultados] _populate_tabs - keys ordenados:", ordenados)
        except Exception as e:
            print("[DEBUG][DialogoResultados] ERROR ordenando keys en _populate_tabs:", repr(e))
            raise

        for lote_num in ordenados:
            tab = QWidget()
            layout = QVBoxLayout(tab)
            table = QTableWidget(0, 9)
            table.setHorizontalHeaderLabels([
                "Nº", "Pos.", "Participante", "Califica",
                "P. Téc.", "Monto", "P. Eco.", "P. Final", "Desc.?"
            ])
            table.verticalHeader().setVisible(False)
            table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
            table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            table.horizontalHeader().setSectionResizeMode(self.COL_PART, QHeaderView.ResizeMode.Stretch)
            table.horizontalHeader().setSectionResizeMode(self.COL_PTEC, QHeaderView.ResizeMode.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(self.COL_MONTO, QHeaderView.ResizeMode.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(self.COL_PECO, QHeaderView.ResizeMode.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(self.COL_PFIN, QHeaderView.ResizeMode.ResizeToContents)
            layout.addWidget(table)
            self.tabs.addTab(tab, self._make_tab_title(str(lote_num)))
            self._fill_table_for_lote(table, str(lote_num), self.resultados_por_lote.get(lote_num, []))
            table.itemChanged.connect(
                lambda item, t=table, ln=str(lote_num): self._on_item_changed(item, t, ln)
            )

    def _fill_table_for_lote(self, table: QTableWidget, lote_num: str, filas: List[Dict[str, Any]]):
        table.blockSignals(True)
        table.setRowCount(0)
        pos = 0
        for res in filas:
            pos += 1
            participante = res.get("participante", "")
            califica = bool(res.get("califica_tecnicamente", False))
            ptec = self._get_field(res, ["puntaje_tecnico", "tec", "tec_pct"])
            monto = self._get_field(res, ["monto_ofertado", "monto"])
            peco = self._get_field(res, ["puntaje_economico", "eco", "eco_pct"])
            pfin = self._get_field(res, ["puntaje_final", "total"])

            row = table.rowCount()
            table.insertRow(row)

            it_num = QTableWidgetItem(str(self.participante_map.get(participante, "")))
            it_num.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_pos = QTableWidgetItem(str(pos))
            it_pos.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_part = QTableWidgetItem(participante)
            it_part.setData(Qt.ItemDataRole.UserRole, participante)
            it_cal = QTableWidgetItem("Sí" if califica else "NO")
            it_cal.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_ptec = QTableWidgetItem(f"{ptec:.2f}")
            it_ptec.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            try:
                import locale
                locale.setlocale(locale.LC_ALL, '')
                monto_txt = locale.currency(monto, grouping=True)
            except Exception:
                monto_txt = f"RD$ {monto:,.2f}"
            it_monto = QTableWidgetItem(monto_txt)
            it_monto.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            it_monto.setData(Qt.ItemDataRole.UserRole, float(monto))
            it_peco = QTableWidgetItem(f"{peco:.2f}")
            it_peco.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_pfin = QTableWidgetItem(f"{pfin:.2f}")
            it_pfin.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            it_desc = QTableWidgetItem("Descalificar")
            it_desc.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_desc.setFlags(Qt.ItemFlag.ItemIsUserCheckable |
                             Qt.ItemFlag.ItemIsEnabled |
                             Qt.ItemFlag.ItemIsSelectable)

            raw = participante.replace("⚑ ", "").replace("➡️ ", "")
            ya_desc_base = any(
                (f.get("documento_id") == -1 and
                 (f.get("participante_nombre") or "").replace("➡️ ", "") == raw)
                for f in self._fallas_base
            )
            ya_desc_sim = raw in self._sim_desc_raw
            it_desc.setCheckState(
                Qt.CheckState.Checked if (ya_desc_base or ya_desc_sim)
                else Qt.CheckState.Unchecked
            )

            table.setItem(row, self.COL_NUM, it_num)
            table.setItem(row, self.COL_POS, it_pos)
            table.setItem(row, self.COL_PART, it_part)
            table.setItem(row, self.COL_CALIF, it_cal)
            table.setItem(row, self.COL_PTEC, it_ptec)
            table.setItem(row, self.COL_MONTO, it_monto)
            table.setItem(row, self.COL_PECO, it_peco)
            table.setItem(row, self.COL_PFIN, it_pfin)
            table.setItem(row, self.COL_DESC, it_desc)

            es_adj = bool(self.adjudicados and
                          lote_num in self.adjudicados and
                          self.adjudicados[lote_num] == participante)
            is_winner = bool(res.get("es_ganador")) or (pos == 1 and califica)
            
            # Check if it's our company
            # Note: The application marks our companies with ⚑ or ➡️ symbols in participant names
            # This is handled elsewhere in the codebase (see oferente handling logic)
            is_nuestra = "⚑" in participante or "➡️" in participante
            
            # Check if disqualified
            is_disqualified = not califica or (ya_desc_base or ya_desc_sim)
            
            # Apply colors based on status (priority: disqualified > our company > winner)
            if is_disqualified:
                for c in range(table.columnCount()):
                    item = table.item(row, c)
                    if item:
                        item.setBackground(RED_BG)
                        item.setForeground(RED_TEXT)
            elif is_nuestra:
                for c in range(table.columnCount()):
                    item = table.item(row, c)
                    if item:
                        item.setBackground(INDIGO_BG)
                        item.setForeground(INDIGO_TEXT)
                        item.setFont(FONT_BOLD)
            elif is_winner or es_adj:
                for c in range(table.columnCount()):
                    item = table.item(row, c)
                    if item:
                        item.setBackground(GREEN_BG)
                        item.setForeground(GREEN_TEXT)
                        item.setFont(FONT_BOLD)

        table.blockSignals(False)

    # ---------- Exportación ----------
    def _exportar(self, kind: str = "pdf"):
        print(f"[DEBUG][DialogoResultados] _exportar llamado. kind={kind}")
        print("[DEBUG][DialogoResultados] reporter:", self.reporter)
        print("[DEBUG][DialogoResultados] REPORTLAB_AVAILABLE:", REPORTLAB_AVAILABLE,
              "OPENPYXL_AVAILABLE:", OPENPYXL_AVAILABLE)
        print("[DEBUG][DialogoResultados] resultados_por_lote keys al exportar:",
              list(self.resultados_por_lote.keys()))

        if not self.reporter:
            QMessageBox.information(self, "No Disponible", "No hay ReportGenerator disponible.")
            return
        if kind == "pdf" and not REPORTLAB_AVAILABLE:
            QMessageBox.information(self, "No Disponible", "reportlab no está instalado.")
            return
        if kind == "xlsx" and not OPENPYXL_AVAILABLE:
            QMessageBox.information(self, "No Disponible", "openpyxl no está instalado.")
            return

        default_ext = ".pdf" if kind == "pdf" else ".xlsx"
        default_name = f"Evaluacion_{getattr(self.licitacion, 'numero_proceso', '')}{default_ext}"
        filter_str = "Archivos PDF (*.pdf)" if kind == "pdf" else "Archivos de Excel (*.xlsx)"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Resultados de Evaluación",
            default_name,
            filter_str
        )
        print("[DEBUG][DialogoResultados] ruta seleccionada:", path)
        if not path:
            print("[DEBUG][DialogoResultados] Cancelado por el usuario.")
            return
        if not path.lower().endswith(default_ext):
            path += default_ext
        print("[DEBUG][DialogoResultados] path final:", path)

        try:
            # Priorizar SIEMPRE el reporte de evaluación desde esta ventana
            if hasattr(self.reporter, "generate_evaluation_report"):
                print("[DEBUG][DialogoResultados] Llamando reporter.generate_evaluation_report(...)")
                print("[DEBUG][DialogoResultados] Tipo de resultados_por_lote:",
                      type(self.resultados_por_lote),
                      "keys:", list(self.resultados_por_lote.keys()))
                self.reporter.generate_evaluation_report(
                    self.licitacion,
                    self.resultados_por_lote,
                    path
                )
            elif hasattr(self.reporter, "generate_package_analysis_report"):
                print("[DEBUG][DialogoResultados] Llamando reporter.generate_package_analysis_report(...) [FALLBACK]")
                self.reporter.generate_package_analysis_report(self.licitacion, path)
            else:
                raise RuntimeError(
                    "ReportGenerator no tiene generate_evaluation_report "
                    "ni generate_package_analysis_report."
                )
            QMessageBox.information(self, "Éxito", f"Archivo exportado en:\n{path}")
        except Exception as e:
            print("[DEBUG][DialogoResultados] ERROR en _exportar:", repr(e))
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"No se pudo exportar:\n{e}")