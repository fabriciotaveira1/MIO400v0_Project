import struct
from typing import Any, Dict

from app.core.opcodes.heartbeat_tcp import (
    build_heartbeat_tcp_configuration,
    build_heartbeat_tcp_read_request,
)


def configure_heartbeat_tcp(client, data_code: int = 4, interval_ms: int = 3000) -> Dict[str, Any]:
    payload = build_heartbeat_tcp_configuration(data_code=data_code, interval_ms=interval_ms)
    response = client.send(opcode=90, application_data=payload)
    if response.get("status") != "ack":
        raise RuntimeError(f"Failed to configure heartbeat TCP (opcode 90): {response}")
    return {"data_code": int(data_code), "interval_ms": int(interval_ms)}


def read_heartbeat_tcp_config(client) -> Dict[str, Any]:
    response = client.send(opcode=91, application_data=build_heartbeat_tcp_read_request())
    status = response.get("status")

    if status == "data_raw":
        payload = response.get("payload", b"")
        if isinstance(payload, bytes) and len(payload) >= 8:
            data_code = struct.unpack(">I", payload[0:4])[0]
            interval_ms = struct.unpack(">I", payload[4:8])[0]
            return {"data_code": data_code, "interval_ms": interval_ms}

    if status == "data_combined" and int(response.get("opcode", 0)) == 91:
        # Compatibilidade com parser legado que interpreta payload de 8 bytes como I/O combinado.
        data_code = int(response.get("inputs", 0))
        interval_ms = int(response.get("outputs", 0))
        return {"data_code": data_code, "interval_ms": interval_ms}

    if status == "data":
        # Fallback para formatos reduzidos que retornem apenas um inteiro.
        return {"data_code": int(response.get("value", 0)), "interval_ms": 0}

    raise RuntimeError(f"Failed to read heartbeat TCP config (opcode 91): {response}")
