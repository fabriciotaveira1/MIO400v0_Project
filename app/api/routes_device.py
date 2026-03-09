# api/routes_device.py

from fastapi import APIRouter, HTTPException

from app.models.schema import DeviceConfig
from app.services.device_capabilities import detect_capabilities
from app.services.device_manager import device_manager
from app.services.state_instance import state_manager

router = APIRouter()


@router.post("/device/configure")
def configure_device(config: DeviceConfig):
    device_manager.configure(config.device_ip, config.device_port)
    return {"status": "device configured"}


@router.get("/device/capabilities")
def get_device_capabilities():
    try:
        client = device_manager.get_client()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        return detect_capabilities(client)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/device/disconnect")
def disconnect_device():
    device_manager.disconnect()
    state_manager.last_heartbeat = 0.0
    return {"status": "device disconnected"}


@router.post("/device/reconnect")
def reconnect_device():
    try:
        device_manager.reconnect()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "device reconnected"}


@router.get("/device/status")
def get_device_status():
    status = device_manager.get_current_config()
    status["online"] = bool(state_manager.is_online())
    return status
