# app/ui/theme/theme_manager.py
from __future__ import annotations
import importlib
import inspect
import pkgutil
import sys
import os
import importlib.util
from dataclasses import dataclass
from typing import Callable, List, Optional, Dict, Tuple

from PyQt6.QtWidgets import QApplication

# Persistencia en JSON
from app.core.app_settings import get_value, set_value

# Paquetes posibles para temas (soporta 'theme' y 'themes')
POSSIBLE_THEME_PACKAGES = ("app.ui.theme", "app.ui.themes")

# Módulos que no deben considerarse temas
EXCLUDE_MODULES = {
    "theme_manager",  # este archivo
    "__init__",       # init de paquete
}

# Puedes excluir 'auto_theme' si no quieres listarlo
EXCLUDE_OPTIONAL = {
    # "auto_theme",
}


@dataclass
class ThemeInfo:
    id: str                 # id único = nombre de módulo (p.ej. dim_theme)
    title: str              # nombre amigable para menú
    module_name: str        # ruta completa del módulo (app.ui.theme.dim_theme) o file path when frozen
    apply_func_name: str    # nombre de la función a invocar (apply_dim_theme, apply_theme, etc.)


def _humanize(name: str) -> str:
    n = name.replace("_", " ").strip().title()
    for suf in (" Theme", " Dim"):
        n = n.replace(suf, suf.strip())
    return n


def _discover_theme_apply(mod) -> Optional[str]:
    """
    Encuentra el nombre de la función de aplicación del tema en un módulo.
    Prioridad:
      - apply_theme
      - cualquier función que comience con 'apply_' y termine con '_theme'
      - cualquier función que comience con 'apply_'
    """
    fn = getattr(mod, "apply_theme", None)
    if callable(fn):
        return "apply_theme"

    for name, obj in inspect.getmembers(mod, inspect.isfunction):
        if name.startswith("apply_") and name.endswith("_theme"):
            return name

    for name, obj in inspect.getmembers(mod, inspect.isfunction):
        if name.startswith("apply_"):
            return name

    return None


def _load_module_from_path(path: str, module_alias: str):
    """
    Carga un módulo Python desde un archivo .py y lo devuelve.
    Usa importlib.util para evitar colisiones con imports normales.
    """
    try:
        spec = importlib.util.spec_from_file_location(module_alias, path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            # Insert in sys.modules temporarily so imports inside the module work
            sys.modules[module_alias] = mod
            spec.loader.exec_module(mod)  # type: ignore
            return mod
    except Exception:
        # No propagar error; el caller decidirá
        pass
    finally:
        # opcional: dejar module en sys.modules para debugging; no lo removemos para evitar problemas
        pass
    return None


def _collect_theme_info_from_module_object(mod, module_name_hint: str) -> Optional[ThemeInfo]:
    try:
        title = getattr(mod, "THEME_NAME", None)
        if not isinstance(title, str) or not title.strip():
            leaf = module_name_hint.rsplit(".", 1)[-1] if "." in module_name_hint else os.path.splitext(os.path.basename(module_name_hint))[0]
            title = _humanize(leaf)

        apply_name = _discover_theme_apply(mod)
        if not apply_name:
            return None

        theme_id = module_name_hint.rsplit(".", 1)[-1] if "." in module_name_hint else os.path.splitext(os.path.basename(module_name_hint))[0]
        return ThemeInfo(
            id=theme_id,
            title=title,
            module_name=module_name_hint,
            apply_func_name=apply_name,
        )
    except Exception:
        return None


def _collect_theme_info(module_name: str) -> Optional[ThemeInfo]:
    """
    Intenta importar un módulo por nombre y extraer ThemeInfo.
    """
    try:
        mod = importlib.import_module(module_name)
    except Exception:
        return None
    return _collect_theme_info_from_module_object(mod, module_name)


def _select_themes_package() -> Tuple[str, object]:
    """
    Devuelve (package_name, package_module) elegido entre POSSIBLE_THEME_PACKAGES.
    Lanza ImportError si ninguno existe.
    """
    last_err: Optional[Exception] = None
    for pkg_name in POSSIBLE_THEME_PACKAGES:
        try:
            pkg = importlib.import_module(pkg_name)
            return pkg_name, pkg
        except Exception as e:
            last_err = e
            continue

    # Fallback para aplicaciones congeladas (PyInstaller): intentar detectar carpeta en sys._MEIPASS
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None) or os.path.dirname(sys.executable)
        for candidate in ("app/ui/theme", "app/ui/themes", "ui/themes", "ui/theme"):
            path = os.path.join(meipass, candidate)
            if os.path.isdir(path):
                # Creamos un "paquete virtual" usando el path como módulo container
                # Devolvemos el paquete name as 'frozen_theme_path' and the path string as second element
                return "frozen_theme_path", path  # caller will handle this special case
    raise ImportError(f"No se pudo importar ninguno de los paquetes de temas: {POSSIBLE_THEME_PACKAGES}. Último error: {last_err}")


def list_themes() -> List[ThemeInfo]:
    """
    Lista todos los temas detectados en app.ui.theme (o app.ui.themes).
    Funciona también cuando la aplicación está congelada (PyInstaller) y los módulos no se pueden importar
    mediante importlib normal. En ese caso escanea archivos .py dentro del bundle.
    """
    themes: List[ThemeInfo] = []

    try:
        pkg_name, pkg = _select_themes_package()
    except Exception:
        return []

    # Caso normal: pkg es un módulo con __path__
    if isinstance(pkg, str):
        # En la rama frozen, pkg contains the directory path
        theme_dir = pkg
        try:
            for fname in sorted(os.listdir(theme_dir)):
                if not fname.endswith(".py"):
                    continue
                name = os.path.splitext(fname)[0]
                if name in EXCLUDE_MODULES or name in EXCLUDE_OPTIONAL:
                    continue
                full_path = os.path.join(theme_dir, fname)
                mod_alias = f"frozen_theme_{name}"
                mod = _load_module_from_path(full_path, mod_alias)
                if not mod:
                    continue
                info = _collect_theme_info_from_module_object(mod, full_path)
                if info:
                    themes.append(info)
        except Exception:
            pass
        themes.sort(key=lambda t: t.title.lower())
        return themes

    # Normal flow: package module object
    pkg_path = pkg.__path__
    for m in pkgutil.iter_modules(pkg_path):
        name = m.name
        if name in EXCLUDE_MODULES or name in EXCLUDE_OPTIONAL:
            continue
        full = f"{pkg_name}.{name}"
        info = _collect_theme_info(full)
        if info:
            themes.append(info)

    themes.sort(key=lambda t: t.title.lower())
    return themes


def _load_module_by_name_or_path(module_name: str, theme_id: str):
    """
    Intenta importar módulo por nombre; si falla, intenta buscar en sys._MEIPASS/app/ui/theme/<theme_id>.py
    y cargar desde archivo.
    Devuelve el módulo objeto o None.
    """
    try:
        return importlib.import_module(module_name)
    except Exception:
        # intentar cargar desde bundle (frozen) path
        if getattr(sys, "frozen", False):
            meipass = getattr(sys, "_MEIPASS", None) or os.path.dirname(sys.executable)
            candidate_paths = [
                os.path.join(meipass, "app", "ui", "theme", f"{theme_id}.py"),
                os.path.join(meipass, "app", "ui", "themes", f"{theme_id}.py"),
                os.path.join(meipass, "ui", "theme", f"{theme_id}.py"),
                os.path.join(meipass, f"{theme_id}.py"),
            ]
            for p in candidate_paths:
                if os.path.isfile(p):
                    mod_alias = f"frozen_theme_mod_{theme_id}"
                    mod = _load_module_from_path(p, mod_alias)
                    if mod:
                        return mod
    return None


def apply_theme_by_id(app: QApplication, theme_id: str) -> bool:
    """
    Aplica un tema por id (nombre de archivo sin .py).
    Prueba ambos prefijos de paquete ('app.ui.theme' y 'app.ui.themes').
    Soporta también cargar módulos desde el bundle cuando la app está congelada.
    """
    for pkg_name in POSSIBLE_THEME_PACKAGES:
        module_name = f"{pkg_name}.{theme_id}"
        mod = _load_module_by_name_or_path(module_name, theme_id)
        if not mod:
            continue
        fn_name = _discover_theme_apply(mod)
        if not fn_name:
            continue
        try:
            fn: Callable = getattr(mod, fn_name)
            fn(app)
            return True
        except Exception:
            # no abortar, intentar siguiente
            continue

    # último recurso: si estamos en frozen, intentar cargar con rutas absolutas
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None) or os.path.dirname(sys.executable)
        p = os.path.join(meipass, "app", "ui", "theme", f"{theme_id}.py")
        if os.path.isfile(p):
            mod = _load_module_from_path(p, f"frozen_theme_final_{theme_id}")
            if mod:
                fn_name = _discover_theme_apply(mod)
                if fn_name and hasattr(mod, fn_name):
                    try:
                        getattr(mod, fn_name)(app)
                        return True
                    except Exception:
                        pass
    return False


def current_theme_id(default: str = "dim_theme") -> str:
    val = get_value("ui_theme", "").strip()
    return val or default


def apply_theme_from_settings(app: QApplication, fallback: str = "dim_theme") -> str:
    """
    Lee el tema desde licitaciones_config (ui_theme) y lo aplica.
    Si falla, intenta el fallback. Devuelve el id aplicado (o el que quedó seleccionado).
    """
    tid = current_theme_id(default=fallback)
    ok = apply_theme_by_id(app, tid)
    if not ok:
        if tid != fallback and apply_theme_by_id(app, fallback):
            save_theme_selection(fallback)
            return fallback
        # Intento final: light_theme
        if apply_theme_by_id(app, "light_theme"):
            save_theme_selection("light_theme")
            return "light_theme"
    return tid


def save_theme_selection(theme_id: str) -> None:
    set_value("ui_theme", theme_id)


def theme_accent_hex(app: QApplication) -> str:
    """Color de acento actual desde la paleta (highlight)."""
    return app.palette().highlight().color().name()