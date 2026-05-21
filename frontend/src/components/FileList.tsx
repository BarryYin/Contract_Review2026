import { useNavigate } from 'react-router-dom';
import {
  Eye,
  Download,
  Trash2,
  FileText,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  Inbox,
} from 'lucide-react';
import { getDownloadUrl } from '../api/client';
import type { FileInfo } from '../types';

interface FileListProps {
  files: FileInfo[];
  onDelete: (id: string) => void;
  onRefresh?: () => void;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function RiskBadge({ level }: { level: 'low' | 'medium' | 'high' }) {
  const config = {
    low: {
      label: '低风险',
      color: '#15be53',
      bg: 'rgba(21,190,83,0.1)',
    },
    medium: {
      label: '中风险',
      color: '#f59e0b',
      bg: 'rgba(245,158,11,0.1)',
    },
    high: {
      label: '高风险',
      color: '#ef4444',
      bg: 'rgba(239,68,68,0.1)',
    },
  };
  const c = config[level];
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
      style={{ color: c.color, backgroundColor: c.bg }}
    >
      {c.label}
    </span>
  );
}

function StatusBadge({ status, progress }: { status: FileInfo['status']; progress?: number }) {
  if (status === 'completed') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium text-[#15be53] bg-[rgba(21,190,83,0.1)]">
        <CheckCircle2 className="w-3.5 h-3.5" />
        已完成
      </span>
    );
  }
  if (status === 'processing') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium text-[#533afd] bg-[rgba(83,58,253,0.08)]">
        <Loader2 className="w-3.5 h-3.5 animate-spin" />
        审查中 {progress !== undefined ? `${progress}%` : ''}
      </span>
    );
  }
  if (status === 'uploading') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium text-[#64748d] bg-gray-100">
        <Clock className="w-3.5 h-3.5" />
        上传中
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium text-[#ef4444] bg-[rgba(239,68,68,0.1)]">
      <AlertTriangle className="w-3.5 h-3.5" />
      错误
    </span>
  );
}

export default function FileList({ files, onDelete }: FileListProps) {
  const navigate = useNavigate();

  if (files.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="w-16 h-16 rounded-full bg-gray-50 flex items-center justify-center mb-4">
          <Inbox className="w-8 h-8 text-[#64748d]" />
        </div>
        <p className="text-[#061b31] font-medium text-base">还没有上传合同</p>
        <p className="text-sm text-[#64748d] mt-1">
          拖拽文件到上传区域开始审查
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-[#e5edf5]">
            <th className="text-left py-3 px-4 text-xs font-medium text-[#64748d] uppercase tracking-wider">
              文件名
            </th>
            <th className="text-left py-3 px-4 text-xs font-medium text-[#64748d] uppercase tracking-wider">
              合同类型
            </th>
            <th className="text-left py-3 px-4 text-xs font-medium text-[#64748d] uppercase tracking-wider">
              大小
            </th>
            <th className="text-left py-3 px-4 text-xs font-medium text-[#64748d] uppercase tracking-wider">
              上传时间
            </th>
            <th className="text-left py-3 px-4 text-xs font-medium text-[#64748d] uppercase tracking-wider">
              风险等级
            </th>
            <th className="text-left py-3 px-4 text-xs font-medium text-[#64748d] uppercase tracking-wider">
              状态
            </th>
            <th className="text-right py-3 px-4 text-xs font-medium text-[#64748d] uppercase tracking-wider">
              操作
            </th>
          </tr>
        </thead>
        <tbody>
          {files.map((file) => (
            <tr
              key={file.id}
              className="border-b border-[#e5edf5] last:border-0 hover:bg-gray-50/60 transition-colors duration-150"
            >
              <td className="py-3.5 px-4">
                <div className="flex items-center gap-2.5">
                  <FileText className="w-4.5 h-4.5 text-[#533afd] shrink-0" />
                  <span className="text-sm font-medium text-[#061b31] truncate max-w-[240px]">
                    {file.filename}
                  </span>
                </div>
              </td>
              <td className="py-3.5 px-4 text-sm text-[#273951]">
                {file.contract_type || '-'}
              </td>
              <td className="py-3.5 px-4 text-sm text-[#64748d]">
                {formatSize(file.size)}
              </td>
              <td className="py-3.5 px-4 text-sm text-[#64748d]">
                {file.upload_time}
              </td>
              <td className="py-3.5 px-4">
                {file.risk_level ? (
                  <RiskBadge level={file.risk_level} />
                ) : (
                  <span className="text-sm text-[#64748d]">-</span>
                )}
              </td>
              <td className="py-3.5 px-4">
                <StatusBadge status={file.status} progress={file.review_progress} />
              </td>
              <td className="py-3.5 px-4">
                <div className="flex items-center justify-end gap-1">
                  {file.status === 'completed' && (
                    <button
                      onClick={() => navigate(`/review/${file.id}`)}
                      className="p-2 text-[#64748d] hover:text-[#533afd] hover:bg-[rgba(83,58,253,0.06)] rounded-md transition-colors duration-150"
                      title="查看报告"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                  )}
                  <button
                    onClick={() => {
                      window.open(getDownloadUrl(file.id), '_blank');
                    }}
                    className="p-2 text-[#64748d] hover:text-[#533afd] hover:bg-[rgba(83,58,253,0.06)] rounded-md transition-colors duration-150"
                    title="下载"
                  >
                    <Download className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => {
                      onDelete(file.id);
                    }}
                    className="p-2 text-[#64748d] hover:text-[#ef4444] hover:bg-[rgba(239,68,68,0.06)] rounded-md transition-colors duration-150"
                    title="删除"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
