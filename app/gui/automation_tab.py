import json
from typing import Any, Dict, Optional
from urllib import error, request

from PyQt6.QtCore import Qt, QTime
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)


def _http_json(method: str, url: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = request.Request(url=url, method=method, data=data, headers=headers)
    with request.urlopen(req, timeout=3) as response:
        body = response.read().decode("utf-8")
        return json.loads(body) if body else {}


class RuleEditorDialog(QDialog):
    def __init__(
        self,
        parent=None,
        rule: Optional[Dict[str, Any]] = None,
        input_count: int = 0,
        output_count: int = 0,
        io_names: Optional[Dict[str, Dict[str, str]]] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Editor de Regra")
        self.resize(560, 460)
        self.rule = rule or {}
        self.input_count = max(1, input_count)
        self.output_count = max(1, output_count)
        self.io_names = io_names or {"inputs": {}, "outputs": {}}

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_input = QLineEdit(self.rule.get("name", ""))

        self.trigger_type = QComboBox()
        self._add_trigger_items()
        self.trigger_input = self._channel_combo("inputs", self.input_count)
        self.trigger_state = QComboBox()
        self.trigger_state.addItem("Ligado", True)
        self.trigger_state.addItem("Desligado", False)
        self.trigger_time = QTimeEdit()
        self.trigger_time.setDisplayFormat("HH:mm")

        self.condition_type = QComboBox()
        self._add_condition_items()
        self.condition_input = self._channel_combo("inputs", self.input_count)
        self.condition_output = self._channel_combo("outputs", self.output_count)
        self.condition_state = QComboBox()
        self.condition_state.addItem("Ligado", True)
        self.condition_state.addItem("Desligado", False)
        self.condition_start = QTimeEdit()
        self.condition_start.setDisplayFormat("HH:mm")
        self.condition_end = QTimeEdit()
        self.condition_end.setDisplayFormat("HH:mm")

        self.action_output = self._channel_combo("outputs", self.output_count)
        self.action_type = QComboBox()
        self.action_type.addItem("Ligar saida", "on")
        self.action_type.addItem("Desligar saida", "off")
        self.action_type.addItem("Inverter saida", "toggle")
        self.action_type.addItem("Pulso temporizado", "pulse")
        self.action_duration = QSpinBox()
        self.action_duration.setRange(1, 3600)
        self.action_duration.setValue(2)
        self.action_delay = QSpinBox()
        self.action_delay.setRange(0, 3600)
        self.action_delay.setValue(0)

        self.notice_label = QLabel("")
        self.notice_label.setStyleSheet("color: #a53f00; font-size: 11px;")
        self.notice_label.setWordWrap(True)

        form.addRow("Nome da regra", self.name_input)
        form.addRow("Quando disparar", self.trigger_type)
        form.addRow("Entrada do gatilho", self.trigger_input)
        form.addRow("Estado do gatilho", self.trigger_state)
        form.addRow("Horario (HH:MM)", self.trigger_time)
        form.addRow("Condicao extra", self.condition_type)
        form.addRow("Entrada da condicao", self.condition_input)
        form.addRow("Saida da condicao", self.condition_output)
        form.addRow("Estado da condicao", self.condition_state)
        form.addRow("Inicio da faixa", self.condition_start)
        form.addRow("Fim da faixa", self.condition_end)
        form.addRow("Saida da acao", self.action_output)
        form.addRow("Acao", self.action_type)
        form.addRow("Duracao da acao (s)", self.action_duration)
        form.addRow("Atraso antes da acao (s)", self.action_delay)

        layout.addLayout(form)
        layout.addWidget(self.notice_label)

        buttons = QHBoxLayout()
        ok_btn = QPushButton("Salvar")
        cancel_btn = QPushButton("Cancelar")
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(ok_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

        self.trigger_type.currentIndexChanged.connect(self._update_visibility)
        self.condition_type.currentIndexChanged.connect(self._update_visibility)
        self.action_type.currentIndexChanged.connect(self._update_visibility)

        self._load_rule_into_ui()
        self._update_visibility()

    def _add_trigger_items(self) -> None:
        self.trigger_type.addItem("Evento de entrada", "event")
        self.trigger_type.addItem("Enquanto entrada estiver", "while")
        self.trigger_type.addItem("Horario fixo", "time")

    def _add_condition_items(self) -> None:
        self.condition_type.addItem("Nenhuma", "none")
        self.condition_type.addItem("Entrada em estado", "input")
        self.condition_type.addItem("Saida em estado", "output")
        self.condition_type.addItem("Faixa de horario", "time_range")

    def _channel_combo(self, kind: str, count: int) -> QComboBox:
        combo = QComboBox()
        for channel in range(1, count + 1):
            combo.addItem(self._channel_name(kind, channel), channel)
        return combo

    def _channel_name(self, kind: str, channel: int) -> str:
        names = self.io_names.get(kind, {})
        custom = str(names.get(str(channel), "")).strip()
        prefix = "Entrada" if kind == "inputs" else "Saida"
        if custom:
            return f"{channel:02d} - {custom}"
        return f"{prefix} {channel:02d}"

    def _set_combo_value(self, combo: QComboBox, value: Any) -> None:
        idx = combo.findData(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _set_time(self, widget: QTimeEdit, hhmm: str) -> None:
        parsed = QTime.fromString(hhmm or "", "HH:mm")
        widget.setTime(parsed if parsed.isValid() else QTime(0, 0))

    def _load_rule_into_ui(self) -> None:
        trigger = dict(self.rule.get("trigger", {}))
        self._set_combo_value(self.trigger_type, str(trigger.get("type", "event")).lower())
        self._set_combo_value(self.trigger_input, int(trigger.get("input", 1) or 1))
        self._set_combo_value(self.trigger_state, bool(trigger.get("state", True)))
        self._set_time(self.trigger_time, str(trigger.get("schedule", "00:00")))

        conditions = list(self.rule.get("conditions", []))
        if conditions:
            self._load_condition(conditions[0])
            if len(conditions) > 1:
                self.notice_label.setText(
                    "A regra original tinha varias condicoes. O editor simplificado usa somente a primeira."
                )

        actions = list(self.rule.get("actions", []))
        if actions:
            self._load_actions(actions)

    def _load_condition(self, condition: Dict[str, Any]) -> None:
        ctype = str(condition.get("type", "")).lower()
        if ctype == "input":
            self._set_combo_value(self.condition_type, "input")
            self._set_combo_value(self.condition_input, int(condition.get("input", 1) or 1))
            self._set_combo_value(self.condition_state, bool(condition.get("state", True)))
            return
        if ctype == "state":
            scope = str(condition.get("scope", "input")).lower()
            if scope == "output":
                self._set_combo_value(self.condition_type, "output")
                self._set_combo_value(self.condition_output, int(condition.get("channel", 1) or 1))
                self._set_combo_value(self.condition_state, bool(condition.get("state", True)))
                return
            self._set_combo_value(self.condition_type, "input")
            self._set_combo_value(self.condition_input, int(condition.get("channel", 1) or 1))
            self._set_combo_value(self.condition_state, bool(condition.get("state", True)))
            return
        if ctype == "time_range":
            self._set_combo_value(self.condition_type, "time_range")
            self._set_time(self.condition_start, str(condition.get("start", "00:00")))
            self._set_time(self.condition_end, str(condition.get("end", "23:59")))
            return
        self.notice_label.setText(
            "A condicao original nao e suportada no modo simples. Salve para substituir por uma condicao simples."
        )

    def _load_actions(self, actions: list[Dict[str, Any]]) -> None:
        index = 0
        first = actions[0]
        if str(first.get("type", "")).lower() == "delay":
            delay_ms = int(first.get("duration_ms", first.get("delay_ms", 0)))
            self.action_delay.setValue(max(0, delay_ms // 1000))
            index = 1

        if index >= len(actions):
            return

        action = actions[index]
        atype = str(action.get("type", "")).lower()
        if atype == "timer":
            self._set_combo_value(self.action_type, "pulse")
            self._set_combo_value(self.action_output, int(action.get("output", 1) or 1))
            self.action_duration.setValue(max(1, int(action.get("duration_ms", 1000)) // 1000))
            return

        if atype == "output":
            action_name = str(action.get("action", "on")).lower()
            self._set_combo_value(self.action_type, action_name if action_name in {"on", "off", "toggle"} else "on")
            self._set_combo_value(self.action_output, int(action.get("output", action.get("channel", 1)) or 1))
            duration_ms = int(action.get("duration_ms", 0))
            if action_name == "on" and duration_ms > 0:
                self._set_combo_value(self.action_type, "pulse")
                self.action_duration.setValue(max(1, duration_ms // 1000))
            return

        self.notice_label.setText(
            "A acao original nao e suportada no modo simples. Salve para substituir por uma acao simples."
        )

    def _update_visibility(self) -> None:
        trigger_value = self.trigger_type.currentData()
        show_trigger_io = trigger_value in {"event", "while"}
        self.trigger_input.setVisible(show_trigger_io)
        self.trigger_state.setVisible(show_trigger_io)
        self.trigger_time.setVisible(trigger_value == "time")
        self._set_form_row_visible(self.trigger_input, show_trigger_io)
        self._set_form_row_visible(self.trigger_state, show_trigger_io)
        self._set_form_row_visible(self.trigger_time, trigger_value == "time")

        condition_value = self.condition_type.currentData()
        self._set_form_row_visible(self.condition_input, condition_value == "input")
        self._set_form_row_visible(self.condition_output, condition_value == "output")
        self._set_form_row_visible(self.condition_state, condition_value in {"input", "output"})
        self._set_form_row_visible(self.condition_start, condition_value == "time_range")
        self._set_form_row_visible(self.condition_end, condition_value == "time_range")

        is_pulse = self.action_type.currentData() == "pulse"
        self._set_form_row_visible(self.action_duration, is_pulse)

    def _set_form_row_visible(self, widget: QWidget, visible: bool) -> None:
        parent_layout = widget.parentWidget().layout()
        if not isinstance(parent_layout, QVBoxLayout):
            return
        form = parent_layout.itemAt(0).layout()
        if not isinstance(form, QFormLayout):
            return
        label = form.labelForField(widget)
        if label is not None:
            label.setVisible(visible)
        widget.setVisible(visible)

    def get_rule_data(self) -> Dict[str, Any]:
        trigger_type = str(self.trigger_type.currentData())
        trigger: Dict[str, Any] = {"type": trigger_type}
        if trigger_type in {"event", "while"}:
            trigger["input"] = int(self.trigger_input.currentData())
            trigger["state"] = bool(self.trigger_state.currentData())
        if trigger_type == "time":
            trigger["schedule"] = self.trigger_time.time().toString("HH:mm")

        conditions: list[Dict[str, Any]] = []
        condition_type = str(self.condition_type.currentData())
        if condition_type == "input":
            conditions.append(
                {
                    "type": "input",
                    "input": int(self.condition_input.currentData()),
                    "state": bool(self.condition_state.currentData()),
                }
            )
        elif condition_type == "output":
            conditions.append(
                {
                    "type": "state",
                    "scope": "output",
                    "channel": int(self.condition_output.currentData()),
                    "state": bool(self.condition_state.currentData()),
                }
            )
        elif condition_type == "time_range":
            conditions.append(
                {
                    "type": "time_range",
                    "start": self.condition_start.time().toString("HH:mm"),
                    "end": self.condition_end.time().toString("HH:mm"),
                }
            )

        actions: list[Dict[str, Any]] = []
        if self.action_delay.value() > 0:
            actions.append({"type": "delay", "duration_ms": self.action_delay.value() * 1000})

        action_type = str(self.action_type.currentData())
        output_channel = int(self.action_output.currentData())
        if action_type == "pulse":
            actions.append(
                {
                    "type": "timer",
                    "mode": "pulse",
                    "output": output_channel,
                    "duration_ms": self.action_duration.value() * 1000,
                }
            )
        else:
            actions.append(
                {
                    "type": "output",
                    "output": output_channel,
                    "action": action_type,
                }
            )

        return {
            "name": self.name_input.text().strip() or "Regra sem nome",
            "trigger": trigger,
            "conditions": conditions,
            "actions": actions,
            "enabled": bool(self.rule.get("enabled", True)),
        }


class AutomationTab(QWidget):
    def __init__(
        self,
        api_base_url: str,
        input_count: int = 0,
        output_count: int = 0,
        io_names: Optional[Dict[str, Dict[str, str]]] = None,
    ):
        super().__init__()
        self.api_base_url = api_base_url.rstrip("/")
        self.input_count = max(0, input_count)
        self.output_count = max(0, output_count)
        self.io_names = io_names or {"inputs": {}, "outputs": {}}
        self._load_device_context()
        self._build_ui()
        self.load_rules()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Regra", "Gatilho", "Condicao", "Acao", "Ativa"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        buttons = QHBoxLayout()
        self.add_btn = QPushButton("Adicionar regra")
        self.edit_btn = QPushButton("Editar regra")
        self.delete_btn = QPushButton("Excluir regra")
        self.enable_btn = QPushButton("Ativar")
        self.disable_btn = QPushButton("Desativar")
        self.sync_btn = QPushButton("Sincronizar")
        self.status_label = QLabel("")

        self.add_btn.clicked.connect(self.add_rule)
        self.edit_btn.clicked.connect(self.edit_rule)
        self.delete_btn.clicked.connect(self.delete_rule)
        self.enable_btn.clicked.connect(lambda: self.set_enabled(True))
        self.disable_btn.clicked.connect(lambda: self.set_enabled(False))
        self.sync_btn.clicked.connect(self.load_rules)

        buttons.addWidget(self.add_btn)
        buttons.addWidget(self.edit_btn)
        buttons.addWidget(self.delete_btn)
        buttons.addWidget(self.enable_btn)
        buttons.addWidget(self.disable_btn)
        buttons.addWidget(self.sync_btn)
        layout.addLayout(buttons)
        layout.addWidget(self.status_label)

    def _load_device_context(self) -> None:
        try:
            if self.input_count <= 0 or self.output_count <= 0:
                caps = _http_json("GET", f"{self.api_base_url}/device/capabilities")
                self.input_count = max(self.input_count, int(caps.get("inputs", 0)))
                self.output_count = max(self.output_count, int(caps.get("outputs", 0)))
        except Exception:
            pass

        try:
            names = _http_json("GET", f"{self.api_base_url}/io/names")
            self.io_names = {
                "inputs": dict(names.get("inputs", {})),
                "outputs": dict(names.get("outputs", {})),
            }
        except Exception:
            self.io_names = self.io_names or {"inputs": {}, "outputs": {}}

    def update_io_context(self, io_names: Dict[str, Dict[str, str]]) -> None:
        self.io_names = {
            "inputs": dict(io_names.get("inputs", {})),
            "outputs": dict(io_names.get("outputs", {})),
        }
        self.load_rules()

    def _selected_rule_id(self) -> Optional[int]:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        return int(item.data(Qt.ItemDataRole.UserRole))

    def _channel_name(self, kind: str, channel: int) -> str:
        names = self.io_names.get(kind, {})
        custom = str(names.get(str(channel), "")).strip()
        prefix = "E" if kind == "inputs" else "S"
        if custom:
            return f"{prefix}{channel:02d} ({custom})"
        return f"{prefix}{channel:02d}"

    def _describe_trigger(self, trigger: Dict[str, Any]) -> str:
        ttype = str(trigger.get("type", "event")).lower()
        if ttype == "time":
            return f"Horario {str(trigger.get('schedule', '--:--'))}"
        input_id = int(trigger.get("input", 0) or 0)
        state = "ligado" if bool(trigger.get("state", True)) else "desligado"
        prefix = "Evento" if ttype == "event" else "Enquanto"
        return f"{prefix} {self._channel_name('inputs', input_id)} {state}"

    def _describe_condition(self, conditions: list[Dict[str, Any]]) -> str:
        if not conditions:
            return "Sem condicao"
        c = conditions[0]
        ctype = str(c.get("type", "")).lower()
        if ctype == "input":
            state = "ligado" if bool(c.get("state", True)) else "desligado"
            return f"{self._channel_name('inputs', int(c.get('input', 0) or 0))} {state}"
        if ctype == "state" and str(c.get("scope", "")).lower() == "output":
            state = "ligado" if bool(c.get("state", True)) else "desligado"
            return f"{self._channel_name('outputs', int(c.get('channel', 0) or 0))} {state}"
        if ctype == "time_range":
            return f"Horario {c.get('start', '--:--')} ate {c.get('end', '--:--')}"
        return "Condicao avancada"

    def _describe_action(self, actions: list[Dict[str, Any]]) -> str:
        if not actions:
            return "Sem acao"
        start_idx = 1 if str(actions[0].get("type", "")).lower() == "delay" else 0
        delay = ""
        if start_idx == 1:
            delay_ms = int(actions[0].get("duration_ms", actions[0].get("delay_ms", 0)))
            delay = f"Apos {delay_ms // 1000}s: "
        if start_idx >= len(actions):
            return f"{delay}Sem acao"
        a = actions[start_idx]
        atype = str(a.get("type", "")).lower()
        if atype == "timer":
            out_id = int(a.get("output", 0) or 0)
            dur = int(a.get("duration_ms", 0)) // 1000
            return f"{delay}Pulso em {self._channel_name('outputs', out_id)} por {dur}s"
        if atype == "output":
            out_id = int(a.get("output", a.get("channel", 0)) or 0)
            action = str(a.get("action", "on")).lower()
            action_map = {"on": "Ligar", "off": "Desligar", "toggle": "Inverter"}
            return f"{delay}{action_map.get(action, 'Acionar')} {self._channel_name('outputs', out_id)}"
        return f"{delay}Acao avancada"

    def load_rules(self) -> None:
        try:
            self._load_device_context()
            payload = _http_json("GET", f"{self.api_base_url}/automation/rules")
            rules = payload.get("rules", [])
        except Exception as exc:
            self.status_label.setText(f"Falha ao carregar regras: {exc}")
            return

        self.table.setRowCount(len(rules))
        for row, rule in enumerate(rules):
            name_item = QTableWidgetItem(str(rule.get("name", "")))
            name_item.setData(Qt.ItemDataRole.UserRole, int(rule.get("id", 0)))
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, QTableWidgetItem(self._describe_trigger(dict(rule.get("trigger", {})))))
            self.table.setItem(row, 2, QTableWidgetItem(self._describe_condition(list(rule.get("conditions", [])))))
            self.table.setItem(row, 3, QTableWidgetItem(self._describe_action(list(rule.get("actions", [])))))
            self.table.setItem(row, 4, QTableWidgetItem("Sim" if bool(rule.get("enabled", True)) else "Nao"))
        self.status_label.setText(f"{len(rules)} regra(s) carregada(s)")

    def _open_editor(self, rule: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        dialog = RuleEditorDialog(
            self,
            rule=rule,
            input_count=self.input_count,
            output_count=self.output_count,
            io_names=self.io_names,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        return dialog.get_rule_data()

    def add_rule(self) -> None:
        payload = self._open_editor()
        if payload is None:
            return
        try:
            _http_json("POST", f"{self.api_base_url}/automation/rules", payload)
            self.load_rules()
        except Exception as exc:
            QMessageBox.warning(self, "Erro", f"Nao foi possivel adicionar a regra: {exc}")

    def edit_rule(self) -> None:
        rule_id = self._selected_rule_id()
        if rule_id is None:
            QMessageBox.information(self, "Selecione", "Selecione uma regra primeiro.")
            return
        row = self.table.currentRow()
        try:
            payload = _http_json("GET", f"{self.api_base_url}/automation/rules")
            rules = list(payload.get("rules", []))
            current = next((r for r in rules if int(r.get("id", -1)) == rule_id), None)
            if current is None:
                raise KeyError("Regra nao encontrada.")
        except Exception as exc:
            QMessageBox.warning(self, "Erro", f"Nao foi possivel abrir a regra: {exc}")
            return

        updated = self._open_editor(current)
        if updated is None:
            return
        updated["enabled"] = current.get("enabled", True)
        try:
            _http_json("PUT", f"{self.api_base_url}/automation/rules/{rule_id}", updated)
            self.load_rules()
        except Exception as exc:
            QMessageBox.warning(self, "Erro", f"Nao foi possivel editar a regra: {exc}")
            return

        if row >= 0:
            self.table.selectRow(row)

    def delete_rule(self) -> None:
        rule_id = self._selected_rule_id()
        if rule_id is None:
            QMessageBox.information(self, "Selecione", "Selecione uma regra primeiro.")
            return
        try:
            _http_json("DELETE", f"{self.api_base_url}/automation/rules/{rule_id}")
            self.load_rules()
        except Exception as exc:
            QMessageBox.warning(self, "Erro", f"Nao foi possivel excluir a regra: {exc}")

    def set_enabled(self, enabled: bool) -> None:
        rule_id = self._selected_rule_id()
        if rule_id is None:
            QMessageBox.information(self, "Selecione", "Selecione uma regra primeiro.")
            return
        suffix = "enable" if enabled else "disable"
        try:
            _http_json("PUT", f"{self.api_base_url}/automation/rules/{rule_id}/{suffix}")
            self.load_rules()
        except Exception as exc:
            QMessageBox.warning(self, "Erro", f"Nao foi possivel atualizar o estado: {exc}")
