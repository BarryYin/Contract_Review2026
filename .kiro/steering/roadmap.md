# Roadmap

## Overview
AI驱动的智能合同合规审查工具，面向黑客松评委演示。基于黑客松任务书三阶段要求，当前已完成基础功能（文档解析+LLM分析+PDF报告），需要按评审标准补齐：规则引擎、NER实体识别、结构化JSON、双语分析、批量处理、合同对比、前端交互规范、审计日志、AI使用说明。

## Approach Decision
- **Chosen**: 规则引擎+LLM双轨架构（YAML规则库做确定性检查 + LLM做语义级风险识别）
- **Why**: 评委明确要求"可配置规则库"且"不得仅依赖关键词匹配"，双轨兼顾确定性和智能性
- **Rejected alternatives**: 纯LLM方案（缺规则库，评委扣分）、纯规则方案（无法识别语义风险）

## Scope
- **In**: 规则库YAML+7条预置规则、NER实体高亮、结构化JSON、双语一致性、批量Dashboard、合同对比、一键采纳DOCX导出、审计日志、AI使用说明
- **Out**: 多用户认证、Webhook推送（加分项，时间允许再做）、规则管理Web界面（加分项）

## Constraints
- 黑客松时间限制，优先做评委必看项
- 法律条文引用必须真实，严禁LLM编造
- 不得声称具有法律效力
- 使用 Step API（step-1v-8k OCR + step-3.5-flash 分析）

## Boundary Strategy
- **Why this split**: 按黑客松三阶段评审维度拆分，每个spec对应一个评审阶段的硬性要求
- **Shared seams to watch**: doc-parser输出的结构化JSON是compliance-engine和batch-compare的共同输入；NER实体的前端高亮组件被多个页面复用

## Existing Spec Updates
- [ ] doc-parser -- 补充：结构化JSON字段（签约方/期限/付款等）、NER实体识别、双语一致性分析。Dependencies: none
- [ ] compliance-engine -- 补充：YAML规则库+7条预置规则+规则引擎执行逻辑、评分权重可解释、风险等级矩阵修正。Dependencies: doc-parser
- [ ] report-output -- 补充：前端三栏对比布局、行内高亮+侧边栏、一键采纳+DOCX Track Changes导出、审计日志。Dependencies: compliance-engine

## Direct Implementation Candidates
- [ ] ai-usage-doc -- AI工具使用说明文档（必须提交，简单文档，不需要spec）
- [ ] score-weight-ui -- 评分权重说明UI组件（小改动，直接实现）

## Specs (dependency order)
- [ ] batch-compare -- 批量上传Dashboard(≥5份)+热力图+合同逐条对比。Dependencies: compliance-engine
