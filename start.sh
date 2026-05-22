#!/bin/bash
# ContractAI 启动脚本
# 用法:
#   ./start.sh          - 开发模式（前后端分别启动）
#   ./start.sh prod     - 生产模式（前端 build 后用 uvicorn + 静态文件服务）

set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
MODE="${1:-dev}"

echo "🚀 ContractAI - 智能合同合规审查工具"
echo "========================================="
echo "  模式: $MODE"
echo ""

# ── 环境变量检查 ────────────────────────────────────────
if [ ! -f "$BACKEND_DIR/.env" ]; then
    echo "⚠️  未找到 $BACKEND_DIR/.env"
    echo "   请复制 .env.example 并填入 API Key:"
    echo "   cp $BACKEND_DIR/.env.example $BACKEND_DIR/.env"
    echo ""
    echo "   必需的环境变量:"
    echo "     LLM_API_KEY  - LLM API 密钥"
    echo "     LLM_BASE_URL - API 地址 (默认: https://api.stepfun.com)"
    echo "     LLM_MODEL    - 模型名 (默认: step-3.5-flash)"
    exit 1
fi

# ── 检查依赖 ────────────────────────────────────────────
command -v python3 >/dev/null 2>&1 || { echo "❌ python3 未安装"; exit 1; }

# Prefer Node 20+ from nvm (Vite 8 requires Node 20.19+)
for node_ver in "v22.22.1" "v20.19.4" "v20.18.2"; do
    if [ -x "$HOME/.nvm/versions/node/$node_ver/bin/node" ]; then
        export PATH="$HOME/.nvm/versions/node/$node_ver/bin:$PATH"
        break
    fi
done
command -v node >/dev/null 2>&1 || { echo "❌ node 未安装 (需要 Node 20.19+)"; exit 1; }
echo "  ▶ Node: $(node --version)"
echo "  ▶ Python: $(python3 --version)"

# ── 后端依赖 ────────────────────────────────────────────
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

if [ "$MODE" = "prod" ]; then
    # ── 生产模式 ────────────────────────────────────────
    echo ""
    echo "📦 构建前端..."
    cd "$FRONTEND_DIR"
    if [ ! -d "node_modules" ]; then
        npm install
    fi
    npm run build
    echo "  ✅ 前端构建完成 (dist/)"

    echo ""
    echo "🔥 启动生产服务..."
    cd "$BACKEND_DIR"
    source venv/bin/activate

    HOST="${HOST:-0.0.0.0}"
    PORT="${PORT:-8000}"
    
    echo "  ▶ 服务地址: http://$HOST:$PORT"
    echo "  ▶ API 文档: http://$HOST:$PORT/docs"
    exec uvicorn app.main:app --host "$HOST" --port "$PORT"

else
    # ── 开发模式 ────────────────────────────────────────
    echo ""
    echo "📦 检查前端依赖..."
    cd "$FRONTEND_DIR"
    if [ ! -d "node_modules" ]; then
        npm install
    fi
    echo "  ✅ 前端依赖就绪"

    echo ""
    echo "🔥 启动开发服务..."
    echo ""

    # Start backend
    cd "$BACKEND_DIR"
    source venv/bin/activate
    echo "  ▶ 后端: http://localhost:8000"
    echo "  ▶ API 文档: http://localhost:8000/docs"
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
    BACKEND_PID=$!

    # Start frontend
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
    wait
fi
