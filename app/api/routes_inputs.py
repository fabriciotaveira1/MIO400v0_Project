# app/api/routes_inputs.py

from fastapi import APIRouter, HTTPException
from app.core.commbox_client import CommboxClient
from app.services.state_instance import state_manager

router = APIRouter()
client = CommboxClient(ip="192.168.26.228", port=5000)


@router.get("/inputs/status")
def read_inputs():

    response = client.send(opcode=6, application_data=b'')

    if response["status"] == "data":

        mask = response["value"]

        inputs = {
            i + 1: bool(mask & (1 << i))
            for i in range(32)
        }

        return {
            "raw_mask": mask,
            "inputs": inputs
        }

    raise HTTPException(status_code=400, detail=response)

@router.get("/io/status")
def read_io_combined():

    response = client.send(opcode=3, application_data=b'')

    if response["status"] == "data_combined":

        input_mask = response["inputs"]
        output_mask = response["outputs"]

        state_manager.update_both(input_mask, output_mask)

        return state_manager.get_full_state()

    raise HTTPException(status_code=400, detail=response)
    