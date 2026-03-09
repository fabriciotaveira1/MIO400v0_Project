import json
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_API_PORT = 8000
DEFAULT_DEVICE_PORT = 5000
DEFAULT_SERVER_IP = "127.0.0.1"
DEFAULT_DEVICE_IP = "192.168.1.100"

ConfigDict = Dict[str, Any]
DeviceDict = Dict[str, Any]


def _config_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config.json"


def _default_config() -> ConfigDict:
    return {"devices": [], "last_device": ""}


def _normalize_device(raw: Dict[str, Any], fallback_name: str) -> DeviceDict:
    name = str(raw.get("name", fallback_name)).strip() or fallback_name
    server_ip = str(raw.get("server_ip", DEFAULT_SERVER_IP)).strip() or DEFAULT_SERVER_IP
    device_ip = str(raw.get("device_ip", DEFAULT_DEVICE_IP)).strip() or DEFAULT_DEVICE_IP

    try:
        api_port = int(raw.get("api_port", DEFAULT_API_PORT))
    except (TypeError, ValueError):
        api_port = DEFAULT_API_PORT

    try:
        port = int(raw.get("port", DEFAULT_DEVICE_PORT))
    except (TypeError, ValueError):
        port = DEFAULT_DEVICE_PORT

    return {
        "name": name,
        "server_ip": server_ip,
        "device_ip": device_ip,
        "port": port,
        "api_port": api_port,
    }


def _from_legacy(raw: Dict[str, Any]) -> Optional[ConfigDict]:
    if not isinstance(raw.get("api"), dict) or not isinstance(raw.get("device"), dict):
        return None

    legacy = {
        "name": "Dispositivo 1",
        "server_ip": raw["api"].get("ip", DEFAULT_SERVER_IP),
        "device_ip": raw["device"].get("ip", DEFAULT_DEVICE_IP),
        "port": raw["device"].get("port", DEFAULT_DEVICE_PORT),
        "api_port": raw["api"].get("port", DEFAULT_API_PORT),
    }
    device = _normalize_device(legacy, "Dispositivo 1")
    return {"devices": [device], "last_device": device["name"]}


def _normalize_config(raw: Any) -> ConfigDict:
    if not isinstance(raw, dict):
        return _default_config()

    migrated = _from_legacy(raw)
    if migrated is not None:
        return migrated

    normalized: ConfigDict = _default_config()
    devices_raw = raw.get("devices")
    if isinstance(devices_raw, list):
        seen = set()
        devices: List[DeviceDict] = []
        for idx, entry in enumerate(devices_raw, start=1):
            if not isinstance(entry, dict):
                continue
            device = _normalize_device(entry, f"Dispositivo {idx}")
            if device["name"] in seen:
                continue
            seen.add(device["name"])
            devices.append(device)
        normalized["devices"] = devices

    last_name = str(raw.get("last_device", "")).strip()
    names = {str(d.get("name", "")) for d in normalized["devices"]}
    if last_name and last_name in names:
        normalized["last_device"] = last_name
    elif normalized["devices"]:
        normalized["last_device"] = str(normalized["devices"][0]["name"])
    return normalized


def load_config() -> ConfigDict:
    path = _config_path()
    if not path.exists():
        config = _default_config()
        save_config(config)
        return config

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        config = _default_config()
        save_config(config)
        return config

    normalized = _normalize_config(raw)
    save_config(normalized)
    return normalized


def save_config(config: ConfigDict) -> None:
    path = _config_path()
    normalized = _normalize_config(config)
    path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")


def get_devices(config: ConfigDict) -> List[DeviceDict]:
    return list(config.get("devices", [])) if isinstance(config, dict) else []


def get_last_device(config: ConfigDict) -> Optional[DeviceDict]:
    devices = get_devices(config)
    if not devices:
        return None
    last_name = str(config.get("last_device", "")).strip() if isinstance(config, dict) else ""
    for device in devices:
        if str(device.get("name", "")) == last_name:
            return dict(device)
    return dict(devices[0])


def upsert_device(config: ConfigDict, device: DeviceDict, make_last: bool = True) -> ConfigDict:
    normalized_config = _normalize_config(config)
    normalized_device = _normalize_device(device, "Dispositivo")

    updated_devices: List[DeviceDict] = []
    replaced = False
    for existing in normalized_config["devices"]:
        if str(existing.get("name", "")) == normalized_device["name"]:
            updated_devices.append(normalized_device)
            replaced = True
        else:
            updated_devices.append(existing)
    if not replaced:
        updated_devices.append(normalized_device)

    normalized_config["devices"] = updated_devices
    if make_last:
        normalized_config["last_device"] = normalized_device["name"]
    return normalized_config


def set_last_device(config: ConfigDict, device_name: str) -> ConfigDict:
    normalized_config = _normalize_config(config)
    name = str(device_name).strip()
    if not name:
        return normalized_config
    if any(str(d.get("name", "")) == name for d in normalized_config["devices"]):
        normalized_config["last_device"] = name
    return normalized_config
