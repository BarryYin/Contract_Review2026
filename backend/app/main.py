from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import CORS_ORIGINS
from .middleware.error_handler import ErrorHandlerMiddleware
from .routers import health, files, reviews

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


@app.get("/")
async def root():
    return {"message": "ContractAI API", "docs": "/docs"}
