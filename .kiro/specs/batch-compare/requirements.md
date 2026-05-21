# Requirements: batch-compare

批量上传Dashboard(≥5份)+风险分布热力图+合同逐条差异对比

## REQ-BC-001: 批量上传
- **Priority**: high
- **Type**: functional
- **Description**: 支持一次上传≥5份合同文件，批量触发审查。显示每份文件处理进度。

## REQ-BC-002: Dashboard概览
- **Priority**: high
- **Type**: functional
- **Description**: 统一Dashboard展示所有合同的合规评分概览、风险等级分布、处理状态。支持按等级/类型/评分排序。

## REQ-BC-003: 风险分布热力图
- **Priority**: normal
- **Type**: functional
- **Description**: 展示所有合同的风险维度分布热力图（行=合同，列=风险维度，颜色=得分/等级）。

## REQ-BC-004: 合同逐条对比
- **Priority**: high
- **Type**: functional
- **Description**: 选择两份同类合同→逐条款差异对比→高亮显示变化。左右双栏对照布局。

## REQ-BC-005: 批量审查JSON输出
- **Priority**: high
- **Type**: deliverable
- **Description**: 批量审查结果JSON样本（5份合同同时处理）。

