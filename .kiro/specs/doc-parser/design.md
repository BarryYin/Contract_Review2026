# Design: doc-parser

## StructuredParser
新增LLM结构化提取服务，调用Step 3.5 Flash，prompt要求返回标准化JSON（签约方/期限/付款等9类字段）

## NERService
LLM NER提取服务，返回实体列表[{type, value, start, end, context}]

## BilingualAnalyzer
双语一致性分析：拆分中英文部分分别结构化，再对比关键字段一致性

## 前端实体高亮组件
在ReviewDetail页面的合同原文区域，用span+背景色高亮实体，点击弹出popover

## GET /api/reviews/{id}/structured
返回结构化JSON+NER实体列表

## GET /api/reviews/{id}/bilingual
返回双语一致性分析结果

