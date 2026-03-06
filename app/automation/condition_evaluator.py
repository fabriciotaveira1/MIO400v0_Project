from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from app.services.state_instance import state_manager


class ConditionEvaluator:
    def evaluate_all(self, conditions: List[Dict[str, Any]], context: Dict[str, Any]) -> bool:
        for condition in conditions:
            if not self.evaluate(condition, context):
                return False
        return True

    def evaluate(self, condition: Dict[str, Any], context: Dict[str, Any]) -> bool:
        ctype = condition.get("type")

        if ctype == "input":
            return self._eval_input(condition)
        if ctype == "state":
            return self._eval_state(condition)
        if ctype == "time_range":
            return self._eval_time_range(condition, context)
        if ctype == "logical":
            return self._eval_logical(condition, context)
        if ctype == "not":
            child = condition.get("condition", {})
            return not self.evaluate(child, context)

        return True

    def _eval_input(self, condition: Dict[str, Any]) -> bool:
        input_id = int(condition.get("input", 0))
        expected = bool(condition.get("state", True))
        if input_id <= 0:
            return False
        mask = state_manager.get_inputs_mask()
        current = bool(mask & (1 << (input_id - 1)))
        return current == expected

    def _eval_state(self, condition: Dict[str, Any]) -> bool:
        scope = str(condition.get("scope", "input")).lower()
        channel = int(condition.get("channel", 0))
        expected = bool(condition.get("state", True))
        if channel <= 0:
            return False
        if scope == "output":
            mask = state_manager.get_outputs_mask()
        else:
            mask = state_manager.get_inputs_mask()
        current = bool(mask & (1 << (channel - 1)))
        return current == expected

    def _eval_time_range(self, condition: Dict[str, Any], context: Dict[str, Any]) -> bool:
        now = context.get("now", datetime.now())
        start = self._parse_time(condition.get("start", "00:00"))
        end = self._parse_time(condition.get("end", "23:59"))
        if start is None or end is None:
            return False
        current = now.time()
        if start <= end:
            return start <= current <= end
        return current >= start or current <= end

    def _eval_logical(self, condition: Dict[str, Any], context: Dict[str, Any]) -> bool:
        operator = str(condition.get("operator", "AND")).upper()
        conditions = list(condition.get("conditions", []))
        if operator == "AND":
            return all(self.evaluate(c, context) for c in conditions)
        if operator == "OR":
            return any(self.evaluate(c, context) for c in conditions)
        if operator == "NOT":
            if not conditions:
                return True
            return not self.evaluate(conditions[0], context)
        return False

    @staticmethod
    def _parse_time(value: str):
        try:
            return datetime.strptime(value, "%H:%M").time()
        except ValueError:
            return None
