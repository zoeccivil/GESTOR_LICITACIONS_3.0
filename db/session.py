"""
Gestión de sesiones para operaciones de base de datos.

Este módulo provee gestión de sesiones para transacciones de base de datos
usando el sessionmaker de SQLAlchemy.
"""

from contextlib import contextmanager
from typing import Generator
from sqlalchemy.orm import sessionmaker, Session
from db.engine import get_engine


# Crear sessionmaker vinculado al motor
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)


def init_session_factory():
    """Inicializar la fábrica de sesiones con el motor."""
    engine = get_engine()
    if engine is not None:
        SessionLocal.configure(bind=engine)


# Inicializar la fábrica de sesiones
init_session_factory()


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Proveer un ámbito transaccional para operaciones de base de datos.
    
    Uso:
        with get_session() as session:
            # Realizar operaciones de base de datos
            session.add(obj)
            session.commit()
    
    La sesión se cierra automáticamente después del bloque.
    Si ocurre una excepción, la transacción se revierte.
    
    Yields:
        Session: Sesión de SQLAlchemy
    """
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_session() -> Session:
    """
    Crear una nueva sesión de base de datos.
    
    Nota: El llamador es responsable de cerrar la sesión.
    Considere usar el context manager get_session() en su lugar.
    
    Returns:
        Session: Sesión de SQLAlchemy
    """
    return SessionLocal()


class ConcurrencyException(Exception):
    """Excepción lanzada cuando el bloqueo optimista detecta un conflicto."""
    pass


def update_with_version(session: Session, table_name: str, record_id: int, 
                       current_version: int, updates: dict) -> bool:
    """
    Actualizar un registro con bloqueo optimista.
    
    Esta función asegura que el registro no haya sido modificado por otro usuario
    desde que fue leído por última vez, verificando el número de versión.
    
    Args:
        session: Sesión de SQLAlchemy
        table_name: Nombre de la tabla
        record_id: ID del registro a actualizar
        current_version: Versión actual esperada
        updates: Diccionario de campos a actualizar
        
    Returns:
        bool: True si la actualización fue exitosa
        
    Raises:
        ConcurrencyException: Si el registro ha sido modificado por otro usuario
    """
    from sqlalchemy import text
    
    # Construir cláusula SET
    set_clauses = []
    params = {'id': record_id, 'version': current_version}
    
    for key, value in updates.items():
        set_clauses.append(f"{key} = :{key}")
        params[key] = value
    
    # Agregar incremento de versión y updated_at
    set_clauses.append("version = version + 1")
    set_clauses.append("updated_at = CURRENT_TIMESTAMP")
    
    set_clause = ", ".join(set_clauses)
    
    # Ejecutar actualización con verificación de versión
    sql = text(f"""
        UPDATE {table_name}
        SET {set_clause}
        WHERE id = :id AND version = :version
    """)
    
    result = session.execute(sql, params)
    
    if result.rowcount == 0:
        # Verificar si el registro existe
        check_sql = text(f"SELECT version FROM {table_name} WHERE id = :id")
        check_result = session.execute(check_sql, {'id': record_id})
        row = check_result.fetchone()
        
        if row is None:
            raise ValueError(f"Registro con id {record_id} no encontrado")
        else:
            raise ConcurrencyException(
                f"El registro ha sido modificado por otro usuario. "
                f"Versión esperada {current_version}, pero la versión actual es {row[0]}. "
                f"Por favor refresque e intente nuevamente."
            )
    
    return True


if __name__ == "__main__":
    # Probar creación de sesión
    print("Probando creación de sesión...")
    
    with get_session() as session:
        result = session.execute("SELECT current_database(), current_user")
        db_name, user = result.fetchone()
        print(f"✓ Conectado a base de datos '{db_name}' como usuario '{user}'")
