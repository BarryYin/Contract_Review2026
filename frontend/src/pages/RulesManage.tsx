import { useState, useEffect } from 'react';
const API_BASE = '/api';

interface Rule {
  _index: number;
  name: string;
  description: string;
  severity: 'high' | 'medium' | 'low';
  contract_types: string[];
  legal_basis: string;
  check_type: string;
  enabled?: boolean;
}

const sevColor = (s: string) =>
  s === 'high' ? 'bg-red-100 text-red-700' : s === 'medium' ? 'bg-yellow-100 text-yellow-700' : 'bg-green-100 text-green-700';
const sevLabel = (s: string) => s === 'high' ? '高' : s === 'medium' ? '中' : '低';

export default function RulesManage() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<Partial<Rule>>({});
  const [showAdd, setShowAdd] = useState(false);
  const [addForm, setAddForm] = useState({ name: '', description: '', severity: 'medium' as const, contract_types: ['all'], legal_basis: '', check_type: 'both' });

  useEffect(() => { fetchRules(); }, []);

  const fetchRules = async () => {
    setLoading(true);
    const r = await fetch(`${API_BASE}/rules`);
    const d = await r.json();
    setRules(d.rules || []);
    setLoading(false);
  };

  const handleSave = async (idx: number) => {
    await fetch(`${API_BASE}/rules/${idx}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(editForm),
    });
    setEditing(null);
    fetchRules();
  };

  const handleDelete = async (idx: number) => {
    if (!confirm('确定删除此规则？')) return;
    await fetch(`${API_BASE}/rules/${idx}`, { method: 'DELETE' });
    fetchRules();
  };

  const handleAdd = async () => {
    await fetch(`${API_BASE}/rules`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(addForm),
    });
    setShowAdd(false);
    setAddForm({ name: '', description: '', severity: 'medium', contract_types: ['all'], legal_basis: '', check_type: 'both' });
    fetchRules();
  };

  if (loading) return <div className="text-center py-8 text-gray-500">加载规则中...</div>;

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold">合规规则管理</h2>
          <p className="text-sm text-gray-500 mt-1">管理 YAML 规则库，无需修改代码即可自定义合规模板</p>
        </div>
        <button
          onClick={() => setShowAdd(true)}
          className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-indigo-700"
        >
          + 新增规则
        </button>
      </div>

      {/* 新增规则表单 */}
      {showAdd && (
        <div className="bg-white border rounded-xl p-6 mb-6 shadow-sm">
          <h3 className="font-semibold mb-4">新增规则</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm text-gray-600">规则名称</label>
              <input className="w-full border rounded-lg px-3 py-2 mt-1" value={addForm.name}
                onChange={e => setAddForm({ ...addForm, name: e.target.value })} />
            </div>
            <div>
              <label className="text-sm text-gray-600">风险等级</label>
              <select className="w-full border rounded-lg px-3 py-2 mt-1" value={addForm.severity}
                onChange={e => setAddForm({ ...addForm, severity: e.target.value as any })}>
                <option value="high">高</option>
                <option value="medium">中</option>
                <option value="low">低</option>
              </select>
            </div>
            <div className="col-span-2">
              <label className="text-sm text-gray-600">描述</label>
              <textarea className="w-full border rounded-lg px-3 py-2 mt-1" rows={2} value={addForm.description}
                onChange={e => setAddForm({ ...addForm, description: e.target.value })} />
            </div>
            <div className="col-span-2">
              <label className="text-sm text-gray-600">法律依据</label>
              <input className="w-full border rounded-lg px-3 py-2 mt-1" value={addForm.legal_basis}
                onChange={e => setAddForm({ ...addForm, legal_basis: e.target.value })} />
            </div>
          </div>
          <div className="flex gap-3 mt-4">
            <button onClick={handleAdd} className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm">保存</button>
            <button onClick={() => setShowAdd(false)} className="border px-4 py-2 rounded-lg text-sm">取消</button>
          </div>
        </div>
      )}

      {/* 规则列表 */}
      <div className="space-y-4">
        {rules.map((rule, idx) => (
          <div key={idx} className="bg-white border rounded-xl p-5 shadow-sm">
            {editing === idx ? (
              <div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-gray-500">名称</label>
                    <input className="w-full border rounded px-2 py-1" value={editForm.name || ''}
                      onChange={e => setEditForm({ ...editForm, name: e.target.value })} />
                  </div>
                  <div>
                    <label className="text-xs text-gray-500">等级</label>
                    <select className="w-full border rounded px-2 py-1" value={editForm.severity || 'medium'}
                      onChange={e => setEditForm({ ...editForm, severity: e.target.value as any })}>
                      <option value="high">高</option><option value="medium">中</option><option value="low">低</option>
                    </select>
                  </div>
                  <div className="col-span-2">
                    <label className="text-xs text-gray-500">法律依据</label>
                    <input className="w-full border rounded px-2 py-1" value={editForm.legal_basis || ''}
                      onChange={e => setEditForm({ ...editForm, legal_basis: e.target.value })} />
                  </div>
                  <div className="col-span-2">
                    <label className="text-xs text-gray-500">描述</label>
                    <textarea className="w-full border rounded px-2 py-1" rows={3} value={editForm.description || ''}
                      onChange={e => setEditForm({ ...editForm, description: e.target.value })} />
                  </div>
                </div>
                <div className="flex gap-2 mt-3">
                  <button onClick={() => handleSave(idx)} className="bg-indigo-600 text-white px-3 py-1 rounded text-sm">保存</button>
                  <button onClick={() => setEditing(null)} className="border px-3 py-1 rounded text-sm">取消</button>
                </div>
              </div>
            ) : (
              <div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${sevColor(rule.severity)}`}>
                      {sevLabel(rule.severity)}
                    </span>
                    <h4 className="font-medium">{rule.name}</h4>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => { setEditing(idx); setEditForm(rule); }}
                      className="text-indigo-600 text-sm hover:underline">编辑</button>
                    <button onClick={() => handleDelete(idx)}
                      className="text-red-500 text-sm hover:underline">删除</button>
                  </div>
                </div>
                <p className="text-sm text-gray-600 mt-2">{rule.description}</p>
                <div className="flex gap-4 mt-3 text-xs text-gray-500">
                  <span>适用: {rule.contract_types.join(', ')}</span>
                  <span>法律依据: {rule.legal_basis ? rule.legal_basis.substring(0, 60) + '...' : '无'}</span>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="mt-6 text-center text-sm text-gray-400">
        共 {rules.length} 条规则 | 规则存储于 backend/app/core/rules.yaml
      </div>
    </div>
  );
}
