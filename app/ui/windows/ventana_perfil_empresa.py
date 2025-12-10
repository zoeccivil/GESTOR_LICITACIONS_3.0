from PyQt6 import QtWidgets, QtCore
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QGroupBox, QApplication, QWidget, QPushButton
)
from PyQt6.QtCore import Qt

from PyQt6 import QtGui
class VentanaPerfilEmpresaNuestra(QtWidgets.QDialog):
    """
    Muestra un dashboard con estadísticas y el historial de una de nuestras empresas en PyQt6.
    """
    def __init__(self, parent, empresa_nombre, todas_las_licitaciones):
        super().__init__(parent)
        self.empresa_nombre = empresa_nombre
        self.todas_las_licitaciones = todas_las_licitaciones
        self.parent_app = parent  # referencia a la app principal

        self.setWindowTitle(f"Perfil de Empresa: {self.empresa_nombre}")
        self.resize(1100, 700)
        self.setModal(True)

        # 1) Procesar datos
        self.historial, self.kpis = self._procesar_historial()

        # 2) UI principal
        main_layout = QVBoxLayout(self)

        # KPIs
        kpi_widget = QWidget()
        kpi_layout = QHBoxLayout(kpi_widget)
        self.crear_widgets_kpi(kpi_layout)
        main_layout.addWidget(kpi_widget)

        # Tabla de historial
        group_hist = QGroupBox("Historial de Participación (Doble clic para ver detalles de la licitación)")
        group_hist_layout = QVBoxLayout(group_hist)
        self.crear_tabla_historial(group_hist_layout)
        main_layout.addWidget(group_hist)

    def _procesar_historial(self):
        """
        Construye el historial de la empresa y sus KPIs.
        """
        historial = []
        participaciones_por_institucion = {}
        total_participaciones = 0
        total_licitaciones_ganadas = 0
        total_lotes_ganados = 0
        monto_adjudicado_total = 0.0
        estados_finalizados = ["Adjudicada", "Descalificado Fase A", "Descalificado Fase B", "Desierta", "Cancelada"]

        def _norm(s: str) -> str:
            s = (s or "").strip().replace("➡️", "").replace("(Nuestra Oferta)", "")
            while "  " in s:
                s = s.replace("  ", " ")
            return s.upper()

        for lic in self.todas_las_licitaciones:
            # Lógica para manejar consorcios
            nombres_empresas_participantes = set()
            for e in lic.empresas_nuestras:
                nombre_str = str(e)
                for nombre_individual in nombre_str.split(','):
                    nombre_limpio = nombre_individual.strip()
                    if nombre_limpio:
                        nombres_empresas_participantes.add(nombre_limpio)
            if self.empresa_nombre not in nombres_empresas_participantes:
                continue

            total_participaciones += 1
            institucion = lic.institucion
            participaciones_por_institucion[institucion] = participaciones_por_institucion.get(institucion, 0) + 1

            nuestras_empresas_en_lic_norm = {_norm(nombre) for nombre in nombres_empresas_participantes}
            ganadores_por_lote = {_norm(l.ganador_nombre) for l in lic.lotes if l.ganador_nombre}
            es_licitacion_ganada_por_grupo = any(ganador in nuestras_empresas_en_lic_norm for ganador in ganadores_por_lote)

            lotes_ganados_por_el_grupo = 0
            monto_adjudicado_en_esta_lic = 0.0

            if es_licitacion_ganada_por_grupo:
                total_licitaciones_ganadas += 1
                for lote in lic.lotes:
                    if _norm(lote.ganador_nombre) in nuestras_empresas_en_lic_norm:
                        lotes_ganados_por_el_grupo += 1
                        monto_adjudicado_en_esta_lic += getattr(lote, "monto_ofertado", 0) or 0.0

                total_lotes_ganados += lotes_ganados_por_el_grupo
                monto_adjudicado_total += monto_adjudicado_en_esta_lic

            resultado = "En Proceso"
            if lic.estado in estados_finalizados:
                if es_licitacion_ganada_por_grupo:
                    resultado = f"🏆 Ganador ({lotes_ganados_por_el_grupo} lote{'s' if lotes_ganados_por_el_grupo != 1 else ''})"
                else:
                    resultado = "Perdedor"

            historial.append({
                'proceso': lic.numero_proceso,
                'nombre': lic.nombre_proceso,
                'institucion': lic.institucion,
                'monto_adjudicado': monto_adjudicado_en_esta_lic,
                'resultado': resultado
            })

        participaciones_finalizadas = sum(1 for item in historial if item['resultado'].startswith("🏆") or item['resultado'] == "Perdedor")

        kpis = {
            'participaciones': total_participaciones,
            'licitaciones_ganadas': total_licitaciones_ganadas,
            'lotes_ganados': total_lotes_ganados,
            'tasa_exito': (total_licitaciones_ganadas / participaciones_finalizadas * 100) if participaciones_finalizadas > 0 else 0,
            'monto_adjudicado_total': monto_adjudicado_total,
            'top_institucion': max(participaciones_por_institucion, key=participaciones_por_institucion.get) if participaciones_por_institucion else "N/A"
        }
        return historial, kpis

    def crear_widgets_kpi(self, layout):
        kpi_widgets = [
            ("Participaciones", f"{self.kpis['participaciones']}"),
            ("Licitaciones Ganadas", f"{self.kpis['licitaciones_ganadas']}"),
            ("Lotes Ganados", f"{self.kpis['lotes_ganados']}"),
            ("Tasa de Éxito", f"{self.kpis['tasa_exito']:.1f}%"),
            ("Monto Total Adjudicado", f"RD$ {self.kpis['monto_adjudicado_total']:,.2f}"),
            ("Institución Frecuente", self.kpis['top_institucion'])
        ]
        for titulo, valor in kpi_widgets:
            card = QGroupBox(titulo)
            vbox = QVBoxLayout(card)
            lbl = QLabel(valor)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("font-size: 18px; font-weight: bold;")
            vbox.addWidget(lbl)
            layout.addWidget(card)

    def crear_tabla_historial(self, layout):
        cols = ['proceso', 'institucion', 'nombre', 'monto', 'resultado']
        headers = ["Proceso", "Institución", "Nombre Licitación", "Monto Adjudicado", "Resultado"]

        table = QTableWidget(len(self.historial), len(cols))
        table.setHorizontalHeaderLabels(headers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.doubleClicked.connect(self._abrir_detalles_licitacion)

        for row_idx, item in enumerate(self.historial):
            table.setItem(row_idx, 0, QTableWidgetItem(str(item['proceso'])))
            table.setItem(row_idx, 1, QTableWidgetItem(str(item['institucion'])))
            table.setItem(row_idx, 2, QTableWidgetItem(str(item['nombre'])))
            monto = f"RD$ {item['monto_adjudicado']:,.2f}"
            table.setItem(row_idx, 3, QTableWidgetItem(monto))
            resultado = item['resultado']
            item_resultado = QTableWidgetItem(resultado)
            if resultado.startswith("🏆"):
                item_resultado.setBackground(QtGui.QColor('#d4edda'))
            table.setItem(row_idx, 4, item_resultado)

        table.resizeColumnsToContents()
        table.setSortingEnabled(True)
        layout.addWidget(table)
        self.table_historial = table

    def _abrir_detalles_licitacion(self):
        sel = self.table_historial.selectedItems()
        if not sel:
            return
        row = sel[0].row()
        numero_proceso = self.table_historial.item(row, 0).text()
        lic = next((l for l in self.todas_las_licitaciones if l.numero_proceso == numero_proceso), None)
        if lic:
            # Llama a la función de la app principal para abrir la ventana de detalles
            if hasattr(self.parent_app, "abrir_ventana_detalles_desde_objeto"):
                self.parent_app.abrir_ventana_detalles_desde_objeto(lic)
            else:
                QtWidgets.QMessageBox.warning(self, "Atención", "No se puede abrir el detalle desde aquí.")

# Si quieres probar esta ventana de forma aislada:
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    # Demo: debes reemplazar por tus modelos reales
    class DummyLote:
        def __init__(self, ganador_nombre, monto_ofertado):
            self.ganador_nombre = ganador_nombre
            self.monto_ofertado = monto_ofertado
    class DummyLic:
        def __init__(self, num, nombre, institucion, empresas_nuestras, estado, lotes):
            self.numero_proceso = num
            self.nombre_proceso = nombre
            self.institucion = institucion
            self.empresas_nuestras = empresas_nuestras
            self.estado = estado
            self.lotes = lotes
    class DummyEmpresa:
        def __init__(self, nombre):
            self.nombre = nombre
        def __str__(self):
            return self.nombre
    licitaciones = [
        DummyLic("PROC-1", "Licitación 1", "ONAPI", [DummyEmpresa("Empresa X")], "Adjudicada", [DummyLote("Empresa X", 10000)]),
        DummyLic("PROC-2", "Licitación 2", "INAP", [DummyEmpresa("Empresa X")], "Descalificado Fase A", [DummyLote("Empresa Y", 0)]),
        DummyLic("PROC-3", "Licitación 3", "ONAPI", [DummyEmpresa("Empresa X")], "Adjudicada", [DummyLote("Empresa X", 15000)]),
    ]
    win = VentanaPerfilEmpresaNuestra(None, "Empresa X", licitaciones)
    win.show()
    sys.exit(app.exec())


    def abrir_perfil_empresa_nuestra(self, empresa_nombre):
        """
        Abre la ventana de perfil de una empresa específica.
        :param empresa_nombre: El nombre de la empresa a mostrar
        """
        # Suponiendo que tienes la lista de todas las licitaciones en self.licitaciones
        win = VentanaPerfilEmpresaNuestra(self, empresa_nombre, self.licitaciones)
        win.exec()  # o win.show() si prefieres modelo no modal

    # Supón que tienes una lista de empresas en tu UI
    def on_ver_perfil_empresa_seleccionada(self):
        empresa_nombre = self.obtener_empresa_seleccionada()  # tu función para obtener el nombre actual
        if not empresa_nombre:
            QtWidgets.QMessageBox.warning(self, "Selecciona una empresa", "Debes seleccionar una empresa.")
            return
        self.abrir_perfil_empresa_nuestra(empresa_nombre)