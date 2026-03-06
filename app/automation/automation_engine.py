from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Any, Dict, Optional

from app.automation.action_executor import ActionExecutor
from app.automation.condition_evaluator import ConditionEvaluator
from app.automation.rule_manager import rule_manager
from app.automation.timer_engine import TimerEngine
from app.services.state_instance import state_manager


class AutomationEngine:
    def __init__(self):
        self.rule_manager = rule_manager
        self.timer_engine = TimerEngine()
        self.condition_evaluator = ConditionEvaluator()
        self.action_executor = ActionExecutor(self.timer_engine)

        self._last_input_state: Dict[int, bool] = {}
        self._last_time_fire: Dict[int, str] = {}
        self._while_latch: Dict[int, bool] = {}
        self._running = True

        self._thread = threading.Thread(target=self._background_loop, daemon=True)
        self._thread.start()

    def process_input_event(self, input_id: int, state: bool) -> None:
        previous = self._last_input_state.get(input_id)
        self._last_input_state[input_id] = state

        context = {
            "input_id": input_id,
            "input_state": state,
            "previous_state": previous,
            "now": datetime.now(),
            "source": "event",
        }
        self._evaluate_rules(context)

    def _background_loop(self) -> None:
        while self._running:
            self._evaluate_rules({"now": datetime.now(), "source": "scan"})
            time.sleep(0.5)

    def _evaluate_rules(self, context: Dict[str, Any]) -> None:
        rules = self.rule_manager.list_rules()
        for rule in rules:
            if not bool(rule.get("enabled", True)):
                continue
            if self._trigger_matches(rule, context):
                if self.condition_evaluator.evaluate_all(rule.get("conditions", []), context):
                    execution_context = dict(context)
                    execution_context["rule_id"] = rule.get("id")
                    execution_context["rule_name"] = rule.get("name")
                    self.action_executor.execute_actions(rule.get("actions", []), execution_context)

    def _trigger_matches(self, rule: Dict[str, Any], context: Dict[str, Any]) -> bool:
        trigger = dict(rule.get("trigger", {}))
        ttype = str(trigger.get("type", "event")).lower()

        if ttype == "event":
            return self._match_event_trigger(trigger, context)
        if ttype in {"while", "state"}:
            return self._match_while_trigger(rule, trigger)
        if ttype == "time":
            return self._match_time_trigger(rule, trigger, context)

        return False

    def _match_event_trigger(self, trigger: Dict[str, Any], context: Dict[str, Any]) -> bool:
        if context.get("source") != "event":
            return False
        input_id = int(trigger.get("input", 0))
        desired_state = bool(trigger.get("state", True))
        if input_id <= 0:
            return False
        if context.get("input_id") != input_id:
            return False
        if bool(context.get("input_state")) != desired_state:
            return False
        return context.get("previous_state") != context.get("input_state")

    def _match_while_trigger(self, rule: Dict[str, Any], trigger: Dict[str, Any]) -> bool:
        input_id = int(trigger.get("input", 0))
        desired_state = bool(trigger.get("state", True))
        if input_id <= 0:
            return False
        mask = state_manager.get_inputs_mask()
        current_state = bool(mask & (1 << (input_id - 1)))
        matched = current_state == desired_state

        rule_id = int(rule.get("id", 0))
        was_matched = self._while_latch.get(rule_id, False)
        self._while_latch[rule_id] = matched
        return matched and not was_matched

    def _match_time_trigger(
        self,
        rule: Dict[str, Any],
        trigger: Dict[str, Any],
        context: Dict[str, Any],
    ) -> bool:
        now: datetime = context.get("now", datetime.now())
        schedule = str(trigger.get("schedule", "")).strip()
        if not schedule:
            return False
        current_hm = now.strftime("%H:%M")
        if current_hm != schedule:
            return False

        rule_id = int(rule.get("id", 0))
        current_key = now.strftime("%Y-%m-%d %H:%M")
        if self._last_time_fire.get(rule_id) == current_key:
            return False
        self._last_time_fire[rule_id] = current_key
        return True


automation_engine = AutomationEngine()
