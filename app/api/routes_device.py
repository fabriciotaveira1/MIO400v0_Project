from fastapi import APIRouter, HTTPException

from app.models.schema import DeviceConfig
from app.services.device_capabilities import detect_capabilities
from app.services.device_manager import device_manager

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
