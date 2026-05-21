import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';

const API_BASE = '/api';

interface ComparisonResult {
  file_a: { id: string; filename: string };
  file_b: { id: string; filename: string };
  score_comparison: { a: number; b: number; diff: number };
  risk_level_comparison: { a: string; b: string };
  field_diffs: { field: string; value_a: any; value_b: any; status: string }[];
  issue_comparison: {
    a_count: number; b_count: number;
    a_high: number; b_high: number;
    a_medium: number; b_medium: number;
    common_titles: string[];
  };
  dimension_comparison: { dimension: string; score_a: number; score_b: number; diff: number }[];
}

const scoreColor = (s: number) => (s >= 80 ? 'text-green-600' : s >= 60 ? 'text-orange-500' : 'text-red-600');
const riskBadge = (l: string) =>
  l === 'high' ? 'bg-red-500 text-white' : l === 'medium' ? 'bg-orange-500 text-white' : 'bg-green-500 text-white';
const riskLabel = (l: string) => (l === 'high' ? '高风险' : l === 'medium' ? '中风险' : '低风险');
const diffColor = (d: number) => (d > 0 ? 'text-green-600' : d < 0 ? 'text-red-600' : 'text-gray-500');
const truncate = (v: any, n = 80) => {
  const s = typeof v === 'string' ? v : JSON.stringify(v);
  return s?.length > n ? s.slice(0, n) + '...' : s || '-';
};

export default function Compare() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const a = params.get('a');
  const b = params.get('b');
  const [data, setData] = useState<ComparisonResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!a || !b) { setError('缺少合同ID参数'); setLoading(false); return; }
    fetch(`${API_BASE}/reviews/compare`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file_id_a: a, file_id_b: b }),
    })
      .then((r) => r.json())
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [a, b]);

  if (loading) return <div className="flex items-center justify-center h-64 text-gray-500">对比分析中...</div>;
  if (error) return <div className="text-center py-8 text-red-600">{error}</div>;
  if (!data) return <div className="text-center py-8 text-gray-500">无对比数据</div>;

  return (
    <div className="max-w-6xl mx-auto p-4">
      <div className="mb-4">
        <button onClick={() => navigate('/dashboard')} className="text-blue-600 hover:underline mb-2 inline-block">&larr; 返回 Dashboard</button>
        <h1 className="text-2xl font-bold">合同对比分析</h1>
      </div>

      {/* Header comparison */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-4 text-center">
          <div className="text-sm text-gray-500 mb-1 truncate" title={data.file_a.filename}>{data.file_a.filename}</div>
          <div className={`text-4xl font-bold ${scoreColor(data.score_comparison.a)}`}>{data.score_comparison.a}</div>
          <span className={`inline-block px-2 py-0.5 rounded text-xs mt-1 ${riskBadge(data.risk_level_comparison.a)}`}>
            {riskLabel(data.risk_level_comparison.a)}
          </span>
        </div>
        <div className="flex items-center justify-center">
          <div className="text-center">
            <div className="text-sm text-gray-500 mb-1">评分差异</div>
            <div className={`text-3xl font-bold ${diffColor(data.score_comparison.diff)}`}>
              {data.score_comparison.diff > 0 ? '+' : ''}{data.score_comparison.diff}
            </div>
            <div className="text-xs text-gray-400 mt-1">B vs A</div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4 text-center">
          <div className="text-sm text-gray-500 mb-1 truncate" title={data.file_b.filename}>{data.file_b.filename}</div>
          <div className={`text-4xl font-bold ${scoreColor(data.score_comparison.b)}`}>{data.score_comparison.b}</div>
          <span className={`inline-block px-2 py-0.5 rounded text-xs mt-1 ${riskBadge(data.risk_level_comparison.b)}`}>
            {riskLabel(data.risk_level_comparison.b)}
          </span>
        </div>
      </div>

      {/* Issue count comparison */}
      <div className="bg-white rounded-lg shadow p-4 mb-4">
        <h3 className="font-semibold mb-3">问题数量对比</h3>
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center">
            <div className="text-lg font-bold">{data.issue_comparison.a_count}</div>
            <div className="text-xs text-gray-500">总问题</div>
            <div className="text-sm text-red-600 mt-1">{data.issue_comparison.a_high} 高风险</div>
            <div className="text-sm text-orange-500">{data.issue_comparison.a_medium} 中风险</div>
          </div>
          <div className="text-center">
            {data.issue_comparison.common_titles.length > 0 ? (
              <div>
                <div className="text-lg font-bold text-blue-600">{data.issue_comparison.common_titles.length}</div>
                <div className="text-xs text-gray-500">共同问题</div>
                <div className="text-xs text-gray-400 mt-1">
                  {data.issue_comparison.common_titles.slice(0, 3).map((t) => (
                    <div key={t} className="truncate">{t}</div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-gray-400 text-sm">无共同问题</div>
            )}
          </div>
          <div className="text-center">
            <div className="text-lg font-bold">{data.issue_comparison.b_count}</div>
            <div className="text-xs text-gray-500">总问题</div>
            <div className="text-sm text-red-600 mt-1">{data.issue_comparison.b_high} 高风险</div>
            <div className="text-sm text-orange-500">{data.issue_comparison.b_medium} 中风险</div>
          </div>
        </div>
      </div>

      {/* Dimension comparison */}
      {data.dimension_comparison.length > 0 && (
        <div className="bg-white rounded-lg shadow p-4 mb-4">
          <h3 className="font-semibold mb-3">维度评分对比</h3>
          <div className="space-y-2">
            {data.dimension_comparison.map((d) => (
              <div key={d.dimension} className="flex items-center gap-2">
                <span className="text-xs w-20 text-right text-gray-600 truncate">{d.dimension}</span>
                <div className="flex-1 flex items-center gap-1">
                  <div className="flex-1">
                    <div className="bg-gray-200 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full ${d.score_a >= 80 ? 'bg-green-500' : d.score_a >= 60 ? 'bg-orange-400' : 'bg-red-500'}`}
                        style={{ width: `${d.score_a}%` }}
                      />
                    </div>
                  </div>
                  <span className="text-xs w-8 text-center">{d.score_a}</span>
                  <span className={`text-xs w-8 text-center ${diffColor(d.diff)}`}>
                    {d.diff > 0 ? '+' : ''}{d.diff}
                  </span>
                  <span className="text-xs w-8 text-center">{d.score_b}</span>
                  <div className="flex-1">
                    <div className="bg-gray-200 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full ${d.score_b >= 80 ? 'bg-green-500' : d.score_b >= 60 ? 'bg-orange-400' : 'bg-red-500'}`}
                        style={{ width: `${d.score_b}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Field diffs */}
      {data.field_diffs.length > 0 && (
        <div className="bg-white rounded-lg shadow p-4 mb-4">
          <h3 className="font-semibold mb-3">条款差异</h3>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b">
                <th className="text-left py-1 w-24">字段</th>
                <th className="text-left py-1">合同 A</th>
                <th className="text-left py-1">合同 B</th>
                <th className="text-center py-1 w-16">差异</th>
              </tr>
            </thead>
            <tbody>
              {data.field_diffs.map((d, i) => (
                <tr key={i} className="border-b last:border-0">
                  <td className="py-1 font-medium">{d.field}</td>
                  <td className="py-1 text-xs">{truncate(d.value_a)}</td>
                  <td className="py-1 text-xs">{truncate(d.value_b)}</td>
                  <td className="py-1 text-center">
                    {d.status === 'different' ? (
                      <span className="text-red-600">✗</span>
                    ) : d.status === 'only_a' ? (
                      <span className="text-orange-500">A独有</span>
                    ) : (
                      <span className="text-orange-500">B独有</span>
                    )}
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
