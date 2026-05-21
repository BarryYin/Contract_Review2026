import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  ShieldAlert,
  ShieldCheck,
  Shield,
  AlertTriangle,
  AlertOctagon,
  Info,
  CheckCircle2,
  ChevronRight,
} from 'lucide-react';
import { fetchReviewResult } from '../api/client';
import type { ReviewResult } from '../types';

function RiskGauge({ score }: { score: number }) {
  const radius = 70;
  const stroke = 10;
  const normalizedRadius = radius - stroke / 2;
  const circumference = normalizedRadius * 2 * Math.PI;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  let color = '#15be53';
  let label = '低风险';
  if (score >= 70) {
    color = '#ef4444';
    label = '高风险';
  } else if (score >= 40) {
    color = '#f59e0b';
    label = '中风险';
  }

  return (
    <div className="flex flex-col items-center">
      <svg height={radius * 2} width={radius * 2} className="transform -rotate-90">
        <circle
          stroke="#e5edf5"
          fill="transparent"
          strokeWidth={stroke}
          r={normalizedRadius}
          cx={radius}
          cy={radius}
        />
        <circle
          stroke={color}
          fill="transparent"
          strokeWidth={stroke}
          strokeDasharray={`${circumference} ${circumference}`}
          style={{ strokeDashoffset, transition: 'stroke-dashoffset 1s ease' }}
          strokeLinecap="round"
          r={normalizedRadius}
          cx={radius}
          cy={radius}
        />
      </svg>
      <div className="absolute flex flex-col items-center justify-center" style={{ marginTop: radius - 28 }}>
        <span className="text-3xl font-semibold text-[#061b31] tracking-tight">{score}</span>
        <span className="text-xs text-[#64748d]">风险评分</span>
      </div>
      <span
        className="mt-3 inline-flex items-center px-3 py-1 rounded-md text-sm font-medium"
        style={{
          color,
          backgroundColor: score >= 70 ? 'rgba(239,68,68,0.1)' : score >= 40 ? 'rgba(245,158,11,0.1)' : 'rgba(21,190,83,0.1)',
        }}
      >
        {label}
      </span>
    </div>
  );
}

function SeverityBadge({ severity }: { severity: 'low' | 'medium' | 'high' }) {
  const config = {
    low: { label: '低', color: '#15be53', bg: 'rgba(21,190,83,0.1)', Icon: Info },
    medium: { label: '中', color: '#f59e0b', bg: 'rgba(245,158,11,0.1)', Icon: AlertTriangle },
    high: { label: '高', color: '#ef4444', bg: 'rgba(239,68,68,0.1)', Icon: AlertOctagon },
  };
  const c = config[severity];
  const IconComponent = c.Icon;
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium"
      style={{ color: c.color, backgroundColor: c.bg }}
    >
      <IconComponent className="w-3 h-3" />
      {c.label}
    </span>
  );
}

export default function ReviewDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [result, setResult] = useState<ReviewResult | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    fetchReviewResult(id).then((data) => {
      setResult(data);
      setLoading(false);
    });
  }, [id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="w-8 h-8 border-2 border-[#533afd] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!result) {
    return (
      <div className="max-w-6xl mx-auto px-6 py-16 text-center">
        <div className="w-16 h-16 rounded-full bg-gray-50 flex items-center justify-center mx-auto mb-4">
          <ShieldAlert className="w-8 h-8 text-[#64748d]" />
        </div>
        <p className="text-[#061b31] font-medium text-lg">审查结果尚未就绪</p>
        <p className="text-sm text-[#64748d] mt-2">该合同正在审查中，请稍后再试</p>
        <button
          onClick={() => navigate('/')}
          className="mt-6 inline-flex items-center gap-2 text-sm font-medium text-[#533afd] hover:text-[#4434d4] transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          返回首页
        </button>
      </div>
    );
  }

  const riskIcon =
    result.risk_level === 'high'
      ? ShieldAlert
      : result.risk_level === 'medium'
        ? Shield
        : ShieldCheck;
  const RiskIcon = riskIcon;

  return (
    <div className="max-w-6xl mx-auto px-6 py-10">
      {/* Back nav */}
      <button
        onClick={() => navigate('/')}
        className="flex items-center gap-1.5 text-sm text-[#64748d] hover:text-[#061b31] mb-6 transition-colors duration-150"
      >
        <ArrowLeft className="w-4 h-4" />
        返回合同列表
      </button>

      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <div className="w-10 h-10 rounded-lg bg-[rgba(83,58,253,0.08)] flex items-center justify-center">
          <RiskIcon className="w-5 h-5 text-[#533afd]" />
        </div>
        <div>
          <h1 className="text-2xl font-semibold text-[#061b31] tracking-tight">
            合同审查报告
          </h1>
          <p className="text-sm text-[#64748d] mt-0.5">
            合同类型：{result.contract_type}
          </p>
        </div>
      </div>

      {/* Top cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Risk Score */}
        <div
          className="bg-white rounded-lg border border-[#e5edf5] p-6 flex flex-col items-center justify-center relative"
          style={{
            boxShadow:
              'rgba(50,50,93,0.08) 0px 2px 8px -2px, rgba(0,0,0,0.05) 0px 4px 12px -4px',
          }}
        >
          <RiskGauge score={result.risk_score} />
        </div>

        {/* Summary */}
        <div
          className="lg:col-span-2 bg-white rounded-lg border border-[#e5edf5] p-6"
          style={{
            boxShadow:
              'rgba(50,50,93,0.08) 0px 2px 8px -2px, rgba(0,0,0,0.05) 0px 4px 12px -4px',
          }}
        >
          <h2 className="text-base font-semibold text-[#061b31] mb-3">审查摘要</h2>
          <p className="text-sm text-[#64748d] leading-relaxed">
            {result.summary}
          </p>
          <div className="flex items-center gap-4 mt-4 pt-4 border-t border-[#e5edf5]">
            <div className="flex items-center gap-2">
              <AlertOctagon className="w-4 h-4 text-[#ef4444]" />
              <span className="text-sm text-[#273951]">
                高风险：{result.issues.filter((i) => i.severity === 'high').length} 项
              </span>
            </div>
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-[#f59e0b]" />
              <span className="text-sm text-[#273951]">
                中风险：{result.issues.filter((i) => i.severity === 'medium').length} 项
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Info className="w-4 h-4 text-[#15be53]" />
              <span className="text-sm text-[#273951]">
                低风险：{result.issues.filter((i) => i.severity === 'low').length} 项
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Issues list */}
      <div>
        <h2 className="text-lg font-semibold text-[#061b31] mb-4">
          风险条款详情
        </h2>
        <div className="space-y-4">
          {result.issues.map((issue) => (
            <div
              key={issue.id}
              className="bg-white rounded-lg border border-[#e5edf5] p-5 transition-shadow duration-150 hover:shadow-md"
              style={{
                boxShadow:
                  'rgba(50,50,93,0.06) 0px 1px 4px -1px, rgba(0,0,0,0.03) 0px 2px 6px -2px',
              }}
            >
              <div className="flex items-start justify-between gap-4 mb-3">
                <div className="flex items-center gap-2">
                  <ChevronRight className="w-4 h-4 text-[#533afd] shrink-0" />
                  <h3 className="text-sm font-semibold text-[#061b31]">
                    {issue.clause}
                  </h3>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-xs text-[#64748d] bg-gray-50 px-2 py-0.5 rounded">
                    {issue.risk_type}
                  </span>
                  <SeverityBadge severity={issue.severity} />
                </div>
              </div>

              <div className="pl-6 space-y-3">
                <div>
                  <p className="text-xs font-medium text-[#273951] mb-1">问题描述</p>
                  <p className="text-sm text-[#64748d] leading-relaxed">
                    {issue.description}
                  </p>
                </div>
                <div className="flex items-start gap-2 p-3 rounded-md bg-[rgba(83,58,253,0.04)] border border-[rgba(83,58,253,0.1)]">
                  <CheckCircle2 className="w-4 h-4 text-[#533afd] shrink-0 mt-0.5" />
                  <div>
                    <p className="text-xs font-medium text-[#533afd] mb-0.5">修改建议</p>
                    <p className="text-sm text-[#273951] leading-relaxed">
                      {issue.suggestion}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
