import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ApiContextService } from '../api-context.service';
import { GenerativeMemoryItem, UserPreferenceMemoryItem, MemoryItem } from '../../models';

@Injectable({ providedIn: 'root' })
export class MemoryApiService {
  constructor(
    private http: HttpClient,
    private apiContext: ApiContextService
  ) {}

getMemoryTimeline(params: {
    start_date?: string
    end_date?: string
    query?: string
    limit?: number
    min_score?: number
    user_id?: string
    conversation_id?: string
  } = {}): Observable<MemoryItem[]> {
    const qs = new URLSearchParams()
    if (params.start_date) qs.set('start_date', params.start_date)
    if (params.end_date) qs.set('end_date', params.end_date)
    if (params.query) qs.set('query', params.query)
    if (params.limit) qs.set('limit', String(params.limit))
    if (params.min_score !== undefined) qs.set('min_score', String(params.min_score))
    if (params.user_id) qs.set('user_id', params.user_id)
    if (params.conversation_id) qs.set('conversation_id', params.conversation_id)
    const headers = params.user_id ? this.apiContext.headersFor(params.user_id) : undefined
    return this.http.get<MemoryItem[]>(
      this.apiContext.buildUrl(`/api/v1/memory/timeline${qs.toString() ? '?' + qs.toString() : ''}`),
      headers ? { headers } : undefined
    )
  }

getGenerativeMemories(
    query: string,
    limit: number = 10,
    filters: { type?: string; userId?: string; conversationId?: string } = {}
  ): Observable<GenerativeMemoryItem[]> {
    const qs = new URLSearchParams()
    qs.set('query', query)
    qs.set('limit', String(limit))
    if (filters.type) qs.set('type', String(filters.type))
    if (filters.userId) qs.set('user_id', String(filters.userId))
    if (filters.conversationId) qs.set('conversation_id', String(filters.conversationId))
    return this.http.get<GenerativeMemoryItem[]>(this.apiContext.buildUrl(`/api/v1/memory/generative?${qs.toString()}`))
  }

addGenerativeMemory(
    content: string,
    opts: { importance?: number; type?: string; userId?: string; conversationId?: string; sessionId?: string } = {}
  ): Observable<GenerativeMemoryItem> {
    const qs = new URLSearchParams()
    qs.set('content', content)
    if (typeof opts.importance === 'number') qs.set('importance', String(opts.importance))
    if (opts.type) qs.set('type', String(opts.type))
    if (opts.userId) qs.set('user_id', String(opts.userId))
    if (opts.conversationId) qs.set('conversation_id', String(opts.conversationId))
    if (opts.sessionId) qs.set('session_id', String(opts.sessionId))
    return this.http.post<GenerativeMemoryItem>(this.apiContext.buildUrl(`/api/v1/memory/generative?${qs.toString()}`), {})
  }

getUserPreferences(params: {
    userId?: string
    conversationId?: string
    query?: string
    limit?: number
    activeOnly?: boolean
  } = {}): Observable<UserPreferenceMemoryItem[]> {
    const qs = new URLSearchParams()
    if (params.userId) qs.set('user_id', String(params.userId))
    if (params.conversationId) qs.set('conversation_id', String(params.conversationId))
    if (params.query) qs.set('query', String(params.query))
    if (typeof params.limit === 'number') qs.set('limit', String(params.limit))
    if (typeof params.activeOnly === 'boolean') qs.set('active_only', String(params.activeOnly))
    const headers = params.userId ? this.apiContext.headersFor(params.userId) : undefined
    return this.http.get<UserPreferenceMemoryItem[]>(
      this.apiContext.buildUrl(`/api/v1/memory/preferences${qs.toString() ? '?' + qs.toString() : ''}`),
      headers ? { headers } : undefined
    )
  }
}
