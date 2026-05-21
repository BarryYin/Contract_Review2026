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
    clause: str
    risk_type: str
    severity: RiskLevel
    description: str
    suggestion: str
    status: IssueStatus = IssueStatus.PENDING


class ReviewResult(BaseModel):
    id: str
    file_id: str
    risk_score: int
    risk_level: RiskLevel
    contract_type: str
    issues: list[RiskIssue]
    summary: str


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
