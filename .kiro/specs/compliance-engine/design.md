# Design: compliance-engine

## rules.yaml
规则库配置文件，7条预置规则+可扩展

## RuleEngine
规则引擎服务：加载YAML规则→逐条执行→返回命中结果[{rule, matched, severity, evidence}]

## ComplianceScorer
评分计算：规则命中+LLM风险结果→各维度子得分→加权总分→风险等级矩阵

## 更新 compliance_engine.py
集成规则引擎结果与LLM结果，合并为最终审查报告

