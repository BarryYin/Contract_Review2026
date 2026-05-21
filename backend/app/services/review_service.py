"""
审查服务：整合文档解析 + LLM合规分析 + 结果存储。
"""

import os
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from .doc_parser import smart_parse_document
from .compliance_engine import analyze_contract
from ..core.config import UPLOAD_DIR

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


async def review_file(file_id: str, file_path: str):
    """
    完整审查流程：智能解析文档(含OCR) → LLM分析 → 存储结果 → 更新元数据。
    """
    from . import file_service

    try:
        # 1. 更新状态为 processing
        file_service.update_file_status(file_id, status="processing")

        # 2. 智能解析（自动判断是否需要 OCR）
        logger.info(f"Starting review for file {file_id}")
        parsed = await smart_parse_document(file_path)
        ocr_flag = parsed.get("ocr_used", False)
        logger.info(
            f"Parsed: {parsed['total_clauses']} clauses, "
            f"{len(parsed['raw_text'])} chars, OCR={ocr_flag}"
        )

        # 3. LLM 分析
        result = await analyze_contract(parsed["raw_text"], parsed["clauses"])

        # 4. 标记是否使用了 OCR
        result["ocr_used"] = ocr_flag

        # 5. 存储
        save_review_result(file_id, result)

        # 6. 更新文件元数据
        file_service.update_file_status(
            file_id,
            status="completed",
            risk_level=result.get("risk_level"),
            contract_type=result.get("contract_type"),
            review_progress=100,
        )

        logger.info(f"Review complete for {file_id}: score={result.get('risk_score')}")
        return result

    except Exception as e:
        logger.error(f"Review failed for {file_id}: {e}")
        file_service.update_file_status(file_id, status="error")
        raise
