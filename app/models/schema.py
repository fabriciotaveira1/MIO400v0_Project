from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CommandRequest(BaseModel):
    component_addr: int = Field(..., description="Output address (example: 1)")
    action: int = Field(..., description="Action: 0=off, 1=on, 2=toggle")
    total_time: int = Field(0, description="Total time in 10ms units")
    memory: int = Field(0, ge=0, le=1, description="1 to persist in NVRAM")


class DeviceConfig(BaseModel):
    device_ip: str
    device_port: int = 5000


class RulePayload(BaseModel):
    id: Optional[int] = None
    name: str
    trigger: Dict[str, Any] = Field(default_factory=dict)
    conditions: List[Dict[str, Any]] = Field(default_factory=list)
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    enabled: bool = True
