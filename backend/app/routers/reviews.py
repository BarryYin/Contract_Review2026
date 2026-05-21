"""
审查结果 API 路由。
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..models.file import ReviewResult
from ..services import review_service
from ..services.report_generator import generate_pdf_report

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


@router.get("/{file_id}", response_model=ReviewResult)
async def get_review(file_id: str):
    """获取指定文件的审查结果。"""
    result = review_service.get_review_result(file_id)
    if result is None:
        raise HTTPException(status_code=404, detail="审查结果尚未就绪")
    return result


@router.get("/{file_id}/export/pdf")
async def export_pdf(file_id: str):
    """导出指定文件的 PDF 合规审查报告。"""
    # 1. 获取审查结果
    result = review_service.get_review_result(file_id)
    if result is None:
        raise HTTPException(status_code=404, detail="审查结果尚未就绪，无法导出报告")

    # 2. 尝试获取原始文件名
    filename = file_id
    try:
        from ..services import file_service
        file_info = file_service.get_file(file_id)
        if file_info:
            filename = file_info.filename
    except Exception:
        pass

    # 3. 生成 PDF
    try:
        pdf_bytes = generate_pdf_report(result, filename=filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF 生成失败: {str(e)}")

    # 4. 返回 PDF 流
    safe_name = filename.rsplit(".", 1)[0] if "." in filename else filename
    download_name = f"{safe_name}_合规审查报告.pdf"

    import urllib.parse
    encoded_name = urllib.parse.quote(download_name)

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}",
        },
    )
