#!/bin/bash
# ContractAI 一键启动脚本
# 同时启动后端 FastAPI 和前端 Vite dev server

set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

echo "🚀 ContractAI - 智能合同合规审查工具"
echo "========================================="

# Check dependencies
command -v python3 >/dev/null 2>&1 || { echo "❌ python3 未安装"; exit 1; }

# Prefer Node 20.19.4 from nvm (Vite 8 requires Node 20.19+)
if [ -x "$HOME/.nvm/versions/node/v20.19.4/bin/node" ]; then
    export PATH="$HOME/.nvm/versions/node/v20.19.4/bin:$PATH"
elif [ -x "$HOME/.nvm/versions/node/v20.18.2/bin/node" ]; then
    export PATH="$HOME/.nvm/versions/node/v20.18.2/bin:$PATH"
fi
command -v node >/dev/null 2>&1 || { echo "❌ node 未安装"; exit 1; }
NODE_VER=$(node --version)
echo "  ▶ Node 版本: $NODE_VER"

# Setup backend
echo ""
echo "📦 检查后端依赖..."
cd "$BACKEND_DIR"
if [ ! -d "venv" ]; then
    echo "  创建 Python 虚拟环境..."
    python3 -m venv venv
fi
source venv/bin/activate
pip install -q -r requirements.txt
echo "  ✅ 后端依赖就绪"

# Setup frontend
echo ""
echo "📦 检查前端依赖..."
cd "$FRONTEND_DIR"
if [ ! -d "node_modules" ]; then
    echo "  安装 npm 依赖..."
    npm install
fi
echo "  ✅ 前端依赖就绪"

# Start servers
echo ""
echo "🔥 启动服务..."
echo ""

# Start backend in background
cd "$BACKEND_DIR"
source venv/bin/activate
echo "  ▶ 后端: http://localhost:8000"
echo "  ▶ API 文档: http://localhost:8000/docs"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Start frontend in background
cd "$FRONTEND_DIR"
echo "  ▶ 前端: http://localhost:5173"
npx vite --host --port 5173 &
FRONTEND_PID=$!

echo ""
echo "========================================="
echo "✅ 服务已启动！按 Ctrl+C 停止所有服务"
echo "   前端: http://localhost:5173"
echo "   后端: http://localhost:8000"
echo "========================================="

# Handle shutdown
cleanup() {
    echo ""
    echo "🛑 正在停止服务..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "✅ 已停止"
    exit 0
}
trap cleanup SIGINT SIGTERM

# Wait for either process
wait
