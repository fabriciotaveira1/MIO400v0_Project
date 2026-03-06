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
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
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


class MainWindow(QMainWindow):
    def __init__(self, api_base_url: str):
        super().__init__()
        self.api_base_url = api_base_url.rstrip("/")
        self.setWindowTitle("MIO400 - Painel de I/O")
        self.resize(1100, 700)

        self.input_labels: Dict[int, QLabel] = {}
        self.output_labels: Dict[int, QLabel] = {}
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
        io_layout.addWidget(self._build_states_panel("Inputs", self.input_labels))
        io_layout.addWidget(self._build_states_panel("Outputs", self.output_labels))

        control_title = QLabel("Controle de Relés")
        control_title.setStyleSheet("font-size: 16px; font-weight: 700;")
        control_scroll = self._build_controls_panel()

        root_layout.addLayout(health_layout)
        root_layout.addLayout(io_layout)
        root_layout.addWidget(control_title)
        root_layout.addWidget(control_scroll)

        self.setCentralWidget(root)

    def _build_states_panel(self, title: str, store: Dict[int, QLabel]) -> QWidget:
        panel = QWidget()
        panel_layout = QVBoxLayout(panel)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 15px; font-weight: 700;")
        panel_layout.addWidget(title_label)

        grid = QGridLayout()
        for channel in range(1, 33):
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

    def _build_controls_panel(self) -> QScrollArea:
        holder = QWidget()
        layout = QGridLayout(holder)
        layout.setSpacing(8)

        for channel in range(1, 33):
            name = QLabel(f"Relé {channel:02d}")
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

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(holder)
        scroll.setMinimumHeight(280)
        return scroll

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

    def _apply_io_state(self, io_data: Dict[str, Any]) -> None:
        inputs = io_data.get("inputs", {})
        outputs = io_data.get("outputs", {})

        for channel in range(1, 33):
            input_on = self._to_bool(inputs.get(str(channel), inputs.get(channel, False)))
            output_on = self._to_bool(outputs.get(str(channel), outputs.get(channel, False)))

            self._set_on_off(self.input_labels[channel], input_on)
            self._set_on_off(self.output_labels[channel], output_on)

    def _apply_health_state(self, health_data: Dict[str, Any]) -> None:
        online = bool(health_data.get("online", False))
        self.health_indicator.setText("ONLINE" if online else "OFFLINE")
        self._set_indicator_color(
            self.health_indicator,
            "#2e7d32" if online else "#c62828",
        )

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


def main() -> None:
    parser = argparse.ArgumentParser(description="Painel PyQt6 para API FastAPI MIO400")
    parser.add_argument(
        "--api-url",
        default="http://127.0.0.1:8000",
        help="Base URL da API FastAPI",
    )
    args = parser.parse_args()

    app = QApplication(sys.argv)
    window = MainWindow(api_base_url=args.api_url)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
