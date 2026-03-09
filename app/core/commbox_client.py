# core/commbox_client.py

import socket
import struct

from app.core.frame_builder import FrameBuilder


class CommboxClient:

    def __init__(self, ip: str, port: int = 5000):
        self.ip = ip
        self.port = port
        self.frame_builder = FrameBuilder()

    def send(self, opcode: int, application_data: bytes) -> dict:

        frame = self.frame_builder.build_frame(opcode, application_data)

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(3)
                s.connect((self.ip, self.port))
                s.sendall(frame)

                full_response = b''

                while True:
                    chunk = s.recv(4096)
                    if not chunk:
                        break

                    full_response += chunk

                    # se já temos pelo menos header completo
                    if len(full_response) >= 32:
                        break

                return self._parse_response(full_response)

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _parse_response(self, data: bytes) -> dict:

        if not data:
            return {"status": "timeout"}

        data_size = struct.unpack(">I", data[8:12])[0]
        opcode = struct.unpack(">I", data[28:32])[0]
        payload = data[32:32 + data_size]

        # Se tem payload
        if data_size > 0:

            clean_opcode = opcode & 0x7FFFFFFF

            if opcode & 0x40000000:
                if len(payload) >= 8:
                    error_code = struct.unpack(">I", payload[0:4])[0]
                    error_data = struct.unpack(">I", payload[4:8])[0]
                    return {
                        "status": "nack",
                        "opcode": opcode,
                        "error_code": error_code,
                        "error_data": error_data
                    }
                return {"status": "nack", "opcode": opcode}

            # Caso 4 bytes (Opcode 02 ou 06)
            if data_size == 4:
                value = struct.unpack(">I", payload)[0]

                return {
                    "status": "data",
                    "opcode": clean_opcode,
                    "value": value,
                    "payload": payload
                }

            # Caso 8 bytes de leitura combinada de entradas/saidas (Opcode 03)
            if data_size == 8 and clean_opcode == 3:
                input_mask = struct.unpack(">I", payload[0:4])[0]
                output_mask = struct.unpack(">I", payload[4:8])[0]

                return {
                    "status": "data_combined",
                    "opcode": clean_opcode,
                    "inputs": input_mask,
                    "outputs": output_mask,
                    "payload": payload
                }
            return {
                "status": "data_raw",
                "opcode": clean_opcode,
                "payload": payload
            }

        # ACK puro
        if opcode & 0x80000000:
            return {"status": "ack", "opcode": opcode}

        # NACK
        if opcode & 0x40000000:
            return {"status": "nack", "opcode": opcode}

        return {"status": "unknown", "raw": data.hex()}
