"""
审计日志服务：记录和查询系统中所有关键操作的审计轨迹。
"""

import os
import json
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from ..core.config import UPLOAD_DIR

logger = logging.getLogger(__name__)

AUDIT_LOG_FILE = os.path.join(UPLOAD_DIR, "audit_log.json")


# ---------------------------------------------------------------------------
# Utility: SHA-256 file hash
# ---------------------------------------------------------------------------

def compute_file_hash(file_path: str) -> Optional[str]:
    """计算文件的 SHA-256 哈希值。

    Args:
        file_path: 文件的绝对/相对路径。

    Returns:
        十六进制格式的 SHA-256 哈希字符串，文件不存在则返回 None。
    """
    if not os.path.exists(file_path):
        return None
    sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    except OSError:
        logger.warning("Failed to compute hash for %s", file_path)
        return None


# ---------------------------------------------------------------------------
# Internal: load / save audit log
# ---------------------------------------------------------------------------

def _load_log() -> List[Dict[str, Any]]:
    """从磁盘读取完整审计日志。"""
    if not os.path.exists(AUDIT_LOG_FILE):
        return []
    try:
        with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save_log(entries: List[Dict[str, Any]]) -> None:
    """将审计日志持久化到磁盘。"""
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    with open(AUDIT_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def log_action(
    file_id: str,
    action: str,
    details: Optional[Dict[str, Any]] = None,
    file_hash: Optional[str] = None,
) -> Dict[str, Any]:
    """追加一条审计日志记录。

    Args:
        file_id:   关联的文件 ID。
        action:    操作类型（upload / review_started / review_completed /
                   issue_adopted / issue_rejected / pdf_exported / docx_exported）。
        details:   附加上下文字典。
        file_hash: 文件 SHA-256 哈希（可选，仅适用于文件操作）。

    Returns:
        新创建的日志条目。
    """
    entry: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "file_id": file_id,
        "action": action,
        "details": details or {},
    }
    if file_hash is not None:
        entry["file_hash"] = file_hash

    entries = _load_log()
    entries.append(entry)
    _save_log(entries)

    logger.info("Audit log: action=%s file_id=%s", action, file_id)
    return entry


def get_audit_log(
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    action: Optional[str] = None,
    file_id: Optional[str] = None,
    contract_type: Optional[str] = None,
    risk_level: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """查询审计日志，支持多种过滤条件。

    Args:
        start_time:    ISO 8601 起始时间（含）。
        end_time:      ISO 8601 截止时间（含）。
        action:        按操作类型过滤。
        file_id:       按文件 ID 过滤。
        contract_type: 按合同类型过滤（匹配 details.contract_type）。
        risk_level:    按风险等级过滤（匹配 details.risk_level）。

    Returns:
        匹配的日志条目列表。
    """
    entries = _load_log()
    filtered: List[Dict[str, Any]] = []

    for entry in entries:
        # 时间范围过滤
        ts = entry.get("timestamp", "")
        if start_time and ts < start_time:
            continue
        if end_time and ts > end_time:
            continue

        # 操作类型过滤
        if action and entry.get("action") != action:
            continue

        # 文件 ID 过滤
        if file_id and entry.get("file_id") != file_id:
            continue

        # 合同类型 / 风险等级 — 从 details 中匹配
        details = entry.get("details", {})
        if contract_type and details.get("contract_type") != contract_type:
            continue
        if risk_level and details.get("risk_level") != risk_level:
            continue

        filtered.append(entry)

    return filtered
