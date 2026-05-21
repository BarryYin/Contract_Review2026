import type { FileInfo, ReviewResult } from '../types';

const API_BASE = '/api';

// ── Mock review data (kept until compliance-engine is built) ──────────

const mockReviewResults: Record<string, ReviewResult> = {
  f001: {
    id: 'r001',
    file_id: 'f001',
    risk_score: 78,
    risk_level: 'high',
    contract_type: '采购合同',
    summary:
      '该采购框架协议存在多项高风险条款，包括付款条件不明确、违约金比例过高、知识产权归属模糊等问题。建议在签署前进行重大修改。',
    issues: [
      {
        id: 'i001',
        clause: '第五条 付款条款',
        risk_type: '付款风险',
        severity: 'high',
        description:
          '付款条件仅约定"验收合格后30日内付款"，未明确验收标准及流程，可能导致付款争议。',
        suggestion:
          '建议增加明确的验收标准和流程，包括验收周期、验收负责人、验收不合格的处理方式等具体条款。',
      },
      {
        id: 'i002',
        clause: '第八条 违约责任',
        risk_type: '违约风险',
        severity: 'high',
        description:
          '违约金设定为合同总金额的30%，远超法律保护范围（通常不超过实际损失的30%），存在被法院调低的风险。',
        suggestion:
          '建议将违约金调整为合理比例，如合同总金额的10%-15%，或明确约定以实际损失为基准计算。',
      },
      {
        id: 'i003',
        clause: '第十条 知识产权',
        risk_type: '知识产权风险',
        severity: 'medium',
        description:
          '定制开发部分的知识产权归属未做明确约定，仅表述"双方协商解决"，存在后续争议隐患。',
        suggestion:
          '应明确约定定制开发成果的知识产权归属，包括著作权、专利权等具体权利的分配方式。',
      },
      {
        id: 'i004',
        clause: '第三条 交付条款',
        risk_type: '交付风险',
        severity: 'medium',
        description:
          '交付时间条款缺少延期交付的惩罚机制和不可抗力条款的细化规定。',
        suggestion:
          '建议增加延期交付的阶梯式违约金条款，并细化不可抗力条款的适用范围和通知义务。',
      },
      {
        id: 'i005',
        clause: '第十二条 争议解决',
        risk_type: '管辖风险',
        severity: 'low',
        description:
          '争议解决条款约定由供方所在地法院管辖，可能对我方不利。',
        suggestion:
          '建议修改为由合同签订地或我方所在地法院管辖，或选择仲裁方式解决争议。',
      },
    ],
  },
  f002: {
    id: 'r002',
    file_id: 'f002',
    risk_score: 52,
    risk_level: 'medium',
    contract_type: '服务合同',
    summary:
      '该IT服务外包合同存在中等风险，主要涉及服务水平协议（SLA）定义不清晰、数据安全保护条款不完善等问题。',
    issues: [
      {
        id: 'i006',
        clause: '第六条 服务水平协议',
        risk_type: 'SLA风险',
        severity: 'medium',
        description:
          'SLA仅约定99.5%的可用性，未明确计算方式、排除情形和违约赔偿机制。',
        suggestion:
          '建议细化SLA指标，明确可用性计算公式、维护窗口排除规则，并建立阶梯式服务信用赔偿机制。',
      },
      {
        id: 'i007',
        clause: '第九条 数据安全',
        risk_type: '数据安全风险',
        severity: 'high',
        description:
          '数据安全条款过于笼统，未约定数据泄露的通报时限、责任认定和赔偿标准。',
        suggestion:
          '建议参照《个人信息保护法》和《数据安全法》，增加数据泄露72小时通报机制、数据本地化存储要求及违约赔偿标准。',
      },
      {
        id: 'i008',
        clause: '第十一条 合同终止',
        risk_type: '终止风险',
        severity: 'low',
        description:
          '合同终止后数据迁移条款不明确，可能影响业务连续性。',
        suggestion:
          '建议增加合同终止后的数据迁移协助期（如90天），明确数据格式和迁移费用的承担方。',
      },
    ],
  },
  f003: {
    id: 'r003',
    file_id: 'f003',
    risk_score: 25,
    risk_level: 'low',
    contract_type: '保密协议',
    summary:
      '该保密协议整体风险较低，条款较为完善，仅有少量条款可进一步优化。',
    issues: [
      {
        id: 'i009',
        clause: '第四条 保密期限',
        risk_type: '期限风险',
        severity: 'low',
        description:
          '保密期限约定为"合作期间及合作结束后2年"，对于核心技术秘密，2年保护期可能不足。',
        suggestion:
          '建议对核心技术秘密和商业秘密设定更长的保密期限（如5年或持续有效），对一般信息维持2年。',
      },
    ],
  },
};

// ── File operations (real backend) ────────────────────────────────────

export async function fetchFiles(): Promise<FileInfo[]> {
  const res = await fetch(`${API_BASE}/files`);
  if (!res.ok) throw new Error(`获取文件列表失败 (${res.status})`);
  const data = await res.json();
  return data.files ?? [];
}

export async function fetchReviewResult(
  fileId: string
): Promise<ReviewResult | null> {
  // Check mock data first (temporary until compliance-engine is built)
  if (mockReviewResults[fileId]) {
    return mockReviewResults[fileId];
  }
  return null;
}

export async function uploadFile(
  file: File,
  onProgress: (progress: number) => void
): Promise<FileInfo> {
  const formData = new FormData();
  formData.append('file', file);

  // xhr-based upload with progress tracking
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_BASE}/files/upload`);

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        const data = JSON.parse(xhr.responseText);
        resolve({
          id: data.id,
          filename: data.filename,
          size: data.size,
          upload_time: new Date().toISOString().replace('T', ' ').slice(0, 19),
          status: 'processing',
          contract_type: '',
          review_progress: 0,
        });
      } else {
        reject(new Error(`上传失败 (${xhr.status})`));
      }
    };

    xhr.onerror = () => reject(new Error('上传失败'));
    xhr.send(formData);
  });
}

export async function deleteFile(fileId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/files/${fileId}`, {
    method: 'DELETE',
  });
  if (!res.ok && res.status !== 404) {
    throw new Error(`删除失败 (${res.status})`);
  }
}

export function getDownloadUrl(fileId: string): string {
  return `${API_BASE}/files/${fileId}/download`;
}
