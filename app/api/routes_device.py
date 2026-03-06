from fastapi import APIRouter

from app.models.schema import DeviceConfig
from app.services.device_manager import device_manager

router = APIRouter()


@router.post("/device/configure")
def configure_device(config: DeviceConfig):
    device_manager.configure(config.device_ip, config.device_port)
    return {"status": "device configured"}
