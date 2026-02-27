# services/socket_listener.py

import socket
import struct
import threading

from app.services.state_instance import state_manager


class SocketListener:

    def __init__(self, host="0.0.0.0", port=4090):
        self.host = host
        self.port = port
        self._running = False

    def start(self):
        self._running = True
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()

    def _run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.bind((self.host, self.port))
            server.listen(5)

            print(f"[SocketListener] Listening on {self.port}")

            while self._running:
                conn, addr = server.accept()
                print(f"[SocketListener] Connection from {addr}")

                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(conn,),
                    daemon=True
                )
                client_thread.start()

    def _handle_client(self, conn):
        with conn:
            data = conn.recv(4096)

            if not data:
                return

            self._process_frame(data)

    def _process_frame(self, data: bytes):

        if len(data) < 32:
            return

        opcode = struct.unpack(">I", data[28:32])[0]

        # Remove bit 31
        clean_opcode = opcode & 0x7FFFFFFF

        # Evento (Opcode 30)
        if clean_opcode == 30:

            event_type = struct.unpack(">I", data[32:36])[0]

            # Evento de entrada digital
            if event_type in (1, 2):

                # Dados do evento começam após timestamp + link status
                # Offset 32 header + 4 event_type + 7 RTC + 4 timestamp + 1 link
                offset = 32 + 4 + 7 + 4 + 1

                input_address = struct.unpack(">B", data[offset:offset+1])[0]
                inputs_mask = struct.unpack(">I", data[offset+1:offset+5])[0]
                outputs_mask = struct.unpack(">I", data[offset+5:offset+9])[0]

                print(f"[EVENT] Input {input_address} changed")

                state_manager.update_both(inputs_mask, outputs_mask)

                print("[STATE UPDATED]")