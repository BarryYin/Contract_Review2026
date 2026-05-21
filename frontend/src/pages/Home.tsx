import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText, CheckCircle2, AlertTriangle, AlertOctagon, LayoutDashboard } from 'lucide-react';
import StatsCard from '../components/StatsCard';
import FileUpload from '../components/FileUpload';
import FileList from '../components/FileList';
import { fetchFiles, deleteFile, listReviews, batchUpload } from '../api/client';
import type { FileInfo } from '../types';

export default function Home() {
  const navigate = useNavigate();
  const [files, setFiles] = useState<FileInfo[]>((null as unknown as FileInfo[]) || []);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);

  const loadFiles = useCallback(async () => {
    try {
      const data = await fetchFiles();
      setFiles(data);
    } catch {}
    finally { setLoading(false); }
  }, []);

  useEffect(() => { loadFiles(); }, [loadFiles]);

  const handleDelete = useCallback(async (id: string) => {
    await deleteFile(id);
    setFiles((prev) => prev.filter((f) => f.id !== id));
  }, []);

  const handleBatchUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files;
    if (!fileList || fileList.length === 0) return;
    setUploading(true);
    try {
      await batchUpload(Array.from(fileList));
      setTimeout(() => { loadFiles(); navigate('/dashboard'); }, 2000);
    } catch {}
    setUploading(false);
    e.target.value = '';
  };

  const completed = files.filter((f: any) => f.status === 'completed').length;
  const highRisk = files.filter((f: any) => f.risk_level === 'high').length;
  const processing = files.filter((f: any) => f.status === 'processing').length;

  return (
    <div className="max-w-6xl mx-auto px-6 py-10">
      {/* Hero */}
      <div className="mb-8">
        <h1 className="text-3xl font-semibold text-[#061b31] tracking-tight">
          智能合同合规审查
        </h1>
        <p className="text-base text-[#64748d] mt-2">
          基于 AI 的合同风险识别与合规分析平台 — 支持 NER 实体识别、规则引擎、批量审查与合同对比
        </p>
      </div>

      {/* Quick actions */}
      <div className="flex gap-3 mb-8">
        <button
          onClick={() => navigate('/dashboard')}
          className="flex items-center gap-2 px-4 py-2 bg-[#533afd] text-white rounded-lg hover:bg-[#4434d4] text-sm font-medium"
        >
          <LayoutDashboard className="w-4 h-4" />
          批量审查 Dashboard
        </button>
        <label className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium cursor-pointer ${
          uploading ? 'bg-gray-400 text-white' : 'bg-green-600 text-white hover:bg-green-700'
        }`}>
          {uploading ? '上传中...' : '批量上传 (≥5份)'}
          <input
            type="file"
            multiple
            accept=".pdf,.docx,.doc,.png,.jpg,.jpeg"
            className="hidden"
            onChange={handleBatchUpload}
            disabled={uploading}
          />
        </label>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
        <StatsCard icon={FileText} value={files.length} label="总合同数" color="#533afd" bgColor="rgba(83,58,253,0.08)" />
        <StatsCard icon={CheckCircle2} value={completed} label="已完成审查" color="#15be53" bgColor="rgba(21,190,83,0.1)" />
        <StatsCard icon={AlertTriangle} value={processing} label="审查中" color="#f59e0b" bgColor="rgba(245,158,11,0.1)" />
        <StatsCard icon={AlertOctagon} value={highRisk} label="高风险项" color="#ef4444" bgColor="rgba(239,68,68,0.1)" />
      </div>

      {/* Upload Section */}
      <div className="mb-10">
        <h2 className="text-lg font-semibold text-[#061b31] mb-4">上传合同</h2>
        <FileUpload onUploadComplete={loadFiles} />
      </div>

      {/* File List */}
      <div id="file-list">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-[#061b31]">合同列表</h2>
          <button onClick={loadFiles} className="text-sm text-[#533afd] hover:text-[#4434d4] font-medium">刷新列表</button>
        </div>
        <div className="bg-white rounded-lg border border-[#e5edf5] overflow-hidden" style={{ boxShadow: 'rgba(50,50,93,0.08) 0px 2px 8px -2px, rgba(0,0,0,0.05) 0px 4px 12px -4px' }}>
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <div className="w-6 h-6 border-2 border-[#533afd] border-t-transparent rounded-full animate-spin" />
            </div>
          ) : (
            <FileList files={files} onDelete={handleDelete} onRefresh={loadFiles} />
          )}
        </div>
      </div>
    </div>
  );
}
