from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from app.automation.storage import io_names_storage
from app.models.schema import RulePayload
from app.services.rule_engine import rule_engine

router = APIRouter()


@router.get("/automation/rules")
def list_automation_rules():
    return {"rules": rule_engine.list_rules()}


@router.post("/automation/rules")
def create_automation_rule(rule: RulePayload):
    created = rule_engine.create_rule(rule.model_dump(exclude_none=True))
    return {"rule": created}


@router.put("/automation/rules/{rule_id}")
def update_automation_rule(rule_id: int, rule: RulePayload):
    try:
        updated = rule_engine.update_rule(rule_id, rule.model_dump(exclude_none=True))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"rule": updated}


@router.delete("/automation/rules/{rule_id}")
def delete_automation_rule(rule_id: int):
    try:
        rule_engine.delete_rule(rule_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "deleted"}


@router.put("/automation/rules/{rule_id}/enable")
def enable_automation_rule(rule_id: int):
    try:
        updated = rule_engine.set_rule_enabled(rule_id, True)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"rule": updated}


@router.put("/automation/rules/{rule_id}/disable")
def disable_automation_rule(rule_id: int):
    try:
        updated = rule_engine.set_rule_enabled(rule_id, False)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"rule": updated}


@router.get("/io/names")
def get_io_names():
    data = io_names_storage.read()
    return {
        "inputs": dict(data.get("inputs", {})),
        "outputs": dict(data.get("outputs", {})),
    }


@router.post("/io/names")
def set_io_names(payload: Dict[str, Any]):
    current = io_names_storage.read()
    current["inputs"] = dict(current.get("inputs", {}))
    current["outputs"] = dict(current.get("outputs", {}))
    current["inputs"].update(
        {str(k): str(v) for k, v in dict(payload.get("inputs", {})).items()}
    )
    current["outputs"].update(
        {str(k): str(v) for k, v in dict(payload.get("outputs", {})).items()}
    )
    io_names_storage.write(current)
    return current
