#!/usr/bin/env python3
"""
Script de migración de SQLite a Firestore para la aplicación LICITACIONES.

Este script migra todos los datos desde una base de datos SQLite local
a Google Firestore en la nube.

Uso:
    python tools/migrate_to_firestore.py --sqlite LICITACIONES_GENERALES.db
    python tools/migrate_to_firestore.py --sqlite LICITACIONES_GENERALES.db --dry-run
    python tools/migrate_to_firestore.py --help

Requisitos:
    - Archivo .env configurado con GOOGLE_APPLICATION_CREDENTIALS
    - Base de datos SQLite origen con datos válidos
    - Proyecto Firestore creado y configurado
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Any

# Configurar el path para importar módulos de la app
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def initialize_firestore():
    """
    Inicializa y retorna el cliente de Firestore.
    
    Returns:
        Cliente de Firestore configurado
    
    Raises:
        RuntimeError: Si las credenciales no están configuradas
    """
    from firebase_admin import App, credentials, firestore, initialize_app
    from app.core import firebase_adapter
    from typing import Optional
    
    load_dotenv()
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    if not credentials_path:
        # Intentar con JSON directo en variable de entorno
        json_key = os.getenv("LICITACIONES_FIRESTORE_KEY_JSON")
        if json_key:
            import json
            cred = credentials.Certificate(json.loads(json_key))
        else:
            raise RuntimeError(
                "GOOGLE_APPLICATION_CREDENTIALS no está configurado en .env\n"
                "Por favor configura la ruta al archivo de credenciales JSON de Firebase."
            )
    else:
        if not os.path.exists(credentials_path):
            raise RuntimeError(
                f"El archivo de credenciales no existe: {credentials_path}\n"
                "Verifica que GOOGLE_APPLICATION_CREDENTIALS en .env apunte al archivo correcto."
            )
        cred = credentials.Certificate(credentials_path)
    
    project_id = os.getenv("FIREBASE_PROJECT_ID")
    options = {"projectId": project_id} if project_id else None
    
    try:
        app: Optional[App] = initialize_app(cred, options)
    except ValueError:
        # App already initialized
        app = None
    
    client = firestore.client(app)
    firebase_adapter.set_client(client)
    
    logger.info(f"Cliente Firestore inicializado para proyecto: {project_id or 'default'}")
    return client


def migrate_data(sqlite_path: str, dry_run: bool = False) -> Dict[str, int]:
    """
    Migra todos los datos desde SQLite a Firestore.
    
    Args:
        sqlite_path: Ruta al archivo SQLite
        dry_run: Si es True, no realiza cambios reales
    
    Returns:
        Diccionario con estadísticas de migración
    """
    from app.core.db_adapter_sqlite import SQLiteDatabaseAdapter
    from app.core.db_adapter import DatabaseAdapter
    
    stats = {
        "licitaciones": 0,
        "empresas_maestras": 0,
        "instituciones_maestras": 0,
        "documentos_maestros": 0,
        "competidores_maestros": 0,
        "responsables_maestros": 0,
        "fallas_fase_a": 0,
        "subsanaciones": 0,
        "errores": 0,
    }
    
    logger.info("=" * 70)
    logger.info("INICIANDO MIGRACIÓN DE SQLITE A FIRESTORE")
    logger.info("=" * 70)
    
    if dry_run:
        logger.warning("MODO DRY-RUN ACTIVADO - No se realizarán cambios reales")
    
    # Verificar que el archivo SQLite existe
    if not os.path.exists(sqlite_path):
        raise FileNotFoundError(f"No se encontró el archivo SQLite: {sqlite_path}")
    
    logger.info(f"Origen SQLite: {sqlite_path}")
    
    # Inicializar adaptadores
    logger.info("Inicializando adaptador SQLite...")
    sqlite_adapter = SQLiteDatabaseAdapter(db_path=sqlite_path)
    sqlite_adapter.open()
    
    if not dry_run:
        logger.info("Inicializando cliente Firestore...")
        firestore_client = initialize_firestore()
        firestore_adapter = DatabaseAdapter(client=firestore_client)
        firestore_adapter.open()
    else:
        firestore_adapter = None
    
    try:
        # ================================================
        # 1. Migrar Licitaciones
        # ================================================
        logger.info("\n[1/8] Migrando Licitaciones...")
        licitaciones = sqlite_adapter.load_all_licitaciones()
        logger.info(f"  Encontradas {len(licitaciones)} licitaciones")
        
        for i, lic in enumerate(licitaciones, 1):
            try:
                if not dry_run:
                    # Guardar en Firestore
                    firestore_adapter.save_licitacion(lic)
                
                stats["licitaciones"] += 1
                if i % 10 == 0:
                    logger.info(f"  Procesadas {i}/{len(licitaciones)} licitaciones...")
            except Exception as e:
                logger.error(f"  Error migrando licitación {lic.numero_proceso}: {e}")
                stats["errores"] += 1
        
        logger.info(f"  ✓ Migradas {stats['licitaciones']} licitaciones")
        
        # ================================================
        # 2. Migrar Empresas Maestras
        # ================================================
        logger.info("\n[2/8] Migrando Empresas Maestras...")
        empresas = sqlite_adapter.get_empresas_maestras()
        logger.info(f"  Encontradas {len(empresas)} empresas")
        
        if not dry_run and empresas:
            try:
                firestore_adapter.save_empresas_maestras(empresas)
                stats["empresas_maestras"] = len(empresas)
            except Exception as e:
                logger.error(f"  Error migrando empresas: {e}")
                stats["errores"] += 1
        else:
            stats["empresas_maestras"] = len(empresas)
        
        logger.info(f"  ✓ Migradas {stats['empresas_maestras']} empresas")
        
        # ================================================
        # 3. Migrar Instituciones Maestras
        # ================================================
        logger.info("\n[3/8] Migrando Instituciones Maestras...")
        instituciones = sqlite_adapter.get_instituciones_maestras()
        logger.info(f"  Encontradas {len(instituciones)} instituciones")
        
        if not dry_run and instituciones:
            try:
                firestore_adapter.save_instituciones_maestras(instituciones)
                stats["instituciones_maestras"] = len(instituciones)
            except Exception as e:
                logger.error(f"  Error migrando instituciones: {e}")
                stats["errores"] += 1
        else:
            stats["instituciones_maestras"] = len(instituciones)
        
        logger.info(f"  ✓ Migradas {stats['instituciones_maestras']} instituciones")
        
        # ================================================
        # 4. Migrar Documentos Maestros
        # ================================================
        logger.info("\n[4/8] Migrando Documentos Maestros...")
        documentos = sqlite_adapter.get_documentos_maestros()
        logger.info(f"  Encontrados {len(documentos)} documentos")
        
        if not dry_run and documentos:
            try:
                firestore_adapter.save_documentos_maestros(documentos)
                stats["documentos_maestros"] = len(documentos)
            except Exception as e:
                logger.error(f"  Error migrando documentos: {e}")
                stats["errores"] += 1
        else:
            stats["documentos_maestros"] = len(documentos)
        
        logger.info(f"  ✓ Migrados {stats['documentos_maestros']} documentos maestros")
        
        # ================================================
        # 5. Migrar Competidores Maestros
        # ================================================
        logger.info("\n[5/8] Migrando Competidores Maestros...")
        competidores = sqlite_adapter.get_competidores_maestros()
        logger.info(f"  Encontrados {len(competidores)} competidores")
        
        if not dry_run and competidores:
            try:
                firestore_adapter.save_competidores_maestros(competidores)
                stats["competidores_maestros"] = len(competidores)
            except Exception as e:
                logger.error(f"  Error migrando competidores: {e}")
                stats["errores"] += 1
        else:
            stats["competidores_maestros"] = len(competidores)
        
        logger.info(f"  ✓ Migrados {stats['competidores_maestros']} competidores")
        
        # ================================================
        # 6. Migrar Responsables Maestros
        # ================================================
        logger.info("\n[6/8] Migrando Responsables Maestros...")
        responsables = sqlite_adapter.get_responsables_maestros()
        logger.info(f"  Encontrados {len(responsables)} responsables")
        
        if not dry_run and responsables:
            try:
                firestore_adapter.save_responsables_maestros(responsables)
                stats["responsables_maestros"] = len(responsables)
            except Exception as e:
                logger.error(f"  Error migrando responsables: {e}")
                stats["errores"] += 1
        else:
            stats["responsables_maestros"] = len(responsables)
        
        logger.info(f"  ✓ Migrados {stats['responsables_maestros']} responsables")
        
        # ================================================
        # 7. Migrar Fallas Fase A
        # ================================================
        logger.info("\n[7/8] Migrando Fallas de Fase A...")
        todas_fallas = sqlite_adapter.obtener_todas_las_fallas()
        logger.info(f"  Encontradas {len(todas_fallas)} fallas")
        
        if not dry_run:
            from app.core.firebase_adapter import add_doc
            from app.core.db_adapter import FALLAS_COLLECTION
            
            for falla in todas_fallas:
                try:
                    add_doc(FALLAS_COLLECTION, falla)
                    stats["fallas_fase_a"] += 1
                except Exception as e:
                    logger.error(f"  Error migrando falla: {e}")
                    stats["errores"] += 1
        else:
            stats["fallas_fase_a"] = len(todas_fallas)
        
        logger.info(f"  ✓ Migradas {stats['fallas_fase_a']} fallas")
        
        # ================================================
        # 8. Migrar Subsanaciones (si existen)
        # ================================================
        logger.info("\n[8/8] Migrando Subsanaciones...")
        # Las subsanaciones se migran por licitación
        total_subsanaciones = 0
        
        for lic in licitaciones:
            try:
                historial = sqlite_adapter.obtener_historial_subsanacion(lic.id)
                if historial and not dry_run:
                    firestore_adapter.registrar_eventos_subsanacion(lic.id, historial)
                total_subsanaciones += len(historial)
            except Exception as e:
                logger.error(f"  Error migrando subsanaciones de licitación {lic.numero_proceso}: {e}")
                stats["errores"] += 1
        
        stats["subsanaciones"] = total_subsanaciones
        logger.info(f"  ✓ Migradas {stats['subsanaciones']} subsanaciones")
        
    finally:
        # Cerrar conexiones
        sqlite_adapter.close()
        if firestore_adapter:
            firestore_adapter.close()
    
    return stats


def print_summary(stats: Dict[str, int], dry_run: bool):
    """
    Imprime un resumen de la migración.
    
    Args:
        stats: Diccionario con estadísticas
        dry_run: Si fue una ejecución en modo dry-run
    """
    logger.info("\n" + "=" * 70)
    logger.info("RESUMEN DE MIGRACIÓN")
    logger.info("=" * 70)
    
    if dry_run:
        logger.info("MODO: DRY-RUN (simulación, sin cambios reales)")
    else:
        logger.info("MODO: PRODUCCIÓN (cambios aplicados)")
    
    logger.info("")
    logger.info(f"  Licitaciones:           {stats['licitaciones']:>6}")
    logger.info(f"  Empresas Maestras:      {stats['empresas_maestras']:>6}")
    logger.info(f"  Instituciones Maestras: {stats['instituciones_maestras']:>6}")
    logger.info(f"  Documentos Maestros:    {stats['documentos_maestros']:>6}")
    logger.info(f"  Competidores Maestros:  {stats['competidores_maestros']:>6}")
    logger.info(f"  Responsables Maestros:  {stats['responsables_maestros']:>6}")
    logger.info(f"  Fallas Fase A:          {stats['fallas_fase_a']:>6}")
    logger.info(f"  Subsanaciones:          {stats['subsanaciones']:>6}")
    logger.info("")
    logger.info(f"  Errores:                {stats['errores']:>6}")
    logger.info("=" * 70)
    
    if stats['errores'] > 0:
        logger.warning(f"\n⚠️  La migración completó con {stats['errores']} errores")
    else:
        logger.info("\n✓ Migración completada exitosamente sin errores")
    
    if dry_run:
        logger.info("\n💡 Ejecuta sin --dry-run para aplicar los cambios reales")


def main():
    """Punto de entrada principal del script."""
    parser = argparse.ArgumentParser(
        description="Migra datos desde SQLite a Firestore",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:

  # Ejecutar migración en modo dry-run (simulación)
  python tools/migrate_to_firestore.py --sqlite LICITACIONES_GENERALES.db --dry-run
  
  # Ejecutar migración real
  python tools/migrate_to_firestore.py --sqlite LICITACIONES_GENERALES.db
  
  # Usar base de datos de backup
  python tools/migrate_to_firestore.py --sqlite backups/LICITACIONES_GENERALES_auto_2025-11-02.db

Requisitos:
  - Archivo .env configurado con GOOGLE_APPLICATION_CREDENTIALS
  - Proyecto Firestore creado y configurado
  - pip install -r requirements.txt
        """
    )
    
    parser.add_argument(
        "--sqlite",
        required=True,
        help="Ruta al archivo de base de datos SQLite origen"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Modo simulación: no realiza cambios reales, solo muestra qué se migraría"
    )
    
    args = parser.parse_args()
    
    try:
        # Ejecutar migración
        stats = migrate_data(args.sqlite, dry_run=args.dry_run)
        
        # Mostrar resumen
        print_summary(stats, args.dry_run)
        
        # Retornar código de salida según resultado
        sys.exit(0 if stats['errores'] == 0 else 1)
        
    except Exception as e:
        logger.error(f"\n❌ Error fatal durante la migración: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
