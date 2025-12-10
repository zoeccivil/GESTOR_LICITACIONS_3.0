# app/core/logic/zip_generator.py
from __future__ import annotations
import os
import io
import logging
import csv # Usar csv en lugar de 'writer'
from zipfile import ZipFile, ZIP_DEFLATED
from typing import List, Dict, TYPE_CHECKING

# Helper para reconstruir rutas
try:
    from app.core.utils import reconstruir_ruta_absoluta
except ImportError:
    print("WARN: No se encontró 'reconstruir_ruta_absoluta' en utils. Usando ruta tal cual.")
    reconstruir_ruta_absoluta = lambda ruta: ruta

if TYPE_CHECKING:
    from app.core.models import Licitacion, Documento
    from app.core.db_adapter import DatabaseAdapter # db_adapter es mejor que db_manager


def generar_expediente_zip_por_categoria(
    licitacion: Licitacion,
    carpeta_salida: str,
    orden_por_cat: Dict[str, List[Documento]], # Dict {cat: [lista_docs_ordenados]}
    incluir: Dict[str, bool], # Dict {cat: bool}
    categorias_orden: List[str] # Lista ordenada de categorías, ej: ["Legal", "Financiera", ...]
    ) -> tuple[bool, List[str], List[str]]: # Devuelve (exito_general, lista_rutas_generadas, lista_errores)
    """
    Crea un ZIP por cada categoría marcada en 'incluir', respetando el orden manual.
    """
    os.makedirs(carpeta_salida, exist_ok=True)
    generados: List[str] = []
    errores: List[str] = []

    for cat_name in categorias_orden:
        if not incluir.get(cat_name, False):
            print(f"ZIP: Categoría '{cat_name}' no incluida, saltando.")
            continue
        
        docs_obj = orden_por_cat.get(cat_name, [])
        if not docs_obj:
            print(f"ZIP: Categoría '{cat_name}' sin documentos, saltando.")
            continue

        # Sanitizar nombre de archivo
        nombre_zip = f"Expediente - {cat_name} - {licitacion.numero_proceso}.zip"
        nombre_zip = "".join(c for c in nombre_zip if c.isalnum() or c in (' ', '.', '-', '_')).rstrip()
        out_zip_path = os.path.join(carpeta_salida, nombre_zip)

        print(f"Generando ZIP para '{cat_name}' en: {out_zip_path}...")
        try:
            with ZipFile(out_zip_path, "w", compression=ZIP_DEFLATED, compresslevel=6) as zf:
                # 1) index.csv con el orden
                # --- CORRECCIÓN AQUÍ ---
                # io.StringIO no acepta 'encoding', solo 'newline' para csv
                buf = io.StringIO(newline='')
                # --- FIN CORRECCIÓN ---
                
                w = csv.writer(buf)
                w.writerow(["orden", "codigo", "nombre", "categoria", "archivo_en_zip"])
                
                archivos_para_zip: List[tuple[int, Documento, str]] = [] # (orden, doc_obj, nombre_en_zip)

                for i, doc in enumerate(docs_obj, start=1):
                    ruta_guardada = getattr(doc, "ruta_archivo", "") or ""
                    nombre_archivo_original = os.path.basename(ruta_guardada) if ruta_guardada else ""
                    
                    orden_prefix = f"{i:03d}" # Prefijo 001, 002...
                    
                    if ruta_guardada and nombre_archivo_original:
                         nombre_limpio = "".join(c for c in nombre_archivo_original if c.isalnum() or c in (' ', '.', '-', '_')).rstrip()
                         nombre_en_zip = f"{orden_prefix} - {nombre_limpio}"
                    else:
                         nombre_limpio = f"FALTANTE_{doc.codigo or i}.txt"
                         nombre_en_zip = f"{orden_prefix} - {nombre_limpio}"

                    archivos_para_zip.append((i, doc, nombre_en_zip))
                    
                    w.writerow([
                        i,
                        getattr(doc, "codigo", "") or "",
                        getattr(doc, "nombre", "") or "",
                        getattr(doc, "categoria", "") or "",
                        nombre_en_zip
                    ])
                
                # --- IMPORTANTE: Escribir los bytes codificados en UTF-8 en el ZIP ---
                zf.writestr("index.csv", buf.getvalue().encode('utf-8'))
                buf.close()
                # --- FIN ---

                # 2) Añadir archivos físicos al ZIP
                for i, doc, nombre_en_zip in archivos_para_zip:
                    ruta_guardada = getattr(doc, "ruta_archivo", "") or ""
                    
                    if ruta_guardada:
                        ruta_absoluta = reconstruir_ruta_absoluta(ruta_guardada)
                        if ruta_absoluta and os.path.isfile(ruta_absoluta):
                            zf.write(ruta_absoluta, arcname=nombre_en_zip)
                            print(f"  - Añadido: {nombre_en_zip} (Desde: {ruta_absoluta})")
                        else:
                            print(f"  - FALTANTE: {nombre_en_zip} (Ruta no encontrada: {ruta_absoluta})")
                            zf.writestr(nombre_en_zip, f"Archivo no encontrado en la ruta:\n{ruta_absoluta}\n\nRuta guardada: {ruta_guardada}")
                    else:
                        print(f"  - FALTANTE: {nombre_en_zip} (Sin ruta)")
                        zf.writestr(nombre_en_zip, "Documento sin archivo adjunto.")

            generados.append(out_zip_path)

        except Exception as e:
            msg = f"No se pudo crear el ZIP para '{cat_name}': {e}"
            print(f"ERROR: {msg}")
            logging.exception(msg)
            errores.append(f"- {cat_name}: {e}")

    return (len(generados) > 0), generados, errores