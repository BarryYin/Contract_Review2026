"""
Webhook 推送服务 — 当高风险合同被识别时自动通知。
支持注册/删除/触发 webhook，事件类型：high_risk_detected, review_completed, issue_adopted。
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# 内存存储（生产环境可替换为数据库）
_webhook_configs: Dict[str, Dict[str, Any]] = {}

SUPPORTED_EVENTS = {"high_risk_detected", "review_completed", "issue_adopted"}


def register_webhook(url: str, events: List[str], headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """注册一个新的 webhook。"""
    wid = str(uuid.uuid4())
    config = {
        "id": wid,
        "url": url,
        "events": [e for e in events if e in SUPPORTED_EVENTS],
        "headers": headers or {},
        "enabled": True,
        "created_at": datetime.now().isoformat(),
        "last_triggered": None,
        "trigger_count": 0,
    }
    _webhook_configs[wid] = config
    logger.info(f"Webhook registered: {wid} -> {url} events={config['events']}")
    return config


def remove_webhook(webhook_id: str) -> bool:
    """删除一个 webhook。"""
    if webhook_id in _webhook_configs:
        del _webhook_configs[webhook_id]
        return True
    return False


def list_webhooks() -> List[Dict[str, Any]]:
    """列出所有已注册的 webhook。"""
    return list(_webhook_configs.values())


def get_webhook(webhook_id: str) -> Optional[Dict[str, Any]]:
    """获取单个 webhook 配置。"""
    return _webhook_configs.get(webhook_id)


async def trigger_webhooks(event_type: str, payload: Dict[str, Any]) -> int:
    """
    触发所有匹配事件类型的 webhook。
    返回成功发送的数量。
    """
    if event_type not in SUPPORTED_EVENTS:
        logger.warning(f"Unknown event type: {event_type}")
        return 0

    payload["event"] = event_type
    payload["timestamp"] = datetime.now().isoformat()

    success_count = 0
    for wid, config in _webhook_configs.items():
        if not config["enabled"]:
            continue
        if event_type not in config["events"]:
            continue

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    config["url"],
                    json=payload,
                    headers={**config["headers"], "Content-Type": "application/json"},
                )
                if resp.status_code < 400:
                    success_count += 1
                    config["last_triggered"] = datetime.now().isoformat()
                    config["trigger_count"] += 1
                    logger.info(f"Webhook {wid} triggered successfully: {resp.status_code}")
                else:
                    logger.warning(f"Webhook {wid} returned {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            logger.error(f"Webhook {wid} delivery failed: {e}")

    return success_count


async def test_webhook(webhook_id: str) -> Dict[str, Any]:
    """发送测试 payload 到指定 webhook。"""
    config = _webhook_configs.get(webhook_id)
    if not config:
        return {"success": False, "error": "Webhook not found"}

    test_payload = {
        "event": "test",
        "timestamp": datetime.now().isoformat(),
        "message": "This is a test webhook from ContractAI",
        "contract_name": "测试合同",
        "risk_score": 85,
        "risk_level": "high",
        "high_risk_issues": 3,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                config["url"],
                json=test_payload,
                headers={**config["headers"], "Content-Type": "application/json"},
            )
            return {
                "success": resp.status_code < 400,
                "status_code": resp.status_code,
                "response": resp.text[:500],
            }
    except Exception as e:
        return {"success": False, "error": str(e)}
