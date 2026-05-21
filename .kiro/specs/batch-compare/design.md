# Design: batch-compare

## 批量上传API
POST /api/files/batch-upload，接收多文件，逐个触发审查，返回batch_id

## Dashboard页面
新页面 /dashboard：合同列表+评分卡片+风险分布图表+热力图

## 对比引擎
后端对比两份合同的结构化JSON，逐字段diff，返回差异列表

## 对比页面
新页面 /compare：左右双栏对照，差异高亮

