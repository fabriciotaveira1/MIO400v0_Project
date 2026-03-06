import threading

from app.core.commbox_client import CommboxClient


class DeviceManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._client = None

    def configure(self, ip: str, port: int) -> None:
        with self._lock:
            self._client = CommboxClient(ip=ip, port=port)

    def get_client(self) -> CommboxClient:
        with self._lock:
            if self._client is None:
                raise RuntimeError("Device not configured")
            return self._client


device_manager = DeviceManager()
