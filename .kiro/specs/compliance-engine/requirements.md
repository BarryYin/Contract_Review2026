# Requirements: compliance-engine

补充：YAML规则库配置机制 + 7条预置规则 + 规则引擎执行（双轨：规则+LLM） + 评分权重可解释 + 风险等级矩阵修正

## REQ-CE-001: YAML规则库配置
- **Priority**: high
- **Type**: functional
- **Description**: 设计YAML规则配置机制，每条规则含：规则名称、检测逻辑（关键词/正则/LLM语义）、风险等级（高/中/低）、适用合同类型、引用法律依据。法务人员可在不修改代码情况下自定义规则。

## REQ-CE-002: 7条预置规则
- **Priority**: high
- **Type**: functional
- **Description**: 全覆盖赛题预置规则集：(1)违约金≤30%(民法典585条) (2)付款周期>60天标注 (3)保密期限≥2年 (4)争议解决明确(仲裁/管辖) (5)知识产权工作成果范围清晰 (6)免责不对等 (7)单方解除权。

## REQ-CE-003: 规则引擎执行
- **Priority**: high
- **Type**: functional
- **Description**: 双轨执行：规则引擎做确定性检查（关键词/正则匹配），LLM做语义级风险识别（措辞模糊、权利不对等、连锁风险）。两者结果合并。

## REQ-CE-004: 评分权重可解释
- **Priority**: high
- **Type**: functional
- **Description**: 综合合规得分0-100，拆分至各风险维度子得分（违约责任权重20%、付款条款15%、保密义务15%、知识产权15%、争议解决10%、免责条款15%、终止条款10%）。前端展示权重饼图/说明。

## REQ-CE-005: 风险等级矩阵
- **Priority**: high
- **Type**: functional
- **Description**: 高风险(≥3条高风险) / 中风险(1-2条高风险或≥5条中风险) / 低风险(其余)。视觉标识区分（红/橙/绿）。

## REQ-CE-006: 语义级风险识别
- **Priority**: high
- **Type**: functional
- **Description**: LLM识别：(1)措辞模糊风险（'合理时间'等→建议量化）(2)权利义务不对等 (3)连锁风险（跨条款逻辑矛盾）。不得仅依赖关键词匹配。

## REQ-CE-007: 4份合同JSON输出
- **Priority**: high
- **Type**: deliverable
- **Description**: 含风险评分、风险等级、逐条标注结果的JSON输出样本，覆盖全部4份测试合同。

