# api/routes_events.py
from fastapi import APIRouter, HTTPException
from app.core.commbox_client import CommboxClient
from app.core.opcodes.host import build_host_configuration
from app.core.opcodes.input_config import build_input_configuration

router = APIRouter()
client = CommboxClient(ip="192.168.26.228", port=5000)


@router.post("/configure/host")
def configure_host():

    try:
        app_data = build_host_configuration(
            host_address=1,
            enabled=1,
            host_id=1,
            protocol=6,              # TCP
            server_ip="192.168.26.224",  # 🔥 ALTERE para o IP do seu servidor
            server_port=4090,
            hw_port=1
        )

        response = client.send(opcode=13, application_data=app_data)

        if response["status"] == "ack":
            return {"status": "Host configurado com sucesso"}

        raise HTTPException(status_code=400, detail=response)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/configure/inputs")
def configure_inputs():

    try:
        for i in range(1, 33):  # 32 entradas

            app_data = build_input_configuration(
                address=i,
                host_report_mode=0b00000111,
                host_report_mask=0x00000001
            )

            response = client.send(opcode=4, application_data=app_data)

            if response["status"] != "ack":
                return {"error_on_input": i, "response": response}

        return {"status": "Todos inputs configurados para reportar eventos"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))