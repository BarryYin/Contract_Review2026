"""
T-CE-03: 多维度评分系统 — 基于规则引擎命中 + LLM 问题计算加权分数与风险等级。
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 维度权重配置
# ---------------------------------------------------------------------------

# 规则名 -> 维度映射
RULE_DIMENSION_MAP: Dict[str, str] = {
    "违约金比例上限": "违约责任",
    "付款周期超过60天": "付款条款",
    "保密期限缺失或过短": "保密义务",
    "争议解决条款不明确": "争议解决",
    "知识产权工作成果范围不清晰": "知识产权",
    "免责条款单方面不对等保护": "免责条款",
    "终止条款赋予一方无条件单方解除权": "终止条款",
}

# 维度 -> 默认权重（总和 = 100%）
DEFAULT_WEIGHTS: Dict[str, float] = {
    "违约责任": 0.20,
    "付款条款": 0.15,
    "保密义务": 0.15,
    "知识产权": 0.15,
    "争议解决": 0.10,
    "免责条款": 0.15,
    "终止条款": 0.10,
}

# LLM issue 标题关键词 -> 维度映射（启发式）
LLM_KEYWORD_DIMENSION_MAP: Dict[str, str] = {
    "违约": "违约责任",
    "违约金": "违约责任",
    "滞纳金": "违约责任",
    "赔偿": "违约责任",
    "付款": "付款条款",
    "支付": "付款条款",
    "结算": "付款条款",
    "账期": "付款条款",
    "保密": "保密义务",
    "商业秘密": "保密义务",
    "不泄露": "保密义务",
    "知识产权": "知识产权",
    "著作权": "知识产权",
    "专利": "知识产权",
    "商标": "知识产权",
    "版权": "知识产权",
    "工作成果": "知识产权",
    "争议": "争议解决",
    "仲裁": "争议解决",
    "诉讼": "争议解决",
    "管辖": "争议解决",
    "免责": "免责条款",
    "不可抗力": "免责条款",
    "免除": "免责条款",
    "终止": "终止条款",
    "解除": "终止条款",
    "解约": "终止条款",
}

# 严重程度 -> 扣分值
SEVERITY_PENALTY: Dict[str, float] = {
    "high": 25.0,
    "medium": 15.0,
    "low": 5.0,
}

# 风险等级阈值
RISK_LEVEL_HIGH_THRESHOLD = 3   # >=3 个 high 级问题
RISK_LEVEL_MED_HIGH = 1         # >=1 个 high
RISK_LEVEL_MED_MEDIUM = 5       # >=5 个 medium


# ---------------------------------------------------------------------------
# 核心评分函数
# ---------------------------------------------------------------------------

def _map_rule_to_dimension(rule_name: str) -> str:
    """将规则名映射到评分维度。"""
    return RULE_DIMENSION_MAP.get(rule_name, "其他")


def _map_llm_issue_to_dimension(issue: Dict[str, Any]) -> str:
    """通过关键词启发式将 LLM issue 映射到维度。"""
    # 优先按 title 匹配
    title = issue.get("title", "")
    risk_desc = issue.get("risk_description", "")
    combined = f"{title} {risk_desc}"

    for keyword, dimension in LLM_KEYWORD_DIMENSION_MAP.items():
        if keyword in combined:
            return dimension

    return "其他"


def compute_score(
    rule_hits: List[Any],
    llm_issues: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    基于规则命中 + LLM 问题计算多维度评分。

    Args:
        rule_hits: RuleEngine.evaluate / evaluate_all 返回的 RuleHit 列表
                   （支持 RuleHit 对象或 dict）。
        llm_issues: compliance_engine 返回的 issues 列表（可选）。

    Returns:
        {
            "overall_score": float,        # 0-100 加权总分
            "risk_level": str,             # "high" / "medium" / "low"
            "dimensions": [
                {
                    "name": str,
                    "score": float,
                    "weight": float,
                    "issues_count": int,
                },
                ...
            ],
            "scoring_explanation": str,
        }
    """
    if llm_issues is None:
        llm_issues = []

    # --- 1. 归集各维度扣分 ---
    dimension_penalties: Dict[str, float] = {}
    dimension_issue_counts: Dict[str, int] = {}

    # 规则命中
    for hit in rule_hits:
        if isinstance(hit, dict):
            matched = hit.get("matched", False)
            if not matched:
                continue
            rule_name = hit.get("rule_name", "")
            severity = hit.get("severity", "medium")
        else:
            matched = getattr(hit, "matched", False)
            if not matched:
                continue
            rule_name = getattr(hit, "rule_name", "")
            severity = getattr(hit, "severity", "medium")

        dim = _map_rule_to_dimension(rule_name)
        penalty = SEVERITY_PENALTY.get(severity, 10.0)
        dimension_penalties[dim] = dimension_penalties.get(dim, 0.0) + penalty
        dimension_issue_counts[dim] = dimension_issue_counts.get(dim, 0) + 1

    # LLM 问题
    for issue in llm_issues:
        dim = _map_llm_issue_to_dimension(issue)
        severity = issue.get("severity", "medium")
        penalty = SEVERITY_PENALTY.get(severity, 10.0)
        dimension_penalties[dim] = dimension_penalties.get(dim, 0.0) + penalty
        dimension_issue_counts[dim] = dimension_issue_counts.get(dim, 0) + 1

    # --- 2. 计算各维度分数 ---
    all_dimensions = set(list(DEFAULT_WEIGHTS.keys()) + list(dimension_penalties.keys()))

    dimensions: List[Dict[str, Any]] = []
    for dim_name in sorted(all_dimensions):
        weight = DEFAULT_WEIGHTS.get(dim_name, 0.0)
        penalty_total = dimension_penalties.get(dim_name, 0.0)
        count = dimension_issue_counts.get(dim_name, 0)
        score = max(0.0, 100.0 - penalty_total)

        dimensions.append({
            "name": dim_name,
            "score": round(score, 1),
            "weight": weight,
            "issues_count": count,
        })

    # --- 3. 加权总分 ---
    weight_sum = 0.0
    weighted_score = 0.0
    for dim in dimensions:
        if dim["weight"] > 0:
            weighted_score += dim["score"] * dim["weight"]
            weight_sum += dim["weight"]

    overall_score = round(weighted_score / weight_sum, 1) if weight_sum > 0 else 100.0
    overall_score = max(0.0, min(100.0, overall_score))

    # --- 4. 风险等级 ---
    high_count = 0
    medium_count = 0
    low_count = 0

    for hit in rule_hits:
        sev: Optional[str] = None
        if isinstance(hit, dict):
            if hit.get("matched", False):
                sev = hit.get("severity", "medium")
        else:
            if getattr(hit, "matched", False):
                sev = getattr(hit, "severity", "medium")
        if sev is None:
            continue
        if sev == "high":
            high_count += 1
        elif sev == "medium":
            medium_count += 1
        else:
            low_count += 1

    for issue in llm_issues:
        sev = issue.get("severity", "medium")
        if sev == "high":
            high_count += 1
        elif sev == "medium":
            medium_count += 1
        else:
            low_count += 1

    if high_count >= RISK_LEVEL_HIGH_THRESHOLD:
        risk_level = "high"
    elif high_count >= RISK_LEVEL_MED_HIGH or medium_count >= RISK_LEVEL_MED_MEDIUM:
        risk_level = "medium"
    else:
        risk_level = "low"

    # --- 5. 评分说明 ---
    total_issues = high_count + medium_count + low_count
    explanation_parts: List[str] = []
    explanation_parts.append(
        f"综合评分 {overall_score} 分（满分100），共发现 {total_issues} 个问题"
        f"（高风险 {high_count}，中风险 {medium_count}，低风险 {low_count}）。"
    )
    explanation_parts.append(f"风险等级：{risk_level}。")

    # 列出扣分最严重的维度
    worst_dims = sorted(
        [d for d in dimensions if d["issues_count"] > 0],
        key=lambda d: d["score"],
    )[:3]
    if worst_dims:
        dim_str = "、".join(
            f"{d['name']}（{d['score']}分，{d['issues_count']}个问题）"
            for d in worst_dims
        )
        explanation_parts.append(f"重点关注维度：{dim_str}。")

    scoring_explanation = "".join(explanation_parts)

    result = {
        "overall_score": overall_score,
        "risk_level": risk_level,
        "dimensions": dimensions,
        "scoring_explanation": scoring_explanation,
    }

    logger.info(
        f"Scorer: overall={overall_score}, risk_level={risk_level}, "
        f"issues={total_issues} (h={high_count}, m={medium_count}, l={low_count})"
    )

    return result
