export interface MetricsSummary {
  llm: { cached_llms: number; circuit_breakers: Record<string, { state: string; failure_count: number }> };
  multi_agent: { active_agents: number; workspace_tasks: number; workspace_artifacts: number };
  poison_pills: Record<string, unknown>;
}

export interface QuarantinedMessage {
  message_id: string; queue: string; reason: string; failure_count: number; quarantined_at: string;
}

export interface QuarantinedMessagesResponse {
  total_quarantined: number; messages: QuarantinedMessage[];
}

export interface GraphQuarantineItem { node_id: number; reason?: string; type?: string; from_name?: string; to_name?: string; confidence?: number; source_snippet?: string }
export type GraphQuarantineListResponse = GraphQuarantineItem[]

export interface AuditEvent { id: number; user_id?: number; endpoint?: string; action?: string; tool?: string; status?: string; latency_ms?: number; trace_id?: string; created_at?: number }
export interface AuditEventsResponse { total: number; events: AuditEvent[] }
export interface ReviewerMetricsResponse { user_id: number; decisions_total: number; approvals: number; rejections: number; synonyms: number; approval_rate: number; rejection_rate: number; avg_latency_ms: number }
export interface PeriodReportResponse { period: string; buckets: { bucket: string; total: number; promote: number; reject: number; synonym: number }[] }
export interface ConsentItem { scope: string; granted: boolean; expires_at?: string | null }
export interface ConsentsListResponse { user_id: number; consents: ConsentItem[] }
export interface PendingAction {
  source?: 'langgraph' | 'sql' | string;
  thread_id?: string;
  action_id?: number;
  status: string;
  message?: string | null;
  user_id?: string;
  tool_name?: string;
  args_json?: string;
  created_at?: string;
  risk_level?: 'low' | 'medium' | 'high' | string;
  risk_summary?: string;
  scope_summary?: string;
  scope_targets?: string[];
  simulation?: Record<string, unknown> | null;
}

// Poison pill stats
export interface PoisonPillStats {
  total: number;
  by_queue: Record<string, { count: number; last_quarantined_at?: string }>;
}

// Reflexion
export interface ReflexionLesson {
  id: string
  content: string
  score?: number
  metadata?: Record<string, unknown>
}
