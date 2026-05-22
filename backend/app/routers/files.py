import os
import asyncio
from pathlib import Path

from typing import List
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


@router.post(
    "/upload",
    response_model=FileUploadResponse,
    summary="Upload a contract file",
    description="Upload a contract file (PDF, DOCX, or DOC) for AI compliance review. Maximum file size is 20 MB. Set auto_review=false to skip automatic review and choose a template later.",
)
async def upload_file(
    file: UploadFile = File(...),
    auto_review: bool = True,
):

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

    # Trigger background review only if auto_review is True
    if auto_review and file_path:
        asyncio.create_task(_trigger_review(file_info.id, file_path))

    return FileUploadResponse(
        id=file_info.id,
        filename=file_info.filename,
        size=file_info.size,
        status=FileStatus.PROCESSING if auto_review else FileStatus.UPLOADING,
        message="文件上传成功，正在审查中" if auto_review else "文件上传成功，请选择审查模板",
    )


@router.get(
    "",
    response_model=FileListResponse,
    summary="List all uploaded files",
    description="Retrieve metadata for all uploaded contract files, including file ID, filename, size, upload time, and processing status.",
)
async def list_files():
    files = file_service.list_files()
    return FileListResponse(files=files, total=len(files))


@router.get(
    "/{file_id}",
    response_model=FileInfo,
    summary="Get file metadata",
    description="Retrieve metadata for a single uploaded file by its unique file ID.",
)
async def get_file(file_id: str):
    info = file_service.get_file(file_id)
    if info is None:
        raise HTTPException(status_code=404, detail="文件未找到")
    return info


@router.get(
    "/{file_id}/download",
    summary="Download original file",
    description="Download the original uploaded contract file by its file ID. Returns the file as a binary attachment.",
)
async def download_file(file_id: str):
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


@router.delete(
    "/{file_id}",
    summary="Delete a file",
    description="Delete an uploaded contract file and its associated metadata. This also removes any related review data.",
)
async def delete_file(file_id: str):
    deleted = file_service.delete_file(file_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="文件未找到")
    return {"message": "文件删除成功", "id": file_id}


@router.post(
    "/batch-upload",
    summary="Upload multiple contract files",
    description="Upload multiple contract files at once. Each file is validated, saved, and queued for background AI review individually.",
)
async def batch_upload_files(files: List[UploadFile] = File(...)):
    """批量上传：复用 file_service.save_file + 后台审查，与单文件上传逻辑一致。"""
    results = []
    for file in files:
        try:
            # 验证扩展名
            if file.filename is None:
                results.append({"filename": "", "status": "error", "error": "缺少文件名"})
                continue

            ext = Path(file.filename).suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                results.append({
                    "filename": file.filename,
                    "status": "error",
                    "error": f"不支持的文件类型: {ext}",
                })
                continue

            # 读取内容并校验大小
            file_content = await file.read()
            if len(file_content) == 0:
                results.append({"filename": file.filename, "status": "error", "error": "文件为空"})
                continue
            if len(file_content) > MAX_FILE_SIZE:
                results.append({
                    "filename": file.filename,
                    "status": "error",
                    "error": f"文件过大（>{MAX_FILE_SIZE // (1024*1024)}MB）",
                })
                continue

            # 复用 file_service 保存（生成 UUID、写磁盘、记录元数据）
            file_info = file_service.save_file(file.filename, file_content)
            file_path = file_service.get_file_path(file_info.id)

            # 后台审查
            if file_path:
                asyncio.create_task(_trigger_review(file_info.id, file_path))

            results.append({
                "file_id": file_info.id,
                "filename": file_info.filename,
                "size": file_info.size,
                "status": "processing",
            })
        except Exception as e:
            results.append({
                "filename": getattr(file, "filename", "unknown"),
                "status": "error",
                "error": str(e),
            })

    return {"results": results, "total": len(results)}
