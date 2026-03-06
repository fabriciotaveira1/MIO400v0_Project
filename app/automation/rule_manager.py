from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from app.automation.rule_model import AutomationRule
from app.automation.storage import io_names_storage, rules_storage


class RuleManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._rules: List[AutomationRule] = []
        self._next_id = 1
        self._load()

    def _load(self) -> None:
        data = rules_storage.read()
        with self._lock:
            self._rules = [AutomationRule.from_dict(r) for r in data.get("rules", [])]
            self._next_id = (
                max((rule.id for rule in self._rules), default=0) + 1
            )

    def _save(self) -> None:
        rules_storage.write({"rules": [rule.to_dict() for rule in self._rules]})

    def list_rules(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [rule.to_dict() for rule in self._rules]

    def get_rule(self, rule_id: int) -> Optional[AutomationRule]:
        with self._lock:
            for rule in self._rules:
                if rule.id == rule_id:
                    return AutomationRule.from_dict(rule.to_dict())
        return None

    def create_rule(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            rule = AutomationRule.from_dict(payload)
            rule.id = self._next_id
            self._next_id += 1
            self._rules.append(rule)
            self._save()
            return rule.to_dict()

    def update_rule(self, rule_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            for idx, existing in enumerate(self._rules):
                if existing.id == rule_id:
                    updated = AutomationRule.from_dict(payload)
                    updated.id = rule_id
                    self._rules[idx] = updated
                    self._save()
                    return updated.to_dict()
        raise KeyError(f"Rule {rule_id} not found")

    def delete_rule(self, rule_id: int) -> None:
        with self._lock:
            before = len(self._rules)
            self._rules = [r for r in self._rules if r.id != rule_id]
            if len(self._rules) == before:
                raise KeyError(f"Rule {rule_id} not found")
            self._save()

    def set_rule_enabled(self, rule_id: int, enabled: bool) -> Dict[str, Any]:
        with self._lock:
            for rule in self._rules:
                if rule.id == rule_id:
                    rule.enabled = enabled
                    self._save()
                    return rule.to_dict()
        raise KeyError(f"Rule {rule_id} not found")

    def get_io_names(self) -> Dict[str, Dict[str, str]]:
        data = io_names_storage.read()
        return {
            "inputs": dict(data.get("inputs", {})),
            "outputs": dict(data.get("outputs", {})),
        }

    def set_io_names(self, names: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
        current = self.get_io_names()
        current["inputs"].update(
            {str(k): str(v) for k, v in dict(names.get("inputs", {})).items()}
        )
        current["outputs"].update(
            {str(k): str(v) for k, v in dict(names.get("outputs", {})).items()}
        )
        io_names_storage.write(current)
        return current


rule_manager = RuleManager()
