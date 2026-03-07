from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.automation.storage import rules_storage
from app.core.opcodes.output import build_output_command
from app.services.device_manager import device_manager
from app.services.state_instance import state_manager


def _upper(value: Any, default: str = "") -> str:
    text = str(value or default).strip()
    return text.upper()


@dataclass
class Rule:
    id: int
    name: str
    trigger: Dict[str, Any]
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    actions: List[Dict[str, Any]] = field(default_factory=list)
    enabled: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Rule":
        return cls(
            id=int(data.get("id", 0)),
            name=str(data.get("name", "Regra sem nome")),
            trigger=dict(data.get("trigger", {})),
            conditions=list(data.get("conditions", [])),
            actions=list(data.get("actions", [])),
            enabled=bool(data.get("enabled", True)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "trigger": self.trigger,
            "conditions": self.conditions,
            "actions": self.actions,
            "enabled": self.enabled,
        }


class RuleEngine:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._rules: List[Rule] = []
        self._next_id = 1
        self._running = True

        self._last_schedule_fire: Dict[int, str] = {}
        self._last_timer_fire: Dict[int, float] = {}
        self._reconcile_queue: List[Dict[str, Any]] = []

        self._load()
        self._thread = threading.Thread(target=self._scan_loop, daemon=True)
        self._thread.start()

    def _load(self) -> None:
        payload = rules_storage.read()
        loaded = [
            self._normalize_rule(Rule.from_dict(raw).to_dict())
            for raw in payload.get("rules", [])
        ]
        with self._lock:
            self._rules = [Rule.from_dict(item) for item in loaded]
            self._next_id = max((rule.id for rule in self._rules), default=0) + 1

    def _save(self) -> None:
        rules_storage.write({"rules": [rule.to_dict() for rule in self._rules]})

    def stop(self) -> None:
        self._running = False

    def list_rules(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [rule.to_dict() for rule in self._rules]

    def get_rule(self, rule_id: int) -> Optional[Dict[str, Any]]:
        with self._lock:
            for rule in self._rules:
                if rule.id == rule_id:
                    return rule.to_dict()
        return None

    def create_rule(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        normalized = self._normalize_rule(payload)
        with self._lock:
            rule = Rule.from_dict(normalized)
            rule.id = self._next_id
            self._next_id += 1
            self._rules.append(rule)
            self._save()
            return rule.to_dict()

    def update_rule(self, rule_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        normalized = self._normalize_rule(payload)
        with self._lock:
            for index, existing in enumerate(self._rules):
                if existing.id != rule_id:
                    continue
                updated = Rule.from_dict(normalized)
                updated.id = rule_id
                self._rules[index] = updated
                self._save()
                return updated.to_dict()
        raise KeyError(f"Rule {rule_id} not found")

    def delete_rule(self, rule_id: int) -> None:
        with self._lock:
            before = len(self._rules)
            self._rules = [rule for rule in self._rules if rule.id != rule_id]
            if len(self._rules) == before:
                raise KeyError(f"Rule {rule_id} not found")
            self._save()

    def set_rule_enabled(self, rule_id: int, enabled: bool) -> Dict[str, Any]:
        with self._lock:
            for rule in self._rules:
                if rule.id != rule_id:
                    continue
                rule.enabled = enabled
                self._save()
                return rule.to_dict()
        raise KeyError(f"Rule {rule_id} not found")

    def process_input_event(
        self,
        input_id: int,
        current_state: bool,
        previous_state: Optional[bool] = None,
    ) -> None:
        context = {
            "source": "input_event",
            "input": int(input_id),
            "current_state": bool(current_state),
            "previous_state": previous_state,
            "now": datetime.now(),
        }
        self._evaluate_rules(context)

    def _scan_loop(self) -> None:
        while self._running:
            self._evaluate_rules({"source": "scan", "now": datetime.now()})
            self._process_reconcile_queue()
            time.sleep(0.5)

    def _evaluate_rules(self, context: Dict[str, Any]) -> None:
        with self._lock:
            snapshot = [rule.to_dict() for rule in self._rules if rule.enabled]

        for rule in snapshot:
            if not self._trigger_matches(rule, context):
                continue
            if not self._evaluate_conditions(rule.get("conditions", []), context):
                continue
            thread = threading.Thread(
                target=self._execute_rule,
                args=(rule, context),
                daemon=True,
            )
            thread.start()

    def _execute_rule(self, rule: Dict[str, Any], context: Dict[str, Any]) -> None:
        started_at = datetime.now()
        success = self._execute_actions_sequential(list(rule.get("actions", [])))
        duration_ms = int((datetime.now() - started_at).total_seconds() * 1000)
        entry = {
            "timestamp": started_at.isoformat(timespec="seconds"),
            "rule_id": int(rule.get("id", 0)),
            "rule_name": str(rule.get("name", "")),
            "source": str(context.get("source", "")),
            "trigger": dict(rule.get("trigger", {})),
            "success": bool(success),
            "duration_ms": duration_ms,
        }
        print(f"[RULE_ENGINE] {json.dumps(entry, ensure_ascii=True)}")

    def _trigger_matches(self, rule: Dict[str, Any], context: Dict[str, Any]) -> bool:
        trigger = dict(rule.get("trigger", {}))
        trigger_type = _upper(trigger.get("type"), "INPUT_CHANGE")
        source = str(context.get("source", ""))
        now = context.get("now", datetime.now())
        rule_id = int(rule.get("id", 0))

        if trigger_type in {"INPUT_CHANGE", "INPUT_ON", "INPUT_OFF"}:
            if source != "input_event":
                return False
            input_channel = int(trigger.get("input", 0))
            if input_channel <= 0 or int(context.get("input", 0)) != input_channel:
                return False
            current_state = bool(context.get("current_state", False))
            previous_state = context.get("previous_state")
            if previous_state is None or bool(previous_state) == current_state:
                return False
            if trigger_type == "INPUT_ON":
                return current_state is True
            if trigger_type == "INPUT_OFF":
                return current_state is False
            return True

        if trigger_type == "TIMER":
            interval = float(trigger.get("interval_seconds", trigger.get("seconds", 0)))
            if interval <= 0:
                return False
            current_ts = now.timestamp()
            last_ts = self._last_timer_fire.get(rule_id)
            if last_ts is None:
                self._last_timer_fire[rule_id] = current_ts
                return False
            if current_ts - last_ts < interval:
                return False
            self._last_timer_fire[rule_id] = current_ts
            return True

        if trigger_type == "SCHEDULE":
            at = str(trigger.get("at", trigger.get("schedule", ""))).strip()
            if not at:
                return False
            key = now.strftime("%Y-%m-%d")
            if now.strftime("%H:%M") != at:
                return False
            if self._last_schedule_fire.get(rule_id) == key:
                return False
            self._last_schedule_fire[rule_id] = key
            return True

        return False

    def _evaluate_conditions(self, conditions: List[Dict[str, Any]], context: Dict[str, Any]) -> bool:
        for condition in conditions:
            if not self._evaluate_condition(condition, context):
                return False
        return True

    def _evaluate_condition(self, condition: Dict[str, Any], context: Dict[str, Any]) -> bool:
        condition_type = _upper(condition.get("type"))
        now = context.get("now", datetime.now())

        if condition_type == "INPUT_STATE":
            channel = int(condition.get("input", 0))
            expected = bool(condition.get("state", False))
            if channel <= 0:
                return False
            return bool(state_manager.get_inputs_mask() & (1 << (channel - 1))) == expected

        if condition_type == "OUTPUT_STATE":
            channel = int(condition.get("output", 0))
            expected = bool(condition.get("state", False))
            if channel <= 0:
                return False
            return bool(state_manager.get_outputs_mask() & (1 << (channel - 1))) == expected

        if condition_type == "TIME_RANGE":
            start = self._parse_hhmm(str(condition.get("start", "00:00")))
            end = self._parse_hhmm(str(condition.get("end", "23:59")))
            if start is None or end is None:
                return False
            current = now.time()
            if start <= end:
                return start <= current <= end
            return current >= start or current <= end

        return True

    def _execute_actions_sequential(self, actions: List[Dict[str, Any]]) -> bool:
        success = True
        for action in actions:
            action_type = _upper(action.get("type"))
            if action_type == "DELAY":
                delay_seconds = float(
                    action.get("seconds", action.get("duration_s", action.get("duration_seconds", 0)))
                )
                if delay_seconds > 0:
                    time.sleep(delay_seconds)
                continue

            output = int(action.get("output", 0))
            if output <= 0:
                success = False
                continue

            if action_type == "OUTPUT_ON":
                ok = self._send_output_with_retry(output=output, action=1, expected_state=True)
                success = success and ok
                if not ok:
                    self._enqueue_reconcile(output=output, action=1, expected_state=True)
                continue
            if action_type == "OUTPUT_OFF":
                ok = self._send_output_with_retry(output=output, action=0, expected_state=False)
                success = success and ok
                if not ok:
                    self._enqueue_reconcile(output=output, action=0, expected_state=False)
                continue
            if action_type == "OUTPUT_TOGGLE":
                ok = self._send_output_with_retry(output=output, action=2, expected_state=None)
                success = success and ok
                continue
            if action_type == "OUTPUT_PULSE":
                t_on = int(action.get("t_on", 0))
                total_time = int(action.get("total_time", 0))
                t_off = max(0, total_time - t_on) if total_time > 0 else 0
                ok = self._send_output_with_retry(
                    output,
                    action=1,
                    total_time=total_time,
                    t_on=t_on,
                    t_off=t_off,
                    expected_state=None,
                )
                success = success and ok
                continue

            success = False

        return success

    def _send_output_with_retry(
        self,
        output: int,
        action: int,
        total_time: int = 0,
        t_on: int = 0,
        t_off: int = 0,
        expected_state: Optional[bool] = None,
        max_attempts: int = 3,
    ) -> bool:
        backoff = [0.1, 0.2, 0.4]
        for attempt in range(max_attempts):
            response = self._send_output(
                output=output,
                action=action,
                total_time=total_time,
                t_on=t_on,
                t_off=t_off,
            )
            status = str(response.get("status", ""))
            if status == "ack":
                if expected_state is None or self._verify_output_state(output, expected_state):
                    return True

            if attempt < max_attempts - 1:
                time.sleep(backoff[min(attempt, len(backoff) - 1)])

        return False

    def _send_output(
        self,
        output: int,
        action: int,
        total_time: int = 0,
        t_on: int = 0,
        t_off: int = 0,
    ) -> Dict[str, Any]:
        try:
            client = device_manager.get_client()
        except RuntimeError:
            return {"status": "error", "message": "device_not_configured"}

        payload = build_output_command(
            component_addr=output,
            action=action,
            total_time=total_time,
            t_on=t_on,
            t_off=t_off,
            memory=0,
        )
        return client.send(opcode=1, application_data=payload)

    def _verify_output_state(self, output: int, expected_state: bool, attempts: int = 2) -> bool:
        try:
            client = device_manager.get_client()
        except RuntimeError:
            return False

        for _ in range(attempts):
            response = client.send(opcode=2, application_data=b"")
            if response.get("status") == "data":
                mask = int(response.get("value", 0))
                current = bool(mask & (1 << (output - 1)))
                if current == expected_state:
                    return True
            time.sleep(0.08)
        return False

    def _enqueue_reconcile(self, output: int, action: int, expected_state: Optional[bool]) -> None:
        with self._lock:
            self._reconcile_queue.append(
                {
                    "output": output,
                    "action": action,
                    "expected_state": expected_state,
                    "attempts": 0,
                    "next_run_ts": time.time() + 0.5,
                }
            )

    def _process_reconcile_queue(self) -> None:
        now = time.time()
        with self._lock:
            queue = list(self._reconcile_queue)
            self._reconcile_queue = []

        pending: List[Dict[str, Any]] = []
        for item in queue:
            if float(item.get("next_run_ts", 0)) > now:
                pending.append(item)
                continue

            ok = self._send_output_with_retry(
                output=int(item.get("output", 0)),
                action=int(item.get("action", 0)),
                expected_state=item.get("expected_state"),
                max_attempts=1,
            )
            if ok:
                continue

            attempts = int(item.get("attempts", 0)) + 1
            if attempts >= 8:
                continue

            item["attempts"] = attempts
            item["next_run_ts"] = now + min(4.0, 0.5 * (2 ** attempts))
            pending.append(item)

        with self._lock:
            self._reconcile_queue.extend(pending)

    def _normalize_rule(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        trigger = self._normalize_trigger(dict(payload.get("trigger", {})))
        conditions = [self._normalize_condition(c) for c in list(payload.get("conditions", []))]
        actions = [self._normalize_action(a) for a in list(payload.get("actions", []))]
        conditions = [c for c in conditions if c is not None]
        actions = [a for a in actions if a is not None]

        return {
            "id": int(payload.get("id", 0)),
            "name": str(payload.get("name", "Regra sem nome")),
            "trigger": trigger,
            "conditions": conditions,
            "actions": actions,
            "enabled": bool(payload.get("enabled", True)),
        }

    def _normalize_trigger(self, trigger: Dict[str, Any]) -> Dict[str, Any]:
        trigger_type = _upper(trigger.get("type"), "INPUT_CHANGE")
        legacy = trigger_type.lower()

        if legacy == "event":
            state = bool(trigger.get("state", True))
            trigger_type = "INPUT_ON" if state else "INPUT_OFF"
        elif legacy in {"while", "state"}:
            state = bool(trigger.get("state", True))
            trigger_type = "INPUT_ON" if state else "INPUT_OFF"
        elif legacy == "time":
            trigger_type = "SCHEDULE"

        normalized: Dict[str, Any] = {"type": trigger_type}
        if trigger_type in {"INPUT_CHANGE", "INPUT_ON", "INPUT_OFF"}:
            normalized["input"] = int(trigger.get("input", 1))
        if trigger_type == "TIMER":
            normalized["interval_seconds"] = float(
                trigger.get("interval_seconds", trigger.get("seconds", 1))
            )
        if trigger_type == "SCHEDULE":
            normalized["at"] = str(trigger.get("at", trigger.get("schedule", "00:00")))
        return normalized

    def _normalize_condition(self, condition: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        condition_type = _upper(condition.get("type"))
        legacy = condition_type.lower()

        if legacy == "input":
            return {
                "type": "INPUT_STATE",
                "input": int(condition.get("input", 1)),
                "state": bool(condition.get("state", True)),
            }
        if legacy == "state":
            scope = str(condition.get("scope", "input")).lower()
            if scope == "output":
                return {
                    "type": "OUTPUT_STATE",
                    "output": int(condition.get("channel", 1)),
                    "state": bool(condition.get("state", True)),
                }
            return {
                "type": "INPUT_STATE",
                "input": int(condition.get("channel", 1)),
                "state": bool(condition.get("state", True)),
            }
        if legacy == "time_range":
            return {
                "type": "TIME_RANGE",
                "start": str(condition.get("start", "00:00")),
                "end": str(condition.get("end", "23:59")),
            }
        if condition_type in {"INPUT_STATE", "OUTPUT_STATE", "TIME_RANGE"}:
            normalized = dict(condition)
            normalized["type"] = condition_type
            return normalized
        return None

    def _normalize_action(self, action: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        action_type = _upper(action.get("type"))
        legacy = action_type.lower()

        if legacy == "delay":
            delay_ms = int(action.get("duration_ms", action.get("delay_ms", 0)))
            return {"type": "DELAY", "seconds": max(0.0, delay_ms / 1000.0)}

        if legacy == "output":
            action_name = _upper(action.get("action"), "ON")
            output = int(action.get("output", action.get("channel", 0)))
            duration_ms = int(action.get("duration_ms", 0))
            if action_name == "ON" and duration_ms > 0:
                ticks = max(1, duration_ms // 10)
                return {
                    "type": "OUTPUT_PULSE",
                    "output": output,
                    "t_on": ticks,
                    "total_time": ticks,
                }
            if action_name == "ON":
                return {"type": "OUTPUT_ON", "output": output}
            if action_name == "OFF":
                return {"type": "OUTPUT_OFF", "output": output}
            return {"type": "OUTPUT_TOGGLE", "output": output}

        if legacy == "timer":
            output = int(action.get("output", 0))
            duration_ms = int(action.get("duration_ms", 0))
            return {
                "type": "OUTPUT_PULSE",
                "output": output,
                "t_on": duration_ms // 10,
                "total_time": duration_ms // 10,
            }

        if action_type in {"OUTPUT_ON", "OUTPUT_OFF", "OUTPUT_TOGGLE", "OUTPUT_PULSE", "DELAY"}:
            normalized = dict(action)
            normalized["type"] = action_type
            return normalized
        return None

    @staticmethod
    def _parse_hhmm(hhmm: str):
        try:
            return datetime.strptime(hhmm, "%H:%M").time()
        except ValueError:
            return None


rule_engine = RuleEngine()
