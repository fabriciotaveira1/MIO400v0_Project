import json
from typing import Any, Dict, List, Optional
from urllib import request

from PyQt6.QtCore import Qt, QTime
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
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


class ConditionRow(QWidget):
    def __init__(self, input_count: int, output_count: int, io_names: Dict[str, Dict[str, str]]):
        super().__init__()
        self.io_names = io_names

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.ctype = QComboBox()
        self.ctype.addItem("Entrada em estado", "INPUT_STATE")
        self.ctype.addItem("Saida em estado", "OUTPUT_STATE")
        self.ctype.addItem("Faixa de horario", "TIME_RANGE")

        self.input_channel = QComboBox()
        for channel in range(1, max(1, input_count) + 1):
            self.input_channel.addItem(self._channel_name("inputs", channel), channel)

        self.output_channel = QComboBox()
        for channel in range(1, max(1, output_count) + 1):
            self.output_channel.addItem(self._channel_name("outputs", channel), channel)

        self.state = QComboBox()
        self.state.addItem("ON", True)
        self.state.addItem("OFF", False)

        self.start = QTimeEdit()
        self.start.setDisplayFormat("HH:mm")
        self.start.setTime(QTime(0, 0))

        self.end = QTimeEdit()
        self.end.setDisplayFormat("HH:mm")
        self.end.setTime(QTime(23, 59))

        self.remove_btn = QPushButton("Remover")
        self.remove_btn.setMaximumWidth(90)

        layout.addWidget(self.ctype)
        layout.addWidget(self.input_channel)
        layout.addWidget(self.output_channel)
        layout.addWidget(self.state)
        layout.addWidget(self.start)
        layout.addWidget(self.end)
        layout.addWidget(self.remove_btn)

        self.ctype.currentIndexChanged.connect(self._refresh_visibility)
        self._refresh_visibility()

    def _channel_name(self, kind: str, channel: int) -> str:
        names = self.io_names.get(kind, {})
        custom = str(names.get(str(channel), "")).strip()
        prefix = "Entrada" if kind == "inputs" else "Saida"
        if custom:
            return f"{prefix} {channel:02d} ({custom})"
        return f"{prefix} {channel:02d}"

    def _refresh_visibility(self) -> None:
        ctype = str(self.ctype.currentData())
        self.input_channel.setVisible(ctype == "INPUT_STATE")
        self.output_channel.setVisible(ctype == "OUTPUT_STATE")
        self.state.setVisible(ctype in {"INPUT_STATE", "OUTPUT_STATE"})
        self.start.setVisible(ctype == "TIME_RANGE")
        self.end.setVisible(ctype == "TIME_RANGE")

    def to_dict(self) -> Dict[str, Any]:
        ctype = str(self.ctype.currentData())
        if ctype == "INPUT_STATE":
            return {
                "type": "INPUT_STATE",
                "input": int(self.input_channel.currentData()),
                "state": bool(self.state.currentData()),
            }
        if ctype == "OUTPUT_STATE":
            return {
                "type": "OUTPUT_STATE",
                "output": int(self.output_channel.currentData()),
                "state": bool(self.state.currentData()),
            }
        return {
            "type": "TIME_RANGE",
            "start": self.start.time().toString("HH:mm"),
            "end": self.end.time().toString("HH:mm"),
        }

    def load_dict(self, payload: Dict[str, Any]) -> None:
        ctype = str(payload.get("type", "INPUT_STATE")).upper()
        idx = self.ctype.findData(ctype)
        if idx >= 0:
            self.ctype.setCurrentIndex(idx)
        if ctype == "INPUT_STATE":
            self._set_combo(self.input_channel, int(payload.get("input", 1)))
            self._set_combo(self.state, bool(payload.get("state", True)))
        elif ctype == "OUTPUT_STATE":
            self._set_combo(self.output_channel, int(payload.get("output", 1)))
            self._set_combo(self.state, bool(payload.get("state", True)))
        elif ctype == "TIME_RANGE":
            self.start.setTime(QTime.fromString(str(payload.get("start", "00:00")), "HH:mm"))
            self.end.setTime(QTime.fromString(str(payload.get("end", "23:59")), "HH:mm"))
        self._refresh_visibility()

    @staticmethod
    def _set_combo(combo: QComboBox, value: Any) -> None:
        idx = combo.findData(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)


class ActionRow(QWidget):
    def __init__(self, output_count: int, io_names: Dict[str, Dict[str, str]]):
        super().__init__()
        self.io_names = io_names

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.atype = QComboBox()
        self.atype.addItem("Ligar saida", "OUTPUT_ON")
        self.atype.addItem("Desligar saida", "OUTPUT_OFF")
        self.atype.addItem("Toggle saida", "OUTPUT_TOGGLE")
        self.atype.addItem("Pulso de saida", "OUTPUT_PULSE")
        self.atype.addItem("Aguardar", "DELAY")

        self.output_channel = QComboBox()
        for channel in range(1, max(1, output_count) + 1):
            self.output_channel.addItem(self._channel_name(channel), channel)

        self.delay_seconds = QDoubleSpinBox()
        self.delay_seconds.setRange(0.1, 3600.0)
        self.delay_seconds.setSingleStep(0.1)
        self.delay_seconds.setSuffix(" s")
        self.delay_seconds.setValue(1.0)

        self.pulse_t_on = QSpinBox()
        self.pulse_t_on.setRange(1, 600000)
        self.pulse_t_on.setSuffix(" x10ms (t_on)")
        self.pulse_t_on.setValue(100)

        self.pulse_total = QSpinBox()
        self.pulse_total.setRange(1, 600000)
        self.pulse_total.setSuffix(" x10ms (total)")
        self.pulse_total.setValue(100)

        self.remove_btn = QPushButton("Remover")
        self.remove_btn.setMaximumWidth(90)

        layout.addWidget(self.atype)
        layout.addWidget(self.output_channel)
        layout.addWidget(self.delay_seconds)
        layout.addWidget(self.pulse_t_on)
        layout.addWidget(self.pulse_total)
        layout.addWidget(self.remove_btn)

        self.atype.currentIndexChanged.connect(self._refresh_visibility)
        self._refresh_visibility()

    def _channel_name(self, channel: int) -> str:
        names = self.io_names.get("outputs", {})
        custom = str(names.get(str(channel), "")).strip()
        if custom:
            return f"Saida {channel:02d} ({custom})"
        return f"Saida {channel:02d}"

    def _refresh_visibility(self) -> None:
        atype = str(self.atype.currentData())
        is_delay = atype == "DELAY"
        is_pulse = atype == "OUTPUT_PULSE"
        self.output_channel.setVisible(not is_delay)
        self.delay_seconds.setVisible(is_delay)
        self.pulse_t_on.setVisible(is_pulse)
        self.pulse_total.setVisible(is_pulse)

    def to_dict(self) -> Dict[str, Any]:
        atype = str(self.atype.currentData())
        if atype == "DELAY":
            return {"type": "DELAY", "seconds": float(self.delay_seconds.value())}
        if atype == "OUTPUT_PULSE":
            return {
                "type": "OUTPUT_PULSE",
                "output": int(self.output_channel.currentData()),
                "t_on": int(self.pulse_t_on.value()),
                "total_time": int(self.pulse_total.value()),
            }
        return {
            "type": atype,
            "output": int(self.output_channel.currentData()),
        }

    def load_dict(self, payload: Dict[str, Any]) -> None:
        atype = str(payload.get("type", "OUTPUT_ON")).upper()
        idx = self.atype.findData(atype)
        if idx >= 0:
            self.atype.setCurrentIndex(idx)

        self._set_combo(self.output_channel, int(payload.get("output", 1)))
        self.delay_seconds.setValue(float(payload.get("seconds", 1.0)))
        self.pulse_t_on.setValue(int(payload.get("t_on", 100)))
        self.pulse_total.setValue(int(payload.get("total_time", 100)))
        self._refresh_visibility()

    @staticmethod
    def _set_combo(combo: QComboBox, value: Any) -> None:
        idx = combo.findData(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)


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
        self.resize(900, 640)
        self.rule = rule or {}
        self.input_count = max(1, input_count)
        self.output_count = max(1, output_count)
        self.io_names = io_names or {"inputs": {}, "outputs": {}}
        self.condition_rows: List[ConditionRow] = []
        self.action_rows: List[ActionRow] = []

        root = QVBoxLayout(self)

        top_form = QFormLayout()
        self.name_input = QLineEdit(str(self.rule.get("name", "")))
        top_form.addRow("Nome da regra", self.name_input)
        root.addLayout(top_form)

        self.when_group = self._build_when_group()
        self.conditions_group = self._build_conditions_group()
        self.actions_group = self._build_actions_group()

        root.addWidget(self.when_group)
        root.addWidget(self.conditions_group)
        root.addWidget(self.actions_group)

        buttons = QHBoxLayout()
        save_btn = QPushButton("Salvar")
        cancel_btn = QPushButton("Cancelar")
        save_btn.clicked.connect(self._on_save_clicked)
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        root.addLayout(buttons)

        self._load_rule()
        self._refresh_trigger_visibility()

    def _build_when_group(self) -> QGroupBox:
        group = QGroupBox("QUANDO")
        form = QFormLayout(group)

        self.trigger_type = QComboBox()
        self.trigger_type.addItem("Mudanca de entrada", "INPUT_CHANGE")
        self.trigger_type.addItem("Entrada ON", "INPUT_ON")
        self.trigger_type.addItem("Entrada OFF", "INPUT_OFF")
        self.trigger_type.addItem("Temporizador", "TIMER")
        self.trigger_type.addItem("Agendado", "SCHEDULE")

        self.trigger_input = QComboBox()
        for channel in range(1, self.input_count + 1):
            label = self._channel_name("inputs", channel)
            self.trigger_input.addItem(label, channel)

        self.trigger_timer = QDoubleSpinBox()
        self.trigger_timer.setRange(0.5, 86400.0)
        self.trigger_timer.setSingleStep(0.5)
        self.trigger_timer.setSuffix(" s")
        self.trigger_timer.setValue(5.0)

        self.trigger_schedule = QTimeEdit()
        self.trigger_schedule.setDisplayFormat("HH:mm")
        self.trigger_schedule.setTime(QTime(6, 0))

        form.addRow("Tipo de gatilho", self.trigger_type)
        form.addRow("Entrada", self.trigger_input)
        form.addRow("Intervalo", self.trigger_timer)
        form.addRow("Horario", self.trigger_schedule)

        self.trigger_type.currentIndexChanged.connect(self._refresh_trigger_visibility)
        return group

    def _build_conditions_group(self) -> QGroupBox:
        group = QGroupBox("SE")
        layout = QVBoxLayout(group)
        layout.addWidget(QLabel("Condições adicionais"))

        self.conditions_holder = QWidget()
        self.conditions_layout = QVBoxLayout(self.conditions_holder)
        self.conditions_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.conditions_holder)

        add_btn = QPushButton("Adicionar condicao")
        add_btn.clicked.connect(lambda: self._add_condition_row())
        layout.addWidget(add_btn)
        return group

    def _build_actions_group(self) -> QGroupBox:
        group = QGroupBox("ENTÃO")
        layout = QVBoxLayout(group)

        self.actions_holder = QWidget()
        self.actions_layout = QVBoxLayout(self.actions_holder)
        self.actions_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.actions_holder)

        add_btn = QPushButton("Adicionar acao")
        add_btn.clicked.connect(lambda: self._add_action_row())
        layout.addWidget(add_btn)
        return group

    def _load_rule(self) -> None:
        trigger = dict(self.rule.get("trigger", {}))
        ttype = str(trigger.get("type", "INPUT_CHANGE")).upper()
        self._set_combo(self.trigger_type, ttype)
        self._set_combo(self.trigger_input, int(trigger.get("input", 1)))
        self.trigger_timer.setValue(float(trigger.get("interval_seconds", 5.0)))
        self.trigger_schedule.setTime(
            QTime.fromString(str(trigger.get("at", "06:00")), "HH:mm")
        )

        for condition in list(self.rule.get("conditions", [])):
            self._add_condition_row(condition)

        for action in list(self.rule.get("actions", [])):
            self._add_action_row(action)

    def _add_condition_row(self, payload: Optional[Dict[str, Any]] = None) -> None:
        row = ConditionRow(self.input_count, self.output_count, self.io_names)
        if payload:
            row.load_dict(payload)
        row.remove_btn.clicked.connect(lambda: self._remove_condition_row(row))
        self.condition_rows.append(row)
        self.conditions_layout.addWidget(row)

    def _remove_condition_row(self, row: ConditionRow) -> None:
        self.condition_rows.remove(row)
        row.setParent(None)
        row.deleteLater()

    def _add_action_row(self, payload: Optional[Dict[str, Any]] = None) -> None:
        row = ActionRow(self.output_count, self.io_names)
        if payload:
            row.load_dict(payload)
        row.remove_btn.clicked.connect(lambda: self._remove_action_row(row))
        self.action_rows.append(row)
        self.actions_layout.addWidget(row)

    def _remove_action_row(self, row: ActionRow) -> None:
        self.action_rows.remove(row)
        row.setParent(None)
        row.deleteLater()

    def _on_save_clicked(self) -> None:
        if not self.action_rows:
            QMessageBox.information(self, "Ação obrigatória", "Adicione ao menos uma ação em ENTÃO.")
            return
        self.accept()

    def _refresh_trigger_visibility(self) -> None:
        ttype = str(self.trigger_type.currentData())
        self.trigger_input.setVisible(ttype in {"INPUT_CHANGE", "INPUT_ON", "INPUT_OFF"})
        self.trigger_timer.setVisible(ttype == "TIMER")
        self.trigger_schedule.setVisible(ttype == "SCHEDULE")

    def _channel_name(self, kind: str, channel: int) -> str:
        names = self.io_names.get(kind, {})
        custom = str(names.get(str(channel), "")).strip()
        prefix = "Entrada" if kind == "inputs" else "Saida"
        if custom:
            return f"{prefix} {channel:02d} ({custom})"
        return f"{prefix} {channel:02d}"

    @staticmethod
    def _set_combo(combo: QComboBox, value: Any) -> None:
        idx = combo.findData(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def get_rule_data(self) -> Dict[str, Any]:
        trigger_type = str(self.trigger_type.currentData())
        trigger: Dict[str, Any] = {"type": trigger_type}
        if trigger_type in {"INPUT_CHANGE", "INPUT_ON", "INPUT_OFF"}:
            trigger["input"] = int(self.trigger_input.currentData())
        elif trigger_type == "TIMER":
            trigger["interval_seconds"] = float(self.trigger_timer.value())
        elif trigger_type == "SCHEDULE":
            trigger["at"] = self.trigger_schedule.time().toString("HH:mm")

        return {
            "name": self.name_input.text().strip() or "Regra sem nome",
            "trigger": trigger,
            "conditions": [row.to_dict() for row in self.condition_rows],
            "actions": [row.to_dict() for row in self.action_rows],
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
        self._build_ui()
        self.load_rules()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Nome", "Gatilho", "Condicoes", "Acoes", "Ativa"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        buttons = QHBoxLayout()
        for label, callback in [
            ("Adicionar regra", self.add_rule),
            ("Editar regra", self.edit_rule),
            ("Excluir regra", self.delete_rule),
            ("Ativar", lambda: self.set_enabled(True)),
            ("Desativar", lambda: self.set_enabled(False)),
            ("Sincronizar", self.load_rules),
        ]:
            btn = QPushButton(label)
            btn.clicked.connect(callback)
            buttons.addWidget(btn)
        layout.addLayout(buttons)

        self.status = QLabel("")
        layout.addWidget(self.status)

    def update_io_context(self, io_names: Dict[str, Dict[str, str]]) -> None:
        self.io_names = {
            "inputs": dict(io_names.get("inputs", {})),
            "outputs": dict(io_names.get("outputs", {})),
        }
        self.load_rules()

    def _api_get_rules(self) -> List[Dict[str, Any]]:
        try:
            return list(_http_json("GET", f"{self.api_base_url}/rules").get("rules", []))
        except Exception:
            return list(_http_json("GET", f"{self.api_base_url}/automation/rules").get("rules", []))

    def _api_create_rule(self, payload: Dict[str, Any]) -> None:
        try:
            _http_json("POST", f"{self.api_base_url}/rules", payload)
        except Exception:
            _http_json("POST", f"{self.api_base_url}/automation/rules", payload)

    def _api_update_rule(self, rule_id: int, payload: Dict[str, Any]) -> None:
        try:
            _http_json("PUT", f"{self.api_base_url}/rules/{rule_id}", payload)
        except Exception:
            _http_json("PUT", f"{self.api_base_url}/automation/rules/{rule_id}", payload)

    def _api_delete_rule(self, rule_id: int) -> None:
        try:
            _http_json("DELETE", f"{self.api_base_url}/rules/{rule_id}")
        except Exception:
            _http_json("DELETE", f"{self.api_base_url}/automation/rules/{rule_id}")

    def _api_set_enabled(self, rule_id: int, enabled: bool) -> None:
        suffix = "enable" if enabled else "disable"
        try:
            _http_json("POST", f"{self.api_base_url}/rules/{rule_id}/{suffix}")
        except Exception:
            _http_json("PUT", f"{self.api_base_url}/automation/rules/{rule_id}/{suffix}")

    def _selected_rule_id(self) -> Optional[int]:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        return int(item.data(Qt.ItemDataRole.UserRole))

    def _describe_trigger(self, trigger: Dict[str, Any]) -> str:
        ttype = str(trigger.get("type", "")).upper()
        if ttype in {"INPUT_CHANGE", "INPUT_ON", "INPUT_OFF"}:
            state = {"INPUT_CHANGE": "mudou", "INPUT_ON": "ON", "INPUT_OFF": "OFF"}[ttype]
            return f"Entrada {trigger.get('input', '?')} {state}"
        if ttype == "TIMER":
            return f"A cada {trigger.get('interval_seconds', 0)}s"
        if ttype == "SCHEDULE":
            return f"Horario {trigger.get('at', '--:--')}"
        return "N/D"

    def _describe_conditions(self, conditions: List[Dict[str, Any]]) -> str:
        if not conditions:
            return "Sem condicoes"
        parts: List[str] = []
        for condition in conditions:
            ctype = str(condition.get("type", "")).upper()
            if ctype == "INPUT_STATE":
                state = "ON" if bool(condition.get("state", False)) else "OFF"
                parts.append(f"E{condition.get('input', '?')}={state}")
            elif ctype == "OUTPUT_STATE":
                state = "ON" if bool(condition.get("state", False)) else "OFF"
                parts.append(f"S{condition.get('output', '?')}={state}")
            elif ctype == "TIME_RANGE":
                parts.append(f"{condition.get('start', '--:--')}-{condition.get('end', '--:--')}")
        return " | ".join(parts) if parts else "Sem condicoes"

    def _describe_actions(self, actions: List[Dict[str, Any]]) -> str:
        if not actions:
            return "Sem acoes"
        parts: List[str] = []
        for action in actions:
            atype = str(action.get("type", "")).upper()
            if atype == "DELAY":
                parts.append(f"DELAY {action.get('seconds', 0)}s")
            elif atype == "OUTPUT_PULSE":
                parts.append(
                    f"PULSE S{action.get('output', '?')} (t_on={action.get('t_on', 0)}, total={action.get('total_time', 0)})"
                )
            elif atype in {"OUTPUT_ON", "OUTPUT_OFF", "OUTPUT_TOGGLE"}:
                parts.append(f"{atype} S{action.get('output', '?')}")
        return " -> ".join(parts) if parts else "Sem acoes"

    def load_rules(self) -> None:
        try:
            rules = self._api_get_rules()
        except Exception as exc:
            self.status.setText(f"Falha ao carregar regras: {exc}")
            return

        self.table.setRowCount(len(rules))
        for row, rule in enumerate(rules):
            item = QTableWidgetItem(str(rule.get("name", "")))
            item.setData(Qt.ItemDataRole.UserRole, int(rule.get("id", 0)))
            self.table.setItem(row, 0, item)
            self.table.setItem(row, 1, QTableWidgetItem(self._describe_trigger(dict(rule.get("trigger", {})))))
            self.table.setItem(row, 2, QTableWidgetItem(self._describe_conditions(list(rule.get("conditions", [])))))
            self.table.setItem(row, 3, QTableWidgetItem(self._describe_actions(list(rule.get("actions", [])))))
            self.table.setItem(row, 4, QTableWidgetItem("Sim" if bool(rule.get("enabled", True)) else "Nao"))
        self.status.setText(f"{len(rules)} regra(s) carregada(s)")

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
            self._api_create_rule(payload)
            self.load_rules()
        except Exception as exc:
            QMessageBox.warning(self, "Erro", f"Nao foi possivel adicionar regra: {exc}")

    def edit_rule(self) -> None:
        rule_id = self._selected_rule_id()
        if rule_id is None:
            QMessageBox.information(self, "Selecione", "Selecione uma regra.")
            return
        try:
            rules = self._api_get_rules()
            current = next((rule for rule in rules if int(rule.get("id", -1)) == rule_id), None)
            if current is None:
                raise KeyError("Regra nao encontrada")
        except Exception as exc:
            QMessageBox.warning(self, "Erro", f"Nao foi possivel abrir regra: {exc}")
            return

        payload = self._open_editor(current)
        if payload is None:
            return
        payload["enabled"] = bool(current.get("enabled", True))
        try:
            self._api_update_rule(rule_id, payload)
            self.load_rules()
        except Exception as exc:
            QMessageBox.warning(self, "Erro", f"Nao foi possivel salvar regra: {exc}")

    def delete_rule(self) -> None:
        rule_id = self._selected_rule_id()
        if rule_id is None:
            QMessageBox.information(self, "Selecione", "Selecione uma regra.")
            return
        try:
            self._api_delete_rule(rule_id)
            self.load_rules()
        except Exception as exc:
            QMessageBox.warning(self, "Erro", f"Nao foi possivel excluir regra: {exc}")

    def set_enabled(self, enabled: bool) -> None:
        rule_id = self._selected_rule_id()
        if rule_id is None:
            QMessageBox.information(self, "Selecione", "Selecione uma regra.")
            return
        try:
            self._api_set_enabled(rule_id, enabled)
            self.load_rules()
        except Exception as exc:
            QMessageBox.warning(self, "Erro", f"Nao foi possivel atualizar regra: {exc}")
