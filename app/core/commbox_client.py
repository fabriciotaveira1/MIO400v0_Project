# core/commbox_client.py

import socket
import struct

from core.frame_builder import FrameBuilder


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

                response = s.recv(4096)

                return self._parse_response(response)

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _parse_response(self, data: bytes) -> dict:

        if not data:
            return {"status": "timeout"}

        # Opcode resposta está na posição 28-32
        response_opcode = struct.unpack(">I", data[28:32])[0]

        if response_opcode & 0x80000000:
            return {"status": "ack", "opcode": response_opcode}

        if response_opcode & 0x40000000:
            return {"status": "nack", "opcode": response_opcode}

        return {"status": "unknown", "raw": data.hex()}