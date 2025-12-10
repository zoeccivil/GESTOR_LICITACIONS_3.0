from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List

APP_NAME = "Licitaciones"
FILENAME_CANDIDATES = ("licitaciones_config.json", "licitaciones_config")

DEFAULT_CONFIG: Dict[str, Any] = {
    "db_path": "",
    "last_backup_dir": "",
    "theme": "light",
    "windows": {
        "MainWindow": {"x": 0, "y": 0, "w": 0, "h": 0, "maximized": False},
        "ReportWindow": {
            "x": 0, "y": 0, "w": 0, "h": 0, "maximized": False,
            "splitters": {"split_mid": []},
            "tabs": {"main": 0}
        },
        "DashboardGlobal": {
            "splitters": {"split_v": [], "split_h": [], "split_fallas": []},
            "tabs": {"main": 0}
        }
    },
}

def _config_dir() -> Path:
    return Path.home() / f".{APP_NAME.lower()}"

def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def get_config_path() -> Path:
    cfg_dir = _config_dir()
    _ensure_dir(cfg_dir)
    for cand in FILENAME_CANDIDATES:
        p = cfg_dir / cand
        if p.exists():
            return p
    return cfg_dir / FILENAME_CANDIDATES[0]

def _deepcopy_default() -> Dict[str, Any]:
    # simple deepcopy for dict of primitives
    return json.loads(json.dumps(DEFAULT_CONFIG))

def load_config() -> Dict[str, Any]:
    path = get_config_path()
    if not path.exists():
        return _deepcopy_default()
    try:
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            return _deepcopy_default()
        data = json.loads(text)
        if not isinstance(data, dict):
            return _deepcopy_default()
        merged = _deepcopy_default()
        # shallow merge over defaults; nested dicts updated
        for k, v in data.items():
            if isinstance(v, dict) and isinstance(merged.get(k), dict):
                merged[k].update(v)
            else:
                merged[k] = v
        return merged
    except Exception:
        return _deepcopy_default()

def save_config(cfg: Dict[str, Any]) -> None:
    path = get_config_path()
    _ensure_dir(path.parent)
    base = _deepcopy_default()
    for k, v in (cfg or {}).items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            base[k].update(v)
        else:
            base[k] = v
    path.write_text(json.dumps(base, ensure_ascii=False, indent=2), encoding="utf-8")

def get_value(key: str, default: Any = None) -> Any:
    return load_config().get(key, default)

def set_value(key: str, value: Any) -> None:
    cfg = load_config()
    cfg[key] = value
    save_config(cfg)

# ----- Estados de ventanas -----
def get_window_state(name: str) -> Dict[str, Any]:
    cfg = load_config()
    wins = cfg.get("windows") or {}
    st = wins.get(name) or {}
    return {
        "x": int(st.get("x") or 0),
        "y": int(st.get("y") or 0),
        "w": int(st.get("w") or 0),
        "h": int(st.get("h") or 0),
        "maximized": bool(st.get("maximized") or False),
    }

def set_window_state(name: str, x: int, y: int, w: int, h: int, maximized: bool) -> None:
    cfg = load_config()
    cfg.setdefault("windows", {})
    cfg["windows"].setdefault(name, {})
    cfg["windows"][name].update({"x": int(x), "y": int(y), "w": int(w), "h": int(h), "maximized": bool(maximized)})
    save_config(cfg)

# ----- Splitters (listas de tamaños en píxeles) -----
def get_splitter_sizes(win_name: str, splitter_key: str) -> List[int]:
    cfg = load_config()
    return list(((cfg.get("windows") or {}).get(win_name, {}).get("splitters") or {}).get(splitter_key, []) or [])

def set_splitter_sizes(win_name: str, splitter_key: str, sizes: List[int]) -> None:
    cfg = load_config()
    cfg.setdefault("windows", {})
    win = cfg["windows"].setdefault(win_name, {})
    win.setdefault("splitters", {})
    win["splitters"][splitter_key] = [int(s) for s in (sizes or [])]
    save_config(cfg)

# ----- Tabs (índices) -----
def get_tab_index(win_name: str, tab_key: str, default: int = 0) -> int:
    cfg = load_config()
    return int(((cfg.get("windows") or {}).get(win_name, {}).get("tabs") or {}).get(tab_key, default) or default)

def set_tab_index(win_name: str, tab_key: str, idx: int) -> None:
    cfg = load_config()
    cfg.setdefault("windows", {})
    win = cfg["windows"].setdefault(win_name, {})
    win.setdefault("tabs", {})
    win["tabs"][tab_key] = int(idx)
    save_config(cfg)