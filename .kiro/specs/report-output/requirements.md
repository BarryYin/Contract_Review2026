# Requirements: report-output

补充：前端三栏对比布局（原文+建议+依据）、行内高亮+侧边栏风险列表、一键采纳+DOCX Track Changes导出、审计日志

## REQ-RO-001: 修改建议三要素
- **Priority**: high
- **Type**: functional
- **Description**: 每个中风险及以上条款自动生成：(1)风险描述（非法律语言）(2)法律依据（引用具体法条，禁止编造）(3)修改示例（原文→建议替换文）。当前LLM输出需格式化为这三要素。

## REQ-RO-002: 前端三栏对比布局
- **Priority**: high
- **Type**: functional
- **Description**: 修改建议卡片采用三栏布局：原文 | 建议修改 | 法律依据。清晰对比展示。

## REQ-RO-003: 侧边栏风险列表
- **Priority**: high
- **Type**: functional
- **Description**: 审查详情页左侧/右侧添加风险列表侧边栏，按等级排序（高→中→低），点击跳转到对应条款位置。

## REQ-RO-004: 合同原文行内高亮
- **Priority**: high
- **Type**: functional
- **Description**: 合同原文阅读视图中，风险条款行内高亮（红色=高风险、橙色=中风险、绿色=低风险）。

## REQ-RO-005: 一键采纳
- **Priority**: high
- **Type**: functional
- **Description**: 用户点击'采纳'按钮，记录采纳操作。支持'拒绝'操作。状态在前端实时反映。

## REQ-RO-006: DOCX Track Changes导出
- **Priority**: high
- **Type**: functional
- **Description**: 采纳的修改建议导出为带修订标记的.docx文件（Track Changes模式），原文标删除线，建议文标下划线插入。

## REQ-RO-007: 审计日志
- **Priority**: high
- **Type**: functional
- **Description**: 记录每次审查：(1)上传时间 (2)文件SHA256哈希 (3)风险识别结果 (4)用户采纳/拒绝操作记录。支持按时间/类型/等级筛选。

## REQ-RO-008: PDF报告完善
- **Priority**: normal
- **Type**: functional
- **Description**: PDF报告增加封面（合同名称/审查日期/综合评分）+ 附件（风险标注版本）。现有PDF报告需补充。

## REQ-RO-009: 完整闭环流程
- **Priority**: normal
- **Type**: functional
- **Description**: 用户流程：上传→选择模板→审查→风险标注→采纳/拒绝→导出报告。需有模板选择步骤。

## REQ-RO-010: AI使用说明文档
- **Priority**: high
- **Type**: deliverable
- **Description**: 必须提交《AI工具使用说明》：列明AI工具+应用+Prompt设计思路。

