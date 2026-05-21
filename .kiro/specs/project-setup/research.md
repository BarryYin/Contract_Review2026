# Research Log: project-setup

## Discovery Scope
绿地项目，项目脚手架搭建。无现有代码需要分析。聚焦于技术选型验证和架构决策。

## Design Decisions

### DD-1: 前后端分离架构
- **决策**: FastAPI 后端 + React 前端，通过 REST API 通信
- **原因**: 前后端独立开发/部署，后端专注数据处理（文档解析、LLM调用），前端专注可视化交互
- **备选**: Next.js 全栈（Python 生态对 OCR/文档处理更成熟，不采用）

### DD-2: 文件存储策略
- **决策**: 本地文件系统存储，按任务 ID 组织目录
- **原因**: 黑客松项目，无需数据库。后续 spec 可扩展为对象存储
- **备选**: SQLite（增加复杂度但无实际收益，不采用）

### DD-3: 前端技术栈
- **决策**: React 18 + Vite 5 + TailwindCSS 3 + TypeScript
- **原因**: Vite 启动快、HMR 速度快；TailwindCSS 适合快速构建专业 UI；TypeScript 保证类型安全
- **备选**: Streamlit（UI 定制性差，不满足评委对产品化的评分要求）

## Generalizations
- 文件上传/下载/列表/删除是标准 CRUD 模式，设计通用 FileService，后续 spec 可复用

## Simplifications
- 无用户认证（黑客松范围外）
- 无数据库（文件系统足够）
- 无 API 版本控制（单一版本足够）
- 前端仅单页应用，无复杂路由
