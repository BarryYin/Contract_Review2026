import { useState, useEffect, Fragment } from 'react';
import { useNavigate } from 'react-router-dom';

const API_BASE = '/api';

interface ReviewItem {
  file_id: string;
  filename: string;
  contract_type: string;
  risk_score: number;
  risk_level: string;
  review_time: string;
  issues_count: number;
}

const riskBadge = (l: string) =>
  l === 'high' ? 'bg-red-500 text-white' : l === 'medium' ? 'bg-orange-500 text-white' : 'bg-green-500 text-white';
const riskLabel = (l: string) => (l === 'high' ? '高风险' : l === 'medium' ? '中风险' : '低风险');
const scoreColor = (s: number) => (s >= 80 ? 'text-green-600' : s >= 60 ? 'text-orange-500' : 'text-red-600');

function formatDate(iso: string | undefined | null): string {
  if (!iso) return '-';
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    const pad = (n: number) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  } catch {
    return iso;
  }
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [reviews, setReviews] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState<'time' | 'score' | 'risk'>('time');
  const [compareMode, setCompareMode] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    loadReviews();
    const interval = setInterval(loadReviews, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadReviews = async () => {
    try {
      const res = await fetch(`${API_BASE}/reviews`);
      if (res.ok) {
        const data = await res.json();
        setReviews(data.reviews || []);
      }
    } catch {}
    setLoading(false);
  };

  const handleBatchUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    setUploading(true);
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) formData.append('files', files[i]);
    try {
      const res = await fetch(`${API_BASE}/files/batch-upload`, { method: 'POST', body: formData });
      if (res.ok) {
        await new Promise((r) => setTimeout(r, 2000));
        loadReviews();
      }
    } catch {}
    setUploading(false);
    e.target.value = '';
  };

  const handleCompare = async () => {
    const ids = Array.from(selected);
    if (ids.length !== 2) { alert('请选择2份合同进行对比'); return; }
    navigate(`/compare?a=${ids[0]}&b=${ids[1]}`);
  };

  const sorted = [...reviews].sort((a, b) => {
    if (sortBy === 'score') return a.risk_score - b.risk_score;
    if (sortBy === 'risk') {
      const order: Record<string, number> = { high: 0, medium: 1, low: 2 };
      return (order[a.risk_level] ?? 2) - (order[b.risk_level] ?? 2);
    }
    return (b.review_time || '').localeCompare(a.review_time || '');
  });

  const total = reviews.length;
  const highCount = reviews.filter((r) => r.risk_level === 'high').length;
  const medCount = reviews.filter((r) => r.risk_level === 'medium').length;
  const lowCount = reviews.filter((r) => r.risk_level === 'low').length;
  const avgScore = total ? Math.round(reviews.reduce((s, r) => s + r.risk_score, 0) / total) : 0;

  return (
    <div className="max-w-7xl mx-auto p-4">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">批量审查 Dashboard</h1>
        <div className="flex gap-2">
          <button
            onClick={() => setCompareMode(!compareMode)}
            className={`px-3 py-1.5 rounded text-sm ${compareMode ? 'bg-purple-600 text-white' : 'bg-gray-200'}`}
          >
            {compareMode ? '取消对比' : '对比分析'}
          </button>
          {compareMode && selected.size === 2 && (
            <button onClick={handleCompare} className="bg-purple-600 text-white px-3 py-1.5 rounded text-sm">
              开始对比
            </button>
          )}
          <label className={`px-4 py-1.5 rounded text-sm cursor-pointer ${uploading ? 'bg-gray-400 text-white' : 'bg-blue-600 text-white hover:bg-blue-700'}`}>
            {uploading ? '上传中...' : '批量上传'}
            <input type="file" multiple accept=".pdf,.docx,.doc,.png,.jpg,.jpeg" className="hidden" onChange={handleBatchUpload} disabled={uploading} />
          </label>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-5 gap-3 mb-6">
        <div className="bg-white rounded-lg shadow p-3 text-center">
          <div className="text-2xl font-bold">{total}</div>
          <div className="text-xs text-gray-500">总合同数</div>
        </div>
        <div className="bg-white rounded-lg shadow p-3 text-center">
          <div className={`text-2xl font-bold ${scoreColor(avgScore)}`}>{avgScore}</div>
          <div className="text-xs text-gray-500">平均评分</div>
        </div>
        <div className="bg-white rounded-lg shadow p-3 text-center">
          <div className="text-2xl font-bold text-red-600">{highCount}</div>
          <div className="text-xs text-gray-500">高风险</div>
        </div>
        <div className="bg-white rounded-lg shadow p-3 text-center">
          <div className="text-2xl font-bold text-orange-500">{medCount}</div>
          <div className="text-xs text-gray-500">中风险</div>
        </div>
        <div className="bg-white rounded-lg shadow p-3 text-center">
          <div className="text-2xl font-bold text-green-600">{lowCount}</div>
          <div className="text-xs text-gray-500">低风险</div>
        </div>
      </div>

      {/* Sort */}
      <div className="flex gap-2 mb-3">
        {(['time', 'score', 'risk'] as const).map((s) => (
          <button key={s} onClick={() => setSortBy(s)} className={`px-3 py-1 rounded text-sm ${sortBy === s ? 'bg-gray-800 text-white' : 'bg-gray-200'}`}>
            {s === 'time' ? '按时间' : s === 'score' ? '按评分' : '按风险'}
          </button>
        ))}
      </div>

      {/* Heatmap — full scrollable with continuous color scale */}
      {reviews.length > 0 && (
        <div className="bg-white rounded-lg shadow p-4 mb-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-sm">风险分布热力图</h3>
            <div className="flex items-center gap-2 text-xs text-gray-400">
              <span>安全</span>
              <div className="flex h-3 rounded overflow-hidden" style={{ width: 120 }}>
                {Array.from({ length: 10 }, (_, i) => {
                  const t = i / 9;
                  const r = Math.round(34 + t * 221);
                  const g = Math.round(197 - t * 145);
                  const b = Math.round(94 - t * 62);
                  return <div key={i} style={{ flex: 1, backgroundColor: `rgb(${r},${g},${b})` }} />;
                })}
              </div>
              <span>危险</span>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs border-collapse" style={{ minWidth: Math.max(400, reviews.length * 90 + 80) }}>
              <thead>
                <tr>
                  <th className="text-left py-1 px-2 w-20 text-gray-500 font-normal sticky left-0 bg-white z-10">维度</th>
                  {reviews.map((r) => (
                    <th key={r.file_id} className="text-center py-1 px-1 font-normal">
                      <div className="truncate max-w-[80px]" title={r.filename}>{r.filename?.replace(/\.[^.]+$/, '').slice(0, 8)}</div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[
                  { label: '评分', getValue: (r: ReviewItem) => r.risk_score, max: 100, invert: true },
                  { label: '高风险', getValue: (r: ReviewItem) => reviews.filter(x => x.risk_level === 'high' && x.file_id === r.file_id).length ? 1 : 0, max: 1, invert: false },
                  { label: '问题数', getValue: (r: ReviewItem) => r.issues_count, max: Math.max(...reviews.map(x => x.issues_count), 1), invert: false },
                  { label: '风险等级', getValue: (r: ReviewItem) => r.risk_level === 'high' ? 3 : r.risk_level === 'medium' ? 2 : 1, max: 3, invert: false },
                ].map((row) => (
                  <tr key={row.label} className="border-t">
                    <td className="py-1 px-2 text-gray-500 sticky left-0 bg-white z-10">{row.label}</td>
                    {reviews.map((r) => {
                      const val = row.getValue(r);
                      const intensity = Math.min(val / row.max, 1);
                      // Continuous green → yellow → red
                      const t = row.invert ? 1 - intensity : intensity;
                      const cr = Math.round(34 + t * 221);
                      const cg = Math.round(197 - t * 145);
                      const cb = Math.round(94 - t * 62);
                      return (
                        <td key={r.file_id} className="text-center py-1.5 px-1">
                          <div
                            className="rounded px-1 py-0.5 font-medium"
                            style={{
                              backgroundColor: `rgba(${cr},${cg},${cb},0.25)`,
                              color: `rgb(${cr},${cg},${cb})`,
                            }}
                          >
                            {row.label === '风险等级'
                              ? (r.risk_level === 'high' ? '高' : r.risk_level === 'medium' ? '中' : '低')
                              : val}
                          </div>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Cards */}
      {loading ? (
        <div className="text-center text-gray-500 py-8">加载中...</div>
      ) : sorted.length === 0 ? (
        <div className="text-center text-gray-500 py-8">暂无审查结果，请上传合同文件</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {sorted.map((r) => (
            <div
              key={r.file_id}
              onClick={() => {
                if (compareMode) {
                  const s = new Set(selected);
                  if (s.has(r.file_id)) s.delete(r.file_id);
                  else if (s.size < 2) s.add(r.file_id);
                  setSelected(s);
                } else {
                  navigate(`/review/${r.file_id}`);
                }
              }}
              className={`bg-white rounded-lg shadow p-3 cursor-pointer hover:shadow-md transition-shadow border-2 ${
                selected.has(r.file_id) ? 'border-purple-500' : 'border-transparent'
              }`}
            >
              <div className="flex justify-between items-start mb-2">
                <div className="font-medium text-sm truncate flex-1" title={r.filename}>{r.filename}</div>
                <span className={`text-xs px-2 py-0.5 rounded ${riskBadge(r.risk_level)}`}>{riskLabel(r.risk_level)}</span>
              </div>
              <div className="flex items-end justify-between">
                <div>
                  <div className={`text-3xl font-bold ${scoreColor(r.risk_score)}`}>{r.risk_score}</div>
                  <div className="text-xs text-gray-500">{r.contract_type || '未知类型'}</div>
                </div>
                <div className="text-right">
                  <div className="text-sm text-gray-600">{r.issues_count} 个问题</div>
                  <div className="text-xs text-gray-400">{formatDate(r.review_time)}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
