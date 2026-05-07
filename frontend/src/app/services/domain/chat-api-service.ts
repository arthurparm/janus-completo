import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map, tap } from 'rxjs/operators';
import { ApiContextService } from '../api-context.service';
import { AppLoggerService } from '../../core/services/app-logger.service';
import { ChatStartResponse, ChatStartRequest, ChatMessageRequest, ChatMessage, ChatStudyJobResponse, ChatMessageResponse, ChatHistoryResponse, ChatListItem, ChatHistoryPaginatedResponse, Citation, TraceStep, ConversationMeta, ConversationsListResponse } from '../../models';

@Injectable({ providedIn: 'root' })
export class ChatApiService {
  constructor(
    private http: HttpClient,
    private apiContext: ApiContextService,
    private logger: AppLoggerService
  ) {}

getConversationTrace(conversationId: string): Observable<TraceStep[]> {
    return this.http.get<TraceStep[]>(this.apiContext.buildUrl(`/api/v1/chat/${encodeURIComponent(conversationId)}/trace`));
  }

startChat(title?: string, persona?: string, user_id?: string, project_id?: string): Observable<ChatStartResponse> {
    const body: ChatStartRequest = { title }
    if (persona) body.persona = persona
    if (user_id) body.user_id = user_id
    if (project_id) body.project_id = project_id
    return this.http.post<ChatStartResponse>(this.apiContext.buildUrl(`/api/v1/chat/start`), body)
  }

sendChatMessage(conversation_id: string, content: string, role: string = 'orchestrator', priority: string = 'fast_and_cheap', timeout_seconds?: number, user_id?: string, project_id?: string, knowledge_space_id?: string): Observable<ChatMessageResponse & { citations?: Citation[] }> {
    // Validate required fields
    // Validate required fields
    if (!conversation_id || conversation_id.trim().length < 1) {
      this.logger.error('[BackendApiService] Invalid conversation_id provided to sendChatMessage', { conversation_id });
      throw new Error(`Invalid conversation_id: ${conversation_id}`);
    }

    this.logger.debug('[BackendApiService] Sending chat message', {
      conversation_id_raw: conversation_id,
      conversation_id_trimmed: conversation_id.trim(),
      role,
      priority,
    });

    const body: ChatMessageRequest = {
      conversation_id: conversation_id.trim(),
      message: content,
      role: role || 'orchestrator',
      priority: priority || 'fast_and_cheap'
    };

    if (typeof timeout_seconds !== 'undefined') body.timeout_seconds = timeout_seconds
    if (user_id) body.user_id = user_id
    if (project_id) body.project_id = project_id
    if (knowledge_space_id) body.knowledge_space_id = knowledge_space_id

    this.logger.debug('[BackendApiService] Sending chat message payload', body);

    return this.http.post<ChatMessageResponse>(this.apiContext.buildUrl(`/api/v1/chat/message`), body).pipe(
      tap({
        next: (res) => this.logger.debug('[BackendApiService] Chat message success', res),
        error: (err) => this.logger.error('[BackendApiService] Chat message failed', err)
      })
    )
  }

getChatStudyJob(jobId: string): Observable<ChatStudyJobResponse> {
    return this.http.get<ChatStudyJobResponse>(this.apiContext.buildUrl(`/api/v1/chat/study-jobs/${encodeURIComponent(jobId)}`))
  }

getChatHistory(conversation_id: string): Observable<ChatHistoryResponse> {
    return this.http.get<ChatHistoryResponse>(this.apiContext.buildUrl(`/api/v1/chat/${encodeURIComponent(conversation_id)}/history`)).pipe(
      map((resp) => {
        const msgs = Array.isArray(resp?.messages) ? resp.messages : []
        const mapped = msgs.map((m) => ({
          message_id: typeof m?.message_id === 'string' ? String(m.message_id) : undefined,
          role: String(m?.role || ''),
          text: this.normalizeChatText(m?.text),
          timestamp: m?.timestamp != null ? Number(m.timestamp) : 0,
          citations: m?.citations,
          citation_status: m?.citation_status,
          reasoning: m?.reasoning,
          ui: m?.ui,
          understanding: m?.understanding,
          confirmation: m?.confirmation,
          agent_state: m?.agent_state,
          delivery_status: typeof m?.delivery_status === 'string' ? String(m.delivery_status) : undefined,
          failure_classification: typeof m?.failure_classification === 'string' ? String(m.failure_classification) : undefined,
          provider: typeof m?.provider === 'string' ? String(m.provider) : undefined,
          model: typeof m?.model === 'string' ? String(m.model) : undefined,
        }))
        return { conversation_id: String(resp?.conversation_id || conversation_id), messages: mapped } as ChatHistoryResponse
      })
    )
  }

getChatHistoryPaginated(conversation_id: string, params: {
    limit?: number;
    offset?: number;
    before_ts?: number;
    after_ts?: number;
  } = {}): Observable<{
    conversation_id: string;
    messages: ChatMessage[];
    total_count: number;
    has_more: boolean;
    next_offset?: number;
    limit: number;
    offset: number;
  }> {
    const qs = new URLSearchParams()
    if (params.limit) qs.set('limit', String(params.limit))
    if (params.offset) qs.set('offset', String(params.offset))
    if (params.before_ts) qs.set('before_ts', String(params.before_ts))
    if (params.after_ts) qs.set('after_ts', String(params.after_ts))

    const url = this.apiContext.buildUrl(`/api/v1/chat/${encodeURIComponent(conversation_id)}/history${qs.toString() ? '?' + qs.toString() : ''}`)

    return this.http.get<ChatHistoryPaginatedResponse>(url).pipe(
      map((resp) => {
        const msgs = Array.isArray(resp?.messages) ? resp.messages : []
        const mapped = msgs.map((m) => ({
          message_id: typeof m?.message_id === 'string' ? String(m.message_id) : undefined,
          role: String(m?.role || ''),
          text: this.normalizeChatText(m?.text),
          timestamp: m?.timestamp != null ? Number(m.timestamp) : 0,
          citations: m?.citations,
          citation_status: m?.citation_status,
          reasoning: m?.reasoning,
          ui: m?.ui,
          understanding: m?.understanding,
          confirmation: m?.confirmation,
          agent_state: m?.agent_state,
          delivery_status: typeof m?.delivery_status === 'string' ? String(m.delivery_status) : undefined,
          failure_classification: typeof m?.failure_classification === 'string' ? String(m.failure_classification) : undefined,
          provider: typeof m?.provider === 'string' ? String(m.provider) : undefined,
          model: typeof m?.model === 'string' ? String(m.model) : undefined,
        }))

        return {
          conversation_id: String(resp?.conversation_id || conversation_id),
          messages: mapped,
          total_count: Number(resp?.total_count || 0),
          has_more: Boolean(resp?.has_more || false),
          next_offset: resp?.next_offset != null ? Number(resp.next_offset) : undefined,
          limit: Number(resp?.limit || params.limit || 50),
          offset: Number(resp?.offset || params.offset || 0)
        }
      })
    )
  }

checkChatHealth(): Observable<{ status: string, repository_accessible: boolean, total_conversations: number }> {
    return this.http.get<{ status: string, repository_accessible: boolean, total_conversations: number }>(this.apiContext.buildUrl('/api/v1/chat/health'))
  }

listConversations(params: { user_id?: string; project_id?: string; limit?: number } = {}): Observable<ConversationsListResponse> {
    const qs = new URLSearchParams()
    if (params.user_id) qs.set('user_id', params.user_id)
    if (params.project_id) qs.set('project_id', params.project_id)
    qs.set('limit', String(params.limit ?? 50))

    return this.http.get<ChatListItem[] | { conversations: ChatListItem[] }>(this.apiContext.buildUrl(`/api/v1/chat/conversations?${qs.toString()}`)).pipe(
      map((resp) => {
        // Backend now returns array directly, not {conversations: [...]}
        const items = Array.isArray(resp) ? resp : (resp as { conversations: ChatListItem[] }).conversations || []

        const mapped = items.map((it) => {
          const lm = it?.last_message
          const last_message: ChatMessage | undefined = lm && typeof lm === 'object' ? {
            role: String(lm?.role || ''),
            text: this.normalizeChatText(lm?.text),
            timestamp: lm?.timestamp != null ? Number(lm.timestamp) : 0,
            citations: lm?.citations,
            citation_status: lm?.citation_status,
            reasoning: lm?.reasoning,
            ui: lm?.ui,
            understanding: lm?.understanding,
            confirmation: lm?.confirmation,
            agent_state: lm?.agent_state,
          } : undefined
          return {
            conversation_id: String(it?.conversation_id || ''),
            title: it?.title,
            created_at: it?.created_at,
            updated_at: it?.updated_at,
            last_message,
            message_count: undefined, // Not in backend response
            tags: undefined, // Not in backend response
          } as ConversationMeta
        })

        return { conversations: mapped } as ConversationsListResponse
      })
    )
  }

renameConversation(conversation_id: string, new_title: string): Observable<{ status: string }> {
    return this.http.put<{ status: string }>(this.apiContext.buildUrl(`/api/v1/chat/${encodeURIComponent(conversation_id)}/rename`), { new_title })
  }

deleteConversation(conversation_id: string): Observable<{ status: string }> {
    return this.http.delete<{ status: string }>(this.apiContext.buildUrl(`/api/v1/chat/${encodeURIComponent(conversation_id)}`))
  }

public normalizeChatText(value: unknown): string {
    if (value === null || value === undefined) return ''
    if (typeof value === 'string') return value
    if (typeof value === 'number' || typeof value === 'boolean') return String(value)
    try {
      return JSON.stringify(value, null, 2)
    } catch {
      return String(value)
    }
  }
}
