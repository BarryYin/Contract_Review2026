import type { FileInfo, ReviewResult } from '../types';

const API_BASE = '/api';

// ── File operations ────────────────────────────────────

export async function fetchFiles(): Promise<FileInfo[]> {
  const res = await fetch(`${API_BASE}/files`);
  if (!res.ok) throw new Error(`获取文件列表失败 (${res.status})`);
  const data = await res.json();
  return data.files ?? [];
}

export async function fetchReviewResult(
  fileId: string
): Promise<ReviewResult | null> {
  try {
    const res = await fetch(`${API_BASE}/reviews/${fileId}`);
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`获取审查结果失败 (${res.status})`);
    return await res.json();
  } catch {
    return null;
  }
}

export async function uploadFile(
  file: File,
  onProgress: (progress: number) => void
): Promise<FileInfo> {
  const formData = new FormData();
  formData.append('file', file);

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_BASE}/files/upload`);

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        const data = JSON.parse(xhr.responseText);
        resolve({
          id: data.id,
          filename: data.filename,
          size: data.size,
          upload_time: new Date().toISOString().replace('T', ' ').slice(0, 19),
          status: 'processing',
          contract_type: '',
          review_progress: 0,
        });
      } else {
        reject(new Error(`上传失败 (${xhr.status})`));
      }
    };

    xhr.onerror = () => reject(new Error('上传失败'));
    xhr.send(formData);
  });
}

export async function deleteFile(fileId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/files/${fileId}`, {
    method: 'DELETE',
  });
  if (!res.ok && res.status !== 404) {
    throw new Error(`删除失败 (${res.status})`);
  }
}

export function getDownloadUrl(fileId: string): string {
  return `${API_BASE}/files/${fileId}/download`;
}

// ── PDF Report export ──────────────────────────────────

export function getPdfExportUrl(fileId: string): string {
  return `${API_BASE}/reviews/${fileId}/export/pdf`;
}

export async function downloadPdfReport(fileId: string, filename?: string): Promise<void> {
  const url = getPdfExportUrl(fileId);
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`导出PDF报告失败 (${res.status})`);
  }

  const blob = await res.blob();
  const blobUrl = URL.createObjectURL(blob);

  const a = document.createElement('a');
  a.href = blobUrl;
  a.download = filename ? filename : '合规审查报告.pdf';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(blobUrl);
}
