# Tasks: compliance-engine

- [ ] T-CE-01: 创建 rules.yaml — 7条预置规则配置文件 [priority:high]
- [ ] T-CE-02: 创建 rule_engine.py — 规则引擎执行服务 [priority:high] [depends:T-CE-01]
- [ ] T-CE-03: 创建 scorer.py — 多维度评分+权重+风险矩阵 [priority:high] [depends:T-CE-02]
- [ ] T-CE-04: 更新 compliance_engine.py — 双轨合并（规则+LLM） [priority:high] [depends:T-CE-02,T-CE-03]
- [ ] T-CE-05: 更新 API 返回结构（维度子得分+权重说明+规则命中详情） [priority:high] [depends:T-CE-04]
- [ ] T-CE-06: 前端：评分权重饼图/说明组件 [priority:normal] [depends:T-CE-05]
- [ ] T-CE-07: 测试：4份合同全部跑通规则+LLM双轨 [priority:high] [depends:T-CE-04]
