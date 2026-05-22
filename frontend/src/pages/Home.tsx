import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FileText,
  CheckCircle2,
  AlertTriangle,
  AlertOctagon,
  LayoutDashboard,
  Shield,
  ShoppingCart,
  Briefcase,
  ChevronRight,
  ArrowLeft,
  Zap,
} from 'lucide-react';
import StatsCard from '../components/StatsCard';
import FileUpload from '../components/FileUpload';
import FileList from '../components/FileList';
import { fetchFiles, deleteFile, startReview } from '../api/client';
import type { FileInfo } from '../types';

/* ── Template definitions ─────────────────────────────── */

interface ReviewTemplate {
  id: string;
  name: string;
  description: string;
  icon: React.ElementType;
  color: string;
  bgColor: string;
}

const TEMPLATES: ReviewTemplate[] = [
  {
    id: 'general',
    name: '通用合同审查',
    description: '适用于各类合同的通用合规审查，覆盖违约责任、付款条款、保密义务等核心条款的风险识别。',
    icon: Shield,
    color: '#533afd',
    bgColor: 'rgba(83,58,253,0.06)',
  },
  {
    id: 'procurement',
    name: '采购合同审查',
    description: '针对采购合同的专项审查模板，重点关注交付验收、质量标准、付款条件、违约金比例等采购风险。',
    icon: ShoppingCart,
    color: '#0ea5e9',
    bgColor: 'rgba(14,165,233,0.06)',
  },
  {
    id: 'labor',
    name: '劳动合同审查',
    description: '针对劳动合同的合规审查模板，覆盖劳动报酬、工时制度、竞业限制、解除条件等劳动法规要点。',
    icon: Briefcase,
    color: '#f59e0b',
    bgColor: 'rgba(245,158,11,0.06)',
  },
];

/* ── Step type ────────────────────────────────────────── */

type Step = 'upload' | 'template';

/* ── Home component ───────────────────────────────────── */

export default function Home() {
  const navigate = useNavigate();
  const [files, setFiles] = useState<FileInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);

  // Step state
  const [currentStep, setCurrentStep] = useState<Step>('upload');
  const [pendingFiles, setPendingFiles] = useState<FileInfo[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');
  const [starting, setStarting] = useState(false);

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

  /* ── Batch upload (unchanged, goes directly to dashboard) ── */

  const handleBatchUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files;
    if (!fileList || fileList.length === 0) return;
    setUploading(true);
    try {
      const { batchUpload } = await import('../api/client');
      await batchUpload(Array.from(fileList));
      setTimeout(() => { loadFiles(); navigate('/dashboard'); }, 2000);
    } catch {}
    setUploading(false);
    e.target.value = '';
  };

  /* ── Single file uploaded → switch to template step ── */

  const handleFileUploaded = useCallback((fileInfo: FileInfo) => {
    setPendingFiles((prev) => [...prev, fileInfo]);
    setCurrentStep('template');
  }, []);

  /* ── Start review with selected template ── */

  const handleStartReview = async () => {
    if (!selectedTemplate || pendingFiles.length === 0) return;
    setStarting(true);
    try {
      // Trigger review for each pending file
      for (const f of pendingFiles) {
        await startReview(f.id, selectedTemplate);
      }
      // Brief delay then navigate to dashboard
      setTimeout(() => {
        loadFiles();
        navigate('/dashboard');
      }, 1500);
    } catch (err) {
      console.error('Failed to start review:', err);
    }
    setStarting(false);
  };

  /* ── Back to upload step ── */

  const handleBackToUpload = () => {
    setPendingFiles([]);
    setSelectedTemplate('');
    setCurrentStep('upload');
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

      {/* ── Step indicator ── */}
      <div className="flex items-center gap-3 mb-6">
        <div className="flex items-center gap-2">
          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold ${
            currentStep === 'upload'
              ? 'bg-[#533afd] text-white'
              : 'bg-green-500 text-white'
          }`}>
            {currentStep === 'upload' ? '1' : '✓'}
          </div>
          <span className={`text-sm font-medium ${currentStep === 'upload' ? 'text-[#533afd]' : 'text-green-600'}`}>
            上传合同
          </span>
        </div>
        <div className={`flex-1 h-0.5 ${currentStep === 'template' ? 'bg-[#533afd]' : 'bg-gray-200'}`} />
        <div className="flex items-center gap-2">
          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold ${
            currentStep === 'template'
              ? 'bg-[#533afd] text-white'
              : 'bg-gray-200 text-gray-500'
          }`}>
            2
          </div>
          <span className={`text-sm font-medium ${currentStep === 'template' ? 'text-[#533afd]' : 'text-gray-400'}`}>
            选择模板
          </span>
        </div>
        <div className="flex-1 h-0.5 bg-gray-200" />
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold bg-gray-200 text-gray-500">
            3
          </div>
          <span className="text-sm font-medium text-gray-400">开始审查</span>
        </div>
      </div>

      {/* ── Step: Upload ── */}
      {currentStep === 'upload' && (
        <div className="mb-10">
          <h2 className="text-lg font-semibold text-[#061b31] mb-4">上传合同</h2>
          <FileUpload onUploadComplete={loadFiles} onFileUploaded={handleFileUploaded} />
        </div>
      )}

      {/* ── Step: Template Selection ── */}
      {currentStep === 'template' && (
        <div className="mb-10">
          {/* Pending files summary */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-semibold text-[#061b31]">选择合规模板</h2>
              <button
                onClick={handleBackToUpload}
                className="flex items-center gap-1.5 text-sm text-[#64748d] hover:text-[#533afd] font-medium transition-colors"
              >
                <ArrowLeft className="w-4 h-4" />
                返回上传
              </button>
            </div>
            <p className="text-sm text-[#64748d]">
              已上传 {pendingFiles.length} 份合同，请选择审查模板后开始合规分析
            </p>
          </div>

          {/* File chips */}
          <div className="flex flex-wrap gap-2 mb-6">
            {pendingFiles.map((f) => (
              <span
                key={f.id}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[rgba(83,58,253,0.08)] text-[#533afd] text-sm rounded-full"
              >
                <FileText className="w-3.5 h-3.5" />
                {f.filename}
              </span>
            ))}
          </div>

          {/* Template cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            {TEMPLATES.map((tmpl) => {
              const Icon = tmpl.icon;
              const isSelected = selectedTemplate === tmpl.id;
              return (
                <button
                  key={tmpl.id}
                  onClick={() => setSelectedTemplate(tmpl.id)}
                  className={`relative text-left p-5 rounded-xl border-2 transition-all duration-200 ${
                    isSelected
                      ? 'border-[#533afd] shadow-lg'
                      : 'border-[#e5edf5] hover:border-[#533afd]/40 hover:shadow-md'
                  }`}
                  style={{
                    background: isSelected ? 'rgba(83,58,253,0.04)' : '#fff',
                    boxShadow: isSelected
                      ? 'rgba(83,58,253,0.15) 0px 4px 16px -2px'
                      : undefined,
                  }}
                >
                  {isSelected && (
                    <div className="absolute top-3 right-3">
                      <div className="w-6 h-6 bg-[#533afd] rounded-full flex items-center justify-center">
                        <CheckCircle2 className="w-4 h-4 text-white" />
                      </div>
                    </div>
                  )}
                  <div
                    className="w-12 h-12 rounded-xl flex items-center justify-center mb-4"
                    style={{ backgroundColor: tmpl.bgColor }}
                  >
                    <Icon className="w-6 h-6" style={{ color: tmpl.color }} />
                  </div>
                  <h3 className="text-base font-semibold text-[#061b31] mb-2">
                    {tmpl.name}
                  </h3>
                  <p className="text-sm text-[#64748d] leading-relaxed">
                    {tmpl.description}
                  </p>
                </button>
              );
            })}
          </div>

          {/* Start review button */}
          <div className="flex items-center gap-4">
            <button
              onClick={handleStartReview}
              disabled={!selectedTemplate || starting}
              className={`flex items-center gap-2 px-6 py-3 rounded-lg text-sm font-semibold transition-all duration-200 ${
                selectedTemplate && !starting
                  ? 'bg-[#533afd] text-white hover:bg-[#4434d4] shadow-md hover:shadow-lg'
                  : 'bg-gray-200 text-gray-400 cursor-not-allowed'
              }`}
            >
              {starting ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  正在启动审查...
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4" />
                  开始审查
                  <ChevronRight className="w-4 h-4" />
                </>
              )}
            </button>
            {selectedTemplate && !starting && (
              <span className="text-sm text-[#64748d]">
                将使用「{TEMPLATES.find((t) => t.id === selectedTemplate)?.name}」模板审查 {pendingFiles.length} 份合同
              </span>
            )}
          </div>
        </div>
      )}

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
