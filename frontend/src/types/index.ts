/* ── File & Upload ──────────────────────────────────── */

export interface FileInfo {
  id: string;
  filename: string;
  size: number;
  upload_time: string;
  status: 'uploading' | 'processing' | 'completed' | 'error';
  risk_level?: 'low' | 'medium' | 'high';
  contract_type?: string;
  review_progress?: number;
}

export interface UploadProgress {
  file_id: string;
  filename: string;
  progress: number;
  status: 'uploading' | 'processing' | 'completed' | 'error';
}

/* ── Risk Issue (updated to match backend RiskIssue model) ── */

export interface ModificationExample {
  original: string;
  suggested: string;
}

export interface RiskIssue {
  id: string;
  title?: string;
  clause_reference?: string;
  severity: 'low' | 'medium' | 'high';
  risk_description?: string;
  legal_basis?: string;
  modification_example?: ModificationExample | null;
  /** Legacy fields (backward compat) */
  clause?: string;
  risk_type?: string;
  description?: string;
  suggestion?: string;
  status?: 'pending' | 'adopted' | 'rejected';
}

/* ── Review Result ─────────────────────────────────── */

export interface ReviewResult {
  id: string;
  file_id: string;
  risk_score: number;
  risk_level: 'low' | 'medium' | 'high';
  contract_type: string;
  issues: RiskIssue[];
  summary: string;
  filename?: string;
  upload_time?: string;
  review_time?: string;
  ocr_used?: boolean;
  rule_hits?: RuleHit[];
  structured_info?: StructuredInfo;
  entities?: EntityResult;
  bilingual_analysis?: BilingualAnalysis | null;
  scoring_dimensions?: ScoringDimension[];
  scoring_explanation?: string;
  file_hash?: string;
  total_clauses?: number;
  llm_risk_score?: number;
}

/* ── Rule Engine ───────────────────────────────────── */

export interface RuleHit {
  rule_name: string;
  matched: boolean;
  severity: 'low' | 'medium' | 'high';
  reason?: string;
}

/* ── Structured Info ───────────────────────────────── */

export interface StructuredInfo {
  contract_type?: string;
  parties?: Party[];
  contract_period?: ContractPeriod;
  payment_terms?: string[];
  breach_liability?: string[];
  dispute_resolution?: string[];
  confidentiality?: string[];
  intellectual_property?: string[];
  termination?: string[];
  clauses?: ClauseInfo[];
}

export interface Party {
  name?: string;
  role?: string;
}

export interface ContractPeriod {
  start_date?: string;
  end_date?: string;
  duration?: string;
}

export interface ClauseInfo {
  number?: string;
  title?: string;
  content?: string;
}

/* ── Structured API response (GET /structured) ─────── */

export interface StructuredResponse {
  file_id: string;
  contract_type: string;
  parties: Party[];
  contract_period: ContractPeriod;
  payment_terms: string[];
  breach_liability: string[];
  dispute_resolution: string[];
  confidentiality: string[];
  intellectual_property: string[];
  termination: string[];
  entities: EntityResult;
}

/* ── NER Entities ──────────────────────────────────── */

export interface Entity {
  text?: string;           // frontend field
  value?: string;          // backend NER field (normalised to text by frontend)
  type: string;
  context?: string;
  position_hint?: string;  // backend NER field
  color?: string;          // backend NER field
  start?: number;
  end?: number;
}

export interface EntityResult {
  entities: Entity[];
  total: number;
  type_counts: Record<string, number>;
}

/* ── Bilingual Analysis ────────────────────────────── */

export interface BilingualConsistency {
  section: string;
  chinese: string;
  english: string;
  consistent: boolean;
  difference?: string;
}

export interface BilingualAnalysis {
  chinese_section?: string;
  english_section?: string;
  consistency?: BilingualConsistency[];
  consistency_score?: number;
}

export interface BilingualResponse {
  file_id: string;
  is_bilingual: boolean;
  message?: string;
  chinese_section?: string | null;
  english_section?: string | null;
  consistency: BilingualConsistency[];
  consistency_score: number | null;
}

/* ── Scoring Dimensions ────────────────────────────── */

export interface ScoringDimension {
  name: string;
  score: number;
  weight: number;
  issues_count: number;
}

export interface WeightExplanation {
  dimension: string;
  weight: number;
  weight_percentage: string;
  description: string;
}

export interface ScoringResponse {
  file_id: string;
  overall_score: number;
  risk_level: 'low' | 'medium' | 'high';
  scoring_explanation: string;
  dimensions: ScoringDimension[];
  weight_explanation: WeightExplanation[];
  llm_risk_score: number;
}

/* ── Issue Action Response ─────────────────────────── */

export interface IssueActionResponse {
  issue_id: string;
  status: 'adopted' | 'rejected';
  message: string;
}
