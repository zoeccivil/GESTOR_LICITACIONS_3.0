#!/usr/bin/env python3
"""
Script to seed demo data into MySQL database.

This script creates sample data for testing the application
with multiple users and concurrent access scenarios.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import random

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from sqlalchemy import text
from db import get_session

# Load environment variables
load_dotenv()


def seed_master_data():
    """Seed master/catalog tables."""
    print("Poblando datos maestros...")
    
    with get_session() as session:
        with session.begin():
            # Instituciones
            session.execute(text("""
                INSERT INTO instituciones_maestras (nombre, rnc, telefono, correo, direccion)
                VALUES
                    ('Ministerio de Obras Públicas', '401-00000-0', '809-565-5678', 'contacto@mopc.gob.do', 'Av. San Martín'),
                    ('Instituto Nacional de Aguas Potables', '401-11111-1', '809-598-1234', 'info@inapa.gob.do', 'Av. Independencia'),
                    ('Dirección General de Contrataciones Públicas', '401-22222-2', '809-686-9191', 'dgcp@gob.do', 'Av. México')
                ON CONFLICT (nombre) DO NOTHING
            """))
            
            # Empresas nuestras
            session.execute(text("""
                INSERT INTO empresas_maestras (nombre, rnc, rpe, representante, cargo_representante)
                VALUES
                    ('ZOEC CIVIL SRL', '131-12345-6', 'RPE-001', 'Juan Pérez', 'Director General'),
                    ('ZOEC CONSTRUCCIONES SRL', '131-23456-7', 'RPE-002', 'María González', 'Gerente de Proyectos')
                ON CONFLICT (nombre) DO NOTHING
            """))
            
            # Competidores
            session.execute(text("""
                INSERT INTO competidores_maestros (nombre, rnc, rpe, total_participaciones, total_ganadas)
                VALUES
                    ('Constructora ABC', '131-98765-4', 'RPE-100', 15, 8),
                    ('Ingeniería XYZ', '131-87654-3', 'RPE-101', 20, 12),
                    ('Obras DEF', '131-76543-2', 'RPE-102', 10, 5)
                ON CONFLICT (nombre) DO NOTHING
            """))
            
            # Responsables
            session.execute(text("""
                INSERT INTO responsables_maestros (nombre)
                VALUES
                    ('Carlos Rodríguez'),
                    ('Ana Martínez'),
                    ('Luis Fernández')
                ON CONFLICT (nombre) DO NOTHING
            """))
            
            # Criterios BNB
            session.execute(text("""
                INSERT INTO criterios_bnb (nombre, peso, activo)
                VALUES
                    ('Experiencia en proyectos similares', 0.30, TRUE),
                    ('Capacidad técnica', 0.25, TRUE),
                    ('Plan de trabajo', 0.20, TRUE),
                    ('Equipo profesional', 0.15, TRUE),
                    ('Referencias', 0.10, TRUE)
                ON CONFLICT DO NOTHING
            """))
            
            # Categorías de documentos
            session.execute(text("""
                INSERT INTO categorias (nombre)
                VALUES
                    ('Legal'),
                    ('Técnica'),
                    ('Financiera'),
                    ('Administrativa')
                ON CONFLICT DO NOTHING
            """))
    
    print("✓ Master data seeded")


def seed_licitaciones():
    """Seed sample licitaciones."""
    print("Poblando licitaciones...")
    
    with get_session() as session:
        with session.begin():
            # Create sample licitaciones
            base_date = datetime.now() - timedelta(days=90)
            
            licitaciones_data = [
                {
                    'nombre_proceso': 'Construcción de Acueducto Rural',
                    'numero_proceso': 'LPN-2024-001',
                    'institucion': 'Instituto Nacional de Aguas Potables',
                    'empresa_nuestra': 'ZOEC CIVIL SRL',
                    'estado': 'En Evaluación',
                    'fecha_creacion': base_date + timedelta(days=10),
                    'adjudicada': False,
                },
                {
                    'nombre_proceso': 'Rehabilitación Carretera Nagua-Cabrera',
                    'numero_proceso': 'LPN-2024-002',
                    'institucion': 'Ministerio de Obras Públicas',
                    'empresa_nuestra': 'ZOEC CONSTRUCCIONES SRL',
                    'estado': 'Adjudicada',
                    'fecha_creacion': base_date + timedelta(days=5),
                    'adjudicada': True,
                    'adjudicada_a': 'ZOEC CONSTRUCCIONES SRL',
                },
                {
                    'nombre_proceso': 'Construcción Puente Peatonal',
                    'numero_proceso': 'LPN-2024-003',
                    'institucion': 'Ministerio de Obras Públicas',
                    'empresa_nuestra': 'ZOEC CIVIL SRL',
                    'estado': 'Preparación Oferta',
                    'fecha_creacion': base_date + timedelta(days=30),
                    'adjudicada': False,
                },
            ]
            
            for lic in licitaciones_data:
                session.execute(text("""
                    INSERT INTO licitaciones 
                    (nombre_proceso, numero_proceso, institucion, empresa_nuestra, estado, 
                     fecha_creacion, adjudicada, adjudicada_a)
                    VALUES 
                    (:nombre_proceso, :numero_proceso, :institucion, :empresa_nuestra, :estado,
                     :fecha_creacion, :adjudicada, :adjudicada_a)
                    ON CONFLICT (numero_proceso) DO NOTHING
                """), lic)
    
    print("✓ Licitaciones seeded")


def seed_lotes_and_documentos():
    """Seed lotes and documentos for licitaciones."""
    print("Poblando lotes y documentos...")
    
    with get_session() as session:
        with session.begin():
            # Get licitacion IDs
            result = session.execute(text("SELECT id, numero_proceso FROM licitaciones ORDER BY id LIMIT 3"))
            licitaciones = result.fetchall()
            
            for lic_id, num_proceso in licitaciones:
                # Add lotes
                if 'LPN-2024-001' in num_proceso:
                    # Single lote
                    session.execute(text("""
                        INSERT INTO lotes 
                        (licitacion_id, numero, nombre, monto_base, participamos)
                        VALUES 
                        (:lic_id, '001', 'Lote Único', 5000000.00, TRUE)
                    """), {'lic_id': lic_id})
                else:
                    # Multiple lotes
                    for i in range(1, 3):
                        session.execute(text("""
                            INSERT INTO lotes 
                            (licitacion_id, numero, nombre, monto_base, participamos)
                            VALUES 
                            (:lic_id, :numero, :nombre, :monto, TRUE)
                        """), {
                            'lic_id': lic_id,
                            'numero': f'{i:03d}',
                            'nombre': f'Lote {i}',
                            'monto': random.uniform(1000000, 10000000)
                        })
                
                # Add documentos
                docs = [
                    ('DOC-001', 'RNC de la empresa', 'Legal', True),
                    ('DOC-002', 'Certificado de RPE', 'Legal', True),
                    ('DOC-003', 'Propuesta Técnica', 'Técnica', True),
                    ('DOC-004', 'Propuesta Económica', 'Financiera', True),
                    ('DOC-005', 'Referencias de proyectos', 'Técnica', True),
                ]
                
                for codigo, nombre, categoria, obligatorio in docs:
                    session.execute(text("""
                        INSERT INTO documentos 
                        (licitacion_id, codigo, nombre, categoria, obligatorio, presentado, revisado)
                        VALUES 
                        (:lic_id, :codigo, :nombre, :categoria, :obligatorio, :presentado, :revisado)
                    """), {
                        'lic_id': lic_id,
                        'codigo': codigo,
                        'nombre': nombre,
                        'categoria': categoria,
                        'obligatorio': obligatorio,
                        'presentado': random.choice([True, False]),
                        'revisado': random.choice([True, False]),
                    })
    
    print("✓ Lotes and documentos seeded")


def seed_oferentes():
    """Seed oferentes (competitors) for licitaciones."""
    print("Poblando oferentes...")
    
    with get_session() as session:
        with session.begin():
            # Get licitacion IDs
            result = session.execute(text("SELECT id FROM licitaciones ORDER BY id LIMIT 3"))
            licitaciones = [row[0] for row in result.fetchall()]
            
            # Get competitor names
            result = session.execute(text("SELECT nombre FROM competidores_maestros"))
            competitors = [row[0] for row in result.fetchall()]
            
            for lic_id in licitaciones:
                # Add 2-3 random competitors per licitacion
                num_competitors = random.randint(2, min(3, len(competitors)))
                selected_competitors = random.sample(competitors, num_competitors)
                
                for comp_name in selected_competitors:
                    session.execute(text("""
                        INSERT INTO oferentes (licitacion_id, nombre, comentario)
                        VALUES (:lic_id, :nombre, :comentario)
                    """), {
                        'lic_id': lic_id,
                        'nombre': comp_name,
                        'comentario': f'Participante en licitación {lic_id}'
                    })
    
    print("✓ Oferentes seeded")


def main():
    """Main seeding function."""
    print("=" * 70)
    print("Población de Datos de Demostración MySQL")
    print("=" * 70)
    print()
    
    try:
        seed_master_data()
        seed_licitaciones()
        seed_lotes_and_documentos()
        seed_oferentes()
        
        print()
        print("=" * 70)
        print("✓ Demo data seeded successfully!")
        print("=" * 70)
        print()
        print("Resumen:")
        
        with get_session() as session:
            tables = [
                'instituciones_maestras',
                'empresas_maestras',
                'competidores_maestros',
                'responsables_maestros',
                'criterios_bnb',
                'licitaciones',
                'lotes',
                'documentos',
                'oferentes',
            ]
            
            for table in tables:
                result = session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                print(f"  {table:<30} {count:>5} rows")
        
        print()
        print("You can now start the application and test with multiple users!")
        return 0
        
    except Exception as e:
        print()
        print(f"✗ Error seeding data: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
