import { Citation } from './chat.models';

// Meta-Agent
export interface MetaAgentRecommendation {
  id: string;
  category?: string;
  title: string;
  description?: string;
  rationale?: string;
  estimated_impact?: string;
  priority?: number;
  suggested_agent?: string | null;
  created_at?: string;
}

export interface MetaAgentExecutionResult {
  title?: string;
  status?: string;
  [key: string]: unknown;
}

export interface MetaAgentReport {
  cycle_id: string;
  timestamp: string;
  overall_status: string;
  health_score: number;
  issues_detected: Record<string, unknown>[];
  recommendations: MetaAgentRecommendation[];
  summary: string;
  metrics_snapshot: Record<string, unknown>;
  execution_results?: MetaAgentExecutionResult[];
}

export interface MetaAgentLatestReportResponse {
  message: string;
  report: MetaAgentReport | null;
}

export interface MetaAgentHeartbeatStatus {
  heartbeat_active: boolean;
  total_cycles_executed: number;
  last_analysis?: string | null;
}

// Goals
export interface Goal {
  id: string
  title: string
  description: string
  priority: number
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  success_criteria?: string
  deadline_ts?: number
  created_at: number
  updated_at: number
}

export interface GoalCreateRequest {
  title: string
  description: string
  priority?: number
  success_criteria?: string
  deadline_ts?: number
}

// Autonomy
export interface AutonomyStartRequest {
  interval_seconds?: number
  user_id?: string
  project_id?: string
  risk_profile?: 'conservative' | 'balanced' | 'aggressive'
  auto_confirm?: boolean
  allowlist?: string[]
  blocklist?: string[]
  max_actions_per_cycle?: number
  max_seconds_per_cycle?: number
  plan?: { tool: string; args: Record<string, unknown> }[]
}

export interface AutonomyConfig {
  risk_profile?: string;
  interval_seconds?: number;
  max_actions_per_cycle?: number;
  [key: string]: unknown;
}

export interface AutonomyStatusResponse {
  active: boolean
  cycle_count: number
  last_cycle_at?: number | null
  config: AutonomyConfig
}

export interface AutonomyPlanResponse {
  status: string
  active: boolean
  steps_count: number
  plan: { tool: string; args: Record<string, unknown> }[]
}

export interface AutonomyPolicyUpdateRequest {
  risk_profile?: string
  auto_confirm?: boolean
  allowlist?: string[]
  blocklist?: string[]
  max_actions_per_cycle?: number
  max_seconds_per_cycle?: number
}

export interface AdminBacklogSyncResponse {
  created: number
  deduped: number
  capped: number
  closed: number
  fallback_used_count: number
  findings_total: number
}

export interface AdminBacklogTask {
  id: string
  title: string
  description: string
  status: string
  priority: number
  source_kind?: string | null
  source_fingerprint?: string | null
  area?: string | null
  severity?: string | null
  auto_created?: boolean
  created_at?: string | null
  updated_at?: string | null
}

export interface AdminBacklogSprint {
  id: string
  name: string
  status: string
  start_ts?: number | null
  end_ts?: number | null
  tasks: AdminBacklogTask[]
}

export interface AdminBacklogSprintType {
  sprint_type: { id: string; name: string; slug: string }
  sprints: AdminBacklogSprint[]
}

export interface SelfStudyRunFile {
  id: number
  file_path: string
  change_type?: string | null
  sha_before?: string | null
  sha_after?: string | null
  summary_status: string
  error?: string | null
}

export interface SelfStudyRun {
  id: number
  trigger_type: string
  mode: 'incremental' | 'full' | string
  status: string
  files_total: number
  files_processed: number
  error?: string | null
  base_commit?: string | null
  target_commit?: string | null
  created_at?: string | null
  finished_at?: string | null
  files?: SelfStudyRunFile[]
}

export interface SelfStudyStatusResponse {
  last_studied_commit?: string | null
  last_success_at?: string | null
  running?: {
    id: number
    status: string
    mode: string
    created_at?: string | null
    files_total?: number
    files_processed?: number
    current_file_path?: string | null
    current_file_index?: number | null
  } | null
  recent_runs: SelfStudyRun[]
}

export interface AdminCodeQaResponse {
  answer: string
  citations: Citation[]
  self_memory: Array<{ file_path?: string; summary?: string; updated_at?: string | number }>
}
