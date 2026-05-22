"""
T-CE-02: 规则引擎 — 加载 rules.yaml 预置规则并对合同条款进行关键词/正则检查。
语义检查仅做标记，由 compliance_engine 调用 LLM 完成。
"""

import os
import re
import logging
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

class RuleHit:
    """单条规则的检查结果。"""

    __slots__ = (
        "rule_name",
        "severity",
        "matched",
        "evidence",
        "legal_basis",
        "risk_description",
    )

    def __init__(
        self,
        rule_name: str,
        severity: str,
        matched: bool,
        evidence: str,
        legal_basis: str,
        risk_description: str,
    ) -> None:
        self.rule_name = rule_name
        self.severity = severity
        self.matched = matched
        self.evidence = evidence
        self.legal_basis = legal_basis
        self.risk_description = risk_description

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_name": self.rule_name,
            "severity": self.severity,
            "matched": self.matched,
            "evidence": self.evidence,
            "legal_basis": self.legal_basis,
            "risk_description": self.risk_description,
        }


# ---------------------------------------------------------------------------
# 规则引擎
# ---------------------------------------------------------------------------

class RuleEngine:
    """加载 YAML 规则并对文本执行关键词 / 正则检查。"""

    def __init__(self, rules_path: Optional[str] = None) -> None:
        if rules_path is None:
            rules_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "core",
                "rules.yaml",
            )
        self._rules: List[Dict[str, Any]] = []
        self._load_rules(rules_path)

    # ---- 加载 ----

    def _load_rules(self, path: str) -> None:
        """从 YAML 文件加载规则，带完整错误处理。"""
        if not os.path.isfile(path):
            logger.error(f"Rules file not found: {path}")
            return

        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
        except yaml.YAMLError as exc:
            logger.error(f"Failed to parse rules YAML: {exc}")
            return
        except OSError as exc:
            logger.error(f"Failed to read rules file: {exc}")
            return

        if not isinstance(data, dict) or "rules" not in data:
            logger.error("Invalid rules.yaml structure: missing top-level 'rules' key")
            return

        raw_rules = data["rules"]
        if not isinstance(raw_rules, list):
            logger.error("Invalid rules.yaml: 'rules' should be a list")
            return

        # 基本校验
        valid_rules: List[Dict[str, Any]] = []
        for idx, rule in enumerate(raw_rules):
            if not isinstance(rule, dict):
                logger.warning(f"Rule #{idx + 1} is not a dict, skipped")
                continue
            name = rule.get("name")
            if not name:
                logger.warning(f"Rule #{idx + 1} missing 'name', skipped")
                continue
            if "severity" not in rule:
                logger.warning(f"Rule '{name}' missing 'severity', defaulting to 'medium'")
                rule["severity"] = "medium"
            if "contract_types" not in rule:
                logger.warning(f"Rule '{name}' missing 'contract_types', defaulting to ['all']")
                rule["contract_types"] = ["all"]
            if "check_config" not in rule:
                logger.warning(f"Rule '{name}' missing 'check_config', skipped")
                continue
            valid_rules.append(rule)

        self._rules = valid_rules
        logger.info(f"Loaded {len(self._rules)} rules from {path}")

    @property
    def rules(self) -> List[Dict[str, Any]]:
        """返回已加载的规则列表（只读副本）。"""
        return list(self._rules)

    # ---- 过滤 ----

    def _applicable_rules(self, contract_type: str) -> List[Dict[str, Any]]:
        """根据合同类型过滤适用规则。"""
        result: List[Dict[str, Any]] = []
        for rule in self._rules:
            types = rule.get("contract_types", [])
            if "all" in types or contract_type in types:
                result.append(rule)
        return result

    # ---- 检查方法 ----

    def _check_keyword(
        self,
        text: str,
        config: Dict[str, Any],
    ) -> bool:
        """关键词检查：text 中出现任一关键词即命中。"""
        keywords = config.get("keywords", [])
        logic = config.get("logic", "any")
        if not keywords:
            return False

        hits = [kw for kw in keywords if kw in text]

        if logic == "all":
            return len(hits) == len(keywords)
        # default: any
        return len(hits) > 0

    def _check_regex(
        self,
        text: str,
        config: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """正则检查：返回 match 信息或 None。"""
        pattern = config.get("pattern", "")
        if not pattern:
            return None
        try:
            m = re.search(pattern, text)
        except re.error as exc:
            logger.warning(f"Invalid regex pattern '{pattern}': {exc}")
            return None

        if m is None:
            return None

        groups = m.groups()
        return {
            "full_match": m.group(0),
            "groups": groups,
        }

    # ---- 单条规则评估 ----

    def _evaluate_one(
        self,
        rule: Dict[str, Any],
        text: str,
    ) -> RuleHit:
        """对一段文本执行单条规则的所有检查。"""
        name: str = rule["name"]
        severity: str = rule.get("severity", "medium")
        legal_basis: str = rule.get("legal_basis", "")
        risk_template: str = rule.get("risk_description_template", "")
        config: Dict[str, Any] = rule.get("check_config", {})

        evidences: List[str] = []
        matched = False

        # --- 关键词检查 ---
        kw_config = config.get("keyword")
        if kw_config:
            if self._check_keyword(text, kw_config):
                matched = True
                matched_kws = [kw for kw in kw_config.get("keywords", []) if kw in text]
                evidences.append(f"关键词命中: {', '.join(matched_kws)}")

        # --- 正则检查 ---
        rx_config = config.get("regex")
        if rx_config:
            rx_result = self._check_regex(text, rx_config)
            if rx_result is not None:
                matched = True
                evidences.append(f"正则匹配: {rx_result['full_match']}")

        # --- 语义检查标记 ---
        sem_config = config.get("semantic")
        if sem_config:
            # 语义检查的 description 会被收集，传给 LLM 做深度分析
            # 此处标记命中，让 review_service 知道需要 LLM 语义审查
            matched = True
            sem_desc = sem_config.get("description", "") if isinstance(sem_config, dict) else ""
            if sem_desc:
                evidences.append(f"[语义检查]: {sem_desc[:100]}")
            else:
                evidences.append("[语义检查待LLM分析]")

        # 构造风险描述
        risk_description = risk_template
        if matched and not risk_description:
            risk_description = f"规则「{name}」检测到潜在风险。"

        evidence_str = "; ".join(evidences) if evidences else "未匹配"

        return RuleHit(
            rule_name=name,
            severity=severity,
            matched=matched,
            evidence=evidence_str,
            legal_basis=legal_basis,
            risk_description=risk_description if matched else "",
        )

    # ---- 公共 API ----

    def evaluate(
        self,
        clauses: List[Dict[str, Any]],
        contract_type: str,
    ) -> List[RuleHit]:
        """
        对条款列表执行规则评估。

        Args:
            clauses: 条款列表，每项需含 ``content`` 字段（str）。
            contract_type: 合同类型，如 "采购合同"。

        Returns:
            命中结果列表。
        """
        applicable = self._applicable_rules(contract_type)
        if not applicable:
            logger.info(f"No applicable rules for contract type: {contract_type}")
            return []

        all_hits: List[RuleHit] = []

        for clause in clauses:
            text = ""
            if isinstance(clause, dict):
                title = clause.get("title", "")
                content = clause.get("content", "")
                text = f"{title}\n{content}" if title else str(content)
            else:
                text = str(clause)

            if not text.strip():
                continue

            for rule in applicable:
                hit = self._evaluate_one(rule, text)
                if hit.matched:
                    # 如果有条款标题，附加到 evidence
                    if isinstance(clause, dict) and clause.get("title"):
                        hit.evidence = f"[{clause['title']}] {hit.evidence}"
                    all_hits.append(hit)

        logger.info(
            f"RuleEngine.evaluate: {len(clauses)} clauses, "
            f"{len(applicable)} rules -> {len(all_hits)} hits"
        )
        return all_hits

    def evaluate_all(
        self,
        text: str,
        contract_type: str,
    ) -> List[RuleHit]:
        """
        对整段合同文本执行所有适用规则。

        等价于将整段文本视为单个条款进行评估。

        Args:
            text: 合同全文。
            contract_type: 合同类型。

        Returns:
            命中结果列表。
        """
        applicable = self._applicable_rules(contract_type)
        if not applicable:
            logger.info(f"No applicable rules for contract type: {contract_type}")
            return []

        hits: List[RuleHit] = []
        for rule in applicable:
            hit = self._evaluate_one(rule, text)
            hits.append(hit)

        matched_count = sum(1 for h in hits if h.matched)
        logger.info(
            f"RuleEngine.evaluate_all: {len(applicable)} rules -> {matched_count} matched"
        )
        return hits


    # ---- 语义检查辅助 ----

    def get_semantic_prompts(self, contract_type: str) -> list[dict]:
        """
        获取指定合同类型的所有含 semantic 配置的规则，用于传给 LLM 做深度语义检查。
        返回 [{rule_name, severity, semantic_description}, ...]
        """
        applicable = self._applicable_rules(contract_type)
        prompts = []
        for rule in applicable:
            config = rule.get("check_config", {})
            sem = config.get("semantic")
            if sem and isinstance(sem, dict):
                desc = sem.get("description", "")
                if desc:
                    prompts.append({
                        "rule_name": rule["name"],
                        "severity": rule.get("severity", "medium"),
                        "semantic_description": desc,
                    })
        return prompts


# ---------------------------------------------------------------------------
# 模块级单例（延迟初始化）
# ---------------------------------------------------------------------------

_engine: Optional[RuleEngine] = None


def get_rule_engine() -> RuleEngine:
    """获取全局规则引擎实例（首次调用时初始化）。"""
    global _engine
    if _engine is None:
        _engine = RuleEngine()
    return _engine
