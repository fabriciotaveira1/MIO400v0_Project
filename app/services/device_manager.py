import threading

from app.core.commbox_client import CommboxClient


class DeviceManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._client = None
        self._device_ip = ""
        self._device_port = 0

    def configure(self, ip: str, port: int) -> None:
        with self._lock:
            self._client = CommboxClient(ip=ip, port=port)
            self._device_ip = str(ip).strip()
            self._device_port = int(port)

    def disconnect(self) -> None:
        with self._lock:
            self._client = None

    def reconnect(self) -> None:
        with self._lock:
            if not self._device_ip or self._device_port <= 0:
                raise RuntimeError("Device not configured")
            self._client = CommboxClient(ip=self._device_ip, port=self._device_port)

    def get_client(self) -> CommboxClient:
        with self._lock:
            if self._client is None:
                raise RuntimeError("Device not configured")
            return self._client

    def get_current_config(self) -> dict:
        with self._lock:
            return {
                "configured": self._client is not None,
                "device_ip": self._device_ip,
                "device_port": self._device_port,
            }


device_manager = DeviceManager()
