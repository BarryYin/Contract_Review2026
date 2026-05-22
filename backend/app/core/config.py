import os
from dotenv import load_dotenv

# Load .env from backend/ directory (config.py = backend/app/core/config.py → 2x dirname = backend/)
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"))

# ── 文件上传 ────────────────────────────────────────────
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
ALLOWED_EXTENSIONS = {
    ".pdf", ".docx", ".doc",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif",
}

# ── CORS ────────────────────────────────────────────────
_default_cors = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"
CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CORS_ORIGINS", _default_cors).split(",")
    if origin.strip()
]

os.makedirs(UPLOAD_DIR, exist_ok=True)
