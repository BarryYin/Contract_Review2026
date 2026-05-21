"""
审查结果 API 路由。
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from ..models.file import (
    ReviewResult,
    IssueActionResponse,
    AuditLogEntry,
    AuditLogResponse,
)
from ..services import review_service
from ..services import audit_service
from ..services.report_generator import generate_pdf_report
from ..core.config import UPLOAD_DIR

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


# ---------------------------------------------------------------------------
# Helper: load / save review JSON, find issue by id
# ---------------------------------------------------------------------------

def _review_json_path(file_id: str) -> str:
    return os.path.join(UPLOAD_DIR, "reviews", f"{file_id}.json")


def _load_review_json(file_id: str) -> dict:
    """加载审查结果 JSON，失败则抛出 404。"""
    path = _review_json_path(file_id)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="审查结果尚未就绪")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_review_json(file_id: str, data: dict) -> None:
    """将审查结果写回磁盘。"""
    os.makedirs(os.path.join(UPLOAD_DIR, "reviews"), exist_ok=True)
    path = _review_json_path(file_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _find_issue(issues: list, issue_id: str) -> Optional[dict]:
    """在 issues 列表中按 id 查找问题。"""
    for issue in issues:
        if issue.get("id") == issue_id:
            return issue
    return None


# ---------------------------------------------------------------------------
# GET /api/reviews/{file_id}
# ---------------------------------------------------------------------------

@router.get("/{file_id}", response_model=ReviewResult)
async def get_review(file_id: str):
    """获取指定文件的审查结果。"""
    result = review_service.get_review_result(file_id)
    if result is None:
        raise HTTPException(status_code=404, detail="审查结果尚未就绪")
    return result


# ---------------------------------------------------------------------------
# POST /api/reviews/{file_id}/issues/{issue_id}/adopt
# ---------------------------------------------------------------------------

@router.post(
    "/{file_id}/issues/{issue_id}/adopt",
    response_model=IssueActionResponse,
)
async def adopt_issue(file_id: str, issue_id: str):
    """将指定问题标记为「已采纳」。"""
    data = _load_review_json(file_id)
    issues = data.get("issues", [])
    issue = _find_issue(issues, issue_id)
    if issue is None:
        raise HTTPException(status_code=404, detail="未找到指定问题")

    issue["status"] = "adopted"
    _save_review_json(file_id, data)

    # 审计日志
    audit_service.log_action(
        file_id=file_id,
        action="issue_adopted",
        details={
            "issue_id": issue_id,
            "clause": issue.get("clause", ""),
            "risk_type": issue.get("risk_type", ""),
            "severity": issue.get("severity", ""),
        },
    )

    return IssueActionResponse(
        issue_id=issue_id,
        status="adopted",
        message="问题已标记为采纳",
    )


# ---------------------------------------------------------------------------
# POST /api/reviews/{file_id}/issues/{issue_id}/reject
# ---------------------------------------------------------------------------

@router.post(
    "/{file_id}/issues/{issue_id}/reject",
    response_model=IssueActionResponse,
)
async def reject_issue(file_id: str, issue_id: str):
    """将指定问题标记为「已拒绝」。"""
    data = _load_review_json(file_id)
    issues = data.get("issues", [])
    issue = _find_issue(issues, issue_id)
    if issue is None:
        raise HTTPException(status_code=404, detail="未找到指定问题")

    issue["status"] = "rejected"
    _save_review_json(file_id, data)

    # 审计日志
    audit_service.log_action(
        file_id=file_id,
        action="issue_rejected",
        details={
            "issue_id": issue_id,
            "clause": issue.get("clause", ""),
            "risk_type": issue.get("risk_type", ""),
            "severity": issue.get("severity", ""),
        },
    )

    return IssueActionResponse(
        issue_id=issue_id,
        status="rejected",
        message="问题已标记为拒绝",
    )


# ---------------------------------------------------------------------------
# GET /api/reviews/{file_id}/export/pdf
# ---------------------------------------------------------------------------

@router.get("/{file_id}/export/pdf")
async def export_pdf(file_id: str):
    """导出指定文件的 PDF 合规审查报告。"""
    # 1. 获取审查结果
    result = review_service.get_review_result(file_id)
    if result is None:
        raise HTTPException(status_code=404, detail="审查结果尚未就绪，无法导出报告")

    # 2. 尝试获取原始文件名
    filename = file_id
    try:
        from ..services import file_service
        file_info = file_service.get_file(file_id)
        if file_info:
            filename = file_info.filename
    except Exception:
        pass

    # 3. 生成 PDF
    try:
        pdf_bytes = generate_pdf_report(result, filename=filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF 生成失败: {str(e)}")

    # 4. 审计日志
    audit_service.log_action(
        file_id=file_id,
        action="pdf_exported",
        details={"filename": filename},
    )

    # 5. 返回 PDF 流
    safe_name = filename.rsplit(".", 1)[0] if "." in filename else filename
    download_name = f"{safe_name}_合规审查报告.pdf"

    import urllib.parse
    encoded_name = urllib.parse.quote(download_name)

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}",
        },
    )


# ---------------------------------------------------------------------------
# GET /api/reviews/audit-log  (审计日志查询)
# ---------------------------------------------------------------------------

@router.get("/audit-log/log", response_model=AuditLogResponse)
async def query_audit_log(
    start_time: Optional[str] = Query(None, description="ISO 8601 起始时间"),
    end_time: Optional[str] = Query(None, description="ISO 8601 截止时间"),
    action: Optional[str] = Query(None, description="操作类型过滤"),
    file_id: Optional[str] = Query(None, description="文件 ID 过滤"),
    contract_type: Optional[str] = Query(None, description="合同类型过滤"),
    risk_level: Optional[str] = Query(None, description="风险等级过滤"),
):
    """查询审计日志。"""
    entries = audit_service.get_audit_log(
        start_time=start_time,
        end_time=end_time,
        action=action,
        file_id=file_id,
        contract_type=contract_type,
        risk_level=risk_level,
    )
    logs = [
        AuditLogEntry(
            timestamp=e["timestamp"],
            file_id=e["file_id"],
            action=e["action"],
            details=e.get("details"),
            file_hash=e.get("file_hash"),
        )
        for e in entries
    ]
    return AuditLogResponse(logs=logs, total=len(logs))
