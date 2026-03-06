from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from app.automation.rule_manager import rule_manager

router = APIRouter()


@router.get("/automation/rules")
def list_automation_rules():
    return {"rules": rule_manager.list_rules()}


@router.post("/automation/rules")
def create_automation_rule(rule: Dict[str, Any]):
    created = rule_manager.create_rule(rule)
    return {"rule": created}


@router.put("/automation/rules/{rule_id}")
def update_automation_rule(rule_id: int, rule: Dict[str, Any]):
    try:
        updated = rule_manager.update_rule(rule_id, rule)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"rule": updated}


@router.delete("/automation/rules/{rule_id}")
def delete_automation_rule(rule_id: int):
    try:
        rule_manager.delete_rule(rule_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "deleted"}


@router.put("/automation/rules/{rule_id}/enable")
def enable_automation_rule(rule_id: int):
    try:
        updated = rule_manager.set_rule_enabled(rule_id, True)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"rule": updated}


@router.put("/automation/rules/{rule_id}/disable")
def disable_automation_rule(rule_id: int):
    try:
        updated = rule_manager.set_rule_enabled(rule_id, False)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"rule": updated}


@router.get("/io/names")
def get_io_names():
    return rule_manager.get_io_names()


@router.post("/io/names")
def set_io_names(payload: Dict[str, Any]):
    return rule_manager.set_io_names(payload)
