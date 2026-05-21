import os
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from typing import Optional

from ..core.config import UPLOAD_DIR
from ..models.file import FileInfo, FileStatus

METADATA_FILE = os.path.join(UPLOAD_DIR, "metadata.json")


def load_metadata() -> dict:
    """Load file metadata from the JSON store. Returns a dict keyed by file_id."""
    if not os.path.exists(METADATA_FILE):
        return {}
    try:
        with open(METADATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_metadata(metadata: dict) -> None:
    """Persist file metadata to the JSON store."""
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


def save_file(filename: str, content_bytes: bytes) -> FileInfo:
    """Save an uploaded file to disk and record its metadata.

    Args:
        filename: Original filename from the upload.
        content_bytes: Raw file content.

    Returns:
        FileInfo with generated id and metadata.
    """
    file_id = str(uuid.uuid4())
    upload_time = datetime.now(timezone.utc).isoformat()
    size = len(content_bytes)

    # Build a unique on-disk name to avoid collisions
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    disk_name = f"{file_id}_{stem}{suffix}"
    file_path = os.path.join(UPLOAD_DIR, disk_name)

    # Write file to disk
    with open(file_path, "wb") as f:
        f.write(content_bytes)

    file_info = FileInfo(
        id=file_id,
        filename=filename,
        size=size,
        upload_time=upload_time,
        status=FileStatus.COMPLETED,
    )

    # Persist metadata
    metadata = load_metadata()
    metadata[file_id] = {
        "id": file_id,
        "filename": filename,
        "size": size,
        "upload_time": upload_time,
        "status": FileStatus.COMPLETED,
        "disk_name": disk_name,
        "risk_level": None,
        "contract_type": None,
        "review_progress": 0,
    }
    save_metadata(metadata)

    return file_info


def list_files() -> list[FileInfo]:
    """Return metadata for all uploaded files, newest first."""
    metadata = load_metadata()
    files = []
    for entry in metadata.values():
        files.append(FileInfo(
            id=entry["id"],
            filename=entry["filename"],
            size=entry["size"],
            upload_time=entry["upload_time"],
            status=entry.get("status", FileStatus.COMPLETED),
            risk_level=entry.get("risk_level"),
            contract_type=entry.get("contract_type"),
            review_progress=entry.get("review_progress", 0),
        ))
    # Sort by upload_time descending (newest first)
    files.sort(key=lambda f: f.upload_time, reverse=True)
    return files


def get_file(file_id: str) -> Optional[FileInfo]:
    """Return metadata for a single file, or None if not found."""
    metadata = load_metadata()
    entry = metadata.get(file_id)
    if entry is None:
        return None
    return FileInfo(
        id=entry["id"],
        filename=entry["filename"],
        size=entry["size"],
        upload_time=entry["upload_time"],
        status=entry.get("status", FileStatus.COMPLETED),
        risk_level=entry.get("risk_level"),
        contract_type=entry.get("contract_type"),
        review_progress=entry.get("review_progress", 0),
    )


def get_file_path(file_id: str) -> Optional[str]:
    """Return the absolute path to the physical file on disk, or None."""
    metadata = load_metadata()
    entry = metadata.get(file_id)
    if entry is None:
        return None
    disk_name = entry.get("disk_name")
    if disk_name is None:
        return None
    path = os.path.join(UPLOAD_DIR, disk_name)
    if os.path.exists(path):
        return path
    return None


def delete_file(file_id: str) -> bool:
    """Delete a file and its metadata. Returns True if deleted, False if not found."""
    metadata = load_metadata()
    entry = metadata.pop(file_id, None)
    if entry is None:
        return False

    # Remove physical file
    disk_name = entry.get("disk_name")
    if disk_name:
        file_path = os.path.join(UPLOAD_DIR, disk_name)
        if os.path.exists(file_path):
            os.remove(file_path)

    save_metadata(metadata)
    return True



def update_file_status(
    file_id: str,
    status: str = None,
    risk_level: str = None,
    contract_type: str = None,
    review_progress: int = None,
):
    """更新文件元数据的状态字段。"""
    metadata = load_metadata()
    entry = metadata.get(file_id)
    if entry is None:
        return
    if status is not None:
        entry["status"] = status
    if risk_level is not None:
        entry["risk_level"] = risk_level
    if contract_type is not None:
        entry["contract_type"] = contract_type
    if review_progress is not None:
        entry["review_progress"] = review_progress
    save_metadata(metadata)
