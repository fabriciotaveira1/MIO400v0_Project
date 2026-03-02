# app/api/routes_heartbeaht.py
from fastapi import APIRouter, HTTPException
from app.core.commbox_client import CommboxClient
from app.core.opcodes.heartbeat_tcp import build_heartbeat_tcp_configuration

router = APIRouter()
client = CommboxClient(ip="192.168.26.228", port=5000)

@router.post("/configure/heartbeat_tcp")
def configure_heartbeat():

    try:
        app_data = build_heartbeat_tcp_configuration(
            data_code=4,     # inputs + outputs
            interval_ms=3000
        )

        response = client.send(opcode=90, application_data=app_data)

        if response["status"] == "ack":
            return {"status": "Heartbeat TCP configurado com sucesso"}

        raise HTTPException(status_code=400, detail=response)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))