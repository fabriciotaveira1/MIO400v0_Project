from fastapi import APIRouter, HTTPException

from app.core.opcodes.output import build_output_command
from app.models.schema import CommandRequest
from app.services.device_manager import device_manager
from app.services.state_instance import state_manager

router = APIRouter()


def _get_client():
    try:
        return device_manager.get_client()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/control/output")
def control_output(cmd: CommandRequest):
    client = _get_client()
    app_data = build_output_command(
        component_addr=cmd.component_addr,
        action=cmd.action,
        total_time=cmd.total_time,
        memory=cmd.memory,
    )
    response = client.send(opcode=1, application_data=app_data)

    if response["status"] == "ack":
        return {"status": "success"}

    raise HTTPException(status_code=400, detail=response)


@router.get("/outputs/status")
def read_outputs():
    client = _get_client()
    response = client.send(opcode=2, application_data=b"")

    if response["status"] == "data":
        mask = response["value"]
        state_manager.update_outputs(mask)
        return state_manager.get_full_state()

    raise HTTPException(status_code=400, detail=response)
