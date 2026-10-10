export interface PolicyVersion {
  id: string;
  version: string;
  effective_from: string;
  effective_until: string | null;
  status: "pending" | "processing" | "ready" | "failed";
  chunk_count: number;
  created_at: string;
}

export interface Policy {
  id: string;
  name: string;
  insurer: string;
  created_at: string;
  versions: PolicyVersion[];
}

export interface EvidenceItem {
  chunk_id: string;
  content: string;
  page: number | null;
  section: string | null;
  policy_version: string;
  relevance_score: number;
}

export interface VerifiedClaim {
  claim: string;
  status: "SUPPORTED" | "PARTIALLY_SUPPORTED" | "UNSUPPORTED";
  support_score: number;
  page?: number | null;
  warnings?: string[];
}

export interface ChatQueryResponse {
  answer: string;
  policy_version: string | null;
  evidence: EvidenceItem[];
  confidence: number;
  warnings: string[];
  crag_regime?: "correct" | "ambiguous" | "incorrect";
  retrieval_strategy?: string;
  sub_queries?: string[];
  factual_precision?: number;
  reasoning_paths?: string[];
  calibrated_confidence?: number;
  should_abstain?: boolean;
  coverage_guarantee?: number;
  entropy_level?: "low" | "medium" | "high";
  speculative_drafts_count?: number;
  community_summaries?: string[];
  verified_claims?: VerifiedClaim[];
  merkle_root?: string;
  certificate_signature?: string;
  conformal_interval?: [number, number];
  topological_dispersion?: number;
  lattice_arbitration_status?: string;
}

export interface ClauseDiff {
  type: "SAME" | "UPDATED" | "CONTRADICTORY" | "REMOVED" | "ADDED";
  clause_a: string | null;
  clause_b: string | null;
  explanation: string;
  confidence: number;
}

export interface CompareResponse {
  added: ClauseDiff[];
  removed: ClauseDiff[];
  modified: ClauseDiff[];
  contradictions: ClauseDiff[];
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  data: Record<string, unknown>;
}

export interface GraphEdge {
  source: string;
  target: string;
  relation: string;
}

export interface GraphCommunity {
  community_id: number;
  theme?: string;
  summary?: string;
  key_entities?: string[];
  node_count?: number;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  communities?: GraphCommunity[];
}

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in_minutes: number;
  user: User;
}

export interface HealthStatus {
  status: string;
  env: string;
}

export interface OkfConcept {
  id: string;
  title: string;
  category: string;
  status: string;
  version: string;
  tags?: string[];
  rules_count?: number;
  relations_count?: number;
  rules?: string[];
  relations?: Record<string, any[]>;
  markdown_body?: string;
}

export interface FamilyMember {
  name: string;
  relation: string;
  age: number;
  gender: string;
}

export interface PatientProfile {
  id: string;
  full_name: string;
  age?: number;
  gender?: string;
  date_of_birth?: string;
  policy_start_date?: string;
  sum_insured?: number;
  plan_type?: string;
  is_primary_insured?: boolean;
  family_members?: FamilyMember[];
  pre_existing_diseases?: string[];
  current_conditions?: string[];
  current_medications?: string[];
  is_smoker?: boolean;
  is_diabetic?: boolean;
  is_hypertensive?: boolean;
  notes?: string;
  created_at?: string;
}
