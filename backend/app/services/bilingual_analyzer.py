"""
双语合同一致性分析服务：将中英文合同分别提取结构化信息后逐字段对比，
输出一致性报告与评分。
"""

import re
import logging
import asyncio
from typing import Optional, List, Dict, Any, Tuple

from .structured_parser import (
    extract_structured_info,
    _fallback_structured_result,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Language detection helpers
# ---------------------------------------------------------------------------

# CJK Unified Ideographs range (U+4E00 – U+9FFF) covers the vast majority of
# Chinese / Japanese / Korean characters.  For our use-case (Chinese-English
# bilingual contracts) this heuristic is sufficient.
_CJK_PATTERN = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")


def _cjk_ratio(text: str) -> float:
    """Return the ratio of CJK characters to total non-whitespace chars."""
    if not text:
        return 0.0
    stripped = re.sub(r"\s", "", text)
    if not stripped:
        return 0.0
    cjk_count = len(_CJK_PATTERN.findall(stripped))
    return cjk_count / len(stripped)


def split_bilingual_text(raw_text: str, threshold: float = 0.3) -> Tuple[str, str]:
    """
    改进版双语切分，支持三种双语合同格式：
    1. 双栏对照："English text | Chinese text"（逐行用 | 分隔）
    2. 标题混合："1. Scope of Services / 服务范围"（用 / 分隔）
    3. 分块式：连续中文段落 + 连续英文段落

    Returns:
        (chinese_text, english_text) – either may be an empty string.
    """
    lines = raw_text.splitlines()
    zh_parts: List[str] = []
    en_parts: List[str] = []

    # 预过滤：页码、表头等噪音行
    skip_re = re.compile(
        r"^Page\s+\d+\s*/\s*\d+$"
        r"|^English\s*\|\s*中文$"
        r"|^字段\s*\|\s*内容"
        r"|^第\d+页\s*/\s*\d+$",
        re.IGNORECASE,
    )

    for line in lines:
        s = line.strip()
        if not s or skip_re.match(s):
            continue

        # === 1. 双栏对照：按 | 分隔 ===
        if "|" in s:
            segs = [seg.strip() for seg in s.split("|")]
            for seg in segs:
                if not seg:
                    continue
                if _cjk_ratio(seg) >= threshold:
                    zh_parts.append(seg)
                else:
                    en_parts.append(seg)
            continue

        # === 2. 标题混合："EN title / ZH 标题" ===
        if "/" in s and len(s) < 150:
            parts = [p.strip() for p in s.split("/", 1)]
            if len(parts) == 2:
                l_cjk = _cjk_ratio(parts[0])
                r_cjk = _cjk_ratio(parts[1])
                if l_cjk < r_cjk:
                    en_parts.append(parts[0])
                    zh_parts.append(parts[1])
                    continue
                elif l_cjk > r_cjk:
                    zh_parts.append(parts[0])
                    en_parts.append(parts[1])
                    continue

        # === 3. 兜底：按 CJK 比例分类 ===
        if _cjk_ratio(s) >= threshold:
            zh_parts.append(s)
        else:
            en_parts.append(s)

    return "\n\n".join(zh_parts), "\n\n".join(en_parts)

def _norm_text(value: Any) -> str:
    """Normalise a value to a lowercase string for fuzzy comparison."""
    if value is None:
        return ""
    return str(value).strip().lower()


def _texts_similar(a: str, b: str) -> bool:
    """Very lightweight similarity check – sufficient for flagging obvious
    mismatches without pulling in heavy NLP deps."""
    a = a.strip().lower()
    b = b.strip().lower()
    if a == b:
        return True
    # One is a substring of the other (handles cases like extra whitespace)
    if a and b and (a in b or b in a):
        return True
    return False


def _compare_scalar(
    field_name: str,
    zh_val: Any,
    en_val: Any,
) -> Optional[Dict[str, Any]]:
    """Compare a single scalar field.  Returns an inconsistency dict or None."""
    zh_str = _norm_text(zh_val)
    en_str = _norm_text(en_val)

    if not zh_str and not en_str:
        return None  # both empty – nothing to report

    if not zh_str or not en_str:
        return {
            "field": field_name,
            "status": "missing",
            "detail": (
                f"中文侧缺失" if not zh_str else f"英文侧缺失"
            ),
            "chinese_value": zh_val,
            "english_value": en_val,
        }

    if _texts_similar(zh_str, en_str):
        return {
            "field": field_name,
            "status": "consistent",
            "detail": "一致",
            "chinese_value": zh_val,
            "english_value": en_val,
        }

    return {
        "field": field_name,
        "status": "inconsistent",
        "detail": f"不一致: 中文='{zh_val}' vs 英文='{en_val}'",
        "chinese_value": zh_val,
        "english_value": en_val,
    }


def _compare_list_of_dicts(
    field_name: str,
    zh_list: List[Dict[str, Any]],
    en_list: List[Dict[str, Any]],
    key_fields: List[str],
) -> List[Dict[str, Any]]:
    """
    Compare two lists of dicts (e.g. parties, payment_terms) by matching on
    *key_fields* and then comparing all sub-fields.

    Returns a list of consistency items.
    """
    results: List[Dict[str, Any]] = []

    zh_len = len(zh_list)
    en_len = len(en_list)

    # If both empty – nothing to report
    if zh_len == 0 and en_len == 0:
        return results

    # If one side has entries and the other doesn't
    if zh_len == 0 or en_len == 0:
        results.append({
            "field": field_name,
            "status": "missing",
            "detail": (
                f"中文侧有 {zh_len} 条, 英文侧有 {en_len} 条"
            ),
            "chinese_value": zh_list,
            "english_value": en_list,
        })
        return results

    # Count mismatch
    if zh_len != en_len:
        results.append({
            "field": f"{field_name}.count",
            "status": "inconsistent",
            "detail": f"条目数不一致: 中文 {zh_len} 条 vs 英文 {en_len} 条",
            "chinese_value": zh_len,
            "english_value": en_len,
        })

    # Pairwise comparison (up to min length)
    pairs = min(zh_len, en_len)
    for idx in range(pairs):
        zh_item = zh_list[idx]
        en_item = en_list[idx]
        prefix = f"{field_name}[{idx}]"

        # Try to identify the item by key_fields for a more readable label
        label_parts = []
        for kf in key_fields:
            v = zh_item.get(kf) or en_item.get(kf)
            if v:
                label_parts.append(str(v))
        label = "/".join(label_parts) if label_parts else str(idx)

        for sub_key in _all_keys(zh_item, en_item):
            zh_v = zh_item.get(sub_key)
            en_v = en_item.get(sub_key)
            comp = _compare_scalar(f"{prefix}.{sub_key} ({label})", zh_v, en_v)
            if comp is not None:
                results.append(comp)

    return results


def _all_keys(*dicts: Dict[str, Any]) -> List[str]:
    """Return the union of keys from multiple dicts, deduplicated, order-
    preserved."""
    seen = set()
    keys: List[str] = []
    for d in dicts:
        for k in d.keys():
            if k not in seen:
                seen.add(k)
                keys.append(k)
    return keys


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _compute_consistency_score(items: List[Dict[str, Any]]) -> int:
    """
    Compute an overall consistency score (0-100) based on comparison items.
    - Each 'consistent' item adds weight.
    - Each 'inconsistent' item heavily penalises.
    - Each 'missing' item moderately penalises.
    """
    if not items:
        return 100  # nothing to compare → perfectly consistent (vacuously)

    weight_map = {
        "consistent": 0,
        "inconsistent": -12,
        "missing": -3,
    }

    penalty = 0
    for item in items:
        status = item.get("status", "consistent")
        penalty += weight_map.get(status, 0)

    score = 100 + penalty
    return max(0, min(100, score))


# ---------------------------------------------------------------------------
# Main public API
# ---------------------------------------------------------------------------

async def analyze_bilingual_consistency(raw_text: str) -> Dict[str, Any]:
    """
    Analyze a bilingual (Chinese-English) contract for cross-language
    consistency.

    Steps:
        1. Split text into Chinese / English sections.
        2. Extract structured info from each section via LLM.
        3. Compare the two results field by field.
        4. Return structured comparison with overall score.

    Args:
        raw_text: Full bilingual contract text.

    Returns:
        {
            "chinese_section": { ... },   # structured extraction of Chinese text
            "english_section": { ... },   # structured extraction of English text
            "consistency": [ ... ],       # field-by-field comparison items
            "consistency_score": 0-100,
        }
    """
    # 1. Split
    zh_text, en_text = split_bilingual_text(raw_text)

    # If either section is empty, we cannot perform a bilingual comparison.
    if not zh_text.strip() or not en_text.strip():
        dominant = "chinese" if zh_text.strip() else "english"
        logger.warning(
            f"Bilingual analysis skipped: document appears monolingual "
            f"(dominant language: {dominant})"
        )
        # Still extract from whichever text we have
        if zh_text.strip():
            zh_result = await extract_structured_info(zh_text)
        else:
            zh_result = _fallback_structured_result("No Chinese text found")
        if en_text.strip():
            en_result = await extract_structured_info(en_text)
        else:
            en_result = _fallback_structured_result("No English text found")

        return {
            "chinese_section": zh_result,
            "english_section": en_result,
            "consistency": [
                {
                    "field": "overall",
                    "status": "missing",
                    "detail": (
                        f"无法进行双语对比：文档为单语（{dominant}）。"
                        f"中文段长度={len(zh_text)}, 英文段长度={len(en_text)}"
                    ),
                    "chinese_value": None,
                    "english_value": None,
                }
            ],
            "consistency_score": 0,
        }

    # 2. Parallel extraction
    zh_result, en_result = await asyncio.gather(
        extract_structured_info(zh_text),
        extract_structured_info(en_text),
    )

    # 3. Field-by-field comparison
    consistency_items: List[Dict[str, Any]] = _compare_structured_results(
        zh_result, en_result
    )

    # 4. Score
    score = _compute_consistency_score(consistency_items)

    logger.info(
        f"Bilingual analysis complete: {len(consistency_items)} fields compared, "
        f"score={score}"
    )

    return {
        "chinese_section": zh_result,
        "english_section": en_result,
        "consistency": consistency_items,
        "consistency_score": score,
    }


def _compare_structured_results(
    zh: Dict[str, Any],
    en: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Compare two structured extraction results and return a list of comparison
    items.
    """
    items: List[Dict[str, Any]] = []

    # --- contract_type (scalar) ---
    comp = _compare_scalar("contract_type", zh.get("contract_type"), en.get("contract_type"))
    if comp:
        items.append(comp)

    # --- parties (list of dicts) ---
    items.extend(
        _compare_list_of_dicts(
            "parties",
            zh.get("parties", []),
            en.get("parties", []),
            key_fields=["name", "role"],
        )
    )

    # --- contract_period (nested dict) ---
    zh_cp = zh.get("contract_period") or {}
    en_cp = en.get("contract_period") or {}
    for sub in ["start_date", "end_date", "duration_description"]:
        comp = _compare_scalar(
            f"contract_period.{sub}",
            zh_cp.get(sub),
            en_cp.get(sub),
        )
        if comp:
            items.append(comp)

    # --- payment_terms (list of dicts) ---
    items.extend(
        _compare_list_of_dicts(
            "payment_terms",
            zh.get("payment_terms", []),
            en.get("payment_terms", []),
            key_fields=["amount", "currency", "payment_cycle"],
        )
    )

    # --- breach_liability (list of dicts) ---
    items.extend(
        _compare_list_of_dicts(
            "breach_liability",
            zh.get("breach_liability", []),
            en.get("breach_liability", []),
            key_fields=["clause_title"],
        )
    )

    # --- dispute_resolution (list of dicts) ---
    items.extend(
        _compare_list_of_dicts(
            "dispute_resolution",
            zh.get("dispute_resolution", []),
            en.get("dispute_resolution", []),
            key_fields=["clause_title", "arbitration_institution"],
        )
    )

    # --- confidentiality (list of dicts) ---
    items.extend(
        _compare_list_of_dicts(
            "confidentiality",
            zh.get("confidentiality", []),
            en.get("confidentiality", []),
            key_fields=["clause_title"],
        )
    )

    # --- intellectual_property (list of dicts) ---
    items.extend(
        _compare_list_of_dicts(
            "intellectual_property",
            zh.get("intellectual_property", []),
            en.get("intellectual_property", []),
            key_fields=["clause_title"],
        )
    )

    # --- termination (list of dicts) ---
    items.extend(
        _compare_list_of_dicts(
            "termination",
            zh.get("termination", []),
            en.get("termination", []),
            key_fields=["clause_title"],
        )
    )

    return items
