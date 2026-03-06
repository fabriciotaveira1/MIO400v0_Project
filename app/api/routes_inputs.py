from fastapi import APIRouter, HTTPException

from app.services.device_manager import device_manager
from app.services.state_instance import state_manager

router = APIRouter()


def _get_client():
    try:
        return device_manager.get_client()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/inputs/status")
def read_inputs():
    client = _get_client()
    response = client.send(opcode=6, application_data=b"")

    if response["status"] == "data":
        mask = response["value"]
        inputs = {i + 1: bool(mask & (1 << i)) for i in range(32)}
        return {"raw_mask": mask, "inputs": inputs}

    raise HTTPException(status_code=400, detail=response)


@router.get("/io/status")
def read_io_combined():
    client = _get_client()
    response = client.send(opcode=3, application_data=b"")

    if response["status"] == "data_combined":
        input_mask = response["inputs"]
        output_mask = response["outputs"]
        state_manager.update_both(input_mask, output_mask)
        return state_manager.get_full_state()

    raise HTTPException(status_code=400, detail=response)
