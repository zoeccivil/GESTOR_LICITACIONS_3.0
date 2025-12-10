# app/core/logic/pdf_generator.py
from __future__ import annotations
import os
import io
import logging
# --- CORRECCIÓN DE IMPORTACIÓN ---
from typing import List, Dict, TYPE_CHECKING, Optional, Any
# --- FIN CORRECCIÓN ---

# --- Bibliotecas Necesarias ---
try:
    from PyPDF2 import PdfReader, PdfMerger
except ImportError:
    print("ERROR: Falta PyPDF2. Instala con: pip install pypdf2")
    PdfReader = PdfMerger = None # Placeholder

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph
    from reportlab.lib.utils import ImageReader
    import qrcode # Necesita 'pip install qrcode[pil]'
    from PIL import Image # Necesita 'pip install Pillow' (normalmente viene con qrcode[pil])
except ImportError as e:
    print(f"ERROR: Falta reportlab, qrcode o Pillow ({e}). Instala con: pip install reportlab qrcode[pil]")
    canvas = letter = inch = getSampleStyleSheet = Paragraph = ImageReader = qrcode = Image = None # Placeholders
# --- Fin Bibliotecas ---

if TYPE_CHECKING:
    from app.core.models import Documento, Licitacion
    # from app.core.db_adapter import DatabaseAdapter # Si se necesitara acceso DB aquí (evitarlo)

# Helper (asumiendo que existe en utils)
try:
    from app.core.utils import reconstruir_ruta_absoluta
except ImportError:
    print("WARN: No se encontró 'reconstruir_ruta_absoluta' en utils. Usando ruta tal cual.")
    # Fallback simple
    reconstruir_ruta_absoluta = lambda ruta: ruta


# --- Funciones Helper para Portada e Índice (Implementaciones Básicas) ---

def _render_portada_pdf_bytes(titulo: str, info_licitacion: Dict, qr_text: Optional[str] = None) -> bytes:
    """Genera una portada simple en PDF como bytes usando reportlab."""
    if not canvas: return b"" # Si reportlab no está instalado
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    styles = getSampleStyleSheet()
    style_title = styles['h1']
    style_body = styles['BodyText']
    style_body.fontSize = 10

    # Título Centrado
    p_title = Paragraph(titulo, style_title)
    p_title.wrapOn(c, width - 2*inch, height)
    p_title.drawOn(c, inch, height - 1.5*inch)

    # Información
    y_pos = height - 2.5*inch
    info_lines = [
        f"<b>Número Proceso:</b> {info_licitacion.get('numero_proceso', 'N/D')}",
        f"<b>Nombre Proceso:</b> {info_licitacion.get('nombre_proceso', 'N/D')}",
        f"<b>Institución:</b> {info_licitacion.get('institucion', 'N/D')}",
        f"<b>Empresa(s):</b> {info_licitacion.get('empresa_nuestra', 'N/D')}", # Asegúrate que esto se pase formateado
    ]
    for line in info_lines:
        p_info = Paragraph(line, style_body)
        p_info.wrapOn(c, width - 2*inch, height)
        text_height = p_info.height
        if y_pos < inch + text_height: break # Evitar dibujar fuera de página
        p_info.drawOn(c, inch, y_pos)
        y_pos -= text_height + 6 # Espacio entre líneas

    # Código QR (si se proporciona texto)
    if qr_text and qrcode and Image:
        try:
            qr_img = qrcode.make(qr_text, error_correction=qrcode.constants.ERROR_CORRECT_L)
            qr_img_pil = qr_img.get_image()
            qr_buffer = io.BytesIO()
            qr_img_pil.save(qr_buffer, format='PNG')
            qr_buffer.seek(0)
            img_reader = ImageReader(qr_buffer)
            img_width, img_height = img_reader.getSize()
            aspect = img_height / float(img_width)
            display_width = 1.5 * inch
            display_height = display_width * aspect
            c.drawImage(img_reader, width - inch - display_width, inch, width=display_width, height=display_height)
        except Exception as e_qr:
            print(f"Error generando QR en portada: {e_qr}")

    c.save()
    buffer.seek(0)
    return buffer.getvalue()


def _render_indice_pdf_bytes(items_indice: List[Dict]) -> bytes:
    """Genera un índice simple en PDF como bytes usando reportlab."""
    if not canvas: return b""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    styles = getSampleStyleSheet()
    style_title = styles['h2']
    style_item = styles['BodyText']
    style_item.fontSize = 9

    # Título
    p_title = Paragraph("Índice de Contenido", style_title)
    p_title.wrapOn(c, width - 2*inch, height)
    p_title.drawOn(c, inch, height - 1.0*inch)

    # Items del índice
    y_pos = height - 1.5*inch
    max_title_width = width - 2.5*inch # Ancho para título
    page_num_width = 0.5*inch # Ancho para número de página

    for item in items_indice:
        titulo = item.get('titulo', 'Sin Título')
        pagina = item.get('pagina_inicio', '?')

        # Usar wrap y draw para manejar títulos largos y calcular altura
        p_item_text = Paragraph(f"{titulo}", style_item)
        p_item_text.wrapOn(c, max_title_width, height)
        text_height = p_item_text.height

        # Dibujar puntos (...) - Simplificado, podría mejorarse
        p_dots = Paragraph("." * 60, style_item) # Ajustar cantidad de puntos si es necesario
        p_dots.wrapOn(c, width, height)

        p_page = Paragraph(str(pagina), style_item)
        p_page.wrapOn(c, page_num_width, height)

        if y_pos < inch + text_height: # Salto de página (simplificado, no implementado aquí)
             # c.showPage() # Necesitaría manejar cabeceras/pies de página
             # y_pos = height - inch
             print("WARN: Índice excede una página (salto no implementado)")
             break

        p_item_text.drawOn(c, inch, y_pos)
        # Dibujar número de página alineado a la derecha
        p_page.drawOn(c, width - inch - page_num_width, y_pos)
        # Dibujar puntos entre texto y número (aproximado)
        # title_width_actual = p_item_text.width # No siempre disponible fácilmente
        # dot_x = inch + title_width_actual + 5
        # p_dots.drawOn(c, dot_x, y_pos)

        y_pos -= text_height + 4 # Espacio entre ítems

    c.save()
    buffer.seek(0)
    return buffer.getvalue()


# --- Función Principal Adaptada ---

def generar_pdf_expediente_categoria(
    documentos_categoria: List[Documento], # Lista de objetos Documento YA ORDENADOS para esta categoría
    ruta_salida: str,
    licitacion_info: Licitacion, # Objeto Licitacion completo para info de portada
    metadata: Dict[str, Any] # Diccionario con título, creado_por, qr_text
    ) -> tuple[bool, str]:
    """
    Une PDFs de UNA categoría en un solo expediente con portada e índice.
    Devuelve (True, "Éxito") o (False, "Mensaje de error").
    """
    if not PdfReader or not PdfMerger or not canvas:
        return False, "Faltan bibliotecas requeridas (PyPDF2, reportlab, qrcode)."

    merger = PdfMerger()
    errores_archivos = []
    indice_items = []
    pagina_actual_contenido = 0 # Páginas después del índice

    try:
        # --- 1. Portada ---
        print("Generando portada...")
        empresas_str = ", ".join(str(e) for e in licitacion_info.empresas_nuestras) if licitacion_info.empresas_nuestras else "No Asignada"
        info_lic = {
             'numero_proceso': licitacion_info.numero_proceso,
             'nombre_proceso': licitacion_info.nombre_proceso,
             'institucion': licitacion_info.institucion,
             'empresa_nuestra': empresas_str,
        }
        portada_bytes = _render_portada_pdf_bytes(metadata.get('titulo_expediente', 'Expediente'), info_lic, metadata.get('qr_text'))
        if portada_bytes:
             merger.append(PdfReader(io.BytesIO(portada_bytes)))
        else: print("WARN: No se pudo generar la portada.")

        # --- 2. Preparar datos para Índice y Contenido ---
        print(f"Procesando {len(documentos_categoria)} documentos para el contenido...")
        archivos_a_incluir = [] # Lista de (ruta_absoluta, titulo_indice)
        for doc in documentos_categoria:
            titulo_indice = f"[{doc.codigo or 'S/C'}] {doc.nombre or 'Sin Nombre'}"
            ruta_guardada = getattr(doc, "ruta_archivo", "") or ""
            if not ruta_guardada:
                print(f"WARN: Documento '{titulo_indice}' no tiene ruta de archivo.")
                archivos_a_incluir.append((None, f"[FALTANTE] {titulo_indice}"))
                continue

            # Reconstruir ruta absoluta
            ruta_absoluta = reconstruir_ruta_absoluta(ruta_guardada)
            if not ruta_absoluta or not os.path.isfile(ruta_absoluta):
                print(f"WARN: Archivo no encontrado para '{titulo_indice}' en ruta: {ruta_absoluta} (Guardada: {ruta_guardada})")
                errores_archivos.append(f"- {titulo_indice} (Archivo no encontrado)")
                archivos_a_incluir.append((None, f"[FALTANTE] {titulo_indice}"))
            elif not ruta_absoluta.lower().endswith(".pdf"):
                print(f"WARN: Archivo para '{titulo_indice}' no es PDF ({ruta_absoluta}). Se omitirá del contenido.")
                errores_archivos.append(f"- {titulo_indice} (No es PDF)")
                archivos_a_incluir.append((None, f"[OMITIDO - NO PDF] {titulo_indice}")) # Omitir del índice y contenido
            else:
                 archivos_a_incluir.append((ruta_absoluta, titulo_indice))


        # --- 3. Generar Índice (temporalmente) ---
        print("Generando índice...")
        pagina_inicio_contenido = len(merger.pages) + 1 # El contenido empieza después de la portada y el índice
        for i, (ruta, titulo) in enumerate(archivos_a_incluir):
            # Asumimos 1 página para faltantes/omitidos, calcularemos para PDFs reales después
             indice_items.append({'titulo': titulo, 'pagina_inicio': pagina_inicio_contenido + pagina_actual_contenido})
             if ruta is None:
                  pagina_actual_contenido += 1 # Sumar 1 pág para faltante/omitido (ajustaremos si añadimos página de aviso)

        # Renderizar índice y añadirlo después de la portada
        indice_bytes = _render_indice_pdf_bytes(indice_items)
        if indice_bytes:
            merger.merge(len(merger.pages), PdfReader(io.BytesIO(indice_bytes))) # Insertar al final por ahora
            # Moveremos el índice a la posición 1 después de añadir contenido
        else:
             print("WARN: No se pudo generar el índice.")


        # --- 4. Añadir Contenido y Actualizar Índice Real ---
        print("Añadiendo contenido PDF...")
        pagina_actual_contenido = 0 # Reiniciar contador para páginas de contenido
        indice_items_final = [] # Reconstruir índice con páginas correctas
        pagina_inicio_contenido = len(merger.pages) # Página donde empieza el primer documento

        for i, (ruta_absoluta, titulo_indice) in enumerate(archivos_a_incluir):
            pagina_inicio_doc = pagina_inicio_contenido + pagina_actual_contenido
            indice_items_final.append({'titulo': titulo_indice, 'pagina_inicio': pagina_inicio_doc}) # Pagina real

            if ruta_absoluta: # Si es un PDF válido
                try:
                    reader = PdfReader(ruta_absoluta)
                    num_pages_doc = len(reader.pages)
                    merger.append(reader) # Añadir páginas del documento
                    # Añadir marcador (si se desea y funciona)
                    # try: merger.add_outline_item(titulo_indice, pagina_inicio_doc -1) # -1 porque PyPDF2 es 0-based?
                    # except Exception as e_outline: print(f"WARN: No se pudo añadir marcador para '{titulo_indice}': {e_outline}")

                    pagina_actual_contenido += num_pages_doc
                    print(f"  - Añadido '{os.path.basename(ruta_absoluta)}' ({num_pages_doc} pág.)")
                except Exception as e_read:
                    msg = f"Error al leer/añadir PDF '{titulo_indice}' ({ruta_absoluta}): {e_read}"
                    print(f"ERROR: {msg}")
                    errores_archivos.append(f"- {titulo_indice}: {e_read}")
                    # Añadir página de error? Por ahora solo sumamos 1 página al índice
                    pagina_actual_contenido += 1
            else:
                 # Añadir página de aviso para [FALTANTE] o [OMITIDO]
                 aviso_bytes = _render_indice_pdf_bytes([{'titulo': titulo_indice, 'pagina_inicio': 0}]) # Reusar render de índice
                 if aviso_bytes:
                      merger.append(PdfReader(io.BytesIO(aviso_bytes)))
                 pagina_actual_contenido += 1

        # --- 5. Re-generar Índice con páginas correctas e Insertarlo ---
        print("Regenerando índice final...")
        indice_final_bytes = _render_indice_pdf_bytes(indice_items_final)
        if indice_final_bytes:
             # Eliminar el índice temporal (asumiendo que era la última página añadida antes del contenido)
             # Esto es complejo con PyPDF2. Una alternativa es crear el índice al final y luego moverlo.
             # Por simplicidad ahora, lo añadimos de nuevo al final. El usuario puede moverlo manualmente.
             # TODO: Investigar cómo insertar páginas eficientemente con PyPDF2 o cambiar a PyMuPDF.
             # merger.merge(1, PdfReader(io.BytesIO(indice_final_bytes))) # Intentar insertar en pos 1
             # Lo añadimos al final por ahora
              merger.append(PdfReader(io.BytesIO(indice_final_bytes)))
              print("WARN: Índice final añadido al final del documento.")
        else:
              print("ERROR: No se pudo generar el índice final.")


        # --- 6. Guardar PDF final ---
        print(f"Guardando PDF final en: {ruta_salida}")
        with open(ruta_salida, "wb") as f_out:
            merger.write(f_out)

        merger.close()
        print("PDF guardado.")

        mensaje_final = "Éxito."
        if errores_archivos:
             mensaje_final += "\nSe encontraron problemas con algunos archivos:\n" + "\n".join(errores_archivos)
        return True, mensaje_final

    except Exception as e:
        logging.exception(f"Error fatal generando PDF para '{metadata.get('titulo_expediente', 'N/A')}'")
        try: merger.close() # Intentar cerrar el merger si falla
        except: pass
        return False, f"Error inesperado: {e}"