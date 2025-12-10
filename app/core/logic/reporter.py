# app/core/logic/reporter.py
from __future__ import annotations
import os
import logging
from typing import List, Any, TYPE_CHECKING

# --- Bibliotecas Necesarias (Ejemplo: ReportLab) ---
# Necesitarás instalarla: pip install reportlab
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
except ImportError:
    print("ADVERTENCIA: Falta 'reportlab'. Instala con: pip install reportlab. La exportación a PDF fallará.")
    # Placeholders para que el archivo importe sin fallar
    canvas = letter = inch = SimpleDocTemplate = Paragraph = Spacer = Table = TableStyle = getSampleStyleSheet = colors = None

if TYPE_CHECKING:
    from app.core.models import Licitacion

def generate_subsanacion_report(
    licitacion: Licitacion,
    historial_data: List[Any],
    file_path: str
):
    """
    Genera un reporte PDF simple del historial de subsanaciones.
    Esta es una implementación de placeholder.
    """
    if not SimpleDocTemplate:
        raise ImportError("La biblioteca 'reportlab' es necesaria para generar reportes PDF. Por favor, instálala (pip install reportlab).")

    print(f"Iniciando generación de reporte de subsanación para: {licitacion.numero_proceso}")
    print(f"Guardando en: {file_path}")

    try:
        doc = SimpleDocTemplate(file_path, pagesize=letter,
                                title=f"Historial Subsanación - {licitacion.numero_proceso}")
        story = []
        styles = getSampleStyleSheet()

        # 1. Título
        title_str = f"Historial de Subsanaciones"
        p_title = Paragraph(title_str, styles['h1'])
        story.append(p_title)
        story.append(Spacer(1, 0.2 * inch))

        # 2. Info Licitación
        info_str = f"<b>Proceso:</b> {licitacion.numero_proceso}<br/>" \
                   f"<b>Nombre:</b> {licitacion.nombre_proceso}<br/>" \
                   f"<b>Institución:</b> {licitacion.institucion}"
        p_info = Paragraph(info_str, styles['BodyText'])
        story.append(p_info)
        story.append(Spacer(1, 0.3 * inch))

        # 3. Tabla de Historial
        # Definir encabezados (deben coincidir con los datos recibidos)
        # Datos de entrada: ('fecha_sol', 'doc_codigo', 'doc_nombre', 'fecha_lim', 'estado', 'comentario')
        table_data = [
            ["Fecha Sol.", "Código", "Documento", "Fecha Límite", "Estado", "Comentario"]
        ]
        
        # Añadir filas de datos
        for row in historial_data:
            # Convertir todos los datos a string para la tabla
            table_data.append([str(col) if col is not None else "" for col in row])

        # Crear la tabla
        t = Table(table_data, colWidths=[1*inch, 1*inch, 2.5*inch, 1*inch, 0.8*inch, 2*inch])
        
        # Estilo de la tabla
        table_style = TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#D5D5D5")), # Encabezado gris
            ('TEXTCOLOR', (0,0), (-1,0), colors.black),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('ALIGN', (0,0), (0,-1), 'CENTER'), # Col Fecha Sol.
            ('ALIGN', (3,0), (3,-1), 'CENTER'), # Col Fecha Lím.
            ('ALIGN', (4,0), (4,-1), 'CENTER'), # Col Estado
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), # Encabezado en negrita
            ('FONTSIZE', (0,0), (-1,-1), 8), # Fuente más pequeña
            ('BOTTOMPADDING', (0,0), (-1,0), 10), # Espacio en encabezado
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey), # Rejilla
            ('BOX', (0,0), (-1,-1), 1, colors.black), # Borde exterior
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ])
        t.setStyle(table_style)
        story.append(t)

        # Construir el PDF
        doc.build(story)
        
        print("Reporte de subsanación generado exitosamente.")
        
    except Exception as e:
        print(f"ERROR al generar PDF de subsanación: {e}")
        logging.exception(f"Error generando reporte PDF en {file_path}")
        # Relanzar el error para que el diálogo lo capture y muestre al usuario
        raise e