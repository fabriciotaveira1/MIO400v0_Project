from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class AutomationRule:
    id: int
    name: str
    trigger: Dict[str, Any]
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    actions: List[Dict[str, Any]] = field(default_factory=list)
    enabled: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AutomationRule":
        return cls(
            id=int(data.get("id", 0)),
            name=str(data.get("name", "Unnamed Rule")),
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
