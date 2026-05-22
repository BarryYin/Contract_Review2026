"""
Webhook 管理 API — 注册/删除/测试 webhook。
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import Dict, List, Optional

from ..services import webhook_service

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


class WebhookCreateRequest(BaseModel):
    url: str
    events: List[str]  # ["high_risk_detected", "review_completed", "issue_adopted"]
    headers: Optional[Dict[str, str]] = None


class WebhookResponse(BaseModel):
    id: str
    url: str
    events: List[str]
    headers: Dict[str, str]
    enabled: bool
    created_at: str
    last_triggered: Optional[str] = None
    trigger_count: int = 0


@router.post(
    "",
    response_model=WebhookResponse,
    summary="Register a webhook",
    description="Register a new webhook URL to receive event notifications. Supported events: high_risk_detected, review_completed, issue_adopted.",
)
async def create_webhook(req: WebhookCreateRequest):
    if not req.events:
        raise HTTPException(status_code=400, detail="至少需要一个事件类型")
    invalid = [e for e in req.events if e not in webhook_service.SUPPORTED_EVENTS]
    if invalid:
        raise HTTPException(status_code=400, detail=f"不支持的事件类型: {invalid}")
    config = webhook_service.register_webhook(req.url, req.events, req.headers)
    return config


@router.get(
    "",
    response_model=List[WebhookResponse],
    summary="List all webhooks",
    description="Retrieve all registered webhooks.",
)
async def list_webhooks():
    return webhook_service.list_webhooks()


@router.delete(
    "/{webhook_id}",
    summary="Delete a webhook",
    description="Remove a registered webhook by its ID.",
)
async def delete_webhook(webhook_id: str):
    if not webhook_service.remove_webhook(webhook_id):
        raise HTTPException(status_code=404, detail="Webhook not found")
    return {"message": "Webhook deleted", "id": webhook_id}


@router.post(
    "/{webhook_id}/test",
    summary="Test a webhook",
    description="Send a test payload to the webhook URL to verify connectivity.",
)
async def test_webhook(webhook_id: str):
    result = await webhook_service.test_webhook(webhook_id)
    if "error" in result and result.get("error") == "Webhook not found":
        raise HTTPException(status_code=404, detail="Webhook not found")
    return result
