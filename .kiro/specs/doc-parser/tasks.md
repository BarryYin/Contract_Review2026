# Tasks: doc-parser

- [ ] T-DP-01: 创建 structured_parser.py — LLM结构化提取 [priority:high]
- [ ] T-DP-02: 创建 ner_service.py — LLM NER实体提取 [priority:high]
- [ ] T-DP-03: 创建 bilingual_analyzer.py — 双语一致性分析 [priority:high] [depends:T-DP-01]
- [ ] T-DP-04: 更新 review_service.py 集成结构化+NER [priority:high] [depends:T-DP-01,T-DP-02]
- [ ] T-DP-05: 新增API端点：structured + bilingual + ner [priority:high] [depends:T-DP-04]
- [ ] T-DP-06: 前端：实体高亮组件 + 点击详情popover [priority:high] [depends:T-DP-05]
- [ ] T-DP-07: 前端：结构化JSON展示 + 双语对照视图 [priority:high] [depends:T-DP-05]
- [ ] T-DP-08: 测试：2份合同结构化JSON样本输出 [priority:normal] [depends:T-DP-05]
