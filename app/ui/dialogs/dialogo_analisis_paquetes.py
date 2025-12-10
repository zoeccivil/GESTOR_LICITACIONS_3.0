# app/ui/dialogs/dialogo_analisis_paquetes.py
from __future__ import annotations
import locale
import copy
import traceback
from typing import TYPE_CHECKING, List, Dict, Any, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QLabel, QScrollArea,
    QWidget, QDialogButtonBox, QMessageBox, QFileDialog, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush, QFont

from app.core.models import Licitacion
from app.core.reporting.report_generator import ReportGenerator, OPENPYXL_AVAILABLE, REPORTLAB_AVAILABLE

if TYPE_CHECKING:
    from app.ui.windows.main_window import MainWindow

# Locale
try:
    locale.setlocale(locale.LC_ALL, '')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'es_ES.UTF-8')
    except locale.Error:
        print("Advertencia [Analisis Paquetes]: No se pudo setear locale para moneda.")
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QLabel, QScrollArea,
    QWidget, QDialogButtonBox, QMessageBox, QFileDialog, QSizePolicy,
    QStyle, QFrame, QSplitter
)
from PyQt6.QtGui import QColor, QBrush, QFont, QIcon

# Colores y fuentes
COLOR_MIN_OFFER_BG = QColor("#d4edda")
BRUSH_MIN_OFFER_BG = QBrush(COLOR_MIN_OFFER_BG)
FONT_BOLD = QFont()
FONT_BOLD.setBold(True)

class DialogoAnalisisPaquetes(QDialog):
    def __init__(self, parent: QWidget, licitacion: Licitacion):
        super().__init__(parent)
        self.licitacion = licitacion
        self.reporter: Optional[ReportGenerator] = None

        # Buscar reporter en cadena de padres
        current_parent = parent
        while current_parent is not None:
            self.reporter = getattr(current_parent, 'reporter', None)
            if self.reporter is not None:
                print(f"[DialogoAnalisisPaquetes] ReportGenerator encontrado en: {type(current_parent).__name__}")
                break
            if hasattr(current_parent, 'parent') and callable(current_parent.parent):
                current_parent = current_parent.parent()
            else:
                break

# Dentro de __init__ de DialogoAnalisisPaquetes, después del bloque que busca en los padres y window()
        if not self.reporter:
            try:
                # Fallback: crea una instancia local
                self.reporter = ReportGenerator()
                print("[DialogoAnalisisPaquetes] ReportGenerator instanciado localmente (fallback).")
            except Exception as e:
                print(f"[DialogoAnalisisPaquetes WARN] No se pudo instanciar ReportGenerator: {e}")

        if not self.reporter:
            print("[DialogoAnalisisPaquetes WARN] No se encontró instancia de ReportGenerator. Exportación deshabilitada.")

        self.setWindowTitle(f"Análisis de Paquetes: {getattr(self.licitacion, 'numero_proceso', '')}")
        self.setMinimumSize(1000, 700)
        # Habilitar botones de minimizar/maximizar y menú de sistema en el título
        self.setWindowFlag(Qt.WindowType.WindowSystemMenuHint, True)
        self.setWindowFlag(Qt.WindowType.WindowMinimizeButtonHint, True)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)
        # Permitir redimensionar con grip en esquina inferior derecha
        self.setSizeGripEnabled(True)
        # UI elements
        self.table_pivot: QTableWidget | None = QTableWidget()
        self.summary_content_widget: QWidget | None = QWidget()
        self.summary_layout: QVBoxLayout | None = QVBoxLayout(self.summary_content_widget)

        # Datos calculados
        self._matriz_ofertas: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._all_competitors: List[str] = []

        self._build_ui()
        self._load_and_display_data()
# Dentro de la clase DialogoAnalisisPaquetes: añade estos helpers

    def _add_section_header(self, text: str,
                            pixmap_enum: QStyle.StandardPixmap,
                            font_size: int = 11,
                            margin_top: int | None = None,
                            color: str | None = None) -> None:
        """
        Inserta un encabezado con icono nativo de Qt y texto en negrita.
        """
        if self.summary_layout is None:
            return
        container = QWidget()
        if margin_top:
            container.setStyleSheet(f"margin-top: {margin_top}px;")
        from PyQt6.QtWidgets import QHBoxLayout
        h = QHBoxLayout(container)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)

        # Icono nativo (fallback a • si no hay icono)
        icon_lbl = QLabel()
        try:
            icon = self.style().standardIcon(pixmap_enum)
        except Exception:
            icon = QIcon()
        if icon and not icon.isNull():
            icon_lbl.setPixmap(icon.pixmap(18, 18))
        else:
            icon_lbl.setText("•")
            icon_lbl.setStyleSheet("font-size: 14pt; color: #666666;")

        # Texto del título
        title_lbl = QLabel(text)
        title_lbl.setTextFormat(Qt.TextFormat.PlainText)
        css = f"font-weight: 600; font-size: {font_size}pt;"
        if color:
            css += f" color: {color};"
        title_lbl.setStyleSheet(css)

        h.addWidget(icon_lbl, 0, Qt.AlignmentFlag.AlignTop)
        h.addWidget(title_lbl, 1, Qt.AlignmentFlag.AlignVCenter)
        self.summary_layout.addWidget(container)

    def _add_separator(self, margin_top: int = 12, margin_bottom: int = 8) -> None:
        """
        Inserta una línea separadora marcada entre secciones.
        """
        if self.summary_layout is None:
            return
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        # Estilo más visible
        line.setStyleSheet(f"""
            QFrame {{
                color: #BDBDBD;
                margin-top: {margin_top}px;
                margin-bottom: {margin_bottom}px;
            }}
        """)
        self.summary_layout.addWidget(line)

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # Splitter vertical para permitir redimensionar entre la tabla y el resumen
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        main_splitter.setChildrenCollapsible(False)

        # --- 1. Tabla Pivote ---
        group_pivot = QGroupBox("Tabla Pivote de Ofertas (Lotes vs. Competidores)")
        layout_pivot = QVBoxLayout(group_pivot)
        self.table_pivot.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_pivot.setAlternatingRowColors(True)
        self.table_pivot.setSortingEnabled(True)
        layout_pivot.addWidget(self.table_pivot)

        # Asegurar que el grupo pivote expanda
        group_pivot.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # --- 2. Resumen del Análisis ---
        group_summary = QGroupBox("Resultados del Análisis")
        layout_summary_outer = QVBoxLayout(group_summary)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        assert self.summary_content_widget is not None
        assert self.summary_layout is not None
        self.summary_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll_area.setWidget(self.summary_content_widget)
        layout_summary_outer.addWidget(scroll_area)

        # Asegurar que el grupo resumen expanda
        group_summary.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Añadir ambos grupos al splitter
        main_splitter.addWidget(group_pivot)
        main_splitter.addWidget(group_summary)
        # Tamaños iniciales (puedes ajustar a tu gusto)
        main_splitter.setSizes([450, 250])
        # Opcional: factores de estiramiento
        main_splitter.setStretchFactor(0, 3)  # Tabla Pivote
        main_splitter.setStretchFactor(1, 2)  # Resumen

        # Insertar el splitter en el layout principal
        main_layout.addWidget(main_splitter)

        # --- 3. Botones Inferiores ---
        button_box = QDialogButtonBox()
        btn_export = button_box.addButton("Exportar Reporte...", QDialogButtonBox.ButtonRole.ActionRole)
        btn_export.clicked.connect(self._exportar_analisis)
        export_enabled = (
            self.reporter is not None
            and hasattr(self.reporter, 'generate_package_analysis_report')
            and (OPENPYXL_AVAILABLE or REPORTLAB_AVAILABLE)
        )
        print(f"[DEBUG] reporter? {bool(self.reporter)} "
              f"has_generate={hasattr(self.reporter, 'generate_package_analysis_report') if self.reporter else False} "
              f"OPENPYXL_AVAILABLE={OPENPYXL_AVAILABLE} REPORTLAB_AVAILABLE={REPORTLAB_AVAILABLE} "
              f"export_enabled={export_enabled}")
        btn_export.setEnabled(export_enabled)
        if not export_enabled:
            tooltip = "Exportación no disponible."
            if not self.reporter:
                tooltip += " (no hay ReportGenerator en la jerarquía de padres y no se pudo instanciar)"
            elif not hasattr(self.reporter, 'generate_package_analysis_report'):
                tooltip += " (el ReportGenerator no implementa generate_package_analysis_report)"
            if not (OPENPYXL_AVAILABLE or REPORTLAB_AVAILABLE):
                tooltip += " (faltan librerías openpyxl/reportlab)"
            btn_export.setToolTip(tooltip)
        btn_close = button_box.addButton("Cerrar", QDialogButtonBox.ButtonRole.RejectRole)
        btn_close.clicked.connect(self.reject)
        main_layout.addWidget(button_box, alignment=Qt.AlignmentFlag.AlignRight)

    def _load_and_display_data(self):
        print("\n--- [DialogoAnalisisPaquetes] Iniciando _load_and_display_data ---")
        try:
            print("[DEBUG] Llamando a licitacion.get_matriz_ofertas()...")
            self._matriz_ofertas = self.licitacion.get_matriz_ofertas()
            print(f"[DEBUG] _matriz_ofertas (base): {len(self._matriz_ofertas)} lotes")

            print("[DEBUG] Llamando a _add_our_offers_to_matrix...")
            matriz_con_nuestra = self._add_our_offers_to_matrix(self._matriz_ofertas)
            print(f"[DEBUG] matriz_con_nuestra: {len(matriz_con_nuestra)} lotes")

            all_participants = set()
            for _, ofertas_lote in matriz_con_nuestra.items():
                all_participants.update(ofertas_lote.keys())
            self._all_competitors = sorted(list(all_participants))
            print(f"[DEBUG] _all_competitors (ordenados): {self._all_competitors}")

            print("[DEBUG] Llamando a _populate_pivot_table...")
            self._populate_pivot_table()

            print("[DEBUG] Llamando a _populate_summary...")
            self._populate_summary(matriz_con_nuestra)
            print("--- [DialogoAnalisisPaquetes] _load_and_display_data completado ---")

        except AttributeError as e:
            print(f"[ERROR] AttributeError en _load_and_display_data: {e}")
            QMessageBox.critical(self, "Error de Modelo",
                                 f"El objeto Licitacion no tiene el método necesario.\nVerifica 'get_matriz_ofertas()'.\nError: {e}")
            self._clear_ui_on_error("Error al cargar datos.")
        except Exception as e:
            print(f"[ERROR] Exception en _load_and_display_data: {e}")
            QMessageBox.critical(self, "Error al Cargar Datos", f"Ocurrió un error: {e}")
            traceback.print_exc()
            self._clear_ui_on_error("Error al cargar datos.")

    def _add_our_offers_to_matrix(self, original_matrix: Dict) -> Dict:
        matrix_copy = copy.deepcopy(original_matrix)
        for lote in getattr(self.licitacion, "lotes", []):
            if getattr(lote, 'participamos', False) and float(getattr(lote, 'monto_ofertado', 0) or 0) > 0:
                if getattr(lote, 'fase_A_superada', False):
                    lote_num_str = str(getattr(lote, 'numero', ''))
                    empresa_nuestra = f"➡️ {lote.empresa_nuestra or 'Nuestra Oferta'}"
                    matrix_copy.setdefault(lote_num_str, {})[empresa_nuestra] = {'monto': lote.monto_ofertado}
        return matrix_copy

    def _populate_pivot_table(self):
        print("[DEBUG] Iniciando _populate_pivot_table...")
        if self.table_pivot is None:
            print("[DEBUG] table_pivot es None.")
            return

        competidores_reales = sorted([c for c in self._all_competitors if isinstance(c, str) and not c.startswith("➡️ ")])
        print(f"[DEBUG] Competidores reales para tabla: {competidores_reales}")

        if not self._matriz_ofertas or not competidores_reales:
            print("[DEBUG] No hay matriz base o competidores reales. Mostrando mensaje en tabla.")
            self.table_pivot.clear()
            self.table_pivot.setRowCount(1)
            self.table_pivot.setColumnCount(1)
            self.table_pivot.setHorizontalHeaderLabels(["Información"])
            item = QTableWidgetItem("No hay ofertas válidas de competidores para mostrar en esta tabla.")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            item.setBackground(QBrush(QColor("#EEEEEE")))
            self.table_pivot.setItem(0, 0, item)
            self.table_pivot.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            self.table_pivot.verticalHeader().setVisible(False)
            return

        def _lote_sort_key(v: Any):
            s = str(v)
            return int(s) if s.isdigit() else s

        lotes_ordenados = sorted(self._matriz_ofertas.keys(), key=_lote_sort_key)
        print(f"[DEBUG] Lotes para tabla: {lotes_ordenados}")

        self.table_pivot.setRowCount(len(lotes_ordenados))
        self.table_pivot.setColumnCount(1 + len(competidores_reales))
        headers = ['Lote'] + competidores_reales
        self.table_pivot.setHorizontalHeaderLabels(headers)
        self.table_pivot.verticalHeader().setVisible(True)

        for row, lote_num in enumerate(lotes_ordenados):
            ofertas_lote = self._matriz_ofertas.get(lote_num, {})
            montos_validos = [d['monto'] for d in ofertas_lote.values() if isinstance(d.get('monto'), (int, float)) and d['monto'] > 0]
            monto_minimo_lote = min(montos_validos) if montos_validos else float('inf')

            lote_obj = next((l for l in getattr(self.licitacion, "lotes", []) if str(getattr(l, 'numero', '')) == str(lote_num)), None)
            nombre_lote = getattr(lote_obj, "nombre", 'N/D') if lote_obj else 'N/D'
            item_lote = QTableWidgetItem(f"Lote {str(lote_num)}: {nombre_lote}")
            item_lote.setData(Qt.ItemDataRole.UserRole, str(lote_num))
            self.table_pivot.setItem(row, 0, item_lote)

            for col, competidor in enumerate(competidores_reales, start=1):
                oferta_data = ofertas_lote.get(competidor)
                monto = oferta_data.get('monto') if oferta_data else None
                item_monto = QTableWidgetItem()
                if isinstance(monto, (int, float)) and monto > 0:
                    try:
                        monto_str = locale.currency(monto, grouping=True)
                    except Exception:
                        monto_str = f"{monto:,.2f}"
                    item_monto.setText(monto_str)
                    item_monto.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    item_monto.setData(Qt.ItemDataRole.UserRole, float(monto))
                    item_monto.setToolTip(f"{competidor}\nOferta: {monto_str}")
                    if monto == monto_minimo_lote:
                        item_monto.setBackground(BRUSH_MIN_OFFER_BG)
                        item_monto.setFont(FONT_BOLD)
                else:
                    item_monto.setText("---")
                    item_monto.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    item_monto.setData(Qt.ItemDataRole.UserRole, float('inf'))
                    item_monto.setToolTip(f"{competidor}\nSin oferta válida")
                self.table_pivot.setItem(row, col, item_monto)
            print(f"[DEBUG] Fila {row} poblada para Lote {str(lote_num)}.")

        self.table_pivot.resizeColumnsToContents()
        self.table_pivot.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.table_pivot.setColumnWidth(0, 250)
        for c in range(1, self.table_pivot.columnCount()):
            self.table_pivot.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeMode.Interactive)
        print("[DEBUG] _populate_pivot_table completado.")

    def _populate_summary(self, matriz_con_nuestra: Dict):
        """Llena el área de resumen con el análisis de texto."""
        # DEBUG rápido
        print("[DEBUG] _populate_summary: entrando")
        try:
            matriz_ofertas = self.licitacion.get_matriz_ofertas()
        except Exception as e:
            print("[DEBUG] get_matriz_ofertas: EXCEPTION:", repr(e))
            matriz_ofertas = {}
        try:
            sample_keys = list(matriz_ofertas.keys())[:5]
            print("[DEBUG] matriz_ofertas:", repr(matriz_ofertas)[:1200])
            print("[DEBUG] tipos_claves_matriz:", {str(k): type(k).__name__ for k in sample_keys})
        except Exception:
            pass

        mejor_individual = None
        mejor_por_oferente = None
        try:
            try:
                mejor_individual = self.licitacion.calcular_mejor_paquete_individual(matriz_ofertas)
            except TypeError:
                mejor_individual = self.licitacion.calcular_mejor_paquete_individual()
        except Exception as e:
            print("[DEBUG] calcular_mejor_paquete_individual: EXCEPTION:", repr(e))
        try:
            try:
                mejor_por_oferente = self.licitacion.calcular_mejor_paquete_por_oferente(matriz_ofertas)
            except TypeError:
                mejor_por_oferente = self.licitacion.calcular_mejor_paquete_por_oferente()
        except Exception as e:
            print("[DEBUG] calcular_mejor_paquete_por_oferente: EXCEPTION:", repr(e))

        print("[DEBUG] mejor_individual:", repr(mejor_individual)[:1200])
        print("[DEBUG] mejor_por_oferente:", repr(mejor_por_oferente)[:1200])

        # IMPORTANTE: comprobar None, no flogear por "layout vacío"
        if self.summary_layout is None or self.summary_content_widget is None:
            print("[DEBUG] Layout/Widget de resumen es None.")
            return

        # Limpiar contenido previo
        while self.summary_layout.count():
            item = self.summary_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        print("[DEBUG] Layout de resumen limpiado.")

        if not matriz_con_nuestra:
            print("[DEBUG] matriz_con_nuestra está vacía. Mostrando mensaje.")
            self._add_summary_label("<i>No hay ofertas habilitadas (incluyendo la nuestra) para generar el análisis.</i>")
            return

        # Sección 1
        print("[DEBUG] Añadiendo Sección 1: Ofertas Más Bajas...")
        self._add_summary_label("📊 Análisis de Ofertas Más Bajas por Lote", font_size=11)
        def _lote_sort_key(v: Any):
            s = str(v)
            return int(s) if s.isdigit() else s
        lotes_ordenados = sorted(matriz_con_nuestra.keys(), key=_lote_sort_key)
        found_data_s1 = False
        for lote_num in lotes_ordenados:
            ofertas_lote = matriz_con_nuestra.get(lote_num, {})
            lote_obj = next((l for l in self.licitacion.lotes if str(l.numero) == str(lote_num)), None)
            if not lote_obj:
                continue

            base_lote = float(getattr(lote_obj, 'monto_base', 0) or 0.0)
            ofertas_validas = [
                (data['monto'], oferente)
                for oferente, data in ofertas_lote.items()
                if isinstance(data.get('monto'), (int, float)) and data['monto'] > 0
            ]
            print(f"[DEBUG] S1 - Lote {str(lote_num)}: {len(ofertas_validas)} ofertas válidas encontradas.")
            if not ofertas_validas:
                continue

            ofertas_ordenadas = sorted(ofertas_validas)
            top_2 = ofertas_ordenadas[:2]
            found_data_s1 = True

            try:
                base_lote_str = locale.currency(base_lote, grouping=True)
            except Exception:
                base_lote_str = f"{base_lote:,.2f}"
            lote_header = f"<b><u>Lote {str(lote_num)}: {getattr(lote_obj, 'nombre','')} (Base: {base_lote_str})</u></b>"
            self._add_summary_label(lote_header, margin_top=8)

            for i, (monto, oferente) in enumerate(top_2, start=1):
                dif = monto - base_lote
                pct = (dif / base_lote * 100.0) if base_lote > 0 else 0.0
                try:
                    monto_str = locale.currency(monto, grouping=True)
                except Exception:
                    monto_str = f"{monto:,.2f}"
                try:
                    dif_str = locale.currency(dif, grouping=True, symbol=True)
                except Exception:
                    dif_str = f"{dif:,.2f}"
                detalle_text = f"&nbsp;&nbsp;&nbsp;&nbsp;{i}. {oferente}: <b>{monto_str}</b> (Dif: {dif_str} / {pct:.2f}%)"
                self._add_summary_label(detalle_text)
                print(f"[DEBUG] S1 - Lote {str(lote_num)}: Añadido detalle para {oferente}")

        if not found_data_s1:
            print("[DEBUG] S1 - No se encontró data para ningún lote.")
            self._add_summary_label("<i>No se encontraron ofertas válidas para este análisis.</i>")

        # Sección 2
        print("[DEBUG] Añadiendo Sección 2: Análisis Comparativo...")
        self.summary_layout.addWidget(QLabel("<hr>"))
        self._add_summary_label("⚖️ Análisis Comparativo (Nuestros Lotes)", font_size=11, margin_top=15)
        lotes_participados = [
            l for l in self.licitacion.lotes
            if getattr(l, 'participamos', False)
            and float(getattr(l, 'monto_ofertado', 0) or 0) > 0
            and getattr(l, 'fase_A_superada', False)
        ]
        print(f"[DEBUG] S2 - {len(lotes_participados)} lotes participados encontrados.")
        if not lotes_participados:
            self._add_summary_label("<i>No se participó o no se registraron ofertas habilitadas en ningún lote.</i>")
        else:
            for lote in sorted(lotes_participados, key=lambda l: int(str(l.numero)) if str(l.numero).isdigit() else str(l.numero)):
                nuestra_oferta_monto = float(lote.monto_ofertado or 0.0)
                nuestra_empresa_nombre_display = f"➡️ {lote.empresa_nuestra or 'Nuestra Oferta'}"
                lote_num_str = str(lote.numero)
                ofertas_competidores = [
                    data['monto']
                    for oferente, data in matriz_con_nuestra.get(lote_num_str, {}).items()
                    if oferente != nuestra_empresa_nombre_display
                    and isinstance(data.get('monto'), (int, float))
                    and data['monto'] > 0
                ]
                try:
                    nuestra_monto_str = locale.currency(nuestra_oferta_monto, grouping=True)
                except Exception:
                    nuestra_monto_str = f"{nuestra_oferta_monto:,.2f}"
                texto_resultado = f"<b><u>Lote {lote_num_str}:</u></b> Nuestra oferta ({lote.empresa_nuestra or 'N/A'}) es <b>{nuestra_monto_str}</b>. "
                if not ofertas_competidores:
                    texto_resultado += "<i>Sin ofertas de competidores habilitadas.</i>"
                else:
                    mejor_competidor_monto = min(ofertas_competidores)
                    diferencial = nuestra_oferta_monto - mejor_competidor_monto
                    try:
                        mejor_comp_str = locale.currency(mejor_competidor_monto, grouping=True)
                    except Exception:
                        mejor_comp_str = f"{mejor_competidor_monto:,.2f}"
                    try:
                        diff_str = locale.currency(diferencial, grouping=True, symbol=True)
                    except Exception:
                        diff_str = f"{diferencial:,.2f}"
                    color = "red" if diferencial > 0.01 else "green"
                    texto_resultado += f"Mejor competidor: {mejor_comp_str}. <span style='color:{color};'>Diferencial: {diff_str}</span>"
                self._add_summary_label(texto_resultado, margin_top=5)
                print(f"[DEBUG] S2 - Lote {lote_num_str}: Añadido detalle comparativo.")

        # Sección 3
        print("[DEBUG] Añadiendo Sección 3: Paquetes Globales...")
        self.summary_layout.addWidget(QLabel("<hr>"))
        self._add_summary_label("📦 Análisis de Paquetes Globales", font_size=11, margin_top=15)
        try:
            paquete_individual = self.licitacion.calcular_mejor_paquete_individual()
            print(f"[DEBUG] S3 - Paquete individual calculado: {paquete_individual}")
            monto_ind = float(paquete_individual.get('monto_total', 0.0) if isinstance(paquete_individual, dict) else 0.0)
            try:
                monto_ind_str = locale.currency(monto_ind, grouping=True)
            except Exception:
                monto_ind_str = f"{monto_ind:,.2f}"
            self._add_summary_label(f"<b>Opción 1 (Individual):</b> Suma de la mejor oferta por lote = <b>{monto_ind_str}</b>")
        except Exception as e:
            print(f"[ERROR] S3 - Calculando paquete individual: {e}")
            self._add_summary_label("<b>Opción 1 (Individual):</b> Error al calcular.")
        try:
            paquete_unico = self.licitacion.calcular_mejor_paquete_por_oferente()
            print(f"[DEBUG] S3 - Paquete único calculado: {paquete_unico}")
            if paquete_unico:
                monto_uni = float(paquete_unico.get('monto_total', 0.0))
                oferente_uni = paquete_unico.get('oferente', 'N/A')
                try:
                    monto_uni_str = locale.currency(monto_uni, grouping=True)
                except Exception:
                    monto_uni_str = f"{monto_uni:,.2f}"
                self._add_summary_label(f"<b>Opción 2 (Oferente Único):</b> Mejor paquete completo = <b>{monto_uni_str}</b> <i>({oferente_uni})</i>")
            else:
                self._add_summary_label("<b>Opción 2 (Oferente Único):</b> N/A (Ningún oferente ofertó por todos los lotes)")
        except Exception as e:
            print(f"[ERROR] S3 - Calculando paquete único: {e}")
            self._add_summary_label("<b>Opción 2 (Oferente Único):</b> Error al calcular.")

        # Espaciador + guardas
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.summary_layout.addWidget(spacer)
        if self.summary_layout.count() <= 1:
            self._add_summary_label("<i>Sin resultados generados para el análisis actual.</i>", margin_top=8, )
        print("[DEBUG] _populate_summary widgets count:", self.summary_layout.count())
        print("[DEBUG] _populate_summary completado.")

    def _clear_ui_on_error(self, message: str = "Error al cargar datos."):
        if self.table_pivot is not None:
            self.table_pivot.clear()
            self.table_pivot.setRowCount(1)
            self.table_pivot.setColumnCount(1)
            self.table_pivot.setHorizontalHeaderLabels(["Error"])
            item = QTableWidgetItem(message)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            item.setBackground(QBrush(QColor("#F8D7DA")))
            self.table_pivot.setItem(0, 0, item)
            self.table_pivot.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            self.table_pivot.verticalHeader().setVisible(False)
        if self.summary_layout is not None:
            while self.summary_layout.count():
                item = self.summary_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
            self._add_summary_label(f"<b>{message}</b>")

    def _add_summary_label(self, text: str, font_size: Optional[int] = None, margin_top: Optional[int] = None):
        if self.summary_layout is None:
            return
        label = QLabel(text)
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setWordWrap(True)
        styles = []
        if font_size:
            styles.append(f"font-size: {font_size}pt;")
        if margin_top:
            styles.append(f"margin-top: {margin_top}px;")
        if styles:
            label.setStyleSheet(" ".join(styles))
        self.summary_layout.addWidget(label)

    def _exportar_analisis(self):
        if not self.reporter or not hasattr(self.reporter, 'generate_package_analysis_report'):
            QMessageBox.warning(self, "No Disponible",
                                "La funcionalidad de exportar reportes no está configurada.")
            return

        default_filename = f"Analisis_Paquetes_{self.licitacion.numero_proceso}.xlsx"
        filters = []
        if OPENPYXL_AVAILABLE:
            filters.append("Archivos de Excel (*.xlsx)")
        if REPORTLAB_AVAILABLE:
            filters.append("Archivos PDF (*.pdf)")
        if not filters:
            QMessageBox.warning(self, "Librerías Faltantes", "No se encontraron librerías para exportar (openpyxl o reportlab).")
            return

        filters_str = ";;".join(filters)
        selected_filter = filters[0]
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Exportar Análisis de Paquetes",
            default_filename,
            filters_str,
            selected_filter
        )
        if not file_path:
            return

        ext = ".xlsx" if "xlsx" in selected_filter else ".pdf" if "pdf" in selected_filter else ""
        if ext and not file_path.lower().endswith(ext):
            file_path += ext

        try:
            print(f"[DEBUG] Llamando a reporter.generate_package_analysis_report para: {file_path}")
            self.reporter.generate_package_analysis_report(self.licitacion, file_path)
            QMessageBox.information(self, "Éxito", f"El reporte ha sido guardado exitosamente en:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error de Exportación", f"No se pudo generar el reporte:\n{e}")
            print(f"[ERROR] Error detallado en _exportar_analisis: {e}")
            traceback.print_exc()