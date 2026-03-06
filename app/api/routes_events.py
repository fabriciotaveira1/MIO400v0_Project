from fastapi import APIRouter, HTTPException

from app.core.opcodes.host import build_host_configuration
from app.core.opcodes.input_config import build_input_configuration
from app.services.device_manager import device_manager

router = APIRouter()


def _get_client():
    try:
        return device_manager.get_client()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/configure/host")
def configure_host():
    try:
        client = _get_client()
        app_data = build_host_configuration(
            host_address=1,
            enabled=1,
            host_id=1,
            protocol=6,
            server_ip="192.168.26.224",
            server_port=4090,
            hw_port=1,
        )

        response = client.send(opcode=13, application_data=app_data)

        if response["status"] == "ack":
            return {"status": "Host configurado com sucesso"}

        raise HTTPException(status_code=400, detail=response)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/configure/inputs")
def configure_inputs():
    try:
        client = _get_client()
        valid_inputs = []
        for i in range(1, 33):
            app_data = build_input_configuration(
                address=i,
                host_report_mode=0b00000111,
                host_report_mask=0x00000001,
            )

            response = client.send(opcode=4, application_data=app_data)

            if response["status"] == "ack":
                valid_inputs.append(i)
            else:
                break

        return {
            "status": "Configuracao concluida",
            "max_inputs_detected": len(valid_inputs),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
