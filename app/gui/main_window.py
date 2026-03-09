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
    QComboBox,
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
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.gui.automation_tab import AutomationTab
from app.gui.config_loader import (
    DEFAULT_API_PORT,
    load_config,
    save_config,
    set_last_device,
    upsert_device,
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
            return value.strip(), DEFAULT_API_PORT
    return value.strip(), DEFAULT_API_PORT


class ConnectionConfigDialog(QDialog):
    def __init__(self, parent=None, initial: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.setWindowTitle("Configuracao de Conexao")
        self.resize(460, 250)
        self.result_action = "cancel"

        device = initial or {}

        root = QVBoxLayout(self)
        form = QFormLayout()

        self.name_input = QLineEdit(str(device.get("name", "")))
        self.server_ip_input = QLineEdit(str(device.get("server_ip", "127.0.0.1")))
        self.device_ip_input = QLineEdit(str(device.get("device_ip", "192.168.1.100")))

        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(self._safe_int(device.get("port"), 5000))

        form.addRow("Nome do dispositivo", self.name_input)
        form.addRow("IP do Servidor", self.server_ip_input)
        form.addRow("IP do Dispositivo", self.device_ip_input)
        form.addRow("Porta", self.port_input)
        root.addLayout(form)

        buttons = QHBoxLayout()
        save_btn = QPushButton("Salvar")
        connect_btn = QPushButton("Conectar")
        cancel_btn = QPushButton("Cancelar")

        save_btn.clicked.connect(lambda: self._finish("save"))
        connect_btn.clicked.connect(lambda: self._finish("connect"))
        cancel_btn.clicked.connect(self.reject)

        buttons.addWidget(save_btn)
        buttons.addWidget(connect_btn)
        buttons.addWidget(cancel_btn)
        root.addLayout(buttons)

    @staticmethod
    def _safe_int(value: Any, fallback: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback

    def _finish(self, action: str) -> None:
        if not self.device_payload():
            return
        self.result_action = action
        self.accept()

    def device_payload(self) -> Optional[Dict[str, Any]]:
        payload = {
            "name": self.name_input.text().strip(),
            "server_ip": self.server_ip_input.text().strip(),
            "device_ip": self.device_ip_input.text().strip(),
            "port": int(self.port_input.value()),
        }
        if not payload["name"]:
            QMessageBox.warning(self, "Campo obrigatorio", "Informe o nome do dispositivo.")
            return None
        if not payload["server_ip"]:
            QMessageBox.warning(self, "Campo obrigatorio", "Informe o IP do servidor.")
            return None
        if not payload["device_ip"]:
            QMessageBox.warning(self, "Campo obrigatorio", "Informe o IP do dispositivo.")
            return None
        return payload


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
            "Defina apelidos para entradas e saidas. O rotulo fixo (Entrada 01, Saida 01, etc.) "
            "sempre sera mantido para identificacao."
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
        table.setHorizontalHeaderLabels(["Canal fixo", "Apelido"])
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.setAlternatingRowColors(True)

        prefix = "Entrada" if kind == "inputs" else "Saida"
        for channel in range(1, count + 1):
            channel_item = QTableWidgetItem(f"{prefix} {channel:02d}")
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
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.setWindowTitle("MIO400 - Painel de I/O")
        self.resize(1200, 780)

        self.config = config or load_config()
        self.api_base_url = ""
        self.current_device_name = ""
        self.current_device: Optional[Dict[str, Any]] = None
        self.device_info: Dict[str, Any] = {}
        self.io_names = {"inputs": {}, "outputs": {}}
        self.connected = False
        self._is_refreshing = False
        self._offline_cycles = 0
        self._is_auto_reconnecting = False

        self.input_count = 0
        self.output_count = 0
        self.input_name_labels: Dict[int, QLabel] = {}
        self.output_name_labels: Dict[int, QLabel] = {}
        self.output_control_name_labels: Dict[int, QLabel] = {}
        self.input_state_labels: Dict[int, QLabel] = {}
        self.output_state_labels: Dict[int, QLabel] = {}
        self.automation_tab: Optional[AutomationTab] = None

        self._build_shell_ui()
        self._populate_devices()
        self._setup_timers()
        QTimer.singleShot(0, self._startup_flow)

    def _build_shell_ui(self) -> None:
        container = QWidget()
        root = QVBoxLayout(container)
        root.setSpacing(8)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Dispositivo ativo:"))

        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(260)
        self.device_combo.currentIndexChanged.connect(self._on_device_changed)
        controls.addWidget(self.device_combo)

        self.manage_btn = QPushButton("Configurar")
        self.manage_btn.clicked.connect(self._open_connection_dialog)
        controls.addWidget(self.manage_btn)

        self.connect_btn = QPushButton("Conectar")
        self.connect_btn.clicked.connect(lambda: self.connect_selected_device(manual=True))
        controls.addWidget(self.connect_btn)

        self.disconnect_btn = QPushButton("Desconectar")
        self.disconnect_btn.clicked.connect(self.disconnect_current_device)
        controls.addWidget(self.disconnect_btn)

        self.reconnect_btn = QPushButton("Reconectar")
        self.reconnect_btn.clicked.connect(self.reconnect_current_device)
        controls.addWidget(self.reconnect_btn)

        controls.addStretch()
        root.addLayout(controls)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs)
        self.setCentralWidget(container)

        status_bar = QStatusBar(self)
        self.setStatusBar(status_bar)
        self.connection_status_label = QLabel("Status: Desconectado")
        self.log_label = QLabel("Pronto")
        status_bar.addPermanentWidget(self.connection_status_label)
        status_bar.addWidget(self.log_label, 1)

        self._rebuild_tabs()

    def _setup_timers(self) -> None:
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(1000)
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start()

        self.watchdog_timer = QTimer(self)
        self.watchdog_timer.setInterval(4000)
        self.watchdog_timer.timeout.connect(self._watchdog_check)
        self.watchdog_timer.start()

    def _startup_flow(self) -> None:
        if self.device_combo.count() == 0:
            self._log("Nenhum dispositivo salvo. Abrindo configuracao de conexao.")
            self._open_connection_dialog(force_connect=False)
            return

        self.connect_selected_device(manual=False)

    def _populate_devices(self) -> None:
        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        devices = list(self.config.get("devices", []))
        for device in devices:
            self.device_combo.addItem(str(device.get("name", "")), dict(device))

        last = str(self.config.get("last_device", "")).strip()
        if last:
            idx = self.device_combo.findText(last)
            if idx >= 0:
                self.device_combo.setCurrentIndex(idx)

        self.device_combo.blockSignals(False)

    def _selected_device(self) -> Optional[Dict[str, Any]]:
        data = self.device_combo.currentData()
        return dict(data) if isinstance(data, dict) else None

    def _open_connection_dialog(self, force_connect: bool = False) -> None:
        initial = self._selected_device()
        dialog = ConnectionConfigDialog(self, initial=initial)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        payload = dialog.device_payload()
        if payload is None:
            return

        self.config = upsert_device(self.config, payload, make_last=True)
        save_config(self.config)
        self._populate_devices()
        index = self.device_combo.findText(payload["name"])
        if index >= 0:
            self.device_combo.setCurrentIndex(index)

        self._log(f"Dispositivo salvo: {payload['name']}")
        if force_connect or dialog.result_action == "connect":
            self.connect_selected_device(manual=True)

    def _on_device_changed(self) -> None:
        device = self._selected_device()
        if device is None:
            return
        self.config = set_last_device(self.config, str(device.get("name", "")))
        save_config(self.config)
        self._log(f"Dispositivo ativo alterado para: {device.get('name', '')}")

    def connect_selected_device(self, manual: bool) -> bool:
        device = self._selected_device()
        if device is None:
            if manual:
                QMessageBox.warning(self, "Sem dispositivo", "Configure um dispositivo primeiro.")
            self._set_connection_status("Desconectado")
            return False

        server_ip = str(device.get("server_ip", "")).strip()
        device_ip = str(device.get("device_ip", "")).strip()
        api_port = self._safe_int(device.get("api_port"), DEFAULT_API_PORT)
        device_port = self._safe_int(device.get("port"), 5000)

        if not server_ip or not device_ip:
            if manual:
                QMessageBox.warning(self, "Configuracao invalida", "Preencha IP do servidor e do dispositivo.")
            return False

        self._set_connection_status("Reconectando..." if self.connected else "Conectando...")
        self._log(f"Conectando em {device.get('name', '')} ({server_ip} -> {device_ip}:{device_port})")

        api_base_url = f"http://{server_ip}:{api_port}"
        try:
            _http_json(
                "POST",
                f"{api_base_url}/device/configure",
                payload={"device_ip": device_ip, "device_port": device_port},
                timeout=2.0,
            )
            device_info = _http_json("GET", f"{api_base_url}/device/capabilities", timeout=4.0)
            _http_json("GET", f"{api_base_url}/device/health", timeout=2.0)
        except (error.URLError, error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            self.connected = False
            self._set_connection_status("Desconectado")
            self._log(f"Falha de conexao: {exc}")
            if manual:
                QMessageBox.critical(self, "Erro", "Nao foi possivel conectar ao dispositivo")
            return False

        self.api_base_url = api_base_url.rstrip("/")
        self.current_device = device
        self.current_device_name = str(device.get("name", ""))
        self.device_info = dict(device_info)
        self.input_count = self._safe_int(self.device_info.get("inputs"), 0)
        self.output_count = self._safe_int(self.device_info.get("outputs"), 0)
        self.connected = True
        self._offline_cycles = 0

        self.config = set_last_device(self.config, self.current_device_name)
        save_config(self.config)
        self._load_io_names()
        self._rebuild_tabs()
        self.refresh_data()

        self._set_connection_status("Conectado")
        self._log(f"Conectado ao dispositivo {self.current_device_name}")
        return True

    def disconnect_current_device(self) -> None:
        if not self.current_device:
            self.connected = False
            self._set_connection_status("Desconectado")
            return

        api_base_url = self._api_base_for_device(self.current_device)
        try:
            _http_json("POST", f"{api_base_url}/device/disconnect", timeout=1.5)
        except Exception:
            pass

        self.connected = False
        self._offline_cycles = 0
        self._apply_health_state({"online": False})
        self._set_connection_status("Desconectado")
        self._log("Conexao encerrada")

    def reconnect_current_device(self) -> None:
        if self._selected_device() is None:
            QMessageBox.warning(self, "Sem dispositivo", "Selecione um dispositivo para reconectar.")
            return

        self._set_connection_status("Reconectando...")
        if self.connected:
            self.disconnect_current_device()
        self.connect_selected_device(manual=True)

    def _watchdog_check(self) -> None:
        if not self.connected or self._is_auto_reconnecting:
            return

        online_text = ""
        if hasattr(self, "health_indicator"):
            online_text = self.health_indicator.text().strip().upper()

        if online_text == "ONLINE":
            self._offline_cycles = 0
            return

        self._offline_cycles += 1
        if self._offline_cycles < 2:
            return

        self._is_auto_reconnecting = True
        self._set_connection_status("Reconectando...")
        self._log("Watchdog detectou offline. Tentando reconexao automatica.")
        self.disconnect_current_device()
        ok = self.connect_selected_device(manual=False)
        if not ok:
            self._set_connection_status("Desconectado")
        self._is_auto_reconnecting = False

    def _load_io_names(self) -> None:
        if not self.api_base_url:
            self.io_names = {"inputs": {}, "outputs": {}}
            return
        try:
            names = _http_json("GET", f"{self.api_base_url}/io/names", timeout=2.0)
            self.io_names = {
                "inputs": dict(names.get("inputs", {})),
                "outputs": dict(names.get("outputs", {})),
            }
        except Exception:
            self.io_names = {"inputs": {}, "outputs": {}}

    def _rebuild_tabs(self) -> None:
        self.input_name_labels = {}
        self.output_name_labels = {}
        self.output_control_name_labels = {}
        self.input_state_labels = {}
        self.output_state_labels = {}

        while self.tabs.count() > 0:
            self.tabs.removeTab(0)

        self.tabs.addTab(self._build_io_tab(), "I/O")

        automation_api = self.api_base_url or "http://127.0.0.1:8000"
        self.automation_tab = AutomationTab(
            automation_api,
            input_count=self.input_count,
            output_count=self.output_count,
            io_names=self.io_names,
        )
        self.tabs.addTab(self.automation_tab, "AUTOMACAO")

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
        model = self.device_info.get("model", "MIO")
        firmware = self.device_info.get("firmware", "unknown")
        name = self.current_device_name or "Nenhum"
        self.device_label = QLabel(
            f"Ativo: {name}  |  Controladora: {model}  |  Entradas: {self.input_count}  |  "
            f"Saidas: {self.output_count}  |  Firmware: {firmware}"
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

    def refresh_data(self) -> None:
        if self._is_refreshing or not self.connected or not self.api_base_url:
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
        if not self.connected:
            QMessageBox.warning(self, "Desconectado", "Conecte em um dispositivo antes de enviar comandos.")
            return

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
        if self.connected:
            self._set_connection_status("Conectado" if online else "Desconectado")

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
        if not self.connected:
            QMessageBox.information(self, "Desconectado", "Conecte em um dispositivo para editar nomes I/O.")
            return

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
        fixed = f"{prefix} {channel:02d}"
        if custom:
            return f"{fixed} | {custom}"
        return fixed

    def _api_base_for_device(self, device: Dict[str, Any]) -> str:
        server_ip = str(device.get("server_ip", "127.0.0.1")).strip() or "127.0.0.1"
        api_port = self._safe_int(device.get("api_port"), DEFAULT_API_PORT)
        return f"http://{server_ip}:{api_port}"

    def _set_connection_status(self, status: str) -> None:
        self.connection_status_label.setText(f"Status: {status}")

    def _log(self, message: str) -> None:
        self.log_label.setText(message)
        print(f"[GUI] {message}")

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


def main() -> None:
    parser = argparse.ArgumentParser(description="Painel PyQt6 para API FastAPI MIO400")
    parser.add_argument("--ip", default=None, help="IP/host da API para inserir no dispositivo")
    parser.add_argument("--port", type=int, default=DEFAULT_API_PORT, help="Porta da API")
    parser.add_argument("--device-ip", default=None, help="IP da MIO para inserir no dispositivo")
    parser.add_argument("--device-port", type=int, default=5000, help="Porta da MIO")
    parser.add_argument("--api-url", default=None, help="Compatibilidade: URL completa da API")
    args = parser.parse_args()

    config = load_config()

    if args.api_url:
        api_host, api_port = _parse_api_url(args.api_url)
        cli_device = {
            "name": "Dispositivo CLI",
            "server_ip": api_host,
            "device_ip": args.device_ip or "192.168.1.100",
            "port": args.device_port,
            "api_port": api_port,
        }
        config = upsert_device(config, cli_device, make_last=True)
        save_config(config)
    elif args.ip or args.device_ip:
        cli_device = {
            "name": "Dispositivo CLI",
            "server_ip": args.ip or "127.0.0.1",
            "device_ip": args.device_ip or "192.168.1.100",
            "port": args.device_port,
            "api_port": args.port,
        }
        config = upsert_device(config, cli_device, make_last=True)
        save_config(config)

    app = QApplication(sys.argv)
    window = MainWindow(config=config)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
