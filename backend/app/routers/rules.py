"""
规则管理 API — CRUD 操作 YAML 规则库。
"""

import os
import logging
from typing import Any, Dict, List, Optional

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rules", tags=["rules"])

RULES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "core", "rules.yaml")


def _load_rules() -> Dict[str, Any]:
    if not os.path.isfile(RULES_PATH):
        return {"rules": []}
    with open(RULES_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {"rules": []}


def _save_rules(data: Dict[str, Any]):
    with open(RULES_PATH, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


class RuleCreate(BaseModel):
    name: str
    description: str = ""
    severity: str = "medium"  # high / medium / low
    contract_types: List[str] = ["all"]
    legal_basis: str = ""
    check_type: str = "both"
    check_config: Optional[Dict[str, Any]] = None
    risk_description_template: str = ""


class RuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = None
    contract_types: Optional[List[str]] = None
    legal_basis: Optional[str] = None
    check_type: Optional[str] = None
    check_config: Optional[Dict[str, Any]] = None
    risk_description_template: Optional[str] = None
    enabled: Optional[bool] = None


@router.get(
    "",
    summary="List all rules",
    description="Retrieve all compliance rules from the YAML configuration.",
)
async def list_rules():
    data = _load_rules()
    rules = data.get("rules", [])
    # Add index as id
    for i, rule in enumerate(rules):
        rule["_index"] = i
    return {"rules": rules, "total": len(rules)}


@router.get(
    "/{rule_index}",
    summary="Get a rule",
    description="Get a specific rule by its index.",
)
async def get_rule(rule_index: int):
    data = _load_rules()
    rules = data.get("rules", [])
    if rule_index < 0 or rule_index >= len(rules):
        raise HTTPException(status_code=404, detail="Rule not found")
    rule = rules[rule_index]
    rule["_index"] = rule_index
    return rule


@router.post(
    "",
    summary="Create a rule",
    description="Add a new compliance rule to the YAML configuration.",
)
async def create_rule(req: RuleCreate):
    if req.severity not in ("high", "medium", "low"):
        raise HTTPException(status_code=400, detail="severity must be high/medium/low")
    
    new_rule = {
        "name": req.name,
        "description": req.description,
        "severity": req.severity,
        "contract_types": req.contract_types,
        "legal_basis": req.legal_basis,
        "check_type": req.check_type,
    }
    if req.check_config:
        new_rule["check_config"] = req.check_config
    if req.risk_description_template:
        new_rule["risk_description_template"] = req.risk_description_template
    
    data = _load_rules()
    data.setdefault("rules", []).append(new_rule)
    _save_rules(data)
    logger.info(f"Rule created: {req.name}")
    return {"message": "Rule created", "rule": new_rule, "index": len(data["rules"]) - 1}


@router.put(
    "/{rule_index}",
    summary="Update a rule",
    description="Update an existing compliance rule by its index.",
)
async def update_rule(rule_index: int, req: RuleUpdate):
    data = _load_rules()
    rules = data.get("rules", [])
    if rule_index < 0 or rule_index >= len(rules):
        raise HTTPException(status_code=404, detail="Rule not found")
    
    rule = rules[rule_index]
    updates = req.model_dump(exclude_none=True)
    rule.update(updates)
    _save_rules(data)
    logger.info(f"Rule updated: index={rule_index}, fields={list(updates.keys())}")
    return {"message": "Rule updated", "rule": rule}


@router.delete(
    "/{rule_index}",
    summary="Delete a rule",
    description="Remove a compliance rule from the YAML configuration.",
)
async def delete_rule(rule_index: int):
    data = _load_rules()
    rules = data.get("rules", [])
    if rule_index < 0 or rule_index >= len(rules):
        raise HTTPException(status_code=404, detail="Rule not found")
    
    removed = rules.pop(rule_index)
    _save_rules(data)
    logger.info(f"Rule deleted: {removed.get('name')}")
    return {"message": "Rule deleted", "removed": removed.get("name")}


@router.post(
    "/reload",
    summary="Reload rules from YAML",
    description="Force reload the rules YAML file (useful after manual edits).",
)
async def reload_rules():
    data = _load_rules()
    return {"message": "Rules reloaded", "total": len(data.get("rules", []))}
