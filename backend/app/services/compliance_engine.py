"""
合规审查引擎：调用 DeepSeek/OpenAI 兼容 LLM 进行合同风险分析。
"""

import os
import json
import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

# DeepSeek API 配置（兼容 OpenAI 格式）
LLM_API_KEY = os.environ.get("DEEPSEEK_API_KEY", os.environ.get("OPENAI_API_KEY", "3tTXOQXTjY42d3wFEk9OTd6J3EmmgFX0akj0doTWcRtw1U92VjkGmPWKWnInvBpts"))
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.stepfun.com")
LLM_MODEL = os.environ.get("LLM_MODEL", "step-3.5-flash")

SYSTEM_PROMPT = """你是一位专业的合同合规审查专家。你的任务是分析合同条款，识别潜在的法律风险和合规问题。

你需要按以下JSON格式输出分析结果：
{
    "contract_type": "合同类型（如：采购合同、服务合同、保密协议、劳动合同等）",
    "summary": "200字以内的审查摘要，概括主要风险",
    "risk_score": 0-100的整数（0=无风险，100=极高风险），
    "issues": [
        {
            "clause": "条款标题或位置",
            "risk_type": "风险类型（如：付款风险、违约风险、知识产权风险等）",
            "severity": "low/medium/high",
            "description": "50-150字的问题描述",
            "suggestion": "50-150字的修改建议"
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

注意：
- risk_score 基于问题严重程度和数量综合评估
- 每个 issue 的 description 必须具体说明问题所在
- suggestion 必须给出可操作的修改建议
- 只输出 JSON，不要输出其他内容
"""


async def analyze_contract(raw_text: str, clauses: list[dict] = None) -> dict:
    """
    调用 LLM 分析合同文本，返回审查结果。
    
    Args:
        raw_text: 合同原文
        clauses: 结构化条款（可选，帮助 LLM 定位）
    
    Returns:
        审查结果 dict，包含 contract_type, summary, risk_score, issues
    """
    if not LLM_API_KEY:
        logger.warning("No LLM API key configured, returning fallback result")
        return _fallback_result(raw_text)

    # 构建用户消息
    user_msg = f"请审查以下合同文本并输出JSON格式的审查报告：\n\n"
    
    if clauses and len(clauses) > 0:
        # 带条款结构，帮助 LLM 定位
        user_msg += "【合同条款】\n\n"
        for i, clause in enumerate(clauses, 1):
            if isinstance(clause, dict):
                title = clause.get("title", "")
                content = clause.get("content", "")
            else:
                title = f"条款 {idx+1}"
                content = str(clause)
            user_msg += f"{title}\n{content}\n\n"
    else:
        # 直接用原文
        # 截断超长文本（DeepSeek 最大 64K，留余量给 system prompt + output）
        max_chars = 30000
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
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_msg},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 16384,
                },
            )
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
        assert "contract_type" in result
        assert "summary" in result
        assert "risk_score" in result
        assert "issues" in result
        
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
        
        # 给每个 issue 加 id
        for i, issue in enumerate(result["issues"], 1):
            issue["id"] = f"issue_{i}"
        
        logger.info(f"LLM analysis complete: score={result['risk_score']}, issues={len(result['issues'])}")
        return result

    except Exception as e:
        logger.error(f"LLM analysis failed: {e}")
        return _fallback_result(raw_text, error=str(e))


def _fallback_result(raw_text: str, error: str = None) -> dict:
    """LLM 不可用时的回退结果。"""
    return {
        "contract_type": "未识别",
        "summary": f"AI审查暂不可用{'（' + error + '）' if error else ''}。已上传合同文本，请稍后重试或联系管理员配置LLM API密钥。",
        "risk_score": 0,
        "risk_level": "low",
        "issues": [],
    }
