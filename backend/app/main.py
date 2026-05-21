from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import CORS_ORIGINS
from .middleware.error_handler import ErrorHandlerMiddleware
from .routers import health, files

app = FastAPI(
    title="ContractAI - 智能合同合规审查工具",
    description="AI-powered contract compliance review API",
    version="1.0.0",
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


@app.get("/")
async def root():
    return {"message": "ContractAI API", "docs": "/docs"}
