import socket
import struct
from typing import Any, Dict, List

from app.core.opcodes.host_control import (
    build_host_enable_command,
    build_host_read_request,
    build_hosts_enable_read_request,
)
from app.core.opcodes.input_enable import (
    build_input_enable_command,
    build_inputs_enable_read_request,
)


def _enabled_channels_from_mask(mask: int, size: int = 32) -> List[int]:
    return [i + 1 for i in range(size) if mask & (1 << i)]


def read_host_configuration(client, address: int) -> Dict[str, Any]:
    response = client.send(opcode=14, application_data=build_host_read_request(address))
    status = response.get("status")

    if status == "data_raw":
        payload = response.get("payload", b"")
        if not isinstance(payload, bytes) or len(payload) < 54:
            raise RuntimeError(f"Invalid host config payload size: {len(payload) if isinstance(payload, bytes) else 'n/a'}")

        host_address = struct.unpack(">I", payload[0:4])[0]
        enabled = payload[4]
        host_id = struct.unpack(">I", payload[5:9])[0]
        protocol = payload[9]
        addressing_type = payload[10]
        address_field = payload[11:51]
        source_port = struct.unpack(">H", payload[51:53])[0]
        hw_port = payload[53]

        decoded_address: Any = address_field.hex()
        if addressing_type in {1, 4} and len(address_field) >= 4:
            value = struct.unpack(">I", address_field[:4])[0]
            if addressing_type == 1:
                decoded_address = socket.inet_ntoa(struct.pack(">I", value))
            else:
                decoded_address = value
        elif addressing_type in {2, 3}:
            decoded_address = address_field.split(b"\x00", 1)[0].decode("ascii", errors="ignore")

        return {
            "address": host_address,
            "enabled": bool(enabled),
            "host_id": host_id,
            "ip_protocol": protocol,
            "addressing_type": addressing_type,
            "address_value": decoded_address,
            "source_port": source_port,
            "hw_port": hw_port,
        }

    raise RuntimeError(f"Failed to read host config (opcode 14): {response}")


def set_host_enabled(client, address: int, enabled: int) -> Dict[str, Any]:
    response = client.send(opcode=26, application_data=build_host_enable_command(address, enabled))
    if response.get("status") != "ack":
        raise RuntimeError(f"Failed to set host enabled (opcode 26): {response}")
    return {"address": int(address), "enabled": bool(enabled)}


def read_hosts_enabled_mask(client) -> Dict[str, Any]:
    response = client.send(opcode=27, application_data=build_hosts_enable_read_request())
    if response.get("status") != "data":
        raise RuntimeError(f"Failed to read hosts enabled mask (opcode 27): {response}")
    mask = int(response.get("value", 0))
    return {"enabled_mask": mask, "enabled_hosts": _enabled_channels_from_mask(mask, size=32)}


def set_input_enabled(client, address: int, enabled: int) -> Dict[str, Any]:
    response = client.send(opcode=28, application_data=build_input_enable_command(address, enabled))
    if response.get("status") != "ack":
        raise RuntimeError(f"Failed to set input enabled (opcode 28): {response}")
    return {"address": int(address), "enabled": bool(enabled)}


def read_inputs_enabled_mask(client) -> Dict[str, Any]:
    response = client.send(opcode=29, application_data=build_inputs_enable_read_request())
    if response.get("status") != "data":
        raise RuntimeError(f"Failed to read inputs enabled mask (opcode 29): {response}")
    mask = int(response.get("value", 0))
    return {"enabled_mask": mask, "enabled_inputs": _enabled_channels_from_mask(mask, size=32)}
