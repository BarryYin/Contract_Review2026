# Brief: report-output

## Problem
在风险识别基础上，需要为每个风险条款生成专业修改建议（风险描述+法律依据+修改示例），输出完整合规报告，并完成Web产品最终集成交付。

## Current State
compliance-engine已输出风险标注和评分数据。需要将其转化为用户可理解的建议和可导出的报告。

## Desired Outcome
每个中高风险条款有AI生成的三要素修改建议（风险描述/法律依据/修改示例）；一键采纳功能（自动嵌入修改到合同原文）；PDF格式《合同合规审查报告》导出；DOCX修订标记导出；审计日志记录；完整Web UI闭环（上传→审查→标注→采纳/拒绝→导出）。

## Approach
修改建议通过DeepSeek LLM生成，Prompt设计包含三要素模板和法律依据约束（减少幻觉）。一键采纳通过python-docx修改原文并添加修订标记实现。PDF报告用reportlab/weasyprint生成。Web前端集成所有交互：合同原文阅读视图（行内高亮）、风险侧边栏、评分仪表盘、建议卡片三栏对比布局。

## Scope
- **In**: AI修改建议生成（三要素模板：风险描述/法律依据/修改示例）、一键采纳功能、PDF合规报告导出（封面/摘要/风险表/逐条分析/附件）、DOCX修订标记导出、审计日志（上传时间/文件哈希/审查结果/操作记录）、审查历史查询（按时间/类型/风险等级筛选）、完整Web UI（合同阅读器+高亮、风险侧边栏、评分仪表盘、建议卡片、批量Dashboard、合同对比视图）
- **Out**: 文档解析、规则引擎逻辑、合规评分计算

## Boundary Candidates
- 修改建议生成器（LLM Prompt + 输出解析）
- DOCX修订标记生成器
- PDF报告生成器
- 审计日志服务
- Web UI完整集成层

## Out of Boundary
- 文档解析逻辑
- 规则引擎和评分模型

## Upstream / Downstream
- **Upstream**: compliance-engine（风险标注、评分数据）、doc-parser（原文数据）
- **Downstream**: 无（最终交付层）

## Existing Spec Touchpoints
- **Extends**: 无
- **Adjacent**: 无

## Constraints
- 法律依据引用须准确，禁止LLM幻觉编造法条
- 修改建议须面向业务负责人可读（非法律专业语言）
- PDF报告中风险高亮须与原文精确对应（页码+段落）
- 产品须包含完整闭环流程
- 最终提交须含《AI工具使用说明》
- 界面不得有误导性法律保证表述
