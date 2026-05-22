"""
LLM NER 命名实体识别服务：调用 Step 3.5 Flash 从合同中提取命名实体。
"""

import os
import re
import json
import logging
import httpx
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# API 配置（同 compliance_engine.py）
LLM_API_KEY = os.environ.get(
    "DEEPSEEK_API_KEY",
    os.environ.get("OPENAI_API_KEY", ""),
)
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.stepfun.com")
LLM_MODEL = os.environ.get("LLM_MODEL", "step-3.5-flash")

NER_SYSTEM_PROMPT = """你是一位专业的命名实体识别（NER）专家。你的任务是从合同文本中提取关键命名实体。

请严格按照以下 JSON 格式输出一个对象，包含 entities 列表，不要输出任何其他内容：
{
    "entities": [
        {
            "type": "实体类型，从以下选项中选择：DATE、MONEY、LOCATION、COMPANY、PERSON、CONTRACT_ID",
            "value": "原文中提取的实体文本",
            "context": "实体周围的上下文（约50个字符）",
            "position_hint": "实体所在的大致位置（如：合同首部、第一条、付款条款、签署页等）"
        }
    ]
}

实体类型定义：
- DATE：日期和时间，如 "2024年1月1日"、"签订之日起30天"
- MONEY：金额，如 "人民币壹佰万元整"、"$50,000"
- LOCATION：地点，如 "北京市海淀区"、"中国（上海）自由贸易试验区"
- COMPANY：公司/组织名称，如 "北京某某科技有限公司"
- PERSON：人名，如 "张三"、"李四"
- CONTRACT_ID：合同编号，如 "HT-2024-001"

注意事项：
- 尽可能多地提取实体，不要遗漏
- context 应包含实体前后的文字，约50个字符
- value 必须是原文中的精确文本
- position_hint 帮助前端定位到合同的大致段落
- 只输出 JSON，不要输出任何解释性文字"""

# 实体类型 → 前端高亮颜色映射
ENTITY_COLOR_MAP: Dict[str, str] = {
    "DATE": "blue",
    "MONEY": "green",
    "LOCATION": "orange",
    "COMPANY": "purple",
    "PERSON": "red",
    "CONTRACT_ID": "gray",
}

VALID_ENTITY_TYPES = set(ENTITY_COLOR_MAP.keys())


# ---------------------------------------------------------------------------
# Fallback result
# ---------------------------------------------------------------------------

def _fallback_ner_result(error: Optional[str] = None) -> Dict[str, Any]:
    """LLM 不可用时的回退结果。"""
    return {
        "entities": [],
        "_meta": {
            "source": "fallback",
            "error": error or "LLM service unavailable",
        },
    }


# ---------------------------------------------------------------------------
# Robust JSON helpers
# ---------------------------------------------------------------------------

def _strip_markdown_codeblock(text: str) -> str:
    """去掉 markdown 代码块包裹"""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


def _parse_json_robust(raw: str) -> Dict[str, Any]:
    """
    健壮的 JSON 解析：先直接解析，失败则正则提取。
    对截断输出尝试补全闭合括号。
    """
    cleaned = _strip_markdown_codeblock(raw)

    # 1. 直接解析
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 2. 正则提取最外层 { }
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if match:
        candidate = match.group()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # 3. 截断修复：补全缺失的 ] 和 }
    open_curly = cleaned.count("{") - cleaned.count("}")
    open_bracket = cleaned.count("[") - cleaned.count("]")
    if open_bracket > 0:
        cleaned = cleaned + "]" * open_bracket
    if open_curly > 0:
        cleaned = cleaned + "}" * open_curly
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 4. 最终兜底：从第一个 { 开始，补全闭合
    match = re.search(r"\{[\s\S]*", cleaned)
    if match:
        candidate = match.group()
        open_curly = candidate.count("{") - candidate.count("}")
        open_bracket = candidate.count("[") - candidate.count("]")
        if open_bracket > 0:
            candidate = candidate + "]" * open_bracket
        if open_curly > 0:
            candidate = candidate + "}" * open_curly
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    raise ValueError("Failed to parse JSON from LLM output")


def _normalize_entity(entity: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """规范化单个实体，返回 None 表示无效。"""
    if not isinstance(entity, dict):
        return None

    etype = str(entity.get("type", "")).upper().strip()
    if etype not in VALID_ENTITY_TYPES:
        return None

    value = str(entity.get("value", "")).strip()
    if not value:
        return None

    context = str(entity.get("context", ""))[:200]
    position_hint = str(entity.get("position_hint", ""))[:100]

    return {
        "type": etype,
        "value": value,
        "context": context,
        "position_hint": position_hint,
        "color": ENTITY_COLOR_MAP.get(etype, "gray"),
    }


def _normalize_ner_result(data: Dict[str, Any]) -> Dict[str, Any]:
    """规范化 NER 结果，过滤无效实体。"""
    raw_entities = data.get("entities") or []
    if not isinstance(raw_entities, list):
        raw_entities = []

    entities: List[Dict[str, Any]] = []
    for ent in raw_entities:
        normalized = _normalize_entity(ent)
        if normalized is not None:
            entities.append(normalized)

    # 按类型分组统计
    type_counts: Dict[str, int] = {}
    for ent in entities:
        t = ent["type"]
        type_counts[t] = type_counts.get(t, 0) + 1

    logger.info(
        f"NER extraction: {len(entities)} entities found, "
        f"breakdown: {type_counts}"
    )

    return {
        "entities": entities,
        "total": len(entities),
        "type_counts": type_counts,
    }


# ---------------------------------------------------------------------------
# Main public API
# ---------------------------------------------------------------------------

async def extract_entities(raw_text: str) -> Dict[str, Any]:
    """
    调用 Step 3.5 Flash 从合同文本中提取命名实体。

    Args:
        raw_text: 合同原文

    Returns:
        dict 包含:
        - entities: List[{type, value, context, position_hint, color}]
        - total: int
        - type_counts: Dict[str, int]
    """
    if not LLM_API_KEY:
        logger.warning("No LLM API key configured, returning fallback NER result")
        return _fallback_ner_result("API key not configured")

    # 构建用户消息
    max_chars = 30000
    user_msg = "请从以下合同文本中提取所有命名实体，以 JSON 格式输出：\n\n"
    if len(raw_text) > max_chars:
        user_msg += raw_text[:max_chars] + "\n\n... (文本已截断)"
    else:
        user_msg += raw_text

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{LLM_BASE_URL}/v1/chat/completions",
                headers={"Authorization": f"Bearer {LLM_API_KEY}"},
                json={
                    "model": LLM_MODEL,
                    "messages": [
                        {"role": "system", "content": NER_SYSTEM_PROMPT},
                        {"role": "user", "content": user_msg},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 16384,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        content = data["choices"][0]["message"]["content"].strip()
        parsed = _parse_json_robust(content)
        result = _normalize_ner_result(parsed)

        logger.info(f"NER extraction complete: {result['total']} entities")
        return result

    except Exception as e:
        logger.error(f"NER extraction failed: {e}")
        return _fallback_ner_result(str(e))
