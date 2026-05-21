export interface FileInfo {
  id: string;
  filename: string;
  size: number;
  upload_time: string;
  status: 'uploading' | 'processing' | 'completed' | 'error';
  risk_level?: 'low' | 'medium' | 'high';
  contract_type?: string;
  review_progress?: number;
}

export interface UploadProgress {
  file_id: string;
  filename: string;
  progress: number;
  status: 'uploading' | 'processing' | 'completed' | 'error';
}

export interface ReviewResult {
  id: string;
  file_id: string;
  risk_score: number;
  risk_level: 'low' | 'medium' | 'high';
  contract_type: string;
  issues: RiskIssue[];
  summary: string;
}

export interface RiskIssue {
  id: string;
  clause: string;
  risk_type: string;
  severity: 'low' | 'medium' | 'high';
  description: string;
  suggestion: string;
}
