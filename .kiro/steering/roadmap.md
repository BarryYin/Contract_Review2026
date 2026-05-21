# Roadmap

## Overview
构建一套AI驱动的智能合同合规审查Web工具。用户上传合同文件（PDF/DOCX/扫描件），系统自动完成条款结构化拆解、风险点高亮标注、合规评分计算，并输出带修改建议与法律依据的合规报告。面向黑客松评委演示，需覆盖4份测试合同样本。

## Approach Decision
- **Chosen**: Python FastAPI 后端 + React 前端 + DeepSeek LLM
- **Why**: Python生态对文档解析（python-docx, PaddleOCR）和LLM集成最成熟；FastAPI性能好且自带API文档；React前端可做到专业级UI；DeepSeek中文能力强、性价比高、API兼容OpenAI格式
- **Rejected alternatives**: Next.js全栈（Python生态对OCR/文档处理更成熟）；Streamlit（UI不够专业，评委对产品化有评分权重）

## Scope
- **In**: 多格式文档解析（PDF/DOCX/扫描件）、OCR、条款结构化JSON输出、NER实体识别、中英双语对齐分析、可配置合规规则库、预置规则集（《民法典》等）、LLM语义风险识别、风险评分模型（0-100）、批量处理、合同对比、AI修改建议、PDF合规报告导出、DOCX修订标记导出、审计日志、完整Web UI
- **Out**: 多用户认证系统、数据库持久化（黑客松用文件存储即可）、Webhook推送（加分项，时间允许再做）、Swagger文档（加分项）

## Constraints
- 单人开发（AI Agent），时间约束严格
- 测试合同含模拟敏感信息，不得明文传输至未经批准的第三方
- 法律条文引用须准确，严禁LLM幻觉编造法条
- 不得声称具有正式法律效力
- 最终提交须包含《AI工具使用说明》

## Boundary Strategy
- **Why this split**: 按数据处理管线自然分层，每层有明确的输入/输出契约，可独立测试
- **Shared seams to watch**: doc-parser输出的JSON结构是compliance-engine的输入契约，需严格定义；前端与后端的API接口需统一

## Specs (dependency order)
- [ ] project-setup -- 后端骨架(FastAPI) + 前端骨架(React/Vite/Tailwind) + 文件上传/下载基础流程。Dependencies: none
- [ ] doc-parser -- 文档解析引擎：多格式解析(PDF/DOCX/扫描件)、OCR(PaddleOCR)、条款结构化JSON、NER实体识别、中英双语对齐分析。Dependencies: project-setup
- [ ] compliance-engine -- 合规规则引擎：可配置规则库(YAML)、预置规则集、LLM语义风险识别(DeepSeek)、风险评分模型(0-100)、批量处理与合同对比。Dependencies: doc-parser
- [ ] report-output -- 修改建议与报告输出：AI修改建议生成、PDF合规报告、DOCX修订标记导出、审计日志记录、Web UI完整集成。Dependencies: compliance-engine
