# api/routes_device.py

from fastapi import APIRouter, HTTPException, Path

from app.models.schema import DeviceConfig, EnableRequest, HeartbeatTcpConfigRequest
from app.services.device_capabilities import detect_capabilities
from app.services.device_manager import device_manager
from app.services.device_opcode_service import (
    read_host_configuration,
    read_hosts_enabled_mask,
    read_inputs_enabled_mask,
    set_host_enabled,
    set_input_enabled,
)
from app.services.heartbeat_service import configure_heartbeat_tcp, read_heartbeat_tcp_config
from app.services.state_instance import state_manager

router = APIRouter()


@router.post("/device/configure")
def configure_device(config: DeviceConfig):
    device_manager.configure(config.device_ip, config.device_port)
    heartbeat_applied = False
    heartbeat_error = None

    try:
        client = device_manager.get_client()
        configure_heartbeat_tcp(client, data_code=4, interval_ms=3000)
        heartbeat_applied = True
    except Exception as exc:
        heartbeat_error = str(exc)

    return {
        "status": "device configured",
        "heartbeat_tcp_applied": heartbeat_applied,
        "heartbeat_tcp_error": heartbeat_error,
    }


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


@router.post("/device/heartbeat-tcp")
def configure_device_heartbeat_tcp(config: HeartbeatTcpConfigRequest):
    try:
        client = device_manager.get_client()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        configured = configure_heartbeat_tcp(
            client,
            data_code=config.data_code,
            interval_ms=config.interval_ms,
        )
        return {"status": "heartbeat tcp configured", **configured}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/device/heartbeat-tcp")
def get_device_heartbeat_tcp():
    try:
        client = device_manager.get_client()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        configured = read_heartbeat_tcp_config(client)
        return {"status": "ok", **configured}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/device/host/{address}")
def get_host_configuration(address: int = Path(..., ge=1, le=32)):
    try:
        client = device_manager.get_client()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        host = read_host_configuration(client, address=address)
        return {"status": "ok", **host}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/device/host/{address}/enabled")
def set_host_enabled_state(
    request: EnableRequest,
    address: int = Path(..., ge=1, le=32),
):
    try:
        client = device_manager.get_client()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        result = set_host_enabled(client, address=address, enabled=int(request.enabled))
        return {"status": "updated", **result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/device/hosts/enabled-mask")
def get_hosts_enabled_mask():
    try:
        client = device_manager.get_client()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        result = read_hosts_enabled_mask(client)
        return {"status": "ok", **result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/device/input/{address}/enabled")
def set_input_enabled_state(
    request: EnableRequest,
    address: int = Path(..., ge=1, le=32),
):
    try:
        client = device_manager.get_client()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        result = set_input_enabled(client, address=address, enabled=int(request.enabled))
        return {"status": "updated", **result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/device/inputs/enabled-mask")
def get_inputs_enabled_mask():
    try:
        client = device_manager.get_client()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        result = read_inputs_enabled_mask(client)
        return {"status": "ok", **result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
