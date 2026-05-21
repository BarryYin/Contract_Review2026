from pydantic import BaseModel
from typing import Optional
from enum import Enum


class FileStatus(str, Enum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FileInfo(BaseModel):
    id: str
    filename: str
    size: int
    upload_time: str
    status: FileStatus = FileStatus.COMPLETED
    risk_level: Optional[RiskLevel] = None
    contract_type: Optional[str] = None
    review_progress: Optional[int] = 0


class FileUploadResponse(BaseModel):
    id: str
    filename: str
    size: int
    status: FileStatus
    message: str = "文件上传成功"


class FileListResponse(BaseModel):
    files: list[FileInfo]
    total: int


class IssueStatus(str, Enum):
    PENDING = "pending"
    ADOPTED = "adopted"
    REJECTED = "rejected"


class RiskIssue(BaseModel):
    id: str
    title: Optional[str] = None
    clause_reference: Optional[str] = None
    severity: RiskLevel = RiskLevel.MEDIUM
    risk_description: Optional[str] = None
    legal_basis: Optional[str] = None
    modification_example: Optional[dict] = None
    # Legacy fields (kept for backward compatibility)
    clause: Optional[str] = None
    risk_type: Optional[str] = None
    description: Optional[str] = None
    suggestion: Optional[str] = None
    status: Optional[str] = "pending"


class ReviewResult(BaseModel):
    id: str
    file_id: str
    risk_score: float = 0
    risk_level: RiskLevel = RiskLevel.LOW
    contract_type: str = "未识别"
    issues: list[RiskIssue] = []
    summary: str = ""
    # New fields from integrated services
    filename: Optional[str] = None
    upload_time: Optional[str] = None
    review_time: Optional[str] = None
    ocr_used: Optional[bool] = None
    rule_hits: Optional[list] = None
    structured_info: Optional[dict] = None
    entities: Optional[dict] = None
    bilingual_analysis: Optional[dict] = None
    scoring_dimensions: Optional[list] = None
    scoring_explanation: Optional[str] = None
    file_hash: Optional[str] = None


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
    uptime: Optional[str] = None


class IssueActionResponse(BaseModel):
    """采纳/拒绝操作的返回模型。"""
    issue_id: str
    status: str
    message: str


class AuditLogEntry(BaseModel):
    timestamp: str
    file_id: str
    action: str
    details: Optional[dict] = None
    file_hash: Optional[str] = None


class AuditLogResponse(BaseModel):
    logs: list[AuditLogEntry]
    total: int
