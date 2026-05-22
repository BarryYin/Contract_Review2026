"""
合规审查引擎：调用 Step 3.5 Flash LLM 进行合同风险分析。
T-RO-01: 输出三要素格式（风险描述 + 法律依据 + 修改示例）
"""

import os
import json
import logging
import asyncio
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

# Step 3.5 Flash API 配置（兼容 OpenAI 格式）
LLM_API_KEY = os.environ.get("LLM_API_KEY") or os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.stepfun.com")
LLM_MODEL = os.environ.get("LLM_MODEL", "step-3.5-flash")

SYSTEM_PROMPT = """你是一位专业的合同合规审查专家，精通中国法律法规。你的任务是分析合同条款，识别潜在的法律风险和合规问题。

你需要严格按以下 JSON 格式输出分析结果（不要输出任何 JSON 之外的内容）：
{
    "contract_type": "合同类型（如：采购合同、服务合同、保密协议、劳动合同等）",
    "summary": "200字以内的审查摘要，概括主要风险",
    "risk_score": 0-100的整数（0=无风险，100=极高风险）,
    "issues": [
        {
            "title": "简明的问题标题（10-20字）",
            "clause_reference": "条款标题或位置，如'第四条 付款方式'",
            "page_location": "该条款在原文中的位置，格式如'第3页 第二段'或'第5页 第2条'（尽量定位到页码和段落）",
            "severity": "low / medium / high",
            "risk_description": "用通俗易懂的非法律专业语言说明该条款存在什么风险、如果签署可能导致什么后果（50-200字）",
            "legal_basis": "引用具体法条，格式如：依据《民法典》第577条、参照《合同法》第xxx条。必须准确引用真实法条，禁止编造不存在的法条",
            "modification_example": {
                "original": "合同中的原文（完整摘录有问题的部分）",
                "suggested": "建议修改后的文本（给出具体可替换的修改版本）"
            }
        }
    ]
}

审查要点：
1. 付款条件和违约金是否合理
2. 知识产权归属是否明确
3. 保密条款和竞业限制
4. 争议解决和管辖条款
5. 合同终止和解除条件
6. 免责条款是否过于宽泛
7. 是否存在法律禁止的条款
8. 权利义务是否对等

三要素输出要求：
- risk_description（风险描述）：用非法律专业语言，让普通读者也能理解风险和后果
- legal_basis（法律依据）：必须引用真实存在的具体法条，格式如"依据《民法典》第577条"。绝对禁止编造法条编号
- modification_example（修改示例）：original 字段摘录合同原文，suggested 字段给出修改后的完整文本

注意：
- risk_score 基于问题严重程度和数量综合评估
- 每个 issue 必须同时包含 risk_description、legal_basis、modification_example 三个字段
- legal_basis 引用的法条必须真实准确，宁可只引用模糊依据也不能编造法条编号
- modification_example 的 original 应完整摘录原文中有问题的段落，suggested 应是可直接替换的修改版本
- 只输出 JSON，不要输出其他内容
"""


async def analyze_contract(raw_text: str, clauses: list[dict] = None) -> dict:
    """
    调用 LLM 分析合同文本，返回审查结果。

    Args:
        raw_text: 合同原文
        clauses: 结构化条款（可选，帮助 LLM 定位）

    Returns:
        审查结果 dict，包含:
        - contract_type: str
        - summary: str
        - risk_score: int (0-100)
        - risk_level: str ("low"/"medium"/"high")
        - issues: list of {
            id, title, clause_reference, severity,
            risk_description, legal_basis,
            modification_example: {original, suggested}
          }
    """
    if not LLM_API_KEY:
        logger.warning("No LLM API key configured, returning fallback result")
        return _fallback_result(raw_text)

    # 构建用户消息
    user_msg = "请审查以下合同文本并输出JSON格式的审查报告：\n\n"

    if clauses and len(clauses) > 0:
        # 带条款结构，帮助 LLM 定位
        user_msg += "【合同条款】\n\n"
        for i, clause in enumerate(clauses, 1):
            if isinstance(clause, dict):
                title = clause.get("title", "")
                content = clause.get("content", "")
            else:
                title = f"条款 {i}"
                content = str(clause)
            user_msg += f"{title}\n{content}\n\n"
    else:
        # 直接用原文
        # 截断超长文本（Step 3.5 Flash 最大 64K，留余量给 system prompt + output）
        max_chars = 30000
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
                    f"{LLM_BASE_URL}/v1/chat/completions",
                    headers={"Authorization": f"Bearer {LLM_API_KEY}"},
                    json={
                        "model": LLM_MODEL,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_msg},
                        ],
                        "temperature": 0.1,
                        "max_tokens": 16384,
                    },
                )

                if resp.status_code == 429 and attempt < max_retries - 1:
                    wait = backoff_delays[attempt]
                    logger.warning(f"Compliance rate limited (429), retrying in {wait}s... (attempt {attempt+1}/{max_retries})")
                    await asyncio.sleep(wait)
                    continue

                resp.raise_for_status()
                data = resp.json()

            content = data["choices"][0]["message"]["content"].strip()

            # 清理 markdown 代码块包裹
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            # 尝试直接解析，失败则用正则提取
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                import re
                match = re.search(r'\{[\s\S]*\}', content)
                if match:
                    result = json.loads(match.group())
                else:
                    raise

            # 校验必要字段
            assert "contract_type" in result, "Missing contract_type"
            assert "summary" in result, "Missing summary"
            assert "risk_score" in result, "Missing risk_score"
            assert "issues" in result, "Missing issues"

            # 确保 risk_score 在 0-100 范围
            result["risk_score"] = max(0, min(100, int(result["risk_score"])))

            # 推断 risk_level
            score = result["risk_score"]
            if score >= 70:
                result["risk_level"] = "high"
            elif score >= 40:
                result["risk_level"] = "medium"
            else:
                result["risk_level"] = "low"

            # 规范化每个 issue 的字段（三要素结构）
            for i, issue in enumerate(result["issues"], 1):
                issue["id"] = f"issue_{i}"

                # 兼容旧格式：如果 LLM 仍返回 description/suggestion，做迁移
                if "risk_description" not in issue and "description" in issue:
                    issue["risk_description"] = issue.pop("description", "")
                if "legal_basis" not in issue:
                    issue["legal_basis"] = ""
                if "modification_example" not in issue and "suggestion" in issue:
                    issue["modification_example"] = {
                        "original": "",
                        "suggested": issue.pop("suggestion", ""),
                    }

                # 确保三要素字段存在
                issue.setdefault("title", f"问题 {i}")
                issue.setdefault("clause_reference", "")
                issue.setdefault("page_location", "")
                issue.setdefault("severity", "medium")
                issue.setdefault("risk_description", "")
                issue.setdefault("legal_basis", "")

                # 确保 modification_example 结构正确
                if not isinstance(issue.get("modification_example"), dict):
                    issue["modification_example"] = {
                        "original": "",
                        "suggested": "",
                    }
                else:
                    me = issue["modification_example"]
                    me.setdefault("original", "")
                    me.setdefault("suggested", "")

                # 移除旧字段避免混淆
                issue.pop("description", None)
                issue.pop("suggestion", None)
                issue.pop("clause", None)
                issue.pop("risk_type", None)

            logger.info(f"LLM analysis complete: score={result['risk_score']}, issues={len(result['issues'])}")
            return result

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429 and attempt < max_retries - 1:
                wait = backoff_delays[attempt]
                logger.warning(f"Compliance rate limited (429), retrying in {wait}s... (attempt {attempt+1}/{max_retries})")
                await asyncio.sleep(wait)
                continue
            logger.error(f"LLM analysis failed: {e}")
            return _fallback_result(raw_text, error=str(e))
        except Exception as e:
            if attempt < max_retries - 1:
                wait = backoff_delays[attempt]
                logger.warning(f"LLM analysis error, retrying in {wait}s... (attempt {attempt+1}/{max_retries}): {e}")
                await asyncio.sleep(wait)
                continue
            logger.error(f"LLM analysis failed after {max_retries} retries: {e}")
            return _fallback_result(raw_text, error=str(e))

    return _fallback_result(raw_text, error="Max retries exceeded")


def _fallback_result(raw_text: str, error: str = None) -> dict:
    """LLM 不可用时的回退结果。"""
    return {
        "contract_type": "未识别",
        "summary": f"AI审查暂不可用{'（' + error + '）' if error else ''}。已上传合同文本，请稍后重试或联系管理员配置LLM API密钥。",
        "risk_score": 0,
        "risk_level": "low",
        "issues": [],
    }
