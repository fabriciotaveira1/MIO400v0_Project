# services/socket_listener.py

import socket
import struct
import time
import threading

from app.services.state_instance import state_manager


class SocketListener:

    def __init__(self, host="0.0.0.0", port=4090):
        self.host = host
        self.port = port
        self._running = False

    def start(self):
        if self._running:
            return
        self._running = True
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()

    def _run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                server.bind((self.host, self.port))
            except OSError as exc:
                if getattr(exc, "winerror", None) == 10048:
                    print(
                        f"[SocketListener] Porta {self.port} em uso. "
                        "Listener nao sera iniciado neste processo."
                    )
                    self._running = False
                    return
                raise

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

        # Heartbeat (Opcode 92)
        if clean_opcode == 92:
            state_manager.last_heartbeat = time.time()

            # Payload com data_code 04 + inputs/outputs
            # Suporte para data_code em 1 byte (offset 32) ou 4 bytes (offset 32-36).
            if len(data) >= 41 and data[32] == 4:
                inputs_mask = struct.unpack(">I", data[33:37])[0]
                outputs_mask = struct.unpack(">I", data[37:41])[0]
                state_manager.update_both(inputs_mask, outputs_mask)
            elif len(data) >= 44:
                data_code = struct.unpack(">I", data[32:36])[0]
                if data_code == 4:
                    inputs_mask = struct.unpack(">I", data[36:40])[0]
                    outputs_mask = struct.unpack(">I", data[40:44])[0]
                    state_manager.update_both(inputs_mask, outputs_mask)

            return

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
