import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from urllib import error, request

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

if __package__ is None or __package__ == "":
    # Permite executar este arquivo diretamente sem quebrar imports "from app..."
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.gui.automation_tab import AutomationTab


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
            device_info = _http_json("GET", f"{api_base_url}/device/capabilities", timeout=4.0)
            _http_json("GET", f"{api_base_url}/device/health", timeout=2.0)
        except (error.URLError, error.HTTPError, TimeoutError, json.JSONDecodeError):
            QMessageBox.critical(self, "Erro", "Nao foi possivel conectar ao dispositivo")
            return

        self.main_window = MainWindow(api_base_url=api_base_url, device_info=device_info)
        self.main_window.show()
        self.hide()


class IONamesDialog(QDialog):
    def __init__(
        self,
        parent=None,
        input_count: int = 0,
        output_count: int = 0,
        io_names: Optional[Dict[str, Dict[str, str]]] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Personalizar nomes de I/O")
        self.resize(760, 560)
        self.input_count = max(0, input_count)
        self.output_count = max(0, output_count)
        self.io_names = io_names or {"inputs": {}, "outputs": {}}

        root = QVBoxLayout(self)
        info = QLabel(
            "Defina nomes amigaveis para entradas e saidas. "
            "Campos vazios usam o nome padrao."
        )
        info.setWordWrap(True)
        root.addWidget(info)

        form = QFormLayout()
        self.inputs_table = self._build_table("inputs", self.input_count)
        self.outputs_table = self._build_table("outputs", self.output_count)
        form.addRow("Entradas", self.inputs_table)
        form.addRow("Saidas", self.outputs_table)
        root.addLayout(form)

        buttons = QHBoxLayout()
        save_btn = QPushButton("Salvar")
        cancel_btn = QPushButton("Cancelar")
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        root.addLayout(buttons)

    def _build_table(self, kind: str, count: int) -> QTableWidget:
        table = QTableWidget(count, 2, self)
        table.setHorizontalHeaderLabels(["Canal", "Nome"])
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.setAlternatingRowColors(True)
        for channel in range(1, count + 1):
            channel_item = QTableWidgetItem(f"{channel:02d}")
            channel_item.setFlags(channel_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(channel - 1, 0, channel_item)

            names = self.io_names.get(kind, {})
            current_name = str(names.get(str(channel), "")).strip()
            table.setItem(channel - 1, 1, QTableWidgetItem(current_name))
        return table

    def get_payload(self) -> Dict[str, Dict[str, str]]:
        return {
            "inputs": self._read_names(self.inputs_table),
            "outputs": self._read_names(self.outputs_table),
        }

    @staticmethod
    def _read_names(table: QTableWidget) -> Dict[str, str]:
        names: Dict[str, str] = {}
        for row in range(table.rowCount()):
            channel = str(row + 1)
            item = table.item(row, 1)
            value = item.text().strip() if item is not None else ""
            names[channel] = value
        return names


class MainWindow(QMainWindow):
    def __init__(self, api_base_url: str, device_info: Dict[str, Any]):
        super().__init__()
        self.api_base_url = api_base_url.rstrip("/")
        self.device_info = device_info or {}
        self.io_names = {"inputs": {}, "outputs": {}}
        self.setWindowTitle("MIO400 - Painel de I/O")
        self.resize(1180, 760)

        self.input_name_labels: Dict[int, QLabel] = {}
        self.output_name_labels: Dict[int, QLabel] = {}
        self.output_control_name_labels: Dict[int, QLabel] = {}
        self.input_state_labels: Dict[int, QLabel] = {}
        self.output_state_labels: Dict[int, QLabel] = {}
        self.input_count = self._safe_int(self.device_info.get("inputs"), 0)
        self.output_count = self._safe_int(self.device_info.get("outputs"), 0)
        self._is_refreshing = False
        self.automation_tab: Optional[AutomationTab] = None

        self._load_io_names()
        self._build_ui()
        self._setup_timer()
        self.refresh_data()

    def _load_io_names(self) -> None:
        try:
            names = _http_json("GET", f"{self.api_base_url}/io/names", timeout=2.0)
            self.io_names = {
                "inputs": dict(names.get("inputs", {})),
                "outputs": dict(names.get("outputs", {})),
            }
        except Exception:
            self.io_names = {"inputs": {}, "outputs": {}}

    def _build_ui(self) -> None:
        tabs = QTabWidget()
        tabs.addTab(self._build_io_tab(), "I/O")
        self.automation_tab = AutomationTab(
            self.api_base_url,
            input_count=self.input_count,
            output_count=self.output_count,
            io_names=self.io_names,
        )
        tabs.addTab(self.automation_tab, "AUTOMAÇÃO")
        self.setCentralWidget(tabs)

    def _build_io_tab(self) -> QWidget:
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

        device_layout = QHBoxLayout()
        self.device_label = QLabel(
            "Controladora: "
            f"{self.device_info.get('model', 'MIO')}  |  "
            f"Entradas: {self.input_count}  |  "
            f"Saidas: {self.output_count}  |  "
            f"Firmware: {self.device_info.get('firmware', 'unknown')}"
        )
        self.device_label.setStyleSheet("font-weight: 600;")
        device_layout.addWidget(self.device_label)
        edit_names_btn = QPushButton("Personalizar nomes de I/O")
        edit_names_btn.clicked.connect(self._open_io_names_dialog)
        device_layout.addWidget(edit_names_btn)
        device_layout.addStretch()

        io_layout = QHBoxLayout()
        io_layout.setSpacing(16)
        inputs_panel = self._build_states_panel(
            "Entradas",
            self.input_count,
            "inputs",
            self.input_state_labels,
            self.input_name_labels,
        )
        outputs_panel = self._build_states_panel(
            "Saidas",
            self.output_count,
            "outputs",
            self.output_state_labels,
            self.output_name_labels,
        )
        io_layout.addWidget(inputs_panel)
        io_layout.addWidget(outputs_panel)

        control_title = QLabel("Controle de reles")
        control_title.setStyleSheet("font-size: 16px; font-weight: 700;")
        control_scroll = QScrollArea()
        control_scroll.setWidgetResizable(True)
        control_scroll.setMinimumHeight(280)
        control_scroll.setWidget(self._build_controls_panel(self.output_count))

        root_layout.addLayout(health_layout)
        root_layout.addLayout(device_layout)
        root_layout.addLayout(io_layout)
        root_layout.addWidget(control_title)
        root_layout.addWidget(control_scroll)
        return root

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
            health = _http_json("GET", f"{self.api_base_url}/device/health")
            self._apply_health_state(health)
            if not bool(health.get("online", False)):
                return

            io = _http_json("GET", f"{self.api_base_url}/io/status")
            self._apply_io_state(io)
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

        for channel, label in self.input_state_labels.items():
            self._set_on_off(label, self._to_bool(inputs.get(str(channel), inputs.get(channel, False))))

        for channel, label in self.output_state_labels.items():
            self._set_on_off(label, self._to_bool(outputs.get(str(channel), outputs.get(channel, False))))

    def _apply_health_state(self, health_data: Dict[str, Any]) -> None:
        online = bool(health_data.get("online", False))
        self.health_indicator.setText("ONLINE" if online else "OFFLINE")
        self._set_indicator_color(self.health_indicator, "#2e7d32" if online else "#c62828")

    def _build_states_panel(
        self,
        title: str,
        count: int,
        kind: str,
        state_store: Dict[int, QLabel],
        name_store: Dict[int, QLabel],
    ) -> QWidget:
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
            name = QLabel(self._channel_name(kind, channel))
            state = QLabel("OFF")
            state.setAlignment(Qt.AlignmentFlag.AlignCenter)
            state.setMinimumWidth(64)
            self._set_indicator_color(state, "#b0bec5")

            state_store[channel] = state
            name_store[channel] = name
            row = (channel - 1) // 2
            col = ((channel - 1) % 2) * 2
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
            name = QLabel(self._channel_name("outputs", channel))
            on_btn = QPushButton("Ligar")
            off_btn = QPushButton("Desligar")

            on_btn.clicked.connect(
                lambda _checked=False, ch=channel: self.send_output_command(ch, 1)
            )
            off_btn.clicked.connect(
                lambda _checked=False, ch=channel: self.send_output_command(ch, 0)
            )

            row = channel - 1
            self.output_control_name_labels[channel] = name
            layout.addWidget(name, row, 0)
            layout.addWidget(on_btn, row, 1)
            layout.addWidget(off_btn, row, 2)

        return holder

    def _open_io_names_dialog(self) -> None:
        dialog = IONamesDialog(
            self,
            input_count=self.input_count,
            output_count=self.output_count,
            io_names=self.io_names,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        payload = dialog.get_payload()
        try:
            updated = _http_json("POST", f"{self.api_base_url}/io/names", payload=payload, timeout=2.0)
            self.io_names = {
                "inputs": dict(updated.get("inputs", payload.get("inputs", {}))),
                "outputs": dict(updated.get("outputs", payload.get("outputs", {}))),
            }
            self._refresh_io_name_labels()
            if self.automation_tab is not None:
                self.automation_tab.update_io_context(self.io_names)
            QMessageBox.information(self, "Nomes salvos", "Nomes de I/O atualizados com sucesso.")
        except (error.URLError, error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            QMessageBox.warning(self, "Erro", f"Nao foi possivel salvar os nomes:\n{exc}")

    def _refresh_io_name_labels(self) -> None:
        for channel, label in self.input_name_labels.items():
            label.setText(self._channel_name("inputs", channel))
        for channel, label in self.output_name_labels.items():
            label.setText(self._channel_name("outputs", channel))
        for channel, label in self.output_control_name_labels.items():
            label.setText(self._channel_name("outputs", channel))

    def _channel_name(self, kind: str, channel: int) -> str:
        names = self.io_names.get(kind, {})
        custom = str(names.get(str(channel), "")).strip()
        prefix = "Entrada" if kind == "inputs" else "Saida"
        if custom:
            return f"{channel:02d} - {custom}"
        return f"{prefix} {channel:02d}"

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

    @staticmethod
    def _safe_int(value: Any, default: int = 0) -> int:
        try:
            parsed = int(value)
            return parsed if parsed >= 0 else default
        except (TypeError, ValueError):
            return default


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
