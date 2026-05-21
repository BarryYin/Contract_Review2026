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
from ..services.docx_export import export_track_changes
from ..services import file_service as _file_service
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
# IMPORTANT: More specific routes (/{file_id}/structured, etc.) MUST be
# registered BEFORE the generic /{file_id} to avoid path-parameter
# ambiguity in FastAPI.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# GET /api/reviews/{file_id}/structured — 结构化信息 + 实体
# ---------------------------------------------------------------------------

@router.get("/{file_id}/structured")
async def get_structured_info(file_id: str):
    """获取合同结构化信息（来自 structured_parser）与命名实体（来自 NER）。"""
    result = review_service.get_review_result(file_id)
    if result is None:
        raise HTTPException(status_code=404, detail="审查结果尚未就绪")

    structured_info = result.get("structured_info", {})
    entities = result.get("entities", {"entities": [], "total": 0, "type_counts": {}})

    return {
        "file_id": file_id,
        "contract_type": structured_info.get("contract_type", "未识别"),
        "parties": structured_info.get("parties", []),
        "contract_period": structured_info.get("contract_period", {}),
        "payment_terms": structured_info.get("payment_terms", []),
        "breach_liability": structured_info.get("breach_liability", []),
        "dispute_resolution": structured_info.get("dispute_resolution", []),
        "confidentiality": structured_info.get("confidentiality", []),
        "intellectual_property": structured_info.get("intellectual_property", []),
        "termination": structured_info.get("termination", []),
        "entities": entities,
    }


# ---------------------------------------------------------------------------
# GET /api/reviews/{file_id}/bilingual — 双语一致性分析
# ---------------------------------------------------------------------------

@router.get("/{file_id}/bilingual")
async def get_bilingual_analysis(file_id: str):
    """获取双语合同一致性分析结果。"""
    result = review_service.get_review_result(file_id)
    if result is None:
        raise HTTPException(status_code=404, detail="审查结果尚未就绪")

    bilingual_analysis = result.get("bilingual_analysis")
    if bilingual_analysis is None:
        return {
            "file_id": file_id,
            "is_bilingual": False,
            "message": "该合同非双语合同，无双语分析数据",
            "chinese_section": None,
            "english_section": None,
            "consistency": [],
            "consistency_score": None,
        }

    return {
        "file_id": file_id,
        "is_bilingual": True,
        "chinese_section": bilingual_analysis.get("chinese_section"),
        "english_section": bilingual_analysis.get("english_section"),
        "consistency": bilingual_analysis.get("consistency", []),
        "consistency_score": bilingual_analysis.get("consistency_score"),
    }


# ---------------------------------------------------------------------------
# GET /api/reviews/{file_id}/scoring — 多维度评分详情
# ---------------------------------------------------------------------------

@router.get("/{file_id}/scoring")
async def get_scoring_details(file_id: str):
    """获取多维度评分详情，包含权重说明。"""
    result = review_service.get_review_result(file_id)
    if result is None:
        raise HTTPException(status_code=404, detail="审查结果尚未就绪")

    from ..services.scorer import DEFAULT_WEIGHTS

    dimensions = result.get("scoring_dimensions", [])

    # 为每个维度附加权重说明
    weight_explanation = []
    total_weight = sum(DEFAULT_WEIGHTS.values())
    for dim_name, weight in DEFAULT_WEIGHTS.items():
        weight_explanation.append({
            "dimension": dim_name,
            "weight": weight,
            "weight_percentage": f"{round(weight / total_weight * 100, 1)}%" if total_weight > 0 else "0%",
            "description": _dimension_description(dim_name),
        })

    return {
        "file_id": file_id,
        "overall_score": result.get("risk_score", 0),
        "risk_level": result.get("risk_level", "low"),
        "scoring_explanation": result.get("scoring_explanation", ""),
        "dimensions": dimensions,
        "weight_explanation": weight_explanation,
        "llm_risk_score": result.get("llm_risk_score", 0),
    }


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
# GET /api/reviews/{file_id}/export/docx — Track Changes DOCX 导出
# ---------------------------------------------------------------------------

@router.get("/{file_id}/export/docx")
async def export_docx_track_changes(file_id: str):
    """导出带有 Track Changes 标注的 DOCX 文件（仅采纳的建议）。"""
    # 1. 获取审查结果
    result = review_service.get_review_result(file_id)
    if result is None:
        raise HTTPException(status_code=404, detail="审查结果尚未就绪，无法导出 DOCX")

    # 2. 查找原始 DOCX 文件路径
    original_path = _file_service.get_file_path(file_id)
    if original_path is None or not original_path.lower().endswith((".docx", ".doc")):
        raise HTTPException(
            status_code=400,
            detail="原始文件非 DOCX 格式，无法导出 Track Changes DOCX",
        )

    # 3. 过滤出 status=="adopted" 的问题
    adopted_issues = [
        issue for issue in result.get("issues", [])
        if issue.get("status") == "adopted"
    ]

    if not adopted_issues:
        raise HTTPException(
            status_code=400,
            detail="没有已采纳的问题，无需导出 Track Changes DOCX",
        )

    # 4. 生成带 Track Changes 的 DOCX
    try:
        docx_bytes = export_track_changes(original_path, adopted_issues)
    except Exception as e:
        logger.error(f"DOCX Track Changes export failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"DOCX 导出失败: {str(e)}")

    # 5. 审计日志
    audit_service.log_action(
        file_id=file_id,
        action="docx_exported",
        details={
            "adopted_issues_count": len(adopted_issues),
            "original_filename": result.get("filename", file_id),
        },
    )

    # 6. 返回 DOCX 文件流
    filename = result.get("filename", file_id)
    safe_name = filename.rsplit(".", 1)[0] if "." in filename else filename
    download_name = f"{safe_name}_TrackChanges.docx"

    import urllib.parse
    encoded_name = urllib.parse.quote(download_name)

    return StreamingResponse(
        iter([docx_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}",
        },
    )


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
# GET /api/reviews/{file_id}  (generic — MUST be after specific sub-routes)
# ---------------------------------------------------------------------------

@router.get("/{file_id}", response_model=ReviewResult)
async def get_review(file_id: str):
    """获取指定文件的审查结果。"""
    result = review_service.get_review_result(file_id)
    if result is None:
        raise HTTPException(status_code=404, detail="审查结果尚未就绪")
    return result


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


# ---------------------------------------------------------------------------
# Helper: dimension descriptions for scoring endpoint
# ---------------------------------------------------------------------------

def _dimension_description(dim_name: str) -> str:
    """返回维度的中文说明。"""
    descriptions = {
        "违约责任": "评估违约金比例、赔偿条款的合理性和对等性",
        "付款条款": "评估付款周期、金额、方式等条款的风险",
        "保密义务": "评估保密范围、期限、义务等条款的完备性",
        "知识产权": "评估知识产权归属、授权、保护等条款的清晰性",
        "争议解决": "评估争议解决方式、管辖权等条款的明确性",
        "免责条款": "评估免责范围、不可抗力等条款的公平性",
        "终止条款": "评估合同终止条件、程序等条款的合理性",
        "其他": "其他未归类的风险项",
    }
    return descriptions.get(dim_name, "风险维度评估")


# ---------------------------------------------------------------------------
# List all reviews
# ---------------------------------------------------------------------------

@router.get("")
async def list_reviews():
    """List all review results."""
    import json
    from ..core.config import settings
    
    reviews_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "reviews")
    os.makedirs(reviews_dir, exist_ok=True)
    
    results = []
    for fname in os.listdir(reviews_dir):
        if not fname.endswith("_review.json"):
            continue
        fpath = os.path.join(reviews_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            results.append({
                "file_id": data.get("file_id", ""),
                "filename": data.get("filename", ""),
                "contract_type": data.get("contract_type", ""),
                "risk_score": data.get("risk_score", 0),
                "risk_level": data.get("risk_level", ""),
                "review_time": data.get("review_time", ""),
                "issues_count": len(data.get("issues", [])),
            })
        except Exception:
            continue
    
    results.sort(key=lambda x: x.get("review_time", ""), reverse=True)
    return {"reviews": results, "total": len(results)}


# ---------------------------------------------------------------------------
# Compare two reviews
# ---------------------------------------------------------------------------

@router.post("/compare")
async def compare_reviews(body: dict):
    """Compare two review results."""
    import json
    
    file_id_a = body.get("file_id_a") or body.get("file_id_1")
    file_id_b = body.get("file_id_b") or body.get("file_id_2")
    
    if not file_id_a or not file_id_b:
        raise HTTPException(status_code=400, detail="需要提供 file_id_a 和 file_id_b")
    
    from ..services.compare_service import compare_reviews as do_compare
    
    review_a = _load_review_json(file_id_a)
    review_b = _load_review_json(file_id_b)
    
    return do_compare(review_a, review_b)
