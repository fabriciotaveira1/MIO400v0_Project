# app/api/routes_health.py

from fastapi import APIRouter
from app.services.state_instance import state_manager

router = APIRouter()

@router.get("/device/health")
def device_health():

    return {
        "online": state_manager.is_online(),
        "last_update": state_manager.get_full_state()["last_update"]
    }