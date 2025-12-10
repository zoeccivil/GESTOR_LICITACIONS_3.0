"""
Configuración del motor de base de datos para MySQL.

Este módulo crea y configura el motor SQLAlchemy para la conexión a MySQL
usando variables de entorno para la configuración.
"""

import os
from typing import Optional
from sqlalchemy import create_engine, event, Engine
from sqlalchemy.pool import Pool
from dotenv import load_dotenv

# Instalar PyMySQL como reemplazo de MySQLdb para compatibilidad en Windows
# PyMySQL es puro Python y no requiere compilación, ideal para Windows
try:
    import pymysql
    pymysql.install_as_MySQLdb()
    _USING_PYMYSQL = True
except ImportError:
    _USING_PYMYSQL = False
    # Si PyMySQL no está instalado, intentará usar mysqlclient (más rápido pero requiere compilación)

# Cargar variables de entorno desde archivo .env
load_dotenv()


def get_database_url() -> str:
    """
    Construir la URL de base de datos desde variables de entorno.
    
    Returns:
        str: URL de conexión a MySQL
        
    Raises:
        ValueError: Si faltan variables de entorno requeridas
    """
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST')
    db_port = os.getenv('DB_PORT')
    db_name = os.getenv('DB_NAME')
    
    if not all([db_user, db_password, db_host, db_port, db_name]):
        raise ValueError(
            "Faltan variables de entorno requeridas para la base de datos. "
            "Por favor asegúrese de que DB_USER, DB_PASSWORD, DB_HOST, DB_PORT y DB_NAME estén definidas."
        )
    
    # Usar PyMySQL o mysqlclient como driver para MySQL
    # PyMySQL: Puro Python, fácil de instalar en Windows (recomendado)
    # mysqlclient: Más rápido pero requiere compilación en Windows
    # Formato: mysql+pymysql://user:password@host:port/database
    driver = "pymysql" if _USING_PYMYSQL else "mysqldb"
    return f"mysql+{driver}://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4"


def create_db_engine(echo: bool = False) -> Engine:
    """
    Crear y configurar el motor SQLAlchemy.
    
    Args:
        echo: Si es True, registra todas las sentencias SQL (útil para depuración)
        
    Returns:
        Engine: Motor SQLAlchemy configurado
    """
    url = get_database_url()
    
    # Obtener configuración del pool desde el entorno
    pool_size = int(os.getenv('DB_POOL_SIZE', 10))
    max_overflow = int(os.getenv('DB_MAX_OVERFLOW', 20))
    
    engine = create_engine(
        url,
        echo=echo,
        pool_pre_ping=True,  # Verificar conexiones antes de usarlas
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_recycle=3600,  # Reciclar conexiones después de 1 hora
        connect_args={
            'connect_timeout': 10,
        }
    )
    
    # Agregar listener de eventos para configurar la sesión MySQL
    @event.listens_for(engine, "connect")
    def set_mysql_session_vars(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        # Configurar zona horaria y modo SQL
        cursor.execute("SET time_zone = '-04:00'")  # America/Santo_Domingo
        cursor.execute("SET sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION'")
        cursor.close()
    
    return engine


# Crear la instancia global del motor
# Esto se usará en toda la aplicación
try:
    engine = create_db_engine(echo=os.getenv('SQL_ECHO', '').lower() == 'true')
except ValueError as e:
    # Si las variables de entorno no están definidas, engine será None
    # Esto permite importar el módulo sin fallar durante la configuración
    engine = None
    import warnings
    warnings.warn(
        f"Motor de base de datos no inicializado: {e}\n\n"
        "Para configurar la base de datos:\n"
        "1. Copie el archivo .env.example a .env: cp .env.example .env\n"
        "2. Edite .env con sus valores de configuración\n"
        "3. Asegúrese de que MySQL esté corriendo: docker compose up -d\n\n"
        "Ver README.md para más detalles.",
        stacklevel=2
    )


def get_engine() -> Optional[Engine]:
    """
    Obtener la instancia global del motor de base de datos.
    
    Returns:
        Engine: El motor SQLAlchemy o None si no está inicializado
    """
    return engine


def test_connection() -> bool:
    """
    Probar la conexión a la base de datos.
    
    Returns:
        bool: True si la conexión es exitosa, False en caso contrario
    """
    if engine is None:
        print("✗ Error: Motor de base de datos no inicializado.")
        print("")
        print("Para configurar:")
        print("  1. Copie .env.example a .env: cp .env.example .env")
        print("  2. Edite .env con sus valores")
        print("  3. Inicie MySQL: docker compose up -d")
        print("")
        return False
    
    try:
        with engine.connect() as conn:
            result = conn.execute("SELECT VERSION()")
            version = result.scalar()
            print(f"✓ Conectado a MySQL: {version}")
            return True
    except Exception as e:
        print(f"✗ Conexión fallida: {e}")
        print("")
        print("Verifique que:")
        print("  - MySQL esté corriendo: docker compose ps")
        print("  - Las credenciales en .env sean correctas")
        print("  - El puerto 3306 esté disponible")
        print("")
        return False


if __name__ == "__main__":
    # Probar la conexión cuando se ejecuta directamente
    print("Probando conexión a base de datos...")
    print(f"URL de base de datos: {get_database_url().replace(os.getenv('DB_PASSWORD', ''), '***')}")
    test_connection()
