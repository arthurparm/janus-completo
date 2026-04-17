export interface GenerativeMemoryItem {
  id?: string;
  content: string;
  score?: number;
  type?: string;
  created_at?: string | number;
  updated_at?: string | number;
  metadata?: {
    importance?: number | string;
    user_id?: string;
    conversation_id?: string;
    session_id?: string;
    [key: string]: unknown;
  };
  [key: string]: unknown;
}

export interface UserPreferenceMemoryItem {
  id?: string;
  content: string;
  ts_ms?: number;
  preference_kind?: 'do' | 'dont' | string;
  instruction_text?: string;
  scope?: string;
  confidence?: number;
  user_id?: string;
  conversation_id?: string;
  session_id?: string;
  active?: boolean;
  origin?: string;
  dedupe_key?: string;
  metadata?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface MemoryItem {
  content: string;
  ts_ms: number;
  composite_id?: string;
  metadata?: {
    type?: string;
    user_id?: string;
    conversation_id?: string;
    session_id?: string;
    role?: string;
    timestamp?: number;
    [key: string]: unknown;
  };
}
