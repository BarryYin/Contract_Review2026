# Brief: doc-parser

## Problem
合同文件格式多样（PDF文字型、PDF扫描型、DOCX、含手写补充条款），需要准确解析为结构化数据。解析准确率要求90%以上。双语合同需输出中英文对照并标注一致性偏差。

## Current State
有4份测试合同样本（中文采购协议~20页、双语IT合同~15页、英文NDA~5页、含手写条款劳动合同~8页），无解析代码。

## Desired Outcome
一个文档解析模块，能处理全部4类合同样本，输出标准化JSON结构（合同类型、签约方、期限、付款条款、违约责任、争议解决、保密义务、知识产权、终止条款），自动提取NER实体（日期、金额、地名、公司名、联系人、编号），双语合同输出中英文对照及一致性分析。

## Approach
分层解析策略：先用格式检测器判断文件类型，再分发到对应解析器。DOCX用python-docx提取文本和表格；PDF文字型用pdfplumber；扫描件/手写用PaddleOCR。解析后调用DeepSeek LLM进行条款结构化和NER提取（LLM在结构化提取任务上准确率远超规则方法）。双语对齐也用LLM完成。

## Scope
- **In**: 格式检测（PDF/DOCX/扫描件判断）、DOCX解析（文本+表格+图片提取）、PDF文字型解析、OCR引擎集成(PaddleOCR)、条款结构化JSON输出、NER实体识别、中英双语条款对齐、一致性偏差标注、LLM辅助结构化提取
- **Out**: 风险分析（compliance-engine负责）、修改建议（report-output负责）、Web UI展示

## Boundary Candidates
- 文件格式检测模块
- 各格式解析器（DOCX/PDF文字/PDF扫描）
- OCR引擎封装
- 条款结构化处理器（LLM调用）
- NER提取器
- 双语对齐分析器

## Out of Boundary
- 风险评估和合规判断
- 规则引擎逻辑
- 报告生成

## Upstream / Downstream
- **Upstream**: project-setup（文件上传API、存储路径）
- **Downstream**: compliance-engine（消费结构化JSON输出）

## Existing Spec Touchpoints
- **Extends**: 无
- **Adjacent**: 无

## Constraints
- 解析准确率≥90%（评委人工核对）
- 扫描件须集成OCR（PaddleOCR）
- 双语合同需同时输出中英文对照
- 输出JSON结构须标准化，作为下游spec的输入契约
- 不得将合同内容明文传输至未经批准的第三方LLM服务
