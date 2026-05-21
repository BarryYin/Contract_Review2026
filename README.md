# ContractAI - 智能合同合规审查工具

> 基于 AI 的合同风险识别与合规分析平台

## 项目简介

ContractAI 是一个智能合同合规审查工具，支持上传合同文件（PDF/DOCX），自动进行风险识别和合规性分析，生成详细的审查报告。

### 核心功能

- 📄 合同文件上传（拖拽/点击，支持 PDF、DOCX、DOC）
- 🔍 AI 智能风险识别与合规分析
- 📊 风险评分仪表盘（0-100 分）
- ⚠️ 风险条款定位与改进建议
- 📋 合同列表管理与下载

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 19 + TypeScript + TailwindCSS v4 + Vite |
| 后端 | FastAPI + Pydantic v2 + Uvicorn |
| 设计 | Stripe 风格（Inter 字体 + 紫色调） |

## 快速启动

### 前置条件

- Python 3.10+
- Node.js 18+

### 一键启动

```bash
./start.sh
```

### 手动启动

**后端：**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**前端：**
```bash
cd frontend
npm install
npm run dev
```

### 访问地址

- 前端界面：http://localhost:5173
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

## 项目结构

```
Contract_Review2026/
├── frontend/               # React 前端
│   ├── src/
│   │   ├── api/           # API 客户端（含 mock 数据）
│   │   ├── components/    # UI 组件
│   │   ├── pages/         # 页面组件
│   │   └── types/         # TypeScript 类型定义
│   └── vite.config.ts
├── backend/                # FastAPI 后端
│   ├── app/
│   │   ├── core/          # 配置
│   │   ├── middleware/     # 中间件
│   │   ├── models/        # Pydantic 数据模型
│   │   ├── routers/       # API 路由
│   │   └── services/      # 业务逻辑
│   └── requirements.txt
├── contracts/              # 测试合同样本
├── uploads/                # 上传文件存储
├── start.sh                # 一键启动脚本
└── PRD.md                  # 产品需求文档
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/health | 健康检查 |
| POST | /api/files/upload | 上传合同文件 |
| GET | /api/files | 获取合同列表 |
| GET | /api/files/{id} | 获取单个合同信息 |
| GET | /api/files/{id}/download | 下载合同文件 |
| DELETE | /api/files/{id} | 删除合同 |

## 测试合同样本

`contracts/` 目录包含 4 个测试合同：

1. **中文采购框架协议** — 含表格附件、盖章扫描件
2. **中英双语IT服务合同** — 双栏对照排版
3. **标准保密协议 NDA** — 英文原版
4. **劳动合同** — 含手写补充条款（混合 OCR）

## License

MIT
