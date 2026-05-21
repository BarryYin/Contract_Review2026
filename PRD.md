# PRD: ContractAI — AI智能合同合规审查工具

## 状态总览
- project-setup: ✅ 完成
- doc-parser: ✅ 完成（含OCR）
- compliance-engine: ✅ 完成
- report-output: ⚠️ 部分完成（缺导出和审计）

---

## Phase 1: 项目初始化 ✅
- [x] 初始化 Git 仓库 + .gitignore
- [x] 初始化 backend: Python venv + FastAPI
- [x] 初始化 frontend: Vite + React + TypeScript + TailwindCSS

## Phase 2: 后端 FastAPI 骨架 ✅
- [x] FastAPI 应用入口 (main.py + CORS + 错误处理)
- [x] Pydantic 数据模型 (models/file.py)
- [x] 配置模块 (config.py)
- [x] 健康检查路由 (health.py)
- [x] 文件服务 + 路由 (upload/list/download/delete)
- [x] 路由注册

## Phase 3: 前端 React 骨架 ✅
- [x] API 客户端 (client.ts, 对接真实API)
- [x] TypeScript 类型定义
- [x] 主布局组件 (Layout.tsx)
- [x] 文件上传组件 (拖拽+点击+进度条)
- [x] 文件列表组件
- [x] 首页 (上传+列表+统计)
- [x] 审查详情页 (风险评分+问题列表)
- [x] App.tsx 路由 + Vite 代理

## Phase 4: 文档解析引擎 ✅
- [x] DOCX 文本提取 (python-docx)
- [x] PDF 文本提取 (PyPDF2)
- [x] OCR 图片识别 (Step step-1v-8k 视觉模型)
- [x] 扫描PDF自动检测 + OCR fallback
- [x] 条款结构化拆分 (中英双语正则)
- [x] 图片格式支持 (JPG/PNG/BMP/WebP/TIFF)

## Phase 5: 合规分析引擎 ✅
- [x] LLM 合规分析 (Step 3.5 Flash)
- [x] 风险评分模型 (0-100)
- [x] 风险等级分类 (low/medium/high)
- [x] 异步后台审查编排
- [x] 审查结果存储 + API

## Phase 6: 报告输出与完善
- [x] 审查详情页 (风险仪表盘+问题列表+修改建议)
- [ ] PDF 合规报告导出 [priority:high] [depends:phase5]
- [ ] DOCX 修订标记导出 [priority:normal] [depends:phase5]
- [ ] 审计日志记录 [priority:low] [depends:phase5]
- [ ] 批量合同处理 [priority:normal] [depends:phase5]
- [ ] 合同对比功能 [priority:low] [depends:phase5]

## Phase 7: 端到端验证
- [ ] 端到端验证：上传→列表→审查→报告 全流程跑通 [priority:high] [depends:phase6]
- [ ] 4份测试合同全部通过审查 [priority:high] [depends:phase7]
- [ ] README 更新最终状态 [priority:normal]
