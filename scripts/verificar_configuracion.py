#!/usr/bin/env python3
"""
Script de verificación de configuración.

Este script verifica que todas las variables de entorno necesarias
estén configuradas correctamente y que MySQL esté accesible.
"""

import os
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

def verificar_archivo_env():
    """Verificar que existe el archivo .env"""
    env_path = Path(__file__).parent.parent / '.env'
    env_example_path = Path(__file__).parent.parent / '.env.example'
    
    print("=" * 70)
    print("Verificación de Configuración MySQL")
    print("=" * 70)
    print()
    
    if not env_path.exists():
        print("✗ Archivo .env no encontrado")
        print()
        if env_example_path.exists():
            print("Para crear el archivo .env:")
            print(f"  1. Copie .env.example a .env:")
            print(f"     cp .env.example .env")
            print(f"  2. Edite .env con sus valores de configuración")
            print()
        return False
    
    print("✓ Archivo .env encontrado")
    return True


def verificar_variables_entorno():
    """Verificar que todas las variables requeridas estén definidas"""
    from dotenv import load_dotenv
    load_dotenv()
    
    variables_requeridas = {
        'DB_HOST': 'Host del servidor MySQL',
        'DB_PORT': 'Puerto de MySQL',
        'DB_NAME': 'Nombre de la base de datos',
        'DB_USER': 'Usuario de la base de datos',
        'DB_PASSWORD': 'Contraseña del usuario',
    }
    
    variables_opcionales = {
        'DB_POOL_SIZE': 'Tamaño del pool de conexiones (default: 10)',
        'DB_MAX_OVERFLOW': 'Conexiones adicionales máximas (default: 20)',
    }
    
    print()
    print("Variables de Entorno Requeridas:")
    print("-" * 70)
    
    todas_ok = True
    for var, descripcion in variables_requeridas.items():
        valor = os.getenv(var)
        if valor:
            # Ocultar contraseña
            if 'PASSWORD' in var:
                valor_mostrar = '***' + valor[-3:] if len(valor) > 3 else '***'
            else:
                valor_mostrar = valor
            print(f"  ✓ {var:20} = {valor_mostrar}")
        else:
            print(f"  ✗ {var:20} = (no definida) - {descripcion}")
            todas_ok = False
    
    print()
    print("Variables de Entorno Opcionales:")
    print("-" * 70)
    
    for var, descripcion in variables_opcionales.items():
        valor = os.getenv(var)
        if valor:
            print(f"  ✓ {var:20} = {valor}")
        else:
            print(f"  ○ {var:20} = (usando default) - {descripcion}")
    
    return todas_ok


def verificar_conexion():
    """Verificar la conexión a MySQL"""
    print()
    print("Conexión a MySQL:")
    print("-" * 70)
    
    try:
        from db import test_connection
        return test_connection()
    except Exception as e:
        print(f"✗ Error al probar conexión: {e}")
        return False


def verificar_docker():
    """Verificar si Docker está corriendo y si el contenedor está activo"""
    import subprocess
    
    print()
    print("Estado de Docker:")
    print("-" * 70)
    
    try:
        # Verificar si Docker está disponible
        result = subprocess.run(
            ['docker', 'compose', 'ps'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            if 'zoec_mysql' in result.stdout and 'Up' in result.stdout:
                print("  ✓ Contenedor MySQL está corriendo")
                return True
            else:
                print("  ✗ Contenedor MySQL no está corriendo")
                print()
                print("  Para iniciar MySQL:")
                print("    docker compose up -d")
                return False
        else:
            print("  ○ Docker Compose no disponible o no hay contenedores")
            return None
    except FileNotFoundError:
        print("  ○ Docker no está instalado o no está en el PATH")
        return None
    except subprocess.TimeoutExpired:
        print("  ✗ Timeout al verificar Docker")
        return None
    except Exception as e:
        print(f"  ○ No se pudo verificar Docker: {e}")
        return None


def main():
    """Función principal"""
    
    # Verificar archivo .env
    if not verificar_archivo_env():
        print()
        print("=" * 70)
        print("Configuración INCOMPLETA - Configure el archivo .env primero")
        print("=" * 70)
        return 1
    
    # Verificar variables de entorno
    if not verificar_variables_entorno():
        print()
        print("=" * 70)
        print("Configuración INCOMPLETA - Faltan variables de entorno")
        print("=" * 70)
        return 1
    
    # Verificar Docker (opcional)
    verificar_docker()
    
    # Verificar conexión a MySQL
    if verificar_conexion():
        print()
        print("=" * 70)
        print("✓ Configuración COMPLETA - Todo está listo")
        print("=" * 70)
        return 0
    else:
        print()
        print("=" * 70)
        print("Configuración INCOMPLETA - No se pudo conectar a MySQL")
        print("=" * 70)
        print()
        print("Posibles soluciones:")
        print("  1. Verifique que MySQL esté corriendo:")
        print("     docker compose up -d")
        print("  2. Verifique las credenciales en .env")
        print("  3. Verifique que el puerto 3306 no esté en uso")
        print("  4. Verifique los logs:")
        print("     docker compose logs mysql")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
