import { ReflexionLesson } from './observability.models';
import { ChatMessage } from './chat.models';

export interface ConversationMeta {
  conversation_id: string;
  title?: string;
  last_message_at?: string;
  created_at?: number;
  updated_at?: number;
  last_message?: ChatMessage
  message_count?: number
  tags?: string[]
}
export interface ConversationsListResponse { conversations: ConversationMeta[] }
export interface PostSprintSummaryResponse {
  lessons: ReflexionLesson[]
  meta_report?: Record<string, unknown>
}
