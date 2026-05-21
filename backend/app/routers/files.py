import os
import asyncio
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse

from ..core.config import MAX_FILE_SIZE, ALLOWED_EXTENSIONS
from ..models.file import (
    FileInfo,
    FileUploadResponse,
    FileListResponse,
    FileStatus,
)
from ..services import file_service, review_service

router = APIRouter(prefix="/api/files", tags=["files"])


async def _trigger_review(file_id: str, file_path: str):
    """后台任务：解析并审查合同。"""
    try:
        await review_service.review_file(file_id, file_path)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Background review failed: {e}")


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """Upload a contract file (.pdf, .docx, .doc). Max 20 MB."""

    # Validate extension
    if file.filename is None:
        raise HTTPException(status_code=400, detail="缺少文件名")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {ext}。仅支持 {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # Read content and validate size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件过大，最大允许 {MAX_FILE_SIZE // (1024 * 1024)} MB",
        )

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="上传的文件为空")

    # Save via file service
    file_info = file_service.save_file(file.filename, content)

    # Get file path for background review
    file_path = file_service.get_file_path(file_info.id)

    # Trigger background review
    if file_path:
        asyncio.create_task(_trigger_review(file_info.id, file_path))

    return FileUploadResponse(
        id=file_info.id,
        filename=file_info.filename,
        size=file_info.size,
        status=FileStatus.PROCESSING,
        message="文件上传成功，正在审查中",
    )


@router.get("", response_model=FileListResponse)
async def list_files():
    """Return metadata for all uploaded files."""
    files = file_service.list_files()
    return FileListResponse(files=files, total=len(files))


@router.get("/{file_id}", response_model=FileInfo)
async def get_file(file_id: str):
    """Return metadata for a single file."""
    info = file_service.get_file(file_id)
    if info is None:
        raise HTTPException(status_code=404, detail="文件未找到")
    return info


@router.get("/{file_id}/download")
async def download_file(file_id: str):
    """Download the original uploaded file."""
    info = file_service.get_file(file_id)
    if info is None:
        raise HTTPException(status_code=404, detail="文件未找到")

    file_path = file_service.get_file_path(file_id)
    if file_path is None:
        raise HTTPException(status_code=404, detail="文件内容未找到")

    return FileResponse(
        path=file_path,
        filename=info.filename,
        media_type="application/octet-stream",
    )


@router.delete("/{file_id}")
async def delete_file(file_id: str):
    """Delete a file and its metadata."""
    deleted = file_service.delete_file(file_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="文件未找到")
    return {"message": "文件删除成功", "id": file_id}
