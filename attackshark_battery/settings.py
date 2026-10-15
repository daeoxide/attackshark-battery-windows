"""Caminhos, configuracao (config.json) e estado interno (state.json)."""
import json
import os
import sys

FROZEN = getattr(sys, "frozen", False)   # rodando como .exe (PyInstaller)
SOURCE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# O .exe guarda config e historico no perfil do usuario; rodando do codigo-fonte, na pasta do projeto.
DATA_DIR = (os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "AttackSharkBattery")
            if FROZEN else SOURCE_ROOT)
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
STATE_PATH = os.path.join(DATA_DIR, "state.json")
LOG_PATH = os.path.join(DATA_DIR, "battery_log.csv")
ICON_PATH = os.path.join(DATA_DIR, "icon.png")

DEFAULTS = {
    "language": "",             # "" = perguntar na primeira execucao; "en" ou "pt"
    "warn_percent": 20,
    "critical_percent": 10,
    "repeat_minutes": 10,
    "notify_full": False,       # o % com energia externa e aproximado (docs/PROTOCOL.md)
    "notify_bad_contact": True,
    "sleep_after_seconds": 30,
    "check_updates": True,
}
RANGES = {
    "warn_percent": (1, 99),
    "critical_percent": (0, 99),
    "repeat_minutes": (1, 24 * 60),
    "sleep_after_seconds": (10, 3600),
}


def _validate(key, value):
    """Valor corrigido, ou None se for invalido (usa-se o padrao)."""
    default = DEFAULTS.get(key)
    if key == "language":
        return value if value in ("", "en", "pt") else None
    if isinstance(default, bool):
        return value if isinstance(value, bool) else None
    if key in RANGES:
        try:
            value = int(value)
        except (TypeError, ValueError):
            return None
        lo, hi = RANGES[key]
        return min(max(value, lo), hi)
    return value   # chave desconhecida: preservada


def _read_json(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def _write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def load_config():
    """Config valida. Chaves novas sao acrescentadas ao arquivo; um arquivo com erro de
    sintaxe nao e sobrescrito (usa os padroes ate o usuario corrigir)."""
    cfg = dict(DEFAULTS)
    try:
        raw = _read_json(CONFIG_PATH)
    except FileNotFoundError:
        raw = {}
    except (OSError, ValueError):
        return cfg
    for key, value in raw.items():
        value = _validate(key, value)
        if value is not None:
            cfg[key] = value
    if cfg["critical_percent"] >= cfg["warn_percent"]:
        cfg["critical_percent"] = max(cfg["warn_percent"] - 1, 0)
    if set(DEFAULTS) - set(raw):
        try:
            _write_json(CONFIG_PATH, cfg)
        except OSError:
            pass
    return cfg


def save_config(cfg):
    try:
        _write_json(CONFIG_PATH, cfg)
    except OSError:
        pass


def config_mtime():
    try:
        return os.path.getmtime(CONFIG_PATH)
    except OSError:
        return None


def load_state():
    try:
        return _read_json(STATE_PATH)
    except (OSError, ValueError):
        return {}


def save_state(state):
    try:
        _write_json(STATE_PATH, state)
    except OSError:
        pass
