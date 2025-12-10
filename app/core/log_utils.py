import logging
import os
from datetime import datetime

_LOGGER = None

def get_logger(name: str = "licitaciones") -> logging.Logger:
    global _LOGGER
    if _LOGGER is not None:
        return _LOGGER

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Crear carpeta logs si no existe
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    logs_dir = os.path.join(base_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    # Nombre de archivo con fecha
    fname = datetime.now().strftime("app_%Y%m%d.log")
    log_path = os.path.join(logs_dir, fname)

    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh.setFormatter(formatter)

    logger.addHandler(fh)
    logger.propagate = False

    _LOGGER = logger
    return logger