import threading
import time

from app.services.device_manager import device_manager
from app.services.state_instance import state_manager


class DeviceMonitor:
    def __init__(self, interval=2):
        self.interval = interval
        self._running = False

    def start(self):
        if self._running:
            return
        self._running = True
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()

    def _run(self):
        while self._running:
            try:
                client = device_manager.get_client()
            except RuntimeError:
                time.sleep(self.interval)
                continue

            try:
                response = client.send(opcode=3, application_data=b"")
            except Exception:
                print("[POLLING] Falha de comunicacao")
                time.sleep(self.interval)
                continue

            if response["status"] == "data_combined":
                state_manager.update_both(response["inputs"], response["outputs"])
                state_manager.last_heartbeat = time.time()
                print("[POLLING] Estado atualizado")
            else:
                print("[POLLING] Falha de comunicacao")

            time.sleep(self.interval)
