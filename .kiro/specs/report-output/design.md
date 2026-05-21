# Design: report-output

## 更新 compliance_engine prompt
LLM prompt输出三要素格式：risk_description + legal_basis + modification_example(original→suggested)

## 前端 ReviewDetail 重构
三栏布局：左侧风险列表侧边栏 + 中间合同原文(行内高亮) + 右侧修改建议卡片(原文/建议/依据)

## AdoptionService
采纳/拒绝状态管理：记录到审查结果JSON，更新状态

## DocxExportService
python-docx Track Changes模式导出：采纳的修改标为修订

## AuditService
审计日志：SHA256哈希、时间戳、操作记录，存为audit_log.json

## 前端模板选择
上传后增加模板选择步骤（通用/采购/服务/NDA/劳动）

