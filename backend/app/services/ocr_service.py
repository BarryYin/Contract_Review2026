"""
OCR 服务：基于 Step step-1v-8k 视觉模型，支持图片和扫描件文字识别。
使用与 compliance_engine 相同的 Step API key，无需额外配置。
"""

import os
import base64
import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

# 使用 Step API（与 compliance_engine 共享同一 key）
STEP_API_KEY = os.environ.get(
    "DEEPSEEK_API_KEY",
    os.environ.get("OPENAI_API_KEY", "")
)
STEP_BASE_URL = "https://api.stepfun.com/v1"
OCR_MODEL = "step-1v-8k"


def image_to_base64(image_path: str) -> str:
    """将图片文件转为 base64 编码。"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def get_image_mime(image_path: str) -> str:
    """根据扩展名返回 MIME 类型。"""
    ext = os.path.splitext(image_path)[1].lower()
    mime_map = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".gif": "image/gif",
        ".bmp": "image/bmp", ".webp": "image/webp",
        ".tiff": "image/tiff", ".tif": "image/tiff",
    }
    return mime_map.get(ext, "image/jpeg")


async def ocr_image(image_path: str, language: str = "auto") -> str:
    """
    使用 Step step-1v-8k 视觉模型对图片进行 OCR 文字识别。
    
    Args:
        image_path: 图片文件路径
        language: 语言提示 (auto/zh/en)
    
    Returns:
        识别出的文本内容
    """
    if not STEP_API_KEY:
        raise RuntimeError("Step API key 未配置，无法使用 OCR 功能")

    img_b64 = image_to_base64(image_path)
    mime = get_image_mime(image_path)

    lang_hint = {
        "zh": "这是一份中文文档。",
        "en": "这是一份英文文档。",
    }.get(language, "这可能是一份中文或英文文档。")

    prompt = (
        f"{lang_hint}请将此图片中的所有文字内容完整准确地提取出来，"
        "保持原始格式和排版，包括标题、段落、编号、表格内容等。"
        "如果文字模糊或手写，请尽量辨认。只输出识别到的文字内容，不要添加任何解释或markdown代码块标记。"
    )

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{STEP_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {STEP_API_KEY}"},
            json={
                "model": OCR_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{img_b64}"}},
                            {"type": "text", "text": prompt}
                        ]
                    }
                ],
                "max_tokens": 4096,
                "temperature": 0.1,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    text = data["choices"][0]["message"]["content"]
    # Strip markdown code blocks if present
    if text.strip().startswith("```"):
        lines = text.strip().split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    
    logger.info(f"OCR completed: {len(text)} chars from {image_path}")
    return text


async def ocr_pdf_scanned(pdf_path: str) -> str:
    """
    将扫描版 PDF 逐页转为图片后 OCR。
    """
    try:
        from pdf2image import convert_from_path
    except ImportError:
        logger.warning("pdf2image not installed, falling back to text extraction")
        return _fallback_pdf_text(pdf_path)

    try:
        import tempfile
        images = convert_from_path(pdf_path, dpi=200)
        logger.info(f"PDF converted to {len(images)} pages")

        all_text = []
        for i, img in enumerate(images):
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                img.save(tmp.name, "PNG")
                tmp_path = tmp.name

            try:
                page_text = await ocr_image(tmp_path)
                if page_text:
                    all_text.append(f"--- 第{i+1}页 ---\n{page_text}")
            finally:
                os.unlink(tmp_path)

        return "\n\n".join(all_text)

    except Exception as e:
        logger.warning(f"PDF OCR failed ({e}), falling back to text extraction")
        return _fallback_pdf_text(pdf_path)


def _fallback_pdf_text(pdf_path: str) -> str:
    """Fallback: 用 PyPDF2 提取 PDF 嵌入文本。"""
    from PyPDF2 import PdfReader
    reader = PdfReader(pdf_path)
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text.strip())
    return "\n\n".join(pages)


async def smart_extract(file_path: str) -> str:
    """
    智能文本提取：根据文件类型和内容选择最佳提取方式。
    - DOCX: python-docx 直接提取
    - PDF: 先尝试 PyPDF2 提取文本，如果文本太少则 OCR
    - 图片: 直接 OCR
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext in (".docx", ".doc"):
        from .doc_parser import extract_text_from_docx
        return extract_text_from_docx(file_path)

    if ext in (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif"):
        return await ocr_image(file_path)

    if ext == ".pdf":
        from .doc_parser import extract_text_from_pdf
        text = extract_text_from_pdf(file_path)
        if len(text.strip()) < 100:
            logger.info(f"PDF text too short ({len(text)} chars), switching to OCR")
            return await ocr_pdf_scanned(file_path)
        return text

    raise ValueError(f"不支持的文件格式: {ext}")
