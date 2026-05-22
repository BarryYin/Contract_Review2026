"""
审查结果 API 路由。
"""

import os
import json
import logging
import asyncio
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
# POST /api/reviews/{file_id}/start — 手动触发审查（支持模板参数）
# ---------------------------------------------------------------------------

@router.post(
    "/{file_id}/start",
    summary="Start review with template",
    description="Manually trigger a compliance review for an uploaded file with a specified review template. Use this after uploading with auto_review=false.",
)
async def start_review(file_id: str, body: dict = {}):
    template = body.get("template", "general")

    # Verify file exists
    file_info = _file_service.get_file(file_id)
    if file_info is None:
        raise HTTPException(status_code=404, detail="文件未找到")

    file_path = _file_service.get_file_path(file_id)
    if file_path is None:
        raise HTTPException(status_code=404, detail="文件内容未找到")

    # Check if review already exists
    existing = review_service.get_review_result(file_id)
    if existing is not None:
        raise HTTPException(status_code=409, detail="该文件已有审查结果")

    # Trigger background review with template info
    async def _review_with_template():
        try:
            result = await review_service.review_file(file_id, file_path)
            # Append template metadata to the saved result
            if result:
                result["template"] = template
                review_service.save_review_result(file_id, result)
        except Exception as e:
            logger.error(f"Background review with template failed: {e}")

    asyncio.create_task(_review_with_template())

    return {
        "file_id": file_id,
        "template": template,
        "status": "processing",
        "message": f"已使用「{_template_label(template)}」模板开始审查",
    }


def _template_label(template: str) -> str:
    labels = {
        "general": "通用合同审查",
        "procurement": "采购合同审查",
        "labor": "劳动合同审查",
    }
    return labels.get(template, template)


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

@router.get(
    "/{file_id}/structured",
    summary="Get structured contract info",
    description="Retrieve structured parsing results (parties, clauses, contract type) and named entity recognition (NER) data for a reviewed contract.",
)
async def get_structured_info(file_id: str):
    result = review_service.get_review_result(file_id)
    if result is None:
        raise HTTPException(status_code=404, detail="审查结果尚未就绪")

    structured_info = result.get("structured_info", {})
    entities = result.get("entities", {"entities": [], "total": 0, "type_counts": {}})

    # Build clauses list from structured_info for frontend display
    clauses = []
    clause_fields = {
        "payment_terms": "付款条款",
        "breach_liability": "违约责任",
        "dispute_resolution": "争议解决",
        "confidentiality": "保密义务",
        "intellectual_property": "知识产权",
        "termination": "终止条款",
    }
    for field, title in clause_fields.items():
        items = structured_info.get(field, [])
        if items:
            for i, item in enumerate(items):
                text = item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)
                clauses.append({
                    "number": f"{i+1}",
                    "title": title,
                    "content": text,
                })

    # Also add issues as risk-tagged clauses with full text
    issues_list = result.get("issues", [])
    for issue in issues_list:
        clause_ref = issue.get("clause_reference", "")
        # Get original text from modification_example or risk_description
        orig_text = ""
        mod_example = issue.get("modification_example", {})
        if isinstance(mod_example, dict):
            orig_text = mod_example.get("original", "")
        if not orig_text:
            orig_text = issue.get("risk_description", "")
        clauses.append({
            "number": clause_ref,
            "title": issue.get("title", ""),
            "content": orig_text,
            "risk_level": issue.get("severity", ""),
            "issue_id": issue.get("id", ""),
        })

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
        "clauses": clauses,
    }


# ---------------------------------------------------------------------------
# GET /api/reviews/{file_id}/bilingual — 双语一致性分析
# ---------------------------------------------------------------------------

@router.get(
    "/{file_id}/bilingual",
    summary="Get bilingual consistency analysis",
    description="Retrieve bilingual (Chinese/English) consistency analysis for a contract. Returns consistency issues and score if the contract is bilingual.",
)
async def get_bilingual_analysis(file_id: str):
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

@router.get(
    "/{file_id}/scoring",
    summary="Get multi-dimension scoring details",
    description="Retrieve detailed scoring breakdown across multiple risk dimensions (payment terms, breach liability, confidentiality, etc.) with weight explanations.",
)
async def get_scoring_details(file_id: str):
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

@router.get(
    "/{file_id}/export/pdf",
    summary="Export PDF compliance report",
    description="Generate and download a PDF compliance review report for the specified file. Includes risk scores, issues, and recommendations.",
)
async def export_pdf(file_id: str):
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

@router.get(
    "/{file_id}/export/docx",
    summary="Export DOCX with Track Changes",
    description="Export a DOCX file with Track Changes markup for all adopted (accepted) review issues. Only available when the original file is DOCX format and at least one issue has been adopted.",
)
async def export_docx_track_changes(file_id: str):
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
    summary="Adopt (accept) a review issue",
    description="Mark a specific review issue as **adopted** (accepted). The issue will be included in Track Changes DOCX exports.",
)
async def adopt_issue(file_id: str, issue_id: str):
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
    summary="Reject a review issue",
    description="Mark a specific review issue as **rejected**. Rejected issues will be excluded from Track Changes DOCX exports.",
)
async def reject_issue(file_id: str, issue_id: str):
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

@router.get(
    "/{file_id}",
    response_model=ReviewResult,
    summary="Get review result for a file",
    description="Retrieve the full compliance review result for a specific file, including risk score, risk level, issues list, and all analysis data.",
)
async def get_review(file_id: str):
    result = review_service.get_review_result(file_id)
    if result is None:
        raise HTTPException(status_code=404, detail="审查结果尚未就绪")
    return result


# ---------------------------------------------------------------------------
# GET /api/reviews/audit-log  (审计日志查询)
# ---------------------------------------------------------------------------

@router.get(
    "/audit-log/log",
    response_model=AuditLogResponse,
    summary="Query audit log",
    description="Query the audit log with optional filters for time range, action type, file ID, contract type, and risk level.",
)
async def query_audit_log(
    start_time: Optional[str] = Query(None, description="ISO 8601 起始时间"),
    end_time: Optional[str] = Query(None, description="ISO 8601 截止时间"),
    action: Optional[str] = Query(None, description="操作类型过滤"),
    file_id: Optional[str] = Query(None, description="文件 ID 过滤"),
    contract_type: Optional[str] = Query(None, description="合同类型过滤"),
    risk_level: Optional[str] = Query(None, description="风险等级过滤"),
):
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

@router.get(
    "",
    summary="List all review results",
    description="Retrieve a summary list of all completed review results, sorted by review time (newest first). Each entry includes file_id, filename, contract type, risk score, and issue count.",
)
async def list_reviews():
    import json
    from ..core.config import UPLOAD_DIR
    
    reviews_dir = os.path.join(UPLOAD_DIR, 'reviews')
    os.makedirs(reviews_dir, exist_ok=True)
    
    results = []
    for fname in os.listdir(reviews_dir):
        if not fname.endswith(".json"):
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

@router.post(
    "/compare",
    summary="Compare two review results",
    description="Compare the review results of two contracts. Provide `file_id_a` and `file_id_b` in the request body. Returns a diff of risk scores, issues, and clause differences.",
)
async def compare_reviews(body: dict):
    import json
    
    file_id_a = body.get("file_id_a") or body.get("file_id_1")
    file_id_b = body.get("file_id_b") or body.get("file_id_2")
    
    if not file_id_a or not file_id_b:
        raise HTTPException(status_code=400, detail="需要提供 file_id_a 和 file_id_b")
    
    from ..services.compare_service import compare_reviews as do_compare
    
    review_a = _load_review_json(file_id_a)
    review_b = _load_review_json(file_id_b)
    
    return do_compare(review_a, review_b)
