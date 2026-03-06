import struct
from typing import Any, Dict


MODEL_MAP = {
    (4, 4): "MIO400",
    (4, 2): "MIO402",
    (8, 8): "MIO800",
    (8, 16): "MIO0816",
    (24, 8): "MIO2408",
}


def detect_inputs(client) -> int:
    valid = []
    had_comm = False
    for i in range(1, 33):
        data = struct.pack(">I", i)
        response = client.send(opcode=5, application_data=data)
        status = response.get("status")

        if status in {"data", "data_raw", "ack"}:
            had_comm = True
            valid.append(i)
            continue

        if status == "nack":
            had_comm = True
            break

        if status in {"error", "timeout"}:
            if not had_comm:
                raise RuntimeError("Unable to communicate with device (inputs detection)")
            break

        break

    if not had_comm:
        raise RuntimeError("Unable to detect device inputs")
    return len(valid)


def detect_outputs(client) -> int:
    valid = []
    had_comm = False
    for i in range(1, 33):
        data = struct.pack(">I", i)
        response = client.send(opcode=16, application_data=data)
        status = response.get("status")

        if status in {"data", "data_raw", "ack"}:
            had_comm = True
            valid.append(i)
            continue

        if status == "nack":
            had_comm = True
            break

        if status in {"error", "timeout"}:
            if not had_comm:
                raise RuntimeError("Unable to communicate with device (outputs detection)")
            break

        break

    if not had_comm:
        raise RuntimeError("Unable to detect device outputs")
    return len(valid)


def _decode_firmware(response: Dict[str, Any]) -> str:
    status = response.get("status")

    if status == "data_raw":
        payload = response.get("payload", b"")
        if isinstance(payload, bytes) and payload:
            ascii_text = payload.decode("ascii", errors="ignore").strip("\x00 \t\r\n")
            if ascii_text:
                return ascii_text
            return payload.hex()

    if status == "data":
        value = response.get("value")
        if isinstance(value, int):
            major = (value >> 16) & 0xFFFF
            minor = value & 0xFFFF
            if major == 0 and minor > 0:
                major = minor // 100
                minor = minor % 100
            return f"{major}.{minor:02d}"

    return "unknown"


def detect_capabilities(client) -> Dict[str, Any]:
    inputs = detect_inputs(client)
    outputs = detect_outputs(client)

    firmware_response = client.send(opcode=42, application_data=b"")
    if firmware_response.get("status") in {"error", "timeout"}:
        raise RuntimeError("Unable to read device firmware")
    firmware = _decode_firmware(firmware_response)

    model = MODEL_MAP.get((inputs, outputs), "MIO")
    return {
        "model": model,
        "inputs": inputs,
        "outputs": outputs,
        "firmware": firmware,
    }
