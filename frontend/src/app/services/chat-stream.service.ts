import { Injectable, inject } from '@angular/core'
import { BehaviorSubject, Observable, Subject } from 'rxjs'
import { API_BASE_URL, SSE_MAX_RETRIES, SSE_RETRY_MAX_SECONDS } from './api.config'
import { ChatAgentState, ChatConfirmationState, ChatUnderstanding, Citation, CitationStatus } from './backend-api.service'
import { AppLoggerService } from '../core/services/app-logger.service'
import { buildChatStreamAuthHeaders, generateRequestId } from './chat-auth-headers.util'

type StreamStatus = 'idle' | 'connecting' | 'open' | 'streaming' | 'retrying' | 'closed' | 'error'

export interface StreamDone {
  conversation_id?: string
  provider?: string
  model?: string
  citations?: Citation[]
  citation_status?: CitationStatus
  understanding?: ChatUnderstanding
  confirmation?: ChatConfirmationState
  agent_state?: ChatAgentState
}

export interface StreamError {
  error: string
  code?: string
  category?: string
  retryable?: boolean
  http_status?: number | null
  attempt: number
}

export interface StreamCognitiveStatus {
  state: string
  confidence_band?: string
  requires_confirmation?: boolean
  reason?: string
  timestamp?: number
}

export interface StreamToolStatus {
  phase?: string
  tool_name?: string
  status?: string
  pending_action_id?: number
  risk_level?: string
  message?: string
}

export interface StartParams {
  conversationId: string
  text: string
  role?: string
  priority?: string
  timeoutSeconds?: number
  projectId?: string
}

interface ParsedSseEvent {
  event: string
  data: string
}

@Injectable({ providedIn: 'root' })
export class ChatStreamService {
  private readonly logger = inject(AppLoggerService)
  private abortController?: AbortController
  private streamSeq = 0
  private lastUrl?: string
  private lastProjectId?: string
  private lastRequestId?: string
  private status$ = new BehaviorSubject<StreamStatus>('idle')
  private typing$ = new BehaviorSubject<boolean>(false)
  private partials$ = new Subject<{ text: string }>()
  private done$ = new Subject<StreamDone>()
  private errors$ = new Subject<StreamError>()
  private cognitive$ = new Subject<StreamCognitiveStatus>()
  private toolStatus$ = new Subject<StreamToolStatus>()
  private attempt = 0
  private startTs = 0
  private ttftCaptured = false
  private streamMode: 'token' | 'partial' | null = null

  status(): Observable<StreamStatus> { return this.status$.asObservable() }
  typing(): Observable<boolean> { return this.typing$.asObservable() }
  partials(): Observable<{ text: string }> { return this.partials$.asObservable() }
  done(): Observable<StreamDone> { return this.done$.asObservable() }
  errors(): Observable<StreamError> { return this.errors$.asObservable() }
  cognitive(): Observable<StreamCognitiveStatus> { return this.cognitive$.asObservable() }
  toolStatus(): Observable<StreamToolStatus> { return this.toolStatus$.asObservable() }

  start(params: StartParams): void {
    this.logger.debug('[ChatStreamService] Iniciando stream', params)
    this.stop()
    this.status$.next('connecting')
    this.typing$.next(false)
    this.attempt = 0
    this.startTs = Date.now()
    this.ttftCaptured = false
    this.streamMode = null
    this.lastProjectId = params.projectId
    this.lastRequestId = generateRequestId()

    const role = params.role || 'orchestrator'
    const priority = params.priority || 'fast_and_cheap'
    const qs = new URLSearchParams({
      message: params.text,
      role,
      priority,
    })
    if (typeof params.timeoutSeconds !== 'undefined') {
      qs.set('timeout_seconds', String(params.timeoutSeconds))
    }
    const url = `${API_BASE_URL}/v1/chat/stream/${encodeURIComponent(params.conversationId)}?${qs.toString()}`
    this.logger.debug('[ChatStreamService] URL construída', { url })
    this.open(url, params.projectId, this.lastRequestId)
  }

  stop(): void {
    const ctrl = this.abortController
    this.abortController = undefined
    if (ctrl) {
      try {
        ctrl.abort()
      } catch {
        /* noop */
      }
    }
    this.status$.next('closed')
    this.typing$.next(false)
  }

  private open(url: string, projectId?: string, requestId?: string): void {
    this.lastUrl = url
    this.lastProjectId = projectId
    this.lastRequestId = requestId || this.lastRequestId || generateRequestId()
    const seq = ++this.streamSeq
    const controller = new AbortController()
    this.abortController = controller
    void this.consumeStream(url, controller, seq, projectId, this.lastRequestId)
  }

  private async consumeStream(
    url: string,
    controller: AbortController,
    seq: number,
    projectId?: string,
    requestId?: string,
  ): Promise<void> {
    this.logger.debug('[ChatStreamService] Abrindo fetch-SSE', { url, seq })
    try {
      const headers = buildChatStreamAuthHeaders({ projectId, requestId })
      headers.set('Accept', 'text/event-stream')

      const response = await fetch(url, {
        method: 'GET',
        headers,
        signal: controller.signal,
      })

      if (!response.ok) {
        const bodyText = await this.safeReadErrorBody(response)
        const parsedError = this.parseChatErrorBody(bodyText)
        this.logger.error('[ChatStreamService] HTTP error no stream', {
          status: response.status,
          bodyText,
        })
        const reason = parsedError.message || this.mapHttpErrorReason(response.status, bodyText)
        const retryable = typeof parsedError.retryable === 'boolean'
          ? parsedError.retryable
          : !(response.status === 401 || response.status === 403 || response.status === 404 || response.status === 413 || response.status === 422)
        this.handleError(reason, retryable, {
          code: parsedError.code,
          category: parsedError.category,
          retryable,
          http_status: response.status,
        })
        return
      }

      if (!response.body) {
        this.handleError('empty_stream_body')
        return
      }

      this.logger.info('[ChatStreamService] Stream conectado com sucesso', { seq })
      this.status$.next('open')

      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''

      let streamOpen = true
      while (streamOpen) {
        const { value, done } = await reader.read()
        if (done) {
          streamOpen = false
          continue
        }
        buffer += decoder.decode(value, { stream: true })
        const parsed = this.extractEvents(buffer)
        buffer = parsed.remaining
        for (const evt of parsed.events) {
          this.dispatchSseEvent(evt.event, evt.data)
          if (seq !== this.streamSeq || controller.signal.aborted) return
        }
      }

      buffer += decoder.decode()
      const trailing = this.extractEvents(buffer, true)
      for (const evt of trailing.events) {
        this.dispatchSseEvent(evt.event, evt.data)
      }

      if (!controller.signal.aborted && this.status$.value !== 'closed') {
        this.handleError('stream_closed')
      }
    } catch (error) {
      if (controller.signal.aborted || seq !== this.streamSeq) {
        return
      }
      this.logger.error('[ChatStreamService] Erro em fetch-SSE', error)
      this.handleError('connection_error')
    } finally {
      if (this.abortController === controller) {
        this.abortController = undefined
      }
    }
  }

  private dispatchSseEvent(event: string, data: string): void {
    switch (event) {
      case 'start':
        this.logger.debug('[ChatStreamService] Evento start recebido')
        this.status$.next('open')
        return
      case 'protocol':
        this.logger.debug('[ChatStreamService] Evento protocol recebido', { data })
        return
      case 'heartbeat':
        this.logger.debug('[ChatStreamService] Heartbeat recebido')
        return
      case 'ack':
      case 'cognitive_status':
      case 'tool_status':
      case 'partial':
      case 'token':
      case 'done':
      case 'error':
      case 'message':
        this.handleMessage(event, data)
        return
      default:
        this.logger.debug('[ChatStreamService] Evento SSE desconhecido', { event, data })
    }
  }

  private extractEvents(input: string, flush = false): { events: ParsedSseEvent[]; remaining: string } {
    const normalized = input.replace(/\r\n/g, '\n')
    const events: ParsedSseEvent[] = []
    let cursor = 0

    let hasSeparator = true
    while (hasSeparator) {
      const sep = normalized.indexOf('\n\n', cursor)
      if (sep === -1) {
        hasSeparator = false
        continue
      }
      const block = normalized.slice(cursor, sep)
      cursor = sep + 2
      const evt = this.parseSseBlock(block)
      if (evt) events.push(evt)
    }

    let remaining = normalized.slice(cursor)
    if (flush && remaining.trim()) {
      const evt = this.parseSseBlock(remaining)
      if (evt) events.push(evt)
      remaining = ''
    }

    return { events, remaining }
  }

  private parseSseBlock(block: string): ParsedSseEvent | null {
    const lines = block.split('\n')
    let event = 'message'
    const dataLines: string[] = []

    for (const rawLine of lines) {
      const line = rawLine ?? ''
      if (!line) continue
      if (line.startsWith(':')) continue
      if (line.startsWith('event:')) {
        event = line.slice('event:'.length).trim() || 'message'
        continue
      }
      if (line.startsWith('data:')) {
        dataLines.push(line.slice('data:'.length).trimStart())
      }
    }

    if (event === 'message' && dataLines.length === 0) return null
    return { event, data: dataLines.join('\n') }
  }

  private async safeReadErrorBody(response: Response): Promise<string> {
    try {
      return (await response.text()) || ''
    } catch {
      return ''
    }
  }

  private parseChatErrorBody(bodyText: string): { code?: string; message?: string; category?: string; retryable?: boolean } {
    if (!bodyText) return {}
    try {
      const parsed = JSON.parse(bodyText) as any
      const detail = parsed?.detail ?? parsed
      const canonical = detail?.error ?? detail
      const message = typeof canonical?.message === 'string'
        ? canonical.message
        : (typeof detail === 'string' ? detail : undefined)
      return {
        code: typeof canonical?.code === 'string' ? canonical.code : undefined,
        message,
        category: typeof canonical?.category === 'string' ? canonical.category : undefined,
        retryable: typeof canonical?.retryable === 'boolean' ? canonical.retryable : undefined,
      }
    } catch {
      return {}
    }
  }

  private mapHttpErrorReason(status: number, bodyText: string): string {
    if (status === 401) return 'unauthorized'
    if (status === 403) return 'access_denied'
    if (status === 404) return 'conversation_not_found'
    if (status === 413) return 'message_too_large'
    if (status === 422) return 'invalid_request'
    if (bodyText) return `http_${status}`
    return 'http_error'
  }

  private handleMessage(kind: string, data: string): void {
    this.logger.debug('[ChatStreamService] Processando mensagem', { kind, data })
    try {
      if (kind === 'token') {
        if (this.streamMode && this.streamMode !== 'token') return
        this.streamMode = 'token'
        kind = 'partial'
      } else if (kind === 'partial') {
        if (this.streamMode && this.streamMode !== 'partial') return
        this.streamMode = 'partial'
      }
      if (kind === 'partial') {
        this.status$.next('streaming')
        this.typing$.next(true)
        const parsed = JSON.parse(data || '{}') as { text?: string }
        if (!this.ttftCaptured) {
          this.ttftCaptured = true
        }
        const rawText = parsed?.text
        let text = ''
        if (typeof rawText === 'string') {
          text = rawText
        } else if (rawText != null) {
          try {
            text = JSON.stringify(rawText, null, 2)
          } catch {
            text = String(rawText)
          }
        }
        this.partials$.next({ text })
        return
      }
      if (kind === 'done') {
        this.typing$.next(false)
        const parsed = JSON.parse(data || '{}') as StreamDone
        this.done$.next({
          conversation_id: parsed?.conversation_id,
          provider: parsed?.provider,
          model: parsed?.model,
          citations: parsed?.citations,
          citation_status: parsed?.citation_status,
          understanding: parsed?.understanding,
          confirmation: parsed?.confirmation,
          agent_state: parsed?.agent_state,
        })
        this.stop()
        return
      }
      if (kind === 'error') {
        const parsed = JSON.parse(data || '{}') as { error?: string; message?: string; code?: string; category?: string; retryable?: boolean; http_status?: number | null }
        this.handleError(
          String(parsed?.message || parsed?.error || 'error'),
          parsed?.retryable !== false,
          {
            code: typeof parsed?.code === 'string' ? parsed.code : undefined,
            category: typeof parsed?.category === 'string' ? parsed.category : undefined,
            http_status: typeof parsed?.http_status === 'number' ? parsed.http_status : (parsed?.http_status ?? undefined),
            retryable: parsed?.retryable,
          }
        )
        return
      }
      if (kind === 'cognitive_status') {
        const parsed = JSON.parse(data || '{}') as StreamCognitiveStatus
        this.cognitive$.next(parsed || { state: 'unknown' })
        if (parsed?.state === 'streaming_response') {
          this.status$.next('streaming')
        }
        return
      }
      if (kind === 'tool_status') {
        const parsed = JSON.parse(data || '{}') as StreamToolStatus
        this.toolStatus$.next(parsed || {})
        return
      }
      if (kind === 'ack' || kind === 'message') {
        return
      }
      this.logger.warn('[ChatStreamService] Tipo de mensagem não reconhecido', { kind })
    } catch (e) {
      this.logger.error('[ChatStreamService] Erro ao processar mensagem', e)
      this.handleError('parse_error')
    }
  }

  private handleError(
    reason: string,
    retryable = true,
    meta?: { code?: string; category?: string; retryable?: boolean; http_status?: number | null },
  ): void {
    this.attempt += 1
    this.errors$.next({
      error: reason,
      attempt: this.attempt,
      code: meta?.code,
      category: meta?.category,
      retryable: meta?.retryable,
      http_status: meta?.http_status,
    })

    if (!retryable) {
      this.status$.next('error')
      this.typing$.next(false)
      const ctrl = this.abortController
      if (ctrl) {
        try { ctrl.abort() } catch { /* noop */ }
        this.abortController = undefined
      }
      this.logger.error('[ChatStreamService] Erro não recuperável no stream', { reason })
      return
    }

    if (this.attempt >= Math.max(1, SSE_MAX_RETRIES)) {
      this.status$.next('error')
      this.typing$.next(false)
      const ctrl = this.abortController
      if (ctrl) {
        try { ctrl.abort() } catch { /* noop */ }
        this.abortController = undefined
      }
      this.logger.error('[ChatStreamService] Máximo de tentativas de reconexão atingido', { reason })
      return
    }

    this.status$.next('error')
    this.typing$.next(false)
    const max = Math.max(1, SSE_RETRY_MAX_SECONDS)
    const backoff = Math.min(max, Math.pow(2, this.attempt))
    const jitter = Math.random() * 0.5
    const wait = (backoff + jitter) * 1000
    this.status$.next('retrying')
    const ctrl = this.abortController
    if (ctrl) {
      try { ctrl.abort() } catch { /* noop */ }
      this.abortController = undefined
    }
    const url = this.lastUrl
    const projectId = this.lastProjectId
    const requestId = this.lastRequestId
    setTimeout(() => {
      if (!url) return
      this.status$.next('connecting')
      this.open(url, projectId, requestId)
    }, wait)
  }
}
