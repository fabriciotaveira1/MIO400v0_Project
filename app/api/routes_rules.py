from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from app.models.schema import RulePayload
from app.services.rule_engine import rule_engine

router = APIRouter()


@router.get("/rules")
def list_rules():
    return {"rules": rule_engine.list_rules()}


@router.post("/rules")
def create_rule(rule: RulePayload):
    created = rule_engine.create_rule(rule.model_dump(exclude_none=True))
    return {"rule": created}


@router.put("/rules/{rule_id}")
def update_rule(rule_id: int, rule: RulePayload):
    try:
        updated = rule_engine.update_rule(rule_id, rule.model_dump(exclude_none=True))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"rule": updated}


@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: int):
    try:
        rule_engine.delete_rule(rule_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "deleted"}


@router.post("/rules/{rule_id}/enable")
def enable_rule(rule_id: int):
    try:
        updated = rule_engine.set_rule_enabled(rule_id, True)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"rule": updated}


@router.post("/rules/{rule_id}/disable")
def disable_rule(rule_id: int):
    try:
        updated = rule_engine.set_rule_enabled(rule_id, False)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"rule": updated}
