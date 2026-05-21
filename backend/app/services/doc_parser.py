"""
文档解析服务：提取 DOCX/PDF 文本，结构化为条款列表。
"""

import os
import re
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def extract_text_from_docx(file_path: str) -> str:
    """从 DOCX 文件提取纯文本。"""
    from docx import Document

    doc = Document(file_path)
    paragraphs = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            paragraphs.append(text)

    # 也提取表格中的文本
    for table in doc.tables:
        for row in table.rows:
            row_texts = []
            for cell in row.cells:
                cell_text = cell.text.strip()
                if cell_text:
                    row_texts.append(cell_text)
            if row_texts:
                paragraphs.append(" | ".join(row_texts))

    return "\n\n".join(paragraphs)


def extract_text_from_pdf(file_path: str) -> str:
    """从 PDF 文件提取纯文本。"""
    from PyPDF2 import PdfReader

    reader = PdfReader(file_path)
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text.strip())
    return "\n\n".join(pages)


def extract_text(file_path: str) -> str:
    """根据文件类型提取文本。"""
    ext = Path(file_path).suffix.lower()
    if ext == ".docx":
        return extract_text_from_docx(file_path)
    elif ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext == ".doc":
        logger.warning(".doc format may not be fully supported, attempting .docx parsing")
        return extract_text_from_docx(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {ext}")


def split_into_clauses(text: str) -> list[dict]:
    """
    将合同文本拆分为条款列表。
    返回 [{"title": "...", "content": "..."}]
    """
    clauses = []

    # 常见的中文合同条款编号模式
    patterns = [
        r'(?:^|\n)(第[一二三四五六七八九十百千万\d]+[条章节款项])\s*',
        r'(?:^|\n)((?:[一二三四五六七八九十百千万]+)、)\s*',
        r'(?:^|\n)(\d+[.、)）])\s*',
        r'(?:^|\n)((?:Article|Section|Clause)\s+\d+[.]?\d*)\s*',
        r'(?:^|\n)([（(][一二三四五六七八九十\d]+[）)])\s*',
    ]

    combined = '|'.join(f'({p})' for p in patterns)
    matches = list(re.finditer(combined, text, re.MULTILINE | re.IGNORECASE))

    if len(matches) >= 2:
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            clause_text = text[start:end].strip()
            lines = clause_text.split('\n', 1)
            title = lines[0].strip()[:100]
            content = lines[1].strip() if len(lines) > 1 else ""
            if content or title:
                clauses.append({"title": title, "content": content})
    else:
        paragraphs = re.split(r'\n\s*\n', text)
        for i, para in enumerate(paragraphs):
            para = para.strip()
            if not para:
                continue
            lines = para.split('\n', 1)
            title = lines[0].strip()[:100]
            content = lines[1].strip() if len(lines) > 1 else ""
            clauses.append({
                "title": title if len(paragraphs) > 1 else f"段落 {i + 1}",
                "content": content if content else title,
            })

    return clauses


def parse_document(file_path: str) -> dict:
    """
    解析文档，返回结构化结果。
    """
    ext = Path(file_path).suffix.lower()
    raw_text = extract_text(file_path)
    clauses = split_into_clauses(raw_text)

    logger.info(f"Parsed {file_path}: {len(raw_text)} chars, {len(clauses)} clauses")

    return {
        "raw_text": raw_text,
        "clauses": clauses,
        "total_clauses": len(clauses),
        "file_type": ext,
    }



async def smart_parse_document(file_path: str) -> dict:
    """
    智能文档解析：自动选择文本提取或OCR。
    支持 DOCX/PDF（含扫描件）/图片。
    """
    from .ocr_service import smart_extract

    ext = Path(file_path).suffix.lower()

    # 图片直接走 OCR
    if ext in (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif"):
        raw_text = await smart_extract(file_path)
        clauses = split_into_clauses(raw_text)
        logger.info(f"OCR parsed image: {len(raw_text)} chars, {len(clauses)} clauses")
        return {
            "raw_text": raw_text,
            "clauses": clauses,
            "total_clauses": len(clauses),
            "file_type": ext,
            "ocr_used": True,
        }

    # PDF - 检查是否需要 OCR
    if ext == ".pdf":
        raw_text = extract_text(file_path)
        if len(raw_text.strip()) < 100:
            # 扫描件，走 OCR
            raw_text = await smart_extract(file_path)
            logger.info(f"OCR parsed PDF: {len(raw_text)} chars")
        clauses = split_into_clauses(raw_text)
        return {
            "raw_text": raw_text,
            "clauses": clauses,
            "total_clauses": len(clauses),
            "file_type": ext,
            "ocr_used": len(raw_text.strip()) < 100,
        }

    # DOCX - 直接解析
    raw_text = extract_text(file_path)
    clauses = split_into_clauses(raw_text)
    return {
        "raw_text": raw_text,
        "clauses": clauses,
        "total_clauses": len(clauses),
        "file_type": ext,
        "ocr_used": False,
    }
