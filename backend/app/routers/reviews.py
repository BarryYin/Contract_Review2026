"""
审查结果 API 路由。
"""

from fastapi import APIRouter, HTTPException

from ..models.file import ReviewResult
from ..services import review_service

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


@router.get("/{file_id}", response_model=ReviewResult)
async def get_review(file_id: str):
    """获取指定文件的审查结果。"""
    result = review_service.get_review_result(file_id)
    if result is None:
        raise HTTPException(status_code=404, detail="审查结果尚未就绪")
    return result
