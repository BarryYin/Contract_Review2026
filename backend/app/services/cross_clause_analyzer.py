"""
跨条款连锁风险分析器：基于结构化提取数据进行程序化的跨条款逻辑一致性校验。
作为 LLM 审查的补充（双重保障），不依赖 LLM 调用，纯规则驱动。

检查维度：
1. 期限冲突 — 保密期限 vs 合同期限
2. 付款与交付时间矛盾
3. 违约责任 vs 免责范围重叠
4. 终止通知期矛盾
5. 管辖冲突（或裁或审）
6. 结构化数据字段缺失检测
"""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

class CrossClauseIssue:
    """跨条款风险条目。"""

    __slots__ = (
        "issue_type",
        "severity",
        "title",
        "description",
        "clause_refs",
        "detail",
    )

    def __init__(
        self,
        issue_type: str,
        severity: str,
        title: str,
        description: str,
        clause_refs: List[str],
        detail: str = "",
    ) -> None:
        self.issue_type = issue_type
        self.severity = severity
        self.title = title
        self.description = description
        self.clause_refs = clause_refs
        self.detail = detail

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue_type": self.issue_type,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "clause_refs": self.clause_refs,
            "detail": self.detail,
        }


# ---------------------------------------------------------------------------
# 辅助工具
# ---------------------------------------------------------------------------

def _parse_duration_months(duration_str: str) -> Optional[int]:
    """
    尝试从文本描述中解析月数。
    支持："2年" -> 24, "6个月" -> 6, "三年" -> 36 等。
    无法解析返回 None。
    """
    if not duration_str:
        return None
    duration_str = duration_str.strip()

    # X年
    m = re.search(r"(\d+)\s*[年]", duration_str)
    if m:
        return int(m.group(1)) * 12
    m = re.search(r"[一二三四五六七八九十]+\s*年", duration_str)
    if m:
        cn_map = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
                  "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
        cn_str = m.group(0).replace("年", "").strip()
        val = cn_map.get(cn_str)
        if val:
            return val * 12

    # X个月
    m = re.search(r"(\d+)\s*个?月", duration_str)
    if m:
        return int(m.group(1))

    return None


def _parse_days(period_str: str) -> Optional[int]:
    """
    尝试从文本描述中解析天数。
    支持："30天" -> 30, "提前15日" -> 15 等。
    """
    if not period_str:
        return None
    m = re.search(r"(\d+)\s*[天日]", period_str)
    if m:
        return int(m.group(1))
    return None


# ---------------------------------------------------------------------------
# 核心检查函数
# ---------------------------------------------------------------------------

def _check_confidentiality_vs_contract_period(
    structured_info: Dict[str, Any],
    raw_text: str,
) -> Optional[CrossClauseIssue]:
    """
    检查保密期限与合同期限是否一致。
    风险场景：保密期短于合同期 / 合同终止后保密义务未延续。
    """
    # 提取保密期限
    conf_terms = structured_info.get("confidentiality_terms", [])
    conf_duration = None
    conf_clause_title = ""
    for ct in conf_terms:
        if isinstance(ct, dict):
            dur = ct.get("duration", "")
            if dur:
                conf_duration = _parse_duration_months(dur)
                conf_clause_title = ct.get("clause_title", "保密条款")
                break

    # 提取合同期限
    cp = structured_info.get("contract_period", {})
    cp_start = cp.get("start_date")
    cp_end = cp.get("end_date")
    cp_desc = cp.get("duration_description", "")

    contract_months = None
    if cp_start and cp_end:
        try:
            from datetime import datetime
            start = datetime.fromisoformat(str(cp_start))
            end = datetime.fromisoformat(str(cp_end))
            delta_days = (end - start).days
            contract_months = max(1, delta_days // 30)
        except (ValueError, TypeError):
            pass

    if contract_months is None and cp_desc:
        contract_months = _parse_duration_months(cp_desc)

    # 两个都解析不出来就跳过
    if conf_duration is None and contract_months is None:
        return None

    # 保密期限缺失但合同有期限
    if conf_duration is None and contract_months is not None:
        return CrossClauseIssue(
            issue_type="confidentiality_period_missing",
            severity="medium",
            title="保密期限未明确约定",
            description="合同约定了有效期限，但保密条款未设定明确的保密期限，可能导致合同终止后保密义务失效。",
            clause_refs=["合同期限条款", conf_clause_title or "保密条款"],
            detail=f"合同期限约 {contract_months} 个月，但保密期限未明确。",
        )

    # 保密期短于合同期
    if conf_duration is not None and contract_months is not None:
        if conf_duration < contract_months:
            return CrossClauseIssue(
                issue_type="confidentiality_shorter_than_contract",
                severity="high",
                title="保密期限短于合同期限",
                description="保密义务在合同到期前就已终止，合同后期的敏感信息可能无法得到保护。",
                clause_refs=["合同期限条款", conf_clause_title or "保密条款"],
                detail=f"合同期限约 {contract_months} 个月，保密期限仅 {conf_duration} 个月。",
            )

    return None


def _check_payment_vs_delivery(
    structured_info: Dict[str, Any],
    raw_text: str,
) -> Optional[CrossClauseIssue]:
    """
    检查付款条件中的周期是否过长（超过60天），结合交付条款判断。
    """
    payment_terms = structured_info.get("payment_terms", [])

    long_cycle_found = False
    max_days = 0
    pay_desc = ""
    for pt in payment_terms:
        if not isinstance(pt, dict):
            continue
        cycle = pt.get("payment_cycle", "")
        desc = pt.get("description", "")
        full_text = f"{cycle} {desc}"

        days = _parse_days(full_text)
        if days and days > 60:
            long_cycle_found = True
            max_days = max(max_days, days)
            pay_desc = full_text

    if not long_cycle_found:
        # 回退到正则在原文中搜索
        m = re.search(r"(?:付款|支付|结算).{0,20}?(\d{2,3})\s*[天日]", raw_text)
        if m:
            d = int(m.group(1))
            if d > 60:
                long_cycle_found = True
                max_days = d
                pay_desc = m.group(0)

    if long_cycle_found:
        return CrossClauseIssue(
            issue_type="payment_cycle_excessive",
            severity="medium",
            title="付款周期超过60天",
            description="付款周期过长，存在资金占用风险。根据《保障中小企业款项支付条例》，建议控制在60天以内。",
            clause_refs=["付款条款"],
            detail=f"检测到付款周期约 {max_days} 天：{pay_desc}",
        )

    return None


def _check_liability_vs_exemption(
    structured_info: Dict[str, Any],
    raw_text: str,
) -> Optional[CrossClauseIssue]:
    """
    检查违约责任条款与免责条款是否存在范围重叠/矛盾。
    如果违约责任规定了赔偿范围，而免责条款排除了类似范围的赔偿责任，
    则两者可能矛盾。
    """
    liability_terms = structured_info.get("liability_terms", [])

    # 检查原文中是否同时出现违约责任和免责条款
    has_liability = False
    has_exemption = False
    liability_ref = ""
    exemption_ref = ""

    for lt in liability_terms:
        if isinstance(lt, dict):
            content = lt.get("content", "")
            title = lt.get("clause_title", "")
            if content:
                has_liability = True
                liability_ref = title or "违约责任条款"

    # 在原文中搜索免责条款
    exemption_keywords = ["免责", "不承担责任", "免除责任", "不承担赔偿"]
    for kw in exemption_keywords:
        idx = raw_text.find(kw)
        if idx >= 0:
            has_exemption = True
            # 尝试定位到条款标题
            context = raw_text[max(0, idx - 50):idx + 50]
            title_match = re.search(r"第[一二三四五六七八九十\d]+条\s*([^\n]{2,20})", context)
            exemption_ref = title_match.group(0) if title_match else "免责条款"
            break

    if has_liability and has_exemption:
        # 检查免责条款是否过于宽泛（排除了所有损失赔偿）
        broad_exemption_patterns = [
            r"任何.{0,10}(?:损失|赔偿|责任)",
            r"不承担任何(?:赔偿|责任)",
            r"免除.*?全部.*?(?:责任|赔偿)",
            r"无论.*?原因.*?不承担",
        ]
        for pat in broad_exemption_patterns:
            if re.search(pat, raw_text):
                return CrossClauseIssue(
                    issue_type="liability_exemption_conflict",
                    severity="high",
                    title="违约责任与免责条款存在潜在冲突",
                    description="合同同时约定了违约赔偿责任和宽泛的免责条款，可能导致违约责任条款在部分场景下被架空。",
                    clause_refs=[liability_ref, exemption_ref],
                    detail="免责条款排除了广泛的赔偿责任，与违约责任条款可能产生冲突。",
                )

    return None


def _check_termination_notice(
    structured_info: Dict[str, Any],
    raw_text: str,
) -> Optional[CrossClauseIssue]:
    """
    检查终止条款中的通知期限是否合理、是否存在一方无需通知而另一方需要长期通知的不对等。
    """
    termination_terms = structured_info.get("termination_terms", [])
    notice_periods = []

    for tt in termination_terms:
        if not isinstance(tt, dict):
            continue
        np_str = tt.get("notice_period", "")
        conditions = tt.get("conditions", "")
        title = tt.get("clause_title", "终止条款")
        full = f"{np_str} {conditions}"
        days = _parse_days(full)
        if days is not None:
            notice_periods.append({
                "days": days,
                "title": title,
                "text": full,
            })

    # 检查是否存在不对等的通知期（差异超过3倍）
    if len(notice_periods) >= 2:
        days_list = [np["days"] for np in notice_periods]
        min_d = min(days_list)
        max_d = max(days_list)
        if min_d > 0 and max_d / min_d >= 3:
            return CrossClauseIssue(
                issue_type="termination_notice_imbalance",
                severity="medium",
                title="终止通知期限不对等",
                description="不同终止条件的通知期限差异过大，可能构成权利义务不对等。",
                clause_refs=[np["title"] for np in notice_periods],
                detail=f"通知期限范围：{min_d}天 至 {max_d}天，差异达到 {max_d/min_d:.1f} 倍。",
            )

    # 检查是否存在无条件终止（无通知期要求）
    unconditional_patterns = [
        r"(?:随时|有权|可以).{0,10}?(?:解除|终止).{0,20}?(?:无需|不必|不须)",
        r"(?:随时|有权|可以).{0,10}?(?:解除|终止)(?!.*通知)",
    ]
    for pat in unconditional_patterns:
        m = re.search(pat, raw_text)
        if m and notice_periods:
            # 一方无条件终止，另一方需要通知期
            return CrossClauseIssue(
                issue_type="termination_unconditional_vs_notice",
                severity="high",
                title="终止条件不对等：一方无条件，一方需通知",
                description="合同中一方可以无条件终止，而另一方需要提前通知，构成权利不对等。",
                clause_refs=[np["title"] for np in notice_periods] + ["终止条款"],
                detail=f"一方需提前通知（最长 {max(np['days'] for np in notice_periods)} 天），另一方可无条件终止。",
            )

    return None


def _check_dispute_resolution_conflict(
    structured_info: Dict[str, Any],
    raw_text: str,
) -> Optional[CrossClauseIssue]:
    """
    检查争议解决条款是否同时约定仲裁和诉讼（"或裁或审"无效）。
    """
    has_arbitration = False
    has_litigation = False
    clause_ref = ""

    # 从结构化数据获取
    dispute_terms = structured_info.get("dispute_resolution", [])
    for dt in dispute_terms:
        if isinstance(dt, dict):
            arb = dt.get("arbitration_institution")
            jur = dt.get("jurisdiction")
            title = dt.get("clause_title", "争议解决条款")
            if arb:
                has_arbitration = True
                clause_ref = title
            if jur:
                has_litigation = True
                clause_ref = title

    # 回退到文本搜索
    if not has_arbitration:
        has_arbitration = bool(re.search(r"仲裁", raw_text))
    if not has_litigation:
        has_litigation = bool(re.search(r"诉讼|管辖|向.*?法院", raw_text))

    if has_arbitration and has_litigation:
        return CrossClauseIssue(
            issue_type="arbitration_litigation_conflict",
            severity="high",
            title="争议解决条款'或裁或审'无效",
            description="同一争议解决条款同时约定了仲裁和诉讼，根据《仲裁法》和司法解释，该类'或裁或审'条款无效。",
            clause_refs=[clause_ref or "争议解决条款"],
            detail="条款同时出现仲裁和诉讼约定，构成'或裁或审'无效情形。",
        )

    return None


def _check_missing_critical_clauses(
    structured_info: Dict[str, Any],
    raw_text: str,
) -> List[CrossClauseIssue]:
    """
    检查结构化数据中关键字段是否缺失（可能意味着合同本身缺失这些条款，
    或者 LLM 提取失败）。
    """
    issues = []

    checks = [
        ("parties", "当事人信息", "合同未明确约定当事人信息（名称、地址、法定代表人），可能导致合同主体不明。"),
        ("contract_period", "合同期限", "合同未约定有效期限，可能导致合同关系长期悬而未决。"),
        ("payment_terms", "付款条款", "合同未约定付款条件和方式，可能导致付款纠纷。"),
        ("liability_terms", "违约责任", "合同未约定违约责任，可能导致违约后缺乏救济手段。"),
        ("dispute_resolution", "争议解决", "合同未约定争议解决方式，发生纠纷时可能增加维权成本。"),
    ]

    for field, name, desc in checks:
        val = structured_info.get(field)
        is_empty = (
            val is None
            or val == []
            or (isinstance(val, dict) and all(v is None or v == "" for v in val.values()))
        )
        if is_empty:
            # 二次确认：在原文中搜索相关关键词
            keyword_map = {
                "parties": ["甲方", "乙方", "委托方", "受托方"],
                "contract_period": ["有效期", "合同期限", "履行期限"],
                "payment_terms": ["付款", "支付", "报酬"],
                "liability_terms": ["违约", "赔偿", "滞纳金"],
                "dispute_resolution": ["争议", "仲裁", "管辖"],
            }
            keywords = keyword_map.get(field, [])
            found_in_text = any(kw in raw_text for kw in keywords)

            if not found_in_text:
                issues.append(CrossClauseIssue(
                    issue_type=f"missing_{field}",
                    severity="medium",
                    title=f"缺失{name}条款",
                    description=desc,
                    clause_refs=[],
                    detail="结构化提取和原文搜索均未发现该类条款。",
                ))

    return issues


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def analyze_cross_clause_risks(
    structured_info: Dict[str, Any],
    raw_text: str,
) -> List[Dict[str, Any]]:
    """
    对结构化提取结果执行跨条款逻辑一致性校验。

    Args:
        structured_info: structured_parser 提取的结构化数据
        raw_text: 合同原文

    Returns:
        跨条款风险列表，每项为 dict（含 issue_type / severity / title /
        description / clause_refs / detail）
    """
    issues: List[CrossClauseIssue] = []

    # 1. 保密期限 vs 合同期限
    result = _check_confidentiality_vs_contract_period(structured_info, raw_text)
    if result:
        issues.append(result)

    # 2. 付款周期与交付时间
    result = _check_payment_vs_delivery(structured_info, raw_text)
    if result:
        issues.append(result)

    # 3. 违约责任 vs 免责范围
    result = _check_liability_vs_exemption(structured_info, raw_text)
    if result:
        issues.append(result)

    # 4. 终止通知期限
    result = _check_termination_notice(structured_info, raw_text)
    if result:
        issues.append(result)

    # 5. 或裁或审
    result = _check_dispute_resolution_conflict(structured_info, raw_text)
    if result:
        issues.append(result)

    # 6. 关键条款缺失
    missing_issues = _check_missing_critical_clauses(structured_info, raw_text)
    issues.extend(missing_issues)

    logger.info(f"Cross-clause analysis: found {len(issues)} issues")

    return [issue.to_dict() for issue in issues]
