export interface Tool {
  name: string;
  description: string;
  args_schema?: Record<string, unknown>;
  category?: string;
  permission_level?: string;
  rate_limit_per_minute?: number;
  requires_confirmation?: boolean;
  tags?: string[];
  enabled?: boolean;
}

export interface ToolListResponse {
  tools: Tool[];
}

export interface ToolStats {
  total_tools_registered?: number;
  total_calls?: number;
  successful_calls?: number;
  success_rate?: number;
  tool_usage?: Record<string, { total: number; success: number; avg_duration: number }>;
}