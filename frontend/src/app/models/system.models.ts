export interface SystemStatus {
  app_name: string;
  version: string;
  environment: string;
  status: string;
  timestamp?: string;
  uptime_seconds?: number;
  system?: Record<string, unknown>;
  process?: Record<string, unknown>;
  performance?: Record<string, unknown>;
  config?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface ServiceHealthItem {
  key: string;
  name: string;
  status: string;
  metric_text?: string;
}

export interface ServiceHealthResponse {
  services: ServiceHealthItem[];
}

export interface WorkerStatusResponse {
  id: string;
  status: string;
  last_heartbeat: string | Date; // Backend sends datetime string, but frontend might parse it
  tasks_processed: number;
}

export interface OrchestratorWorkerTaskStatus {
  name: string;
  running: boolean;
  done: boolean;
  cancelled: boolean;
  exception?: string | null;
  state: string;
  reason?: string;
  detail?: string;
  composite?: boolean;
  children?: OrchestratorWorkerTaskStatus[];
}

export interface QueueInfoResponse {
  name: string;
  messages: number;
  consumers: number;
}

export interface SystemOverviewResponse {
  system_status: SystemStatus;
  services_status: ServiceHealthItem[];
  workers_status: WorkerStatusResponse[];
}

// Database Validation
export interface DbValidationCheck {
  table: string;
  name: string;
  kind: string;
  exists: boolean;
}

export interface DbValidationResponse {
  status: string;
  checks: DbValidationCheck[];
}

// Observability health
export interface ObservabilitySystemHealth {
  status: string;
  dependencies?: Record<string, { status: string; details?: Record<string, unknown> }>;
}

export interface QueueAck { status: string; task_id?: string }
export interface WorkersStatusResponse {
  tracked: number;
  workers: OrchestratorWorkerTaskStatus[];
}

// Auto Analysis
export interface HealthInsight {
  issue: string
  severity: 'low' | 'medium' | 'high' | 'unknown'
  suggestion: string
  estimated_impact: string
  source: 'llm_cost_tracker' | 'observability_slo' | 'feedback'
  status: 'ok' | 'warning' | 'critical' | 'insufficient_data' | 'unavailable'
  evidence: Record<string, unknown>
}

export interface AutoAnalysisResponse {
  timestamp: string
  overall_health: 'healthy' | 'warning' | 'critical' | 'unknown'
  insights: HealthInsight[]
  summary: string
  fun_fact: null
}

export type WorkersStatusItem = WorkerStatusResponse;
