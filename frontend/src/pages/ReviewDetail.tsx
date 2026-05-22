// @ts-nocheck
import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  fetchReviewResult,
  getStructuredInfo,
  getBilingualAnalysis,
  getScoring,
  adoptIssue,
  rejectIssue,
  downloadPdfReport,
  downloadDocxReport,
} from '../api/client';
import type {
  ReviewResult,
  RiskIssue,
  StructuredResponse,
  BilingualResponse,
  ScoringResponse,
  Entity,
} from '../types';

const SEVERITY_ORDER: Record<string, number> = { high: 0, medium: 1, low: 2 };
const SEVERITY_COLOR: Record<string, string> = {
  high: 'bg-red-100 text-red-800 border-red-300',
  medium: 'bg-orange-100 text-orange-800 border-orange-300',
  low: 'bg-green-100 text-green-800 border-green-300',
};
const SEVERITY_DOT: Record<string, string> = {
  high: 'bg-red-500',
  medium: 'bg-orange-500',
  low: 'bg-green-500',
};
const ENTITY_COLORS: Record<string, string> = {
  DATE: 'bg-blue-100 text-blue-800',
  MONEY: 'bg-green-100 text-green-800',
  LOCATION: 'bg-orange-100 text-orange-800',
  COMPANY: 'bg-purple-100 text-purple-800',
  PERSON: 'bg-red-100 text-red-800',
  CONTRACT_ID: 'bg-gray-100 text-gray-800',
};

// Utility: highlight entities in text
function highlightEntities(text: string, entities: Entity[]): React.ReactNode {
  if (!entities.length) return text;
  
  // Sort entities by position in text (earliest first)
  const sorted = [...entities]
    .map((e) => {
      const idx = text.indexOf(e.text);
      return { ...e, idx };
    })
    .filter((e) => e.idx >= 0)
    .sort((a, b) => a.idx - b.idx);

  if (!sorted.length) return text;

  const parts: React.ReactNode[] = [];
  let cursor = 0;
  for (const entity of sorted) {
    if (entity.idx < cursor) continue; // skip overlaps
    if (entity.idx > cursor) {
      parts.push(text.slice(cursor, entity.idx));
    }
    parts.push(
      <span
        key={`e-${entity.idx}-${entity.text}`}
        className={`px-0.5 rounded-sm cursor-pointer text-xs ${ENTITY_COLORS[entity.type] || 'bg-gray-100'}`}
        title={`${entity.type}: ${entity.text}`}
      >
        {entity.text}
      </span>
    );
    cursor = entity.idx + entity.text.length;
  }
  if (cursor < text.length) parts.push(text.slice(cursor));
  return <>{parts}</>;
}


export default function ReviewDetail() {
  const { fileId } = useParams<{ fileId: string }>();
  const navigate = useNavigate();
  const [review, setReview] = useState<ReviewResult | null>(null);
  const [structured, setStructured] = useState<StructuredResponse | null>(null);
  const [bilingual, setBilingual] = useState<BilingualResponse | null>(null);
  const [scoring, setScoring] = useState<ScoringResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedIssue, setSelectedIssue] = useState<string | null>(null);
  const [showStructured, setShowStructured] = useState(false);
  const [showBilingual, setShowBilingual] = useState(false);
  const [showEntities, setShowEntities] = useState(false);
  const [activeEntity, setActiveEntity] = useState<Entity | null>(null);
  const issueRefs = useRef<Record<string, HTMLDivElement | null>>({});

  const loadData = useCallback(async () => {
    if (!fileId) return;
    setLoading(true);
    try {
      const [r, s, b, sc] = await Promise.all([
        fetchReviewResult(fileId),
        getStructuredInfo(fileId),
        getBilingualAnalysis(fileId),
        getScoring(fileId),
      ]);
      setReview(r);
      setStructured(s);
      setBilingual(b);
      setScoring(sc);
      if (r?.issues?.length) {
        const sorted = [...r.issues].sort(
          (a, b) => (SEVERITY_ORDER[a.severity] ?? 2) - (SEVERITY_ORDER[b.severity] ?? 2)
        );
        setSelectedIssue(sorted[0].id);
      }
    } finally {
      setLoading(false);
    }
  }, [fileId]);

  useEffect(() => { loadData(); }, [loadData]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500 text-lg">加载审查结果中...</div>
      </div>
    );
  }

  if (!review) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <div className="text-gray-500 text-lg">审查结果未就绪，文件正在处理中...</div>
        <button onClick={() => navigate('/')} className="text-blue-600 hover:underline">返回首页</button>
      </div>
    );
  }

  const issues = [...(review.issues || [])].sort(
    (a, b) => (SEVERITY_ORDER[a.severity] ?? 2) - (SEVERITY_ORDER[b.severity] ?? 2)
  );
  const highCount = issues.filter((i) => i.severity === 'high').length;
  const mediumCount = issues.filter((i) => i.severity === 'medium').length;
  const lowCount = issues.filter((i) => i.severity === 'low').length;

  const handleAction = async (issueId: string, action: 'adopt' | 'reject') => {
    if (!fileId) return;
    try {
      if (action === 'adopt') await adoptIssue(fileId, issueId);
      else await rejectIssue(fileId, issueId);
      setReview((prev) =>
        prev
          ? {
              ...prev,
              issues: prev.issues.map((i) =>
                i.id === issueId ? { ...i, status: action === 'adopt' ? 'adopted' : 'rejected' } : i
              ),
            }
          : prev
      );
    } catch (e) {
      alert(e instanceof Error ? e.message : '操作失败');
    }
  };

  const scoreColor = (s: number) => (s >= 80 ? 'text-green-600' : s >= 60 ? 'text-orange-500' : 'text-red-600');
  const riskLabel = (l: string) => (l === 'high' ? '高风险' : l === 'medium' ? '中风险' : '低风险');
  const riskBadge = (l: string) =>
    l === 'high' ? 'bg-red-500 text-white' : l === 'medium' ? 'bg-orange-500 text-white' : 'bg-green-500 text-white';

  // Build entity-highlighted clauses
  const entities = structured?.entities?.entities || review?.entities?.entities || [];
  const clauses = structured?.clauses || [];

  return (
    <div className="max-w-[1600px] mx-auto p-4">
      {/* Header */}
      <div className="mb-6">
        <button onClick={() => navigate('/')} className="text-blue-600 hover:underline mb-2 inline-block">
          &larr; 返回
        </button>
        <h1 className="text-2xl font-bold">{review.filename || '合同审查报告'}</h1>
        <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
          <span>类型: {review.contract_type || '未知'}</span>
          <span>审查时间: {review.review_time?.slice(0, 19) || '-'}</span>
          {review.ocr_used && <span className="bg-purple-100 text-purple-700 px-2 py-0.5 rounded text-xs">OCR</span>}
        </div>
      </div>

      {/* Score Bar */}
      <div className="bg-white rounded-lg shadow p-4 mb-4 flex flex-wrap items-center gap-6">
        <div className="flex items-center gap-3">
          <div className={`text-4xl font-bold ${scoreColor(scoring?.overall_score ?? review.risk_score)}`}>
            {scoring?.overall_score ?? review.risk_score}
          </div>
          <div>
            <div className="text-sm text-gray-500">综合评分</div>
            <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${riskBadge(review.risk_level)}`}>
              {riskLabel(review.risk_level)}
            </span>
          </div>
        </div>
        <div className="flex-1 min-w-[300px]">
          {scoring?.dimensions?.map((d) => (
            <div key={d.name} className="flex items-center gap-2 mb-1">
              <span className="text-xs w-20 text-right text-gray-600 truncate cursor-help" title={`权重: ${(d.weight * 100).toFixed(0)}% — ${d.description || '风险维度评分'}`}>{d.name}</span>
              <div className="flex-1 bg-gray-200 rounded-full h-2">
                <div
                  className={`h-2 rounded-full ${d.score >= 80 ? 'bg-green-500' : d.score >= 60 ? 'bg-orange-400' : 'bg-red-500'}`}
                  style={{ width: `${d.score}%` }}
                />
              </div>
              <span className="text-xs w-8 text-gray-600">{d.score}</span>
              <span className="text-xs text-gray-400 w-10">{(d.weight * 100).toFixed(0)}%</span>
            </div>
          ))}
        </div>
        <div className="text-xs text-gray-400 flex items-center gap-1">
          <span>💡 悬停维度名称查看权重说明</span>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => downloadPdfReport(fileId!, review.filename)}
            className="bg-blue-600 text-white px-3 py-1.5 rounded text-sm hover:bg-blue-700"
          >
            导出 PDF
          </button>
          <button
            onClick={() => downloadDocxReport(fileId!, review.filename)}
            className="bg-green-600 text-white px-3 py-1.5 rounded text-sm hover:bg-green-700"
          >
            导出 DOCX
          </button>
        </div>
      </div>

      {/* Toggle sections */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setShowStructured(!showStructured)}
          className={`px-3 py-1 rounded text-sm ${showStructured ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'}`}
        >
          结构化信息
        </button>
        <button
          onClick={() => setShowEntities(!showEntities)}
          className={`px-3 py-1 rounded text-sm ${showEntities ? 'bg-purple-600 text-white' : 'bg-gray-200 text-gray-700'}`}
        >
          实体识别 ({entities.length})
        </button>
        {bilingual?.is_bilingual && (
          <button
            onClick={() => setShowBilingual(!showBilingual)}
            className={`px-3 py-1 rounded text-sm ${showBilingual ? 'bg-teal-600 text-white' : 'bg-gray-200 text-gray-700'}`}
          >
            双语分析
          </button>
        )}
      </div>

      {/* Collapsible: Structured Info */}
      {showStructured && structured && (
        <div className="bg-white rounded-lg shadow p-4 mb-4">
          <h3 className="font-semibold mb-3">结构化信息</h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-500">签约方:</span>
              <span className="ml-2">{structured.parties?.map((p) => `${p.name || ''}(${p.role || ''})`).join(', ') || '-'}</span>
            </div>
            <div>
              <span className="text-gray-500">合同期限:</span>
              <span className="ml-2">
                {structured.contract_period?.start_date || '?'} ~ {structured.contract_period?.end_date || '?'}
              </span>
            </div>
            <div>
              <span className="text-gray-500">付款条款:</span>
              <span className="ml-2">{(structured.payment_terms || []).join('; ') || '-'}</span>
            </div>
            <div>
              <span className="text-gray-500">违约责任:</span>
              <span className="ml-2">{(structured.breach_liability || []).join('; ') || '-'}</span>
            </div>
          </div>
        </div>
      )}

      {/* Collapsible: Entities */}
      {showEntities && entities.length > 0 && (
        <div className="bg-white rounded-lg shadow p-4 mb-4">
          <h3 className="font-semibold mb-3">识别实体</h3>
          <div className="flex flex-wrap gap-2">
            {entities.map((e, i) => (
              <span
                key={i}
                className={`px-2 py-0.5 rounded text-xs cursor-pointer transition-all ${ENTITY_COLORS[e.type] || 'bg-gray-100'} ${activeEntity === e ? 'ring-2 ring-offset-1 ring-blue-400' : ''}`}
                onClick={() => {
                  setActiveEntity(activeEntity === e ? null : e);
                  scrollToEntity(e, entities);
                }}
              >
                {e.text}
                <span className="ml-1 opacity-60">{e.type}</span>
              </span>
            ))}
          </div>
          {activeEntity && (
            <div className="mt-2 p-2 bg-gray-50 rounded text-sm border-l-3 border-blue-400">
              <div className="font-medium">
                {activeEntity.text} <span className="opacity-60 text-xs">({activeEntity.type})</span>
              </div>
              {activeEntity.context && (
                <div className="mt-1 text-xs text-gray-500 italic">
                  ...{activeEntity.context}...
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Collapsible: Bilingual */}
      {showBilingual && bilingual?.is_bilingual && bilingual.consistency && (
        <div className="bg-white rounded-lg shadow p-4 mb-4">
          <h3 className="font-semibold mb-2">双语一致性分析</h3>
          <div className="text-sm mb-2">
            一致性评分: <strong>{bilingual.consistency_score ?? '-'}</strong>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b">
                <th className="text-left py-1 w-24">条款</th>
                <th className="text-left py-1">中文</th>
                <th className="text-left py-1">英文</th>
                <th className="text-center py-1 w-16">状态</th>
              </tr>
            </thead>
            <tbody>
              {bilingual.consistency.map((c, i) => (
                <tr key={i} className="border-b last:border-0">
                  <td className="py-1">{c.section}</td>
                  <td className="py-1 text-xs">{c.chinese?.slice(0, 60) || '-'}</td>
                  <td className="py-1 text-xs">{c.english?.slice(0, 60) || '-'}</td>
                  <td className="py-1 text-center">
                    {c.consistent ? (
                      <span className="text-green-600">✓</span>
                    ) : (
                      <span className="text-red-600" title={c.difference}>✗</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Three-Column Layout */}
      <div className="flex gap-4" style={{ minHeight: '60vh' }}>
        {/* LEFT: Issue list sidebar */}
        <div className="w-72 shrink-0 bg-white rounded-lg shadow p-3 overflow-y-auto" style={{ maxHeight: '80vh' }}>
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-sm">风险列表</h3>
            <div className="flex gap-1">
              {highCount > 0 && <span className="bg-red-500 text-white text-xs px-1.5 py-0.5 rounded">{highCount}高</span>}
              {mediumCount > 0 && <span className="bg-orange-500 text-white text-xs px-1.5 py-0.5 rounded">{mediumCount}中</span>}
              {lowCount > 0 && <span className="bg-green-500 text-white text-xs px-1.5 py-0.5 rounded">{lowCount}低</span>}
            </div>
          </div>
          <div className="space-y-1">
            {issues.map((issue) => (
              <button
                key={issue.id}
                onClick={() => {
                  setSelectedIssue(issue.id);
                  issueRefs.current[issue.id]?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }}
                className={`w-full text-left p-2 rounded text-sm border transition-colors ${
                  selectedIssue === issue.id ? 'border-blue-400 bg-blue-50' : 'border-transparent hover:bg-gray-50'
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full shrink-0 ${SEVERITY_DOT[issue.severity]}`} />
                  <span className="truncate font-medium">{issue.title || issue.id}</span>
                </div>
                <div className="text-xs text-gray-400 mt-0.5">
                  {issue.clause_reference || ''}
                  {issue.status === 'adopted' && <span className="ml-1 text-green-600">已采纳</span>}
                  {issue.status === 'rejected' && <span className="ml-1 text-red-600">已拒绝</span>}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* CENTER: Contract text / clause display */}
        <div className="flex-1 bg-white rounded-lg shadow p-4 overflow-y-auto" style={{ maxHeight: '80vh' }}>
          <h3 className="font-semibold mb-3">合同条款</h3>
          {clauses.length > 0 ? (
            <div className="space-y-3">
              {clauses.map((clause, idx) => {
                const relatedIssues = issues.filter(
                  (i) => i.clause_reference?.includes(clause.number || '') || i.clause_reference?.includes(clause.title || '')
                );
                const hasHigh = relatedIssues.some((i) => i.severity === 'high');
                const hasMedium = relatedIssues.some((i) => i.severity === 'medium');
                const bgColor = hasHigh
                  ? 'bg-red-50 border-l-4 border-red-400'
                  : hasMedium
                  ? 'bg-orange-50 border-l-4 border-orange-400'
                  : '';
                return (
                  <div
                    key={idx}
                    ref={(el) => {
                      if (relatedIssues[0]) issueRefs.current[relatedIssues[0].id] = el;
                    }}
                    className={`p-3 rounded ${bgColor}`}
                  >
                    {clause.number && <span className="text-xs text-gray-400 mr-2">#{clause.number}</span>}
                    {clause.title && <strong className="text-sm">{clause.title}</strong>}
                    <p className="text-sm text-gray-700 mt-1">{showEntities ? highlightEntities(clause.content, entities, (e) => { setActiveEntity(e); scrollToEntity(e, entities); }) : clause.content}</p>
                    {relatedIssues.length > 0 && (
                      <div className="mt-1 flex gap-1">
                        {relatedIssues.map((ri) => (
                          <span key={ri.id} className={`text-xs px-1.5 py-0.5 rounded ${SEVERITY_COLOR[ri.severity]}`}>
                            {ri.severity === 'high' ? '高' : ri.severity === 'medium' ? '中' : '低'}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-gray-500 text-sm">
              <p>{review.summary || '暂无条款详情'}</p>
            </div>
          )}
        </div>

        {/* RIGHT: Issue detail card */}
        <div className="w-80 shrink-0 bg-white rounded-lg shadow p-3 overflow-y-auto" style={{ maxHeight: '80vh' }}>
          <h3 className="font-semibold text-sm mb-3">问题详情</h3>
          {(() => {
            const issue = issues.find((i) => i.id === selectedIssue);
            if (!issue) return <div className="text-gray-400 text-sm">选择左侧问题查看详情</div>;
            return (
              <div className="space-y-3">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-xs px-2 py-0.5 rounded font-medium ${SEVERITY_COLOR[issue.severity]}`}>
                      {issue.severity === 'high' ? '高风险' : issue.severity === 'medium' ? '中风险' : '低风险'}
                    </span>
                    {issue.clause_reference && (
                      <span className="text-xs text-gray-400">{issue.clause_reference}</span>
                    )}
                  </div>
                  <h4 className="font-semibold">{issue.title || issue.id}</h4>
                </div>

                {/* Risk Description */}
                <div className="bg-red-50 border border-red-200 rounded p-2">
                  <div className="text-xs text-red-600 font-medium mb-1">⚠ 风险描述</div>
                  <div className="text-sm">{issue.risk_description || issue.description || '-'}</div>
                </div>

                {/* Legal Basis */}
                <div className="bg-blue-50 border border-blue-200 rounded p-2">
                  <div className="text-xs text-blue-600 font-medium mb-1">⚖ 法律依据</div>
                  <div className="text-sm">{issue.legal_basis || '-'}</div>
                </div>

                {/* Modification Example */}
                <div className="bg-green-50 border border-green-200 rounded p-2">
                  <div className="text-xs text-green-600 font-medium mb-1">✏ 修改建议</div>
                  {issue.modification_example ? (
                    <div className="space-y-1">
                      <div>
                        <span className="text-xs text-gray-400">原文:</span>
                        <div className="text-sm text-red-600 line-through">{issue.modification_example.original}</div>
                      </div>
                      <div>
                        <span className="text-xs text-gray-400">建议:</span>
                        <div className="text-sm text-green-700">{issue.modification_example.suggested}</div>
                      </div>
                    </div>
                  ) : issue.suggestion ? (
                    <div className="text-sm">{issue.suggestion}</div>
                  ) : (
                    <div className="text-sm text-gray-400">暂无修改建议</div>
                  )}
                </div>

                {/* Action buttons */}
                <div className="flex gap-2 pt-2">
                  {issue.status === 'adopted' ? (
                    <div className="flex-1 text-center py-2 bg-green-100 text-green-700 rounded text-sm font-medium">
                      ✓ 已采纳
                    </div>
                  ) : issue.status === 'rejected' ? (
                    <div className="flex-1 text-center py-2 bg-red-100 text-red-700 rounded text-sm font-medium">
                      ✗ 已拒绝
                    </div>
                  ) : (
                    <>
                      <button
                        onClick={() => handleAction(issue.id, 'adopt')}
                        className="flex-1 bg-green-600 text-white py-1.5 rounded text-sm hover:bg-green-700"
                      >
                        采纳
                      </button>
                      <button
                        onClick={() => handleAction(issue.id, 'reject')}
                        className="flex-1 bg-gray-400 text-white py-1.5 rounded text-sm hover:bg-gray-500"
                      >
                        拒绝
                      </button>
                    </>
                  )}
                </div>
              </div>
            );
          })()}
        </div>
      </div>
    </div>
  );
}
