# app/api/routes_outputs.py

from fastapi import APIRouter, HTTPException
from app.core.commbox_client import CommboxClient
from app.core.opcodes.output import build_output_command
from app.models.schema import CommandRequest

router = APIRouter()

client = CommboxClient(ip="192.168.26.228", port=5000)


@router.post("/control/output")
def control_output(cmd: CommandRequest):

    try:
        app_data = build_output_command(
            component_addr=cmd.component_addr,
            action=cmd.action,
            total_time=cmd.total_time,
            memory=cmd.memory
        )

        response = client.send(opcode=1, application_data=app_data)

        if response["status"] == "ack":
            return {"status": "success", "device_response": response}

        if response["status"] == "nack":
            raise HTTPException(status_code=400, detail=response)

        raise HTTPException(status_code=500, detail=response)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))