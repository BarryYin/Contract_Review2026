import type {
  FileInfo,
  ReviewResult,
  StructuredResponse,
  BilingualResponse,
  ScoringResponse,
  IssueActionResponse,
} from '../types';

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
  onProgress: (progress: number) => void,
  autoReview: boolean = false
): Promise<FileInfo> {
  const formData = new FormData();
  formData.append('file', file);

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_BASE}/files/upload?auto_review=${autoReview}`);

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
          status: autoReview ? 'processing' : 'uploading',
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

// ── Structured Info ────────────────────────────────────

export async function getStructuredInfo(
  fileId: string
): Promise<StructuredResponse | null> {
  try {
    const res = await fetch(`${API_BASE}/reviews/${fileId}/structured`);
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`获取结构化信息失败 (${res.status})`);
    return await res.json();
  } catch {
    return null;
  }
}

// ── Bilingual Analysis ─────────────────────────────────

export async function getBilingualAnalysis(
  fileId: string
): Promise<BilingualResponse | null> {
  try {
    const res = await fetch(`${API_BASE}/reviews/${fileId}/bilingual`);
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`获取双语分析失败 (${res.status})`);
    return await res.json();
  } catch {
    return null;
  }
}

// ── Scoring Dimensions ─────────────────────────────────

export async function getScoring(
  fileId: string
): Promise<ScoringResponse | null> {
  try {
    const res = await fetch(`${API_BASE}/reviews/${fileId}/scoring`);
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`获取评分详情失败 (${res.status})`);
    return await res.json();
  } catch {
    return null;
  }
}

// ── Issue Actions: Adopt / Reject ──────────────────────

export async function adoptIssue(
  fileId: string,
  issueId: string
): Promise<IssueActionResponse> {
  const res = await fetch(
    `${API_BASE}/reviews/${fileId}/issues/${issueId}/adopt`,
    { method: 'POST' }
  );
  if (!res.ok) throw new Error(`采纳操作失败 (${res.status})`);
  return await res.json();
}

export async function rejectIssue(
  fileId: string,
  issueId: string
): Promise<IssueActionResponse> {
  const res = await fetch(
    `${API_BASE}/reviews/${fileId}/issues/${issueId}/reject`,
    { method: 'POST' }
  );
  if (!res.ok) throw new Error(`拒绝操作失败 (${res.status})`);
  return await res.json();
}

// ── PDF Report export ──────────────────────────────────

export function getPdfExportUrl(fileId: string): string {
  return `${API_BASE}/reviews/${fileId}/export/pdf`;
}

export async function downloadPdfReport(
  fileId: string,
  filename?: string
): Promise<void> {
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

// ── DOCX Track-Changes export ──────────────────────────

export function getDocxExportUrl(fileId: string): string {
  return `${API_BASE}/reviews/${fileId}/export/docx`;
}

export async function downloadDocxReport(
  fileId: string,
  filename?: string
): Promise<void> {
  const url = getDocxExportUrl(fileId);
  const res = await fetch(url);
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new Error(
      data?.detail || `导出DOCX失败 (${res.status})`
    );
  }
  const blob = await res.blob();
  const blobUrl = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = blobUrl;
  a.download = filename ? filename : '合规审查报告_TrackChanges.docx';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(blobUrl);
}


// ── Batch Upload ───────────────────────────────────────

export async function batchUpload(files: File[]): Promise<{ results: any[]; total: number }> {
  const formData = new FormData();
  files.forEach((f) => formData.append('files', f));
  const res = await fetch(`${API_BASE}/files/batch-upload`, { method: 'POST', body: formData });
  if (!res.ok) throw new Error('批量上传失败');
  return await res.json();
}

export async function listReviews(): Promise<{ reviews: any[]; total: number }> {
  const res = await fetch(`${API_BASE}/reviews`);
  if (!res.ok) throw new Error('获取列表失败');
  return await res.json();
}

export async function compareReviews(fileIdA: string, fileIdB: string): Promise<any> {
  const res = await fetch(`${API_BASE}/reviews/compare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file_id_a: fileIdA, file_id_b: fileIdB }),
  });
  if (!res.ok) throw new Error('对比分析失败');
  return await res.json();
}

// ── Start Review with Template ─────────────────────────

export async function startReview(
  fileId: string,
  template: string
): Promise<{ file_id: string; template: string; status: string; message: string }> {
  const res = await fetch(`${API_BASE}/reviews/${fileId}/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ template }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new Error(data?.detail || `启动审查失败 (${res.status})`);
  }
  return await res.json();
}
