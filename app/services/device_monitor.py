# services/device_monitor.py

import threading
import time

from app.core.commbox_client import CommboxClient
from app.services.state_instance import state_manager


class DeviceMonitor:

    def __init__(self, ip="192.168.26.228", port=5000, interval=2):
        self.client = CommboxClient(ip, port)
        self.interval = interval
        self._running = False

    def start(self):
        self._running = True
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()

    def _run(self):

        while self._running:

            response = self.client.send(opcode=3, application_data=b'')

            if response["status"] == "data_combined":

                state_manager.update_both(
                    response["inputs"],
                    response["outputs"]
                )

                state_manager.last_heartbeat = time.time()

                print("[POLLING] Estado atualizado")

            else:
                print("[POLLING] Falha de comunicação")

            time.sleep(self.interval)