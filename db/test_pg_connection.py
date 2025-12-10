"""
Prueba directa de conexión a PostgreSQL 18
"""

from sqlalchemy import create_engine, text

# Configura directamente tus parámetros aquí
DB_USER = "zoec_app"
DB_PASSWORD = "TuContraseñaSegura"
DB_HOST = "10.0.0.250"
DB_PORT = "5432"
DB_NAME = "zoec_db"

# Construir la URL de conexión (psycopg3)
DATABASE_URL = f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def test_connection():
    print("Probando conexión a PostgreSQL...")
    print(f"Conectando a {DB_HOST}:{DB_PORT}/{DB_NAME} como {DB_USER}")

    try:
        engine = create_engine(DATABASE_URL, echo=True, future=True)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.scalar()
            print(f"✅ Conectado correctamente a: {version}")
            return True
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False

if __name__ == "__main__":
    test_connection()
