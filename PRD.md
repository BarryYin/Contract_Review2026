# PRD: project-setup — AI智能合同合规审查工具脚手架

## Phase 1: 项目初始化

- [x] 初始化 Git 仓库 + .gitignore（Python + Node.js） [priority:high]
- [x] 初始化 backend: Python 虚拟环境 + requirements.txt + FastAPI 依赖 [priority:high]
- [x] 初始化 frontend: Vite + React + TypeScript + TailwindCSS 项目 [priority:high]

## Phase 2: 后端 FastAPI 骨架

- [x] 创建 FastAPI 应用入口 app/main.py（CORS + 错误处理中间件 + 路由注册） [priority:high]
- [x] 创建 Pydantic 数据模型 app/models/file.py（FileInfo, FileUploadResponse, FileListResponse, ErrorResponse） [priority:high]
- [x] 创建配置模块 app/core/config.py（上传目录、文件大小限制、CORS 来源等） [priority:normal]
- [x] 创建统一错误处理中间件 app/middleware/error_handler.py [priority:normal]
- [x] 创建健康检查路由 app/routers/health.py（GET /api/health） [priority:normal]
- [x] 创建文件服务 app/services/file_service.py（save/list/get/delete） [priority:high]
- [x] 创建文件路由 app/routers/files.py（upload/list/download/delete 四个端点） [priority:high]
- [x] 在 main.py 中挂载 health 和 files 路由 [priority:high]

## Phase 3: 前端 React 骨架

- [x] 创建 API 客户端 src/api/client.ts（axios 封装，含上传进度支持，mock 模式） [priority:high]
- [x] 创建 TypeScript 类型定义 src/types/index.ts（与后端模型对齐） [priority:high]
- [x] 创建主布局组件 src/components/Layout.tsx（导航栏 + 内容区域，响应式） [priority:high]
- [x] 创建文件上传组件 src/components/FileUpload.tsx（拖拽 + 点击 + 进度条） [priority:high]
- [x] 创建文件列表组件 src/components/FileList.tsx（表格 + 操作按钮 + 空状态） [priority:high]
- [x] 创建首页 src/pages/Home.tsx（集成上传 + 列表 + 统计卡片） [priority:high]
- [x] 创建审查详情页 src/pages/ReviewDetail.tsx（风险评分 + 问题列表） [priority:high]
- [x] 配置 App.tsx 路由 + Vite 代理（/api → localhost:8000） [priority:high]
- [x] 配置 TailwindCSS 样式和基础全局样式（Stripe 设计风格） [priority:normal]

## Phase 4: 集成与启动

- [x] 创建一键启动脚本 start.sh（同时启动前后端 dev server） [priority:high]
- [ ] 端到端验证：上传合同 → 列表显示 → 下载 → 删除 全流程跑通 [priority:high]
- [x] 复制测试合同样本到 contracts/ 目录 [priority:normal]
- [x] 编写 README.md（项目说明 + 启动指南） [priority:normal]
