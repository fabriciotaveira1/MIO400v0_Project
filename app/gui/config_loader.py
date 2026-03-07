import json
from pathlib import Path
from typing import Any, Dict


_DEFAULT_CONFIG: Dict[str, Dict[str, Any]] = {
    "api": {
        "ip": "127.0.0.1",
        "port": 8000,
    },
    "device": {
        "ip": "192.168.1.100",
        "port": 5000,
    },
}


def _config_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config.json"


def _merge_with_defaults(raw: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    merged = {
        "api": dict(_DEFAULT_CONFIG["api"]),
        "device": dict(_DEFAULT_CONFIG["device"]),
    }
    if isinstance(raw.get("api"), dict):
        merged["api"].update(raw["api"])
    if isinstance(raw.get("device"), dict):
        merged["device"].update(raw["device"])

    try:
        merged["api"]["port"] = int(merged["api"].get("port", _DEFAULT_CONFIG["api"]["port"]))
    except (TypeError, ValueError):
        merged["api"]["port"] = _DEFAULT_CONFIG["api"]["port"]
    try:
        merged["device"]["port"] = int(
            merged["device"].get("port", _DEFAULT_CONFIG["device"]["port"])
        )
    except (TypeError, ValueError):
        merged["device"]["port"] = _DEFAULT_CONFIG["device"]["port"]

    merged["api"]["ip"] = str(merged["api"].get("ip", _DEFAULT_CONFIG["api"]["ip"])).strip() or _DEFAULT_CONFIG["api"]["ip"]
    merged["device"]["ip"] = (
        str(merged["device"].get("ip", _DEFAULT_CONFIG["device"]["ip"])).strip()
        or _DEFAULT_CONFIG["device"]["ip"]
    )
    return merged


def load_config() -> Dict[str, Dict[str, Any]]:
    path = _config_path()
    if not path.exists():
        save_config(_DEFAULT_CONFIG)
        return _merge_with_defaults({})

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        save_config(_DEFAULT_CONFIG)
        return _merge_with_defaults({})

    config = _merge_with_defaults(raw if isinstance(raw, dict) else {})
    save_config(config)
    return config


def save_config(config: Dict[str, Dict[str, Any]]) -> None:
    path = _config_path()
    normalized = _merge_with_defaults(config if isinstance(config, dict) else {})
    path.write_text(json.dumps(normalized, indent=4, ensure_ascii=False), encoding="utf-8")
