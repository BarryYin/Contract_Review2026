# PRD: ContractAI — 黑客松评审补齐

## 总览
31个任务，4个spec，按依赖链排序执行。

## Phase A: doc-parser 补齐（8 tasks）
- [x] T-DP-01: 创建 structured_parser.py — LLM结构化提取 [priority:high]
- [x] T-DP-02: 创建 ner_service.py — LLM NER实体提取 [priority:high]
- [x] T-DP-03: 创建 bilingual_analyzer.py — 双语一致性分析 [priority:high] [depends:T-DP-01]
- [x] T-DP-04: 更新 review_service.py 集成结构化+NER [priority:high] [depends:T-DP-01,T-DP-02]
- [x] T-DP-05: 新增API端点：structured + bilingual + ner [priority:high] [depends:T-DP-04]
- [x] T-DP-06: 前端：实体高亮组件 + 点击详情popover [priority:high] [depends:T-DP-05]
- [x] T-DP-07: 前端：结构化JSON展示 + 双语对照视图 [priority:high] [depends:T-DP-05]
- [x] T-DP-08: 测试：2份合同结构化JSON样本输出 [priority:normal] [depends:T-DP-05]

## Phase B: compliance-engine 补齐（7 tasks）
- [x] T-CE-01: 创建 rules.yaml — 7条预置规则配置文件 [priority:high]
- [x] T-CE-02: 创建 rule_engine.py — 规则引擎执行服务 [priority:high] [depends:T-CE-01]
- [x] T-CE-03: 创建 scorer.py — 多维度评分+权重+风险矩阵 [priority:high] [depends:T-CE-02]
- [x] T-CE-04: 更新 compliance_engine.py — 双轨合并（规则+LLM） [priority:high] [depends:T-CE-02,T-CE-03]
- [x] T-CE-05: 更新API返回结构（维度子得分+权重说明+规则命中详情） [priority:high] [depends:T-CE-04]
- [x] T-CE-06: 前端：评分权重饼图/说明组件 [priority:normal] [depends:T-CE-05]
- [x] T-CE-07: 测试：4份合同全部跑通规则+LLM双轨 [priority:high] [depends:T-CE-04]

## Phase C: report-output 补齐（9 tasks）
- [x] T-RO-01: 更新LLM prompt：输出三要素格式（风险描述+法律依据+修改示例） [priority:high]
- [x] T-RO-02: 前端：ReviewDetail三栏布局重构（侧边栏+原文+建议卡） [priority:high] [depends:T-RO-01]
- [x] T-RO-03: 前端：合同原文行内风险高亮 [priority:high] [depends:T-RO-02]
- [x] T-RO-04: 后端：采纳/拒绝状态管理API [priority:high]
- [x] T-RO-05: 后端：DOCX Track Changes导出服务 [priority:high] [depends:T-RO-04]
- [x] T-RO-06: 后端：审计日志服务（SHA256+操作记录） [priority:high]
- [x] T-RO-07: 前端：模板选择步骤 + 采纳/拒绝按钮交互 [priority:normal] [depends:T-RO-04]
- [x] T-RO-08: 完善PDF报告（封面+附件） [priority:normal] [depends:T-RO-01]
- [x] T-RO-09: 创建AI工具使用说明文档 [priority:high]

## Phase D: batch-compare 新增（7 tasks）
- [x] T-BC-01: 后端：批量上传API + 批量审查调度 [priority:high]
- [x] T-BC-02: 前端：批量上传组件（多文件拖拽+进度） [priority:high] [depends:T-BC-01]
- [x] T-BC-03: 前端：Dashboard页面（评分卡片+列表+排序） [priority:high] [depends:T-BC-02]
- [x] T-BC-04: 前端：风险分布热力图 [priority:normal] [depends:T-BC-03]
- [x] T-BC-05: 后端：合同对比引擎（结构化JSON diff） [priority:high]
- [x] T-BC-06: 前端：合同对比页面（双栏+差异高亮） [priority:high] [depends:T-BC-05]
- [x] T-BC-07: 测试：5份合同批量处理演示 [priority:high] [depends:T-BC-03]
