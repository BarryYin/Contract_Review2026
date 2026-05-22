"""
审查服务：整合文档解析 + LLM合规分析 + 规则引擎 + 多维度评分 + 结果存储。
T-DP-04 + T-CE-04 + T-CE-05: 集成所有新服务。
"""

import os
import json
import uuid
import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from .doc_parser import smart_parse_document
from .compliance_engine import analyze_contract
from .structured_parser import extract_structured_info
from .ner_service import extract_entities
from .bilingual_analyzer import analyze_bilingual_consistency, split_bilingual_text
from .rule_engine import get_rule_engine, RuleHit
from .scorer import compute_score, DEFAULT_WEIGHTS
from .cross_clause_analyzer import analyze_cross_clause_risks
from . import audit_service
from ..core.config import UPLOAD_DIR
from . import webhook_service

logger = logging.getLogger(__name__)

REVIEWS_DIR = os.path.join(UPLOAD_DIR, "reviews")


def _ensure_reviews_dir():
    os.makedirs(REVIEWS_DIR, exist_ok=True)


def _review_path(file_id: str) -> str:
    return os.path.join(REVIEWS_DIR, f"{file_id}.json")


def get_review_result(file_id: str) -> Optional[dict]:
    """获取已存储的审查结果。"""
    path = _review_path(file_id)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_review_result(file_id: str, result: dict):
    """保存审查结果到文件。"""
    _ensure_reviews_dir()
    result["file_id"] = file_id
    result["id"] = result.get("id", f"review_{file_id[:8]}")
    with open(_review_path(file_id), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


def _is_bilingual(raw_text: str) -> bool:
    """判断文本是否为双语（中英文并存）合同。"""
    zh_text, en_text = split_bilingual_text(raw_text)
    return bool(zh_text.strip()) and bool(en_text.strip())


def _build_final_result(
    file_id: str,
    filename: str,
    upload_time: str,
    raw_text: str,
    parsed: dict,
    llm_result: dict,
    structured_info: dict,
    entities: dict,
    bilingual_analysis: Optional[dict],
    rule_hits: List[RuleHit],
    scored: dict,
    ocr_flag: bool,
    file_hash: Optional[str],
    cross_clause_risks: list = None,
) -> dict:
    """将所有分析结果合并为最终审查 JSON。"""

    # 从 rule_hits 构建可序列化列表
    rule_hits_list = []
    for hit in rule_hits:
        if hasattr(hit, "to_dict"):
            rule_hits_list.append(hit.to_dict())
        elif isinstance(hit, dict):
            rule_hits_list.append(hit)

    result = {
        # 基础标识
        "file_id": file_id,
        "id": f"review_{file_id[:8]}",
        "filename": filename,
        "upload_time": upload_time,
        "review_time": datetime.now(timezone.utc).isoformat(),

        # 原文（含OCR合并内容）
        "raw_text": raw_text,

        # OCR 标记
        "ocr_used": ocr_flag,
        "ocr_images_count": parsed.get("ocr_images_count", 0),
        "total_clauses": parsed.get("total_clauses", 0),

        # 合同类型（优先使用 structured_parser 的结果，回退到 LLM 的结果）
        "contract_type": (
            structured_info.get("contract_type")
            if structured_info.get("contract_type") and structured_info["contract_type"] != "未识别"
            else llm_result.get("contract_type", "未识别")
        ),

        # 评分（来自 scorer）
        "risk_score": scored["overall_score"],
        "risk_level": scored["risk_level"],
        "scoring_explanation": scored.get("scoring_explanation", ""),

        # LLM 审查摘要
        "summary": llm_result.get("summary", ""),

        # LLM 问题列表（三要素格式）
        "issues": llm_result.get("issues", []),

        # 规则引擎命中
        "rule_hits": rule_hits_list,

        # 结构化信息（来自 structured_parser）
        "structured_info": structured_info,

        # NER 命名实体（来自 ner_service）
        "entities": entities,

        # 双语一致性分析（仅双语合同时有值）
        "bilingual_analysis": bilingual_analysis,

        # 多维度评分详情（来自 scorer）
        "scoring_dimensions": scored.get("dimensions", []),

        # 原始 LLM risk_score 保留
        "llm_risk_score": llm_result.get("risk_score", 0),

        # 跨条款连锁风险（来自 cross_clause_analyzer）
        "cross_clause_risks": cross_clause_risks,

        # 文件哈希
        "file_hash": file_hash,
    }
    return result


async def review_file(file_id: str, file_path: str):
    """
    完整审查流程：
    1. 智能解析文档（含OCR）
    2. 并行执行：结构化信息提取 + NER + 双语分析
    3. LLM 合规分析
    4. 规则引擎评估
    5. 多维度评分
    6. 合并结果 + 审计日志 + 存储
    """
    from . import file_service

    try:
        # ---- 1. 更新状态为 processing ----
        file_service.update_file_status(file_id, status="processing")

        # ---- 2. 智能解析（自动判断是否需要 OCR）----
        logger.info(f"Starting review for file {file_id}")
        parsed = await smart_parse_document(file_path)
        ocr_flag = parsed.get("ocr_used", False)
        raw_text = parsed["raw_text"]
        clauses = parsed.get("clauses", [])
        logger.info(
            f"Parsed: {parsed['total_clauses']} clauses, "
            f"{len(raw_text)} chars, OCR={ocr_flag}"
        )

        # ---- 3. 并行执行结构化提取 + NER + 双语分析 ----
        logger.info(f"Starting parallel extraction for file {file_id}")

        # 判断是否双语合同
        is_bilingual = _is_bilingual(raw_text)

        # 构建并行任务
        tasks = [
            extract_structured_info(raw_text),
            extract_entities(raw_text),
        ]
        if is_bilingual:
            tasks.append(analyze_bilingual_consistency(raw_text))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Unpack results safely (each may be a dict or an Exception)
        _structured_raw = results[0]
        _entities_raw = results[1]

        if isinstance(_structured_raw, Exception):
            logger.error(f"Structured extraction failed: {_structured_raw}")
            structured_info: Dict[str, Any] = {}
        else:
            structured_info = _structured_raw  # type: ignore[assignment]

        if isinstance(_entities_raw, Exception):
            logger.error(f"NER extraction failed: {_entities_raw}")
            entities_result: Dict[str, Any] = {"entities": [], "total": 0, "type_counts": {}}
        else:
            entities_result = _entities_raw  # type: ignore[assignment]

        bilingual_analysis: Optional[Dict[str, Any]] = None
        if is_bilingual and len(results) > 2:
            _bilingual_raw = results[2]
            if isinstance(_bilingual_raw, Exception):
                logger.error(f"Bilingual analysis failed: {_bilingual_raw}")
            else:
                bilingual_analysis = _bilingual_raw  # type: ignore[assignment]

        logger.info(
            f"Extraction complete: structured_type={structured_info.get('contract_type')}, "
            f"entities={entities_result.get('total', 0)}, "
            f"bilingual={'yes' if bilingual_analysis else 'no'}"
        )

        # ---- 3.5 跨条款连锁风险分析（程序化校验，不依赖 LLM）----
        cross_clause_risks = []
        try:
            cross_clause_risks = analyze_cross_clause_risks(structured_info, raw_text)
            if cross_clause_risks:
                logger.info(f"Cross-clause analysis: {len(cross_clause_risks)} issues found")
        except Exception as e:
            logger.warning(f"Cross-clause analysis failed (non-fatal): {e}")

        # ---- 4. LLM 合规分析 ----
        logger.info(f"Starting LLM compliance analysis for file {file_id}")
        llm_result = await analyze_contract(raw_text, clauses)
        logger.info(
            f"LLM analysis: type={llm_result.get('contract_type')}, "
            f"score={llm_result.get('risk_score')}, "
            f"issues={len(llm_result.get('issues', []))}"
        )

        # ---- 5. 规则引擎评估 ----
        _ct_structured = structured_info.get("contract_type")
        _ct_llm = llm_result.get("contract_type", "")
        contract_type: str = (
            _ct_structured if _ct_structured and _ct_structured != "未识别" else _ct_llm
        ) or ""
        engine = get_rule_engine()
        rule_hits = engine.evaluate_all(raw_text, contract_type)
        matched_count = sum(1 for h in rule_hits if h.matched)
        logger.info(
            f"Rule engine: {len(rule_hits)} rules evaluated, {matched_count} matched"
        )

        # ---- 6. 多维度评分 ----
        scored = compute_score(rule_hits, llm_result.get("issues", []), cross_clause_risks)
        logger.info(
            f"Scoring: overall={scored['overall_score']}, "
            f"risk_level={scored['risk_level']}"
        )

        # ---- 7. 计算文件哈希 ----
        file_hash = audit_service.compute_file_hash(file_path)

        # ---- 8. 获取文件元数据 ----
        filename = file_id
        upload_time = datetime.now(timezone.utc).isoformat()
        try:
            file_info = file_service.get_file(file_id)
            if file_info:
                filename = getattr(file_info, "filename", file_id)
                upload_time = getattr(file_info, "upload_time", upload_time)
        except Exception:
            pass

        # ---- 9. 合并最终结果 ----
        result = _build_final_result(
            file_id=file_id,
            filename=filename,
            upload_time=upload_time,
            raw_text=raw_text,
            parsed=parsed,
            llm_result=llm_result,
            structured_info=structured_info,
            entities=entities_result,
            bilingual_analysis=bilingual_analysis,
            rule_hits=rule_hits,
            scored=scored,
            ocr_flag=ocr_flag,
            file_hash=file_hash,
            cross_clause_risks=cross_clause_risks,
        )

        # ---- 10. 保存结果 ----
        save_review_result(file_id, result)

        # ---- 11. 审计日志 ----
        audit_service.log_action(
            file_id=file_id,
            action="review_completed",
            details={
                "contract_type": result["contract_type"],
                "risk_level": result["risk_level"],
                "risk_score": result["risk_score"],
                "issues_count": len(result["issues"]),
                "rule_hits_count": matched_count,
                "entities_count": entities_result.get("total", 0),
                "bilingual": is_bilingual,
                "ocr_used": ocr_flag,
            },
            file_hash=file_hash,
        )

        # ---- 12. 更新文件元数据 ----
        file_service.update_file_status(
            file_id,
            status="completed",
            risk_level=result["risk_level"],
            contract_type=result["contract_type"],
            review_progress=100,
        )

        logger.info(
            f"Review complete for {file_id}: score={result['risk_score']}, "
            f"level={result['risk_level']}, issues={len(result['issues'])}, "
            f"rule_hits={matched_count}"
        )
        return result

    except Exception as e:
        logger.error(f"Review failed for {file_id}: {e}", exc_info=True)
        file_service.update_file_status(file_id, status="error")
        raise
