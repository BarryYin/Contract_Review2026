"""
LLM 结构化合同信息提取服务：调用 Step 3.5 Flash 提取合同关键字段。
"""

import os
import re
import asyncio
import json
import logging
import httpx
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# API 配置（同 compliance_engine.py）
LLM_API_KEY = os.environ.get("LLM_API_KEY") or os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
def _get_base_url():
    base = os.environ.get("LLM_API_BASE_URL", "") or os.environ.get("LLM_BASE_URL", "")
    if base.endswith("/v1"):
        base = base[:-3]
    return base or "https://api.stepfun.com"
LLM_MODEL = os.environ.get("LLM_MODEL", "step-3.5-flash")

EXTRACTION_SYSTEM_PROMPT = """你是一位专业的合同信息提取专家。你的任务是从合同文本中精确提取结构化信息。

请严格按照以下 JSON 格式输出，不要输出任何其他内容：
{
    "contract_type": "合同类型，从以下选项中选择：采购合同、服务合同、保密协议、劳动合同、租赁合同、技术合同、其他",
    "parties": [
        {
            "name": "当事人名称",
            "address": "注册地址或联系地址",
            "legal_representative": "法定代表人姓名",
            "role": "甲方 或 乙方 或 丙方"
        }
    ],
    "contract_period": {
        "start_date": "合同开始日期，格式 YYYY-MM-DD，无法确定则填 null",
        "end_date": "合同结束日期，格式 YYYY-MM-DD，无法确定则填 null",
        "duration_description": "合同期限的文字描述"
    },
    "payment_terms": [
        {
            "amount": "金额数字，如 100000",
            "currency": "币种，如 CNY、USD",
            "payment_cycle": "付款周期描述，如 一次性付款、分期付款、按月付款",
            "payment_method": "付款方式，如 银行转账、现金、支票",
            "description": "付款条款描述"
        }
    ],
    "breach_liability": [
        {
            "clause_title": "违约责任条款标题",
            "content": "违约责任条款内容摘要"
        }
    ],
    "dispute_resolution": [
        {
            "clause_title": "争议解决条款标题",
            "content": "争议解决条款内容摘要",
            "arbitration_institution": "仲裁机构名称，无则填 null",
            "jurisdiction": "管辖法院或地区，无则填 null"
        }
    ],
    "confidentiality": [
        {
            "clause_title": "保密条款标题",
            "content": "保密条款内容摘要",
            "duration": "保密期限描述"
        }
    ],
    "intellectual_property": [
        {
            "clause_title": "知识产权条款标题",
            "content": "知识产权条款内容摘要",
            "scope": "知识产权范围描述"
        }
    ],
    "termination": [
        {
            "clause_title": "终止条款标题",
            "content": "终止条款内容摘要",
            "notice_period": "提前通知期限，如 提前30天",
            "conditions": "终止条件描述"
        }
    ]
}

注意事项：
- 对于无法从文本中提取的字段，使用 null 或空列表 []
- 金额请尽量提取为数字
- 日期请统一为 YYYY-MM-DD 格式
- 只输出 JSON，不要输出任何解释性文字"""


# ---------------------------------------------------------------------------
# Fallback result
# ---------------------------------------------------------------------------

def _fallback_structured_result(error: Optional[str] = None) -> Dict[str, Any]:
    """LLM 不可用时的回退结果。"""
    return {
        "contract_type": "未识别",
        "parties": [],
        "contract_period": {
            "start_date": None,
            "end_date": None,
            "duration_description": "",
        },
        "payment_terms": [],
        "liability_terms": [],
        "dispute_resolution": [],
        "confidentiality_terms": [],
        "ip_terms": [],
        "termination_terms": [],
        "_meta": {
            "source": "fallback",
            "error": error or "LLM service unavailable",
        },
    }


# ---------------------------------------------------------------------------
# Robust JSON helpers
# ---------------------------------------------------------------------------

def _strip_markdown_codeblock(text: str) -> str:
    """去掉 markdown 代码块包裹 (```json ... ```)"""
    text = text.strip()
    if text.startswith("```"):
        # 去掉第一行 ```json / ```
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        # 去掉末尾 ```
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


def _parse_json_robust(raw: str) -> Dict[str, Any]:
    """
    健壮的 JSON 解析：先直接解析，失败则正则提取最外层 { }。
    对于截断的输出，尝试补全闭合括号。
    """
    # 1. 清理 markdown
    cleaned = _strip_markdown_codeblock(raw)

    # 2. 直接解析
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 3. 正则提取最外层 { }
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if match:
        candidate = match.group()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # 4. 截断修复：逐步补全 }
    # 找到最后一个完整的 key-value 或 array element
    # 简单策略：数 { 和 } 的差值，补全缺少的 }
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

    # 5. 最终兜底：尝试找任意 JSON 对象
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


def _ensure_list(value: Any) -> List[Dict[str, Any]]:
    """确保字段值是 list[dict]，如果为 None 或非列表则返回空列表。"""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return []


def _normalize_structured(data: Dict[str, Any]) -> Dict[str, Any]:
    """规范化提取结果，确保所有字段都存在且类型正确。"""
    template = _fallback_structured_result()
    result = dict(template)
    result.pop("_meta", None)

    # contract_type
    result["contract_type"] = str(data.get("contract_type", "未识别")) or "未识别"

    # parties
    result["parties"] = _ensure_list(data.get("parties"))
    for p in result["parties"]:
        if isinstance(p, dict):
            p.setdefault("name", "")
            p.setdefault("address", "")
            p.setdefault("legal_representative", "")
            p.setdefault("role", "")

    # contract_period
    cp = data.get("contract_period") or {}
    result["contract_period"] = {
        "start_date": cp.get("start_date"),
        "end_date": cp.get("end_date"),
        "duration_description": str(cp.get("duration_description", "")) or "",
    }

    # payment_terms
    result["payment_terms"] = _ensure_list(data.get("payment_terms"))
    for pt in result["payment_terms"]:
        if isinstance(pt, dict):
            pt.setdefault("amount", "")
            pt.setdefault("currency", "CNY")
            pt.setdefault("payment_cycle", "")
            pt.setdefault("payment_method", "")
            pt.setdefault("description", "")

    # liability_terms (LLM may return breach_liability or liability_terms)
    result["liability_terms"] = _ensure_list(data.get("breach_liability") or data.get("liability_terms"))
    for bl in result["liability_terms"]:
        if isinstance(bl, dict):
            bl.setdefault("clause_title", "")
            bl.setdefault("content", "")

    # dispute_resolution
    result["dispute_resolution"] = _ensure_list(data.get("dispute_resolution"))
    for dr in result["dispute_resolution"]:
        if isinstance(dr, dict):
            dr.setdefault("clause_title", "")
            dr.setdefault("content", "")
            dr.setdefault("arbitration_institution", None)
            dr.setdefault("jurisdiction", None)

    # confidentiality_terms
    result["confidentiality_terms"] = _ensure_list(data.get("confidentiality") or data.get("confidentiality_terms"))
    for cf in result["confidentiality_terms"]:
        if isinstance(cf, dict):
            cf.setdefault("clause_title", "")
            cf.setdefault("content", "")
            cf.setdefault("duration", "")

    # ip_terms
    result["ip_terms"] = _ensure_list(data.get("intellectual_property") or data.get("ip_terms"))
    for ip in result["ip_terms"]:
        if isinstance(ip, dict):
            ip.setdefault("clause_title", "")
            ip.setdefault("content", "")
            ip.setdefault("scope", "")

    # termination_terms
    result["termination_terms"] = _ensure_list(data.get("termination") or data.get("termination_terms"))
    for tm in result["termination_terms"]:
        if isinstance(tm, dict):
            tm.setdefault("clause_title", "")
            tm.setdefault("content", "")
            tm.setdefault("notice_period", "")
            tm.setdefault("conditions", "")

    return result


# ---------------------------------------------------------------------------
# Main public API
# ---------------------------------------------------------------------------

async def extract_structured_info(raw_text: str) -> Dict[str, Any]:
    """
    调用 Step 3.5 Flash 提取合同结构化信息。

    Args:
        raw_text: 合同原文

    Returns:
        结构化信息 dict，包含 contract_type / parties / contract_period /
        payment_terms / breach_liability / dispute_resolution /
        confidentiality / intellectual_property / termination
    """
    if not LLM_API_KEY:
        logger.warning("No LLM API key configured, returning fallback structured result")
        return _fallback_structured_result("API key not configured")

    # 构建用户消息
    max_chars = 30000
    user_msg = "请从以下合同文本中提取结构化信息，以 JSON 格式输出：\n\n"
    if len(raw_text) > max_chars:
        user_msg += raw_text[:max_chars] + "\n\n... (文本已截断)"
    else:
        user_msg += raw_text

    max_retries = 3
    backoff_delays = [2, 4, 8]
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{_get_base_url()}/v1/chat/completions",
                    headers={"Authorization": f"Bearer {LLM_API_KEY}"},
                    json={
                        "model": LLM_MODEL,
                        "messages": [
                            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                            {"role": "user", "content": user_msg},
                        ],
                        "temperature": 0.1,
                        "max_tokens": 16384,
                    },
                )

                if resp.status_code == 429 and attempt < max_retries - 1:
                    wait = backoff_delays[attempt]
                    logger.warning(f"Rate limited (429), retrying in {wait}s... (attempt {attempt+1}/{max_retries})")
                    await asyncio.sleep(wait)
                    continue

                resp.raise_for_status()
                data = resp.json()

            content = data["choices"][0]["message"]["content"].strip()
            parsed = _parse_json_robust(content)
            result = _normalize_structured(parsed)

            logger.info(
                f"Structured extraction complete: type={result['contract_type']}, "
                f"parties={len(result['parties'])}, "
                f"payment_terms={len(result['payment_terms'])}"
            )
            return result

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429 and attempt < max_retries - 1:
                wait = backoff_delays[attempt]
                logger.warning(f"Rate limited (429), retrying in {wait}s... (attempt {attempt+1}/{max_retries})")
                await asyncio.sleep(wait)
                continue
            logger.error(f"Structured extraction failed: {e}")
            return _fallback_structured_result(str(e))
        except Exception as e:
            logger.error(f"Structured extraction failed: {e}")
            return _fallback_structured_result(str(e))

    return _fallback_structured_result("Max retries exceeded")
