# Requirements: doc-parser

补充：结构化JSON字段（签约方/期限/付款/违约/争议/保密/知识产权/终止）、NER实体识别（日期/金额/地名/公司名/联系人/合同编号）+ 前端不同颜色高亮 + 点击查看上下文、双语合同一致性分析

## REQ-DP-001: 结构化JSON输出
- **Priority**: high
- **Type**: functional
- **Description**: 将合同内容解析为标准化JSON，包含：合同类型、签约方信息（名称/地址/法定代表人）、合同期限（起止日期）、付款条款（金额/周期/方式）、违约责任条款、争议解决条款、保密义务条款、知识产权归属条款、终止与退出条款。准确率≥90%。

## REQ-DP-002: NER实体识别
- **Priority**: high
- **Type**: functional
- **Description**: 自动提取关键实体：日期、金额、地名（管辖法院所在地）、公司名称、联系人、合同编号。返回实体类型+值+位置（字符偏移）。

## REQ-DP-003: NER前端高亮
- **Priority**: high
- **Type**: functional
- **Description**: 前端以不同颜色高亮显示各类实体（日期=蓝、金额=绿、地名=橙、公司=紫、联系人=红、编号=灰），支持点击实体弹出上下文详情。

## REQ-DP-004: 双语一致性分析
- **Priority**: high
- **Type**: functional
- **Description**: 对中英双语合同，同时输出中英文对照结构化结果，标注双语条款一致性（是否存在含义偏差），生成一致性分析报告。

## REQ-DP-005: LLM驱动NER+结构化
- **Priority**: high
- **Type**: technical
- **Description**: 调用Step 3.5 Flash进行NER和结构化提取，返回格式严格的JSON。与现有doc_parser模块集成。

## REQ-DP-006: 结构化JSON样本交付
- **Priority**: high
- **Type**: deliverable
- **Description**: 至少覆盖2份测试合同的结构化JSON输出样本，存于outputs/目录。

