from __future__ import annotations

import json
import os
import sys # Needed for platform check
from typing import Any, Dict, Optional
from PyQt6.QtCore import QStandardPaths


CONFIG_BASENAME = "licitaciones_config.json"


def _config_dir() -> str:
    """Gets the standard application configuration directory."""
    # Carpeta estándar para config de la app (por usuario/sistema)
    cfg_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation)
    # Fallback if standard location fails
    if not cfg_dir:
        cfg_dir = os.path.join(os.path.expanduser("~"), ".zoeccivil", "licitaciones")
    os.makedirs(cfg_dir, exist_ok=True)
    return cfg_dir


def config_path() -> str:
    """Returns the full path to the configuration JSON file."""
    return os.path.join(_config_dir(), CONFIG_BASENAME)


def load_config() -> Dict[str, Any]:
    """Loads the configuration from the JSON file."""
    path = config_path()
    if not os.path.exists(path):
        return {} # Return empty dict if file doesn't exist
    try:
        with open(path, "r", encoding="utf-8") as f:
            config_data = json.load(f)
            # Ensure it returns a dictionary
            return config_data if isinstance(config_data, dict) else {}
    except (json.JSONDecodeError, OSError) as e:
        print(f"Error loading config file '{path}': {e}")
        return {} # Return empty dict on error


def save_config(data: Dict[str, Any]) -> None:
    """Saves the configuration dictionary to the JSON file."""
    path = config_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except OSError as e:
        print(f"Error saving config file '{path}': {e}")
    except Exception as e_gen:
        print(f"Unexpected error saving config: {e_gen}")


def get_db_path_from_config() -> Optional[str]:
    """Retrieves the last used database path from the config."""
    cfg = load_config()
    p = cfg.get("db_path")
    # Check if it's a non-empty string
    if isinstance(p, str) and p.strip():
        return p
    return None


def set_db_path_in_config(db_path: str) -> None:
    """Saves the given database path to the config file."""
    cfg = load_config()
    cfg["db_path"] = db_path
    save_config(cfg)


def default_db_path() -> str:
    """Returns the default path for a new database file within the config dir."""
    # Ruta por defecto para crear una DB si no existe config
    cfg_dir = _config_dir()
    return os.path.join(cfg_dir, "licitaciones.db")


# --- NEW FUNCTION TO FIND DROPBOX PATH ---
def obtener_ruta_dropbox() -> Optional[str]:
    """
    Attempts to find the user's local Dropbox folder path.

    Checks standard locations and environment variables.
    Returns the path as a string if found, otherwise None.
    """
    home = os.path.expanduser("~")
    dropbox_path = None

    # 1. Check common environment variable (less common but worth checking)
    env_path = os.environ.get("DROPBOX_HOME")
    if env_path and os.path.isdir(env_path):
        print(f"Dropbox path found via environment variable: {env_path}")
        return env_path

    # 2. Check Dropbox's own configuration files
    json_path = None
    if sys.platform == "win32":
        # Windows: Check %APPDATA% and %LOCALAPPDATA%
        for appdata_var in ("APPDATA", "LOCALAPPDATA"):
            appdata = os.environ.get(appdata_var)
            if appdata:
                potential_path = os.path.join(appdata, "Dropbox", "info.json")
                if os.path.exists(potential_path):
                    json_path = potential_path
                    break
    elif sys.platform in ("linux", "darwin"): # Linux or macOS
        potential_path = os.path.join(home, ".dropbox", "info.json")
        if os.path.exists(potential_path):
            json_path = potential_path

    if json_path:
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Dropbox usually stores the path under 'personal' or 'business' key
                for key in data: # Look for 'personal' or 'business' keys
                    path_in_json = data[key].get("path")
                    if path_in_json and os.path.isdir(path_in_json):
                        print(f"Dropbox path found via info.json ({key}): {path_in_json}")
                        return path_in_json
        except (IOError, json.JSONDecodeError, KeyError) as e:
            print(f"Could not read or parse Dropbox info.json ('{json_path}'): {e}")

    # 3. Check default location in Home directory
    default_home_path = os.path.join(home, "Dropbox")
    if os.path.isdir(default_home_path):
        print(f"Dropbox path found in default home location: {default_home_path}")
        return default_home_path

    # 4. If none of the above worked
    print("Warning: Could not automatically detect Dropbox folder path.")
    return None

# --- END NEW FUNCTION ---