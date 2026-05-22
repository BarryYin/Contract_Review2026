import os
from dotenv import load_dotenv

# Load .env before any other imports that read env vars
# __file__ = backend/app/main.py → 2x dirname = backend/
_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(_env_path)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .core.config import CORS_ORIGINS
from .middleware.error_handler import ErrorHandlerMiddleware
from .routers import health, files, reviews, webhooks, rules

app = FastAPI(
    title="ContractAI - 智能合同合规审查工具",
    description=(
        "## ContractAI API\n\n"
        "AI-powered contract compliance review platform.\n\n"
        "### Features\n"
        "- Upload contract files (PDF, DOCX, DOC)\n"
        "- AI-driven compliance review with risk scoring\n"
        "- Named entity recognition & structured parsing\n"
        "- Bilingual (Chinese/English) consistency analysis\n"
        "- Issue management (adopt/reject findings)\n"
        "- Export PDF reports & DOCX with Track Changes\n"
        "- Audit logging\n\n"
        "### Quick Start\n"
        "1. Upload a contract via `POST /api/files/upload`\n"
        "2. Check review status via `GET /api/reviews/{file_id}`\n"
        "3. Export a report via `GET /api/reviews/{file_id}/export/pdf`\n"
    ),
    version="1.0.0",
    contact={
        "name": "ContractAI Team",
        "email": "support@contractai.example.com",
    },
    license_info={
        "name": "MIT",
    },
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Error handler
app.add_middleware(ErrorHandlerMiddleware)

# Routes
app.include_router(health.router)
app.include_router(files.router)
app.include_router(reviews.router)
app.include_router(webhooks.router)
app.include_router(rules.router)


_dist_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "frontend", "dist",
)
if os.path.isdir(_dist_dir):
    from fastapi.responses import FileResponse

    app.mount("/assets", StaticFiles(directory=os.path.join(_dist_dir, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """SPA fallback: serve index.html for all non-API, non-static routes."""
        # API routes are already handled by routers above
        file_path = os.path.join(_dist_dir, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(_dist_dir, "index.html"))
