import argparse
import json
import sys
from typing import Any, Dict, Optional
from urllib import error, request

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import (
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


def _http_json(
    method: str,
    url: str,
    payload: Optional[Dict[str, Any]] = None,
    timeout: float = 1.5,
) -> Dict[str, Any]:
    data = None
    headers = {"Accept": "application/json"}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = request.Request(url=url, data=data, headers=headers, method=method)
    with request.urlopen(req, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        return json.loads(body) if body else {}


class ConnectionWindow(QWidget):
    def __init__(
        self,
        default_api_ip: str = "127.0.0.1",
        default_api_port: int = 8000,
        default_device_ip: str = "192.168.1.100",
        default_device_port: int = 5000,
    ):
        super().__init__()
        self.main_window: Optional[MainWindow] = None
        self.setWindowTitle("MIO400 - Conexao")
        self.resize(420, 260)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        api_ip_label = QLabel("IP do Servidor API")
        self.api_ip_input = QLineEdit(default_api_ip)
        self.api_ip_input.setPlaceholderText("Ex: 127.0.0.1")

        api_port_label = QLabel("Porta da API")
        self.api_port_input = QSpinBox()
        self.api_port_input.setRange(1, 65535)
        self.api_port_input.setValue(default_api_port)

        device_ip_label = QLabel("IP da Controladora MIO")
        self.device_ip_input = QLineEdit(default_device_ip)
        self.device_ip_input.setPlaceholderText("Ex: 192.168.1.100")

        device_port_label = QLabel("Porta da MIO")
        self.device_port_input = QSpinBox()
        self.device_port_input.setRange(1, 65535)
        self.device_port_input.setValue(default_device_port)

        self.connect_button = QPushButton("Conectar")
        self.connect_button.clicked.connect(self._connect)

        layout.addWidget(api_ip_label)
        layout.addWidget(self.api_ip_input)
        layout.addWidget(api_port_label)
        layout.addWidget(self.api_port_input)
        layout.addWidget(device_ip_label)
        layout.addWidget(self.device_ip_input)
        layout.addWidget(device_port_label)
        layout.addWidget(self.device_port_input)
        layout.addWidget(self.connect_button)

    def _connect(self) -> None:
        api_host = self.api_ip_input.text().strip()
        device_ip = self.device_ip_input.text().strip()

        if not api_host:
            QMessageBox.warning(self, "Erro", "Informe o IP do servidor API.")
            return
        if not device_ip:
            QMessageBox.warning(self, "Erro", "Informe o IP da controladora MIO.")
            return

        api_base_url = f"http://{api_host}:{self.api_port_input.value()}"
        try:
            _http_json(
                "POST",
                f"{api_base_url}/device/configure",
                payload={
                    "device_ip": device_ip,
                    "device_port": self.device_port_input.value(),
                },
                timeout=2.0,
            )
            _http_json("GET", f"{api_base_url}/device/health", timeout=2.0)
        except (error.URLError, error.HTTPError, TimeoutError, json.JSONDecodeError):
            QMessageBox.critical(self, "Erro", "Nao foi possivel conectar ao dispositivo")
            return

        self.main_window = MainWindow(api_base_url=api_base_url)
        self.main_window.show()
        self.hide()


class MainWindow(QMainWindow):
    def __init__(self, api_base_url: str):
        super().__init__()
        self.api_base_url = api_base_url.rstrip("/")
        self.setWindowTitle("MIO400 - Painel de I/O")
        self.resize(1100, 720)

        self.input_labels: Dict[int, QLabel] = {}
        self.output_labels: Dict[int, QLabel] = {}
        self.input_count = 0
        self.output_count = 0
        self._is_refreshing = False

        self._build_ui()
        self._setup_timer()
        self.refresh_data()

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setSpacing(12)

        health_layout = QHBoxLayout()
        health_title = QLabel("Dispositivo:")
        health_title.setStyleSheet("font-weight: 600;")
        self.health_indicator = QLabel("DESCONHECIDO")
        self.health_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.health_indicator.setMinimumWidth(140)
        self._set_indicator_color(self.health_indicator, "#9e9e9e")
        health_layout.addWidget(health_title)
        health_layout.addWidget(self.health_indicator)
        health_layout.addStretch()

        io_layout = QHBoxLayout()
        io_layout.setSpacing(16)
        self.inputs_panel = QWidget()
        self.outputs_panel = QWidget()
        io_layout.addWidget(self.inputs_panel)
        io_layout.addWidget(self.outputs_panel)

        control_title = QLabel("Controle de Reles")
        control_title.setStyleSheet("font-size: 16px; font-weight: 700;")
        self.control_scroll = QScrollArea()
        self.control_scroll.setWidgetResizable(True)
        self.control_scroll.setMinimumHeight(280)

        root_layout.addLayout(health_layout)
        root_layout.addLayout(io_layout)
        root_layout.addWidget(control_title)
        root_layout.addWidget(self.control_scroll)

        self.setCentralWidget(root)

    def _setup_timer(self) -> None:
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.refresh_data)
        self.timer.start()

    def refresh_data(self) -> None:
        if self._is_refreshing:
            return

        self._is_refreshing = True
        try:
            io = _http_json("GET", f"{self.api_base_url}/io/status")
            health = _http_json("GET", f"{self.api_base_url}/device/health")

            self._refresh_dynamic_structure(io)
            self._apply_io_state(io)
            self._apply_health_state(health)
        except (error.URLError, error.HTTPError, TimeoutError, json.JSONDecodeError):
            self._apply_health_state({"online": False})
        finally:
            self._is_refreshing = False

    def send_output_command(self, component_addr: int, action: int) -> None:
        payload = {
            "component_addr": component_addr,
            "action": action,
            "total_time": 0,
            "memory": 0,
        }
        try:
            _http_json("POST", f"{self.api_base_url}/control/output", payload=payload)
            self.refresh_data()
        except (error.URLError, error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            QMessageBox.warning(self, "Falha no comando", f"Nao foi possivel enviar comando:\n{exc}")

    def _refresh_dynamic_structure(self, io_data: Dict[str, Any]) -> None:
        inputs = io_data.get("inputs", {})
        outputs = io_data.get("outputs", {})
        new_input_count = self._max_channel(inputs)
        new_output_count = self._max_channel(outputs)

        if new_input_count != self.input_count:
            self.input_count = new_input_count
            self.input_labels = {}
            self._set_panel_widget(self.inputs_panel, self._build_states_panel("Inputs", self.input_count, self.input_labels))

        if new_output_count != self.output_count:
            self.output_count = new_output_count
            self.output_labels = {}
            self._set_panel_widget(
                self.outputs_panel,
                self._build_states_panel("Outputs", self.output_count, self.output_labels),
            )
            self.control_scroll.setWidget(self._build_controls_panel(self.output_count))

        if self.control_scroll.widget() is None:
            self.control_scroll.setWidget(self._build_controls_panel(self.output_count))

    def _apply_io_state(self, io_data: Dict[str, Any]) -> None:
        inputs = io_data.get("inputs", {})
        outputs = io_data.get("outputs", {})

        for channel, label in self.input_labels.items():
            self._set_on_off(label, self._to_bool(inputs.get(str(channel), inputs.get(channel, False))))

        for channel, label in self.output_labels.items():
            self._set_on_off(label, self._to_bool(outputs.get(str(channel), outputs.get(channel, False))))

    def _apply_health_state(self, health_data: Dict[str, Any]) -> None:
        online = bool(health_data.get("online", False))
        self.health_indicator.setText("ONLINE" if online else "OFFLINE")
        self._set_indicator_color(self.health_indicator, "#2e7d32" if online else "#c62828")

    def _build_states_panel(self, title: str, count: int, store: Dict[int, QLabel]) -> QWidget:
        panel = QWidget()
        panel_layout = QVBoxLayout(panel)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 15px; font-weight: 700;")
        panel_layout.addWidget(title_label)

        if count <= 0:
            panel_layout.addWidget(QLabel("Nenhum canal detectado"))
            return panel

        grid = QGridLayout()
        for channel in range(1, count + 1):
            name = QLabel(f"{channel:02d}")
            state = QLabel("OFF")
            state.setAlignment(Qt.AlignmentFlag.AlignCenter)
            state.setMinimumWidth(64)
            self._set_indicator_color(state, "#b0bec5")

            store[channel] = state
            row = (channel - 1) // 4
            col = ((channel - 1) % 4) * 2
            grid.addWidget(name, row, col)
            grid.addWidget(state, row, col + 1)

        panel_layout.addLayout(grid)
        return panel

    def _build_controls_panel(self, output_count: int) -> QWidget:
        holder = QWidget()
        layout = QGridLayout(holder)
        layout.setSpacing(8)

        if output_count <= 0:
            layout.addWidget(QLabel("Nenhum rele detectado"), 0, 0)
            return holder

        for channel in range(1, output_count + 1):
            name = QLabel(f"Rele {channel:02d}")
            on_btn = QPushButton("Ligar")
            off_btn = QPushButton("Desligar")

            on_btn.clicked.connect(
                lambda _checked=False, ch=channel: self.send_output_command(ch, 1)
            )
            off_btn.clicked.connect(
                lambda _checked=False, ch=channel: self.send_output_command(ch, 0)
            )

            row = channel - 1
            layout.addWidget(name, row, 0)
            layout.addWidget(on_btn, row, 1)
            layout.addWidget(off_btn, row, 2)

        return holder

    @staticmethod
    def _set_panel_widget(panel: QWidget, widget: QWidget) -> None:
        old_layout = panel.layout()
        if old_layout is not None:
            while old_layout.count():
                item = old_layout.takeAt(0)
                child = item.widget()
                if child is not None:
                    child.deleteLater()
            old_layout.deleteLater()

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(widget)

    @staticmethod
    def _max_channel(channels: Any) -> int:
        if not isinstance(channels, dict):
            return 0

        max_channel = 0
        for key in channels.keys():
            try:
                channel = int(key)
            except (TypeError, ValueError):
                continue
            if channel > max_channel:
                max_channel = channel
        return max_channel

    @staticmethod
    def _to_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "on", "yes"}
        return False

    def _set_on_off(self, label: QLabel, is_on: bool) -> None:
        label.setText("ON" if is_on else "OFF")
        self._set_indicator_color(label, "#2e7d32" if is_on else "#b0bec5")

    @staticmethod
    def _set_indicator_color(label: QLabel, hex_color: str) -> None:
        palette = label.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(hex_color))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#ffffff"))
        label.setAutoFillBackground(True)
        label.setPalette(palette)


def _parse_api_url(api_url: str) -> tuple[str, int]:
    value = api_url.strip()
    if value.startswith("http://"):
        value = value[7:]
    if value.startswith("https://"):
        value = value[8:]

    if ":" in value:
        host, port_text = value.rsplit(":", 1)
        try:
            return host.strip(), int(port_text.strip())
        except ValueError:
            return value.strip(), 8000
    return value.strip(), 8000


def main() -> None:
    parser = argparse.ArgumentParser(description="Painel PyQt6 para API FastAPI MIO400")
    parser.add_argument("--ip", default="127.0.0.1", help="IP/host padrao da API")
    parser.add_argument("--port", type=int, default=8000, help="Porta padrao da API")
    parser.add_argument("--device-ip", default="192.168.1.100", help="IP padrao da MIO")
    parser.add_argument("--device-port", type=int, default=5000, help="Porta padrao da MIO")
    parser.add_argument(
        "--api-url",
        default=None,
        help="Compatibilidade: URL completa da API para preencher IP/porta iniciais",
    )
    args = parser.parse_args()

    default_api_ip = args.ip
    default_api_port = args.port
    if args.api_url:
        default_api_ip, default_api_port = _parse_api_url(args.api_url)

    app = QApplication(sys.argv)
    window = ConnectionWindow(
        default_api_ip=default_api_ip,
        default_api_port=default_api_port,
        default_device_ip=args.device_ip,
        default_device_port=args.device_port,
    )
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
