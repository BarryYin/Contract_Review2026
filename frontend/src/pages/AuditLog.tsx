import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const API_BASE = '/api';

interface AuditEntry {
  timestamp: string;
  file_id: string;
  action: string;
  details: Record<string, any>;
  file_hash?: string;
}

const ACTION_LABELS: Record<string, string> = {
  upload: '上传文件',
  review_started: '开始审查',
  review_completed: '审查完成',
  issue_adopted: '采纳建议',
  issue_rejected: '拒绝建议',
  pdf_exported: '导出PDF',
  docx_exported: '导出DOCX',
};

const ACTION_COLORS: Record<string, string> = {
  upload: 'bg-blue-100 text-blue-800',
  review_started: 'bg-purple-100 text-purple-800',
  review_completed: 'bg-green-100 text-green-800',
  issue_adopted: 'bg-emerald-100 text-emerald-800',
  issue_rejected: 'bg-red-100 text-red-800',
  pdf_exported: 'bg-gray-100 text-gray-800',
  docx_exported: 'bg-gray-100 text-gray-800',
};

const RISK_COLORS: Record<string, string> = {
  high: 'bg-red-100 text-red-700',
  medium: 'bg-orange-100 text-orange-700',
  low: 'bg-green-100 text-green-700',
};

function fmtTime(iso: string): string {
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    const pad = (n: number) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  } catch {
    return iso;
  }
}

function fmtHash(hash?: string): string {
  if (!hash) return '-';
  return hash.slice(0, 12) + '...';
}

export default function AuditLog() {
  const navigate = useNavigate();
  const [logs, setLogs] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterAction, setFilterAction] = useState('');
  const [filterRisk, setFilterRisk] = useState('');
  const [filterType, setFilterType] = useState('');
  const [filterDateFrom, setFilterDateFrom] = useState('');
  const [filterDateTo, setFilterDateTo] = useState('');

  useEffect(() => {
    loadLogs();
  }, [filterAction, filterRisk, filterType, filterDateFrom, filterDateTo]);

  const loadLogs = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filterAction) params.set('action', filterAction);
      if (filterRisk) params.set('risk_level', filterRisk);
      if (filterType) params.set('contract_type', filterType);
      if (filterDateFrom) params.set('start_time', new Date(filterDateFrom).toISOString());
      if (filterDateTo) params.set('end_time', new Date(filterDateTo + 'T23:59:59').toISOString());
      const res = await fetch(`${API_BASE}/reviews/audit-log/log?${params}`);
      if (res.ok) {
        const data = await res.json();
        setLogs(data.logs || []);
      }
    } catch {}
    setLoading(false);
  };

  const contractTypes = [...new Set(
    logs.map((l) => l.details?.contract_type).filter(Boolean)
  )];

  // Group by file_id for a cleaner view
  const groupedByFile = logs.reduce<Record<string, AuditEntry[]>>((acc, log) => {
    const key = log.file_id;
    if (!acc[key]) acc[key] = [];
    acc[key].push(log);
    return acc;
  }, {});

  return (
    <div className="max-w-7xl mx-auto p-4">
      <div className="flex items-center justify-between mb-6">
        <div>
          <button onClick={() => navigate('/dashboard')} className="text-blue-600 hover:underline mb-2 inline-block">
            &larr; 返回 Dashboard
          </button>
          <h1 className="text-2xl font-bold">审计日志</h1>
          <p className="text-sm text-gray-500 mt-1">系统操作记录：上传、审查、采纳/拒绝、导出等所有操作</p>
        </div>
        <div className="text-sm text-gray-500">
          共 {logs.length} 条记录
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-3 mb-4 flex flex-wrap items-center gap-3">
        <span className="text-sm text-gray-500">筛选:</span>
        <select
          value={filterAction}
          onChange={(e) => setFilterAction(e.target.value)}
          className="border rounded px-2 py-1 text-sm"
        >
          <option value="">全部操作</option>
          {Object.entries(ACTION_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
        <select
          value={filterRisk}
          onChange={(e) => setFilterRisk(e.target.value)}
          className="border rounded px-2 py-1 text-sm"
        >
          <option value="">全部风险</option>
          <option value="high">高风险</option>
          <option value="medium">中风险</option>
          <option value="low">低风险</option>
        </select>
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          className="border rounded px-2 py-1 text-sm"
        >
          <option value="">全部类型</option>
          {contractTypes.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
        <input
          type="date"
          value={filterDateFrom}
          onChange={(e) => setFilterDateFrom(e.target.value)}
          className="border rounded px-2 py-1 text-sm"
        />
        <span className="text-gray-400">~</span>
        <input
          type="date"
          value={filterDateTo}
          onChange={(e) => setFilterDateTo(e.target.value)}
          className="border rounded px-2 py-1 text-sm"
        />
        <button
          onClick={() => {
            setFilterAction('');
            setFilterRisk('');
            setFilterType('');
            setFilterDateFrom('');
            setFilterDateTo('');
          }}
          className="text-xs text-gray-400 hover:text-gray-600"
        >
          重置
        </button>
      </div>

      {/* Log table */}
      {loading ? (
        <div className="text-center text-gray-500 py-8">加载中...</div>
      ) : logs.length === 0 ? (
        <div className="text-center text-gray-500 py-8">暂无审计日志</div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b">
                <th className="text-left py-2 px-3 font-medium">时间</th>
                <th className="text-left py-2 px-3 font-medium">操作</th>
                <th className="text-left py-2 px-3 font-medium">文件ID</th>
                <th className="text-left py-2 px-3 font-medium">合同类型</th>
                <th className="text-left py-2 px-3 font-medium">风险</th>
                <th className="text-left py-2 px-3 font-medium">文件哈希</th>
                <th className="text-left py-2 px-3 font-medium">详情</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log, idx) => (
                <tr key={idx} className="border-b last:border-0 hover:bg-gray-50">
                  <td className="py-2 px-3 text-xs text-gray-600 whitespace-nowrap">{fmtTime(log.timestamp)}</td>
                  <td className="py-2 px-3">
                    <span className={`text-xs px-2 py-0.5 rounded ${ACTION_COLORS[log.action] || 'bg-gray-100'}`}>
                      {ACTION_LABELS[log.action] || log.action}
                    </span>
                  </td>
                  <td className="py-2 px-3">
                    <button
                      onClick={() => navigate(`/review/${log.file_id}`)}
                      className="text-xs text-blue-600 hover:underline font-mono"
                    >
                      {log.file_id.slice(0, 8)}...
                    </button>
                  </td>
                  <td className="py-2 px-3 text-xs text-gray-600">
                    {log.details?.contract_type || '-'}
                  </td>
                  <td className="py-2 px-3">
                    {log.details?.risk_level ? (
                      <span className={`text-xs px-2 py-0.5 rounded ${RISK_COLORS[log.details.risk_level] || ''}`}>
                        {log.details.risk_level === 'high' ? '高' : log.details.risk_level === 'medium' ? '中' : '低'}
                      </span>
                    ) : '-'}
                  </td>
                  <td className="py-2 px-3 text-xs font-mono text-gray-400" title={log.file_hash}>
                    {fmtHash(log.file_hash)}
                  </td>
                  <td className="py-2 px-3 text-xs text-gray-500 max-w-xs truncate" title={JSON.stringify(log.details)}>
                    {log.details?.severity && <span>严重度:{log.details.severity} </span>}
                    {log.details?.issue_id && <span>问题:{log.details.issue_id?.slice(0, 8)}... </span>}
                    {log.details?.clause && <span>条款:{String(log.details.clause).slice(0, 20)} </span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
