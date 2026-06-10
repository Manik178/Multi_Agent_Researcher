// ── Agent node names matching the LangGraph pipeline ─────────
export type AgentNode =
  | "planner"
  | "researcher"
  | "critic"
  | "writer"
  | "citation_verifier"
  | "followup_suggester";

export type AgentStatus = "running" | "done" | "retrying" | "waiting";

// ── Agent timeline entry for the UI ──────────────────────────
export interface AgentTimelineEntry {
  id: string;
  node: AgentNode;
  status: AgentStatus;
  message: string;
  timestamp: Date;
  subQuestion?: string;
}

// ── Verified claim from the citation verifier node ───────────
export interface VerifiedClaim {
  claim: string;
  verified: boolean;
  source_index: number;
}

// ── Dashboard metrics ────────────────────────────────────────
export interface Dashboard {
  critic_confidence: number;
  citation_score: number;
  verified_claims: number;
  total_claims: number;
  cache_hits: number;
  qdrant_hits: number;
  web_searches: number;
  iterations_needed: number;
  retrieval_efficiency: number;
}

// ── Full POST /api/v1/research response ──────────────────────
export interface ResearchResponse {
  thread_id: string;
  question: string;
  sub_questions: string[];
  iterations: number;
  critic_verdict: string;
  final_answer: string;
  verified_claims: VerifiedClaim[];
  follow_up_questions: string[];
  dashboard: Dashboard;
}

// ── GET /api/v1/sessions/{thread_id} response ────────────────
// Note: Backend does NOT return sub_questions, iterations, or critic_verdict
export interface SessionResponse {
  thread_id: string;
  question: string;
  final_answer: string;
  follow_up_questions: string[];
  verified_claims: VerifiedClaim[];
  dashboard: Dashboard;
}

// ── SSE event from /api/v1/research/stream ───────────────────
export interface SSENodeUpdate {
  type: "node_update";
  node: AgentNode;
  status: string;
  data: Record<string, unknown>;
  thread_id: string;
}

export interface SSEDoneEvent {
  type: "done";
  thread_id: string;
}

export type SSEEvent = SSENodeUpdate | SSEDoneEvent;

// ── Document management ──────────────────────────────────────
export interface DocumentUploadResponse {
  filename: string;
  chunks_stored: number;
  status: string;
}

export interface DocumentListResponse {
  documents: string[];
}

export interface DocumentDeleteResponse {
  filename: string;
  status: string;
}

// ── Session history (stored in localStorage) ─────────────────
export interface StoredSession {
  threadId: string;
  question: string;
  timestamp: number;
}
