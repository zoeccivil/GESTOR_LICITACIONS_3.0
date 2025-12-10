"""
Diálogo para visualizar reportes y KPIs del sistema.
"""
from __future__ import annotations
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QGroupBox, QGridLayout, QComboBox, QDateEdit, QMessageBox,
    QFileDialog, QTextEdit
)
from PyQt6.QtCore import QDate

from app.core.reporting import ReportingEngine
from app.core.db_adapter import DatabaseAdapter


class DialogoReportes(QDialog):
    """Diálogo para visualizar KPIs y generar reportes."""
    
    def __init__(self, parent, db: DatabaseAdapter):
        super().__init__(parent)
        self.db = db
        self.reporting = ReportingEngine(db)
        
        self.setWindowTitle("Reportes y KPIs")
        self.resize(850, 750)
        self.setModal(True)
        
        self._build_ui()
        self._calcular_kpis()
    
    def _build_ui(self):
        """Construye la interfaz del diálogo."""
        root = QVBoxLayout(self)
        
        # Filtros
        filtros_group = QGroupBox("Filtros")
        filtros_layout = QHBoxLayout(filtros_group)
        
        filtros_layout.addWidget(QLabel("Desde:"))
        self.date_inicio = QDateEdit()
        self.date_inicio.setCalendarPopup(True)
        self.date_inicio.setDate(QDate.currentDate().addMonths(-3))
        filtros_layout.addWidget(self.date_inicio)
        
        filtros_layout.addWidget(QLabel("Hasta:"))
        self.date_fin = QDateEdit()
        self.date_fin.setCalendarPopup(True)
        self.date_fin.setDate(QDate.currentDate())
        filtros_layout.addWidget(self.date_fin)
        
        filtros_layout.addWidget(QLabel("Institución:"))
        self.combo_institucion = QComboBox()
        self.combo_institucion.addItem("Todas", None)
        self._cargar_instituciones()
        filtros_layout.addWidget(self.combo_institucion)
        
        btn_actualizar = QPushButton("🔄 Actualizar")
        btn_actualizar.clicked.connect(self._calcular_kpis)
        filtros_layout.addWidget(btn_actualizar)
        
        filtros_layout.addStretch(1)
        
        root.addWidget(filtros_group)
        
        # KPIs Principales
        kpis_group = QGroupBox("Indicadores Clave de Desempeño (KPIs)")
        kpis_layout = QGridLayout(kpis_group)
        
        # Fila 1
        kpis_layout.addWidget(self._crear_label_titulo("Total Licitaciones:"), 0, 0)
        self.lbl_total_licitaciones = self._crear_label_valor("0")
        kpis_layout.addWidget(self.lbl_total_licitaciones, 0, 1)
        
        kpis_layout.addWidget(self._crear_label_titulo("Adjudicadas:"), 0, 2)
        self.lbl_adjudicadas = self._crear_label_valor("0")
        kpis_layout.addWidget(self.lbl_adjudicadas, 0, 3)
        
        kpis_layout.addWidget(self._crear_label_titulo("Ganadas:"), 0, 4)
        self.lbl_ganadas = self._crear_label_valor("0", "green")
        kpis_layout.addWidget(self.lbl_ganadas, 0, 5)
        
        # Fila 2
        kpis_layout.addWidget(self._crear_label_titulo("Tasa de Adjudicación:"), 1, 0)
        self.lbl_tasa_adjudicacion = self._crear_label_valor("0%")
        kpis_layout.addWidget(self.lbl_tasa_adjudicacion, 1, 1)
        
        kpis_layout.addWidget(self._crear_label_titulo("Tasa de Éxito:"), 1, 2)
        self.lbl_tasa_exito = self._crear_label_valor("0%", "green")
        kpis_layout.addWidget(self.lbl_tasa_exito, 1, 3)
        
        kpis_layout.addWidget(self._crear_label_titulo("Vencimientos (7 días):"), 1, 4)
        self.lbl_vencimientos = self._crear_label_valor("0", "red")
        kpis_layout.addWidget(self.lbl_vencimientos, 1, 5)
        
        # Fila 3
        kpis_layout.addWidget(self._crear_label_titulo("Valor Total Ofertado:"), 2, 0)
        self.lbl_valor_ofertado = self._crear_label_valor("$0.00")
        kpis_layout.addWidget(self.lbl_valor_ofertado, 2, 1)
        
        kpis_layout.addWidget(self._crear_label_titulo("Valor Total Ganado:"), 2, 2)
        self.lbl_valor_ganado = self._crear_label_valor("$0.00", "green")
        kpis_layout.addWidget(self.lbl_valor_ganado, 2, 3)
        
        kpis_layout.addWidget(self._crear_label_titulo("Completitud Docs:"), 2, 4)
        self.lbl_completitud = self._crear_label_valor("0%")
        kpis_layout.addWidget(self.lbl_completitud, 2, 5)
        
        root.addWidget(kpis_group)
        
        # Causas de pérdida
        causas_group = QGroupBox("Causas de Pérdida (Top 5)")
        causas_layout = QVBoxLayout(causas_group)
        
        self.txt_causas = QTextEdit()
        self.txt_causas.setReadOnly(True)
        self.txt_causas.setMaximumHeight(120)
        causas_layout.addWidget(self.txt_causas)
        
        root.addWidget(causas_group)
        
        # Resumen textual
        resumen_group = QGroupBox("Resumen Ejecutivo")
        resumen_layout = QVBoxLayout(resumen_group)
        
        self.txt_resumen = QTextEdit()
        self.txt_resumen.setReadOnly(True)
        resumen_layout.addWidget(self.txt_resumen)
        
        root.addWidget(resumen_group, 1)
        
        # Acciones de exportación
        export_layout = QHBoxLayout()
        
        btn_exportar_excel = QPushButton("📊 Exportar a Excel")
        btn_exportar_excel.clicked.connect(self._exportar_excel)
        export_layout.addWidget(btn_exportar_excel)
        
        btn_reportar_mensual = QPushButton("📅 Reporte Mensual")
        btn_reportar_mensual.clicked.connect(self._generar_reporte_mensual)
        export_layout.addWidget(btn_reportar_mensual)
        
        export_layout.addStretch(1)
        
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(self.accept)
        export_layout.addWidget(btn_cerrar)
        
        root.addLayout(export_layout)
    
    def _crear_label_titulo(self, text: str) -> QLabel:
        """Crea un label para título de KPI."""
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return lbl
    
    def _crear_label_valor(self, text: str, color: str = "blue") -> QLabel:
        """Crea un label para valor de KPI con estilo."""
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        lbl.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {color};")
        return lbl
    
    def _cargar_instituciones(self):
        """Carga las instituciones disponibles en el combo."""
        try:
            licitaciones = self.db.load_all_licitaciones()
            instituciones = set(lic.institucion for lic in licitaciones if lic.institucion)
            for inst in sorted(instituciones):
                self.combo_institucion.addItem(inst, inst)
        except Exception:
            pass
    
    def _calcular_kpis(self):
        """Calcula y muestra los KPIs."""
        # Obtener filtros
        fecha_inicio = self.date_inicio.date().toString("yyyy-MM-dd")
        fecha_fin = self.date_fin.date().toString("yyyy-MM-dd")
        institucion = self.combo_institucion.currentData()
        
        try:
            kpis = self.reporting.calculate_kpis(
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                institucion=institucion
            )
            
            # Actualizar labels
            self.lbl_total_licitaciones.setText(str(kpis.total_licitaciones))
            self.lbl_adjudicadas.setText(str(kpis.licitaciones_adjudicadas))
            self.lbl_ganadas.setText(str(kpis.licitaciones_ganadas))
            
            self.lbl_tasa_adjudicacion.setText(f"{kpis.tasa_adjudicacion:.1f}%")
            self.lbl_tasa_exito.setText(f"{kpis.tasa_exito:.1f}%")
            self.lbl_vencimientos.setText(str(kpis.vencimientos_proximos))
            
            self.lbl_valor_ofertado.setText(f"${kpis.valor_total_ofertado:,.2f}")
            self.lbl_valor_ganado.setText(f"${kpis.valor_total_ganado:,.2f}")
            self.lbl_completitud.setText(f"{kpis.completitud_documentos_promedio:.1f}%")
            
            # Causas de pérdida
            causas_text = []
            for motivo, count in sorted(kpis.causas_perdida.items(), key=lambda x: x[1], reverse=True)[:5]:
                causas_text.append(f"• {motivo}: {count} casos")
            
            if causas_text:
                self.txt_causas.setPlainText("\n".join(causas_text))
            else:
                self.txt_causas.setPlainText("No hay datos de pérdidas en el período seleccionado.")
            
            # Resumen ejecutivo
            resumen = self._generar_resumen_ejecutivo(kpis)
            self.txt_resumen.setPlainText(resumen)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudieron calcular los KPIs: {e}")
    
    def _generar_resumen_ejecutivo(self, kpis) -> str:
        """Genera un resumen ejecutivo en texto."""
        lineas = []
        lineas.append("RESUMEN EJECUTIVO")
        lineas.append("=" * 60)
        lineas.append("")
        
        fecha_inicio = self.date_inicio.date().toString("dd/MM/yyyy")
        fecha_fin = self.date_fin.date().toString("dd/MM/yyyy")
        lineas.append(f"Período: {fecha_inicio} - {fecha_fin}")
        
        institucion = self.combo_institucion.currentText()
        lineas.append(f"Institución: {institucion}")
        lineas.append("")
        
        lineas.append("RESULTADOS GENERALES:")
        lineas.append(f"  • Total de licitaciones: {kpis.total_licitaciones}")
        lineas.append(f"  • Licitaciones adjudicadas: {kpis.licitaciones_adjudicadas}")
        lineas.append(f"  • Licitaciones ganadas por nosotros: {kpis.licitaciones_ganadas}")
        lineas.append("")
        
        lineas.append("TASAS DE ÉXITO:")
        lineas.append(f"  • Tasa de adjudicación: {kpis.tasa_adjudicacion:.1f}%")
        lineas.append(f"  • Tasa de éxito en adjudicadas: {kpis.tasa_exito:.1f}%")
        lineas.append("")
        
        lineas.append("VALORES MONETARIOS:")
        lineas.append(f"  • Total ofertado: ${kpis.valor_total_ofertado:,.2f}")
        lineas.append(f"  • Total ganado: ${kpis.valor_total_ganado:,.2f}")
        if kpis.valor_total_ofertado > 0:
            efectividad = (kpis.valor_total_ganado / kpis.valor_total_ofertado) * 100
            lineas.append(f"  • Efectividad monetaria: {efectividad:.1f}%")
        lineas.append("")
        
        lineas.append("CALIDAD:")
        lineas.append(f"  • Completitud de documentos promedio: {kpis.completitud_documentos_promedio:.1f}%")
        lineas.append("")
        
        lineas.append("ALERTAS:")
        lineas.append(f"  • Vencimientos próximos (7 días): {kpis.vencimientos_proximos}")
        
        if kpis.causas_perdida:
            lineas.append("")
            lineas.append("PRINCIPALES CAUSAS DE PÉRDIDA:")
            for motivo, count in sorted(kpis.causas_perdida.items(), key=lambda x: x[1], reverse=True)[:3]:
                lineas.append(f"  • {motivo}: {count} casos")
        
        return "\n".join(lineas)
    
    def _exportar_excel(self):
        """Exporta los datos a Excel."""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar a Excel",
            f"reporte_licitaciones_{QDate.currentDate().toString('yyyyMMdd')}.xlsx",
            "Excel Files (*.xlsx)"
        )
        
        if not filename:
            return
        
        try:
            success = self.reporting.export_to_excel(
                filename=filename,
                include_kpis=True
            )
            
            if success:
                QMessageBox.information(
                    self, "Éxito", 
                    f"Reporte exportado exitosamente a:\n{filename}"
                )
            else:
                QMessageBox.warning(self, "Error", "No se pudo exportar el reporte")
        
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al exportar: {e}")
    
    def _generar_reporte_mensual(self):
        """Genera un reporte mensual."""
        from PyQt6.QtWidgets import QInputDialog
        
        year = QDate.currentDate().year()
        month = QDate.currentDate().month()
        
        months = [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ]
        
        month_name, ok = QInputDialog.getItem(
            self, "Reporte Mensual", "Seleccione el mes:",
            months, month - 1, False
        )
        
        if not ok:
            return
        
        month = months.index(month_name) + 1
        
        try:
            reporte = self.reporting.generate_monthly_report(year, month)
            
            # Mostrar resumen
            msg = f"""Reporte Mensual Generado
            
Período: {reporte['periodo']}
Fecha Inicio: {reporte['fecha_inicio']}
Fecha Fin: {reporte['fecha_fin']}

KPIs:
- Total Licitaciones: {reporte['kpis']['total_licitaciones']}
- Adjudicadas: {reporte['kpis']['licitaciones_adjudicadas']}
- Ganadas: {reporte['kpis']['licitaciones_ganadas']}
- Tasa de Éxito: {reporte['kpis']['tasa_exito']:.1f}%
- Valor Ganado: ${reporte['kpis']['valor_total_ganado']:,.2f}
"""
            
            QMessageBox.information(self, "Reporte Mensual", msg)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo generar el reporte mensual: {e}")
