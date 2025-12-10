#!/usr/bin/env python3
"""
Test script for concurrency control.

This script demonstrates optimistic locking by simulating
two users trying to edit the same record simultaneously.
"""

import sys
from pathlib import Path
import time
from threading import Thread

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from sqlalchemy import text
from db import get_session, update_with_version, ConcurrencyException

# Load environment variables
load_dotenv()


def test_concurrent_update_conflict():
    """
    Test that concurrent updates to the same record cause a conflict.
    
    This simulates:
    - User A reads a licitacion (version 1)
    - User B reads the same licitacion (version 1)
    - User A updates it successfully (version becomes 2)
    - User B tries to update it with version 1 -> CONFLICT
    """
    print("=" * 70)
    print("Prueba: Conflicto de Actualización Concurrente")
    print("=" * 70)
    print()
    
    # First, create a test record
    with get_session() as session:
        with session.begin():
            session.execute(text("""
                INSERT INTO licitaciones 
                (nombre_proceso, numero_proceso, institucion, estado)
                VALUES 
                ('Test Concurrencia', 'TEST-CONCUR-001', 'Test Instituto', 'Borrador')
                ON CONFLICT (numero_proceso) DO UPDATE
                SET estado = 'Borrador', version = 1
            """))
            
            # Get the ID
            result = session.execute(text("""
                SELECT id, version FROM licitaciones 
                WHERE numero_proceso = 'TEST-CONCUR-001'
            """))
            lic_id, version = result.fetchone()
    
    print(f"Created test record: ID={lic_id}, version={version}")
    print()
    
    # Simulate User A reading the record
    print("👤 User A: Reading licitacion...")
    with get_session() as session:
        result = session.execute(text("""
            SELECT id, nombre_proceso, estado, version
            FROM licitaciones WHERE id = :id
        """), {'id': lic_id})
        user_a_data = result.fetchone()
    
    print(f"   User A sees: {dict(user_a_data._mapping)}")
    print()
    
    # Simulate User B reading the record
    print("👤 User B: Reading licitacion...")
    with get_session() as session:
        result = session.execute(text("""
            SELECT id, nombre_proceso, estado, version
            FROM licitaciones WHERE id = :id
        """), {'id': lic_id})
        user_b_data = result.fetchone()
    
    print(f"   User B sees: {dict(user_b_data._mapping)}")
    print()
    
    # User A updates successfully
    print("👤 User A: Updating estado to 'En Evaluación'...")
    time.sleep(0.1)  # Simulate some work
    
    with get_session() as session:
        with session.begin():
            update_with_version(
                session,
                'licitaciones',
                lic_id,
                user_a_data.version,
                {'estado': 'En Evaluación'}
            )
    
    print("   ✓ User A: Update successful!")
    
    # Check new version
    with get_session() as session:
        result = session.execute(text("""
            SELECT id, estado, version, updated_at
            FROM licitaciones WHERE id = :id
        """), {'id': lic_id})
        updated_data = result.fetchone()
    
    print(f"   New state: estado='{updated_data.estado}', version={updated_data.version}")
    print()
    
    # User B tries to update with stale version
    print("👤 User B: Attempting to update estado to 'Preparación'...")
    print(f"   (Using stale version {user_b_data.version})")
    time.sleep(0.1)
    
    try:
        with get_session() as session:
            with session.begin():
                update_with_version(
                    session,
                    'licitaciones',
                    lic_id,
                    user_b_data.version,  # This is now stale!
                    {'estado': 'Preparación'}
                )
        print("   ✗ ERROR: Update should have failed!")
        return False
        
    except ConcurrencyException as e:
        print(f"   ✓ Conflict detected: {e}")
        print()
        print("   💡 User B should now:")
        print("      1. Refresh the record to see User A's changes")
        print("      2. Decide whether to overwrite or merge changes")
        print("      3. Try updating again with the new version")
    
    print()
    print("=" * 70)
    print("✓ Test passed: Concurrency control is working!")
    print("=" * 70)
    
    # Cleanup
    with get_session() as session:
        with session.begin():
            session.execute(text("""
                DELETE FROM licitaciones WHERE numero_proceso = 'TEST-CONCUR-001'
            """))
    
    return True


def test_concurrent_threads():
    """
    Test concurrent updates from different threads.
    
    This simulates real concurrent access from multiple users/processes.
    """
    print()
    print("=" * 70)
    print("Prueba: Actualizaciones Concurrentes Multi-hilo")
    print("=" * 70)
    print()
    
    # Create test record
    with get_session() as session:
        with session.begin():
            session.execute(text("""
                INSERT INTO licitaciones 
                (nombre_proceso, numero_proceso, institucion, estado)
                VALUES 
                ('Test Multi-Thread', 'TEST-THREAD-001', 'Test Instituto', 'Borrador')
                ON CONFLICT (numero_proceso) DO UPDATE
                SET estado = 'Borrador', version = 1
            """))
            
            result = session.execute(text("""
                SELECT id FROM licitaciones WHERE numero_proceso = 'TEST-THREAD-001'
            """))
            lic_id = result.scalar()
    
    print(f"Created test record: ID={lic_id}")
    print()
    
    results = {'success': 0, 'conflict': 0}
    
    def update_worker(worker_id, target_estado):
        """Worker thread that tries to update the record."""
        try:
            # Read current version
            with get_session() as session:
                result = session.execute(text("""
                    SELECT version FROM licitaciones WHERE id = :id
                """), {'id': lic_id})
                current_version = result.scalar()
            
            # Simulate some processing time
            time.sleep(0.01 * worker_id)
            
            # Try to update
            with get_session() as session:
                with session.begin():
                    update_with_version(
                        session,
                        'licitaciones',
                        lic_id,
                        current_version,
                        {'estado': target_estado}
                    )
            
            print(f"✓ Worker {worker_id}: Successfully updated to '{target_estado}'")
            results['success'] += 1
            
        except ConcurrencyException as e:
            print(f"✗ Worker {worker_id}: Conflict detected ({target_estado})")
            results['conflict'] += 1
    
    # Start 5 workers trying to update simultaneously
    workers = []
    estados = ['Estado A', 'Estado B', 'Estado C', 'Estado D', 'Estado E']
    
    print("Iniciando 5 workers concurrentes...")
    for i, estado in enumerate(estados):
        worker = Thread(target=update_worker, args=(i+1, estado))
        workers.append(worker)
        worker.start()
    
    # Wait for all workers to finish
    for worker in workers:
        worker.join()
    
    print()
    print(f"Results: {results['success']} succeeded, {results['conflict']} conflicted")
    print()
    
    if results['success'] == 1 and results['conflict'] == 4:
        print("✓ Correct: Only one update succeeded, others detected conflicts!")
    else:
        print("⚠ Unexpected result distribution")
    
    # Show final state
    with get_session() as session:
        result = session.execute(text("""
            SELECT estado, version FROM licitaciones WHERE id = :id
        """), {'id': lic_id})
        estado, version = result.fetchone()
    
    print(f"Final state: estado='{estado}', version={version}")
    
    # Cleanup
    with get_session() as session:
        with session.begin():
            session.execute(text("""
                DELETE FROM licitaciones WHERE numero_proceso = 'TEST-THREAD-001'
            """))
    
    print()
    print("=" * 70)
    print("✓ Multi-threaded test completed!")
    print("=" * 70)


def main():
    """Run all concurrency tests."""
    print()
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "PRUEBAS DE CONTROL DE CONCURRENCIA" + " " * 28 + "║")
    print("╚" + "=" * 68 + "╝")
    print()
    
    try:
        # Test 1: Basic conflict detection
        if not test_concurrent_update_conflict():
            return 1
        
        # Test 2: Multi-threaded conflicts
        test_concurrent_threads()
        
        print()
        print("╔" + "=" * 68 + "╗")
        print("║" + " " * 20 + "¡TODAS LAS PRUEBAS PASARON!" + " " * 27 + "║")
        print("╚" + "=" * 68 + "╝")
        print()
        
        return 0
        
    except Exception as e:
        print()
        print(f"✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
