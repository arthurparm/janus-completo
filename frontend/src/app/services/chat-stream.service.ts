import { Injectable, inject } from '@angular/core'
import { BehaviorSubject, Observable, Subject } from 'rxjs'
import { API_BASE_URL, SSE_MAX_RETRIES, SSE_RETRY_MAX_SECONDS } from './api.config'
import { ChatUnderstanding, Citation } from './backend-api.service'
import { AppLoggerService } from '../core/services/app-logger.service'
import { buildChatStreamAuthHeaders } from './chat-auth-headers.util'

type StreamStatus = 'idle' | 'connecting' | 'open' | 'streaming' | 'retrying' | 'closed' | 'error'

export interface StreamDone {
  conversation_id?: string
  provider?: string
  model?: string
  citations?: Citation[]
  understanding?: ChatUnderstanding
}

export interface StreamError {
  error: string
  attempt: number
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
  private status$ = new BehaviorSubject<StreamStatus>('idle')
  private typing$ = new BehaviorSubject<boolean>(false)
  private partials$ = new Subject<{ text: string }>()
  private done$ = new Subject<StreamDone>()
  private errors$ = new Subject<StreamError>()
  private attempt = 0
  private startTs = 0
  private ttftCaptured = false
  private streamMode: 'token' | 'partial' | null = null

  status(): Observable<StreamStatus> { return this.status$.asObservable() }
  typing(): Observable<boolean> { return this.typing$.asObservable() }
  partials(): Observable<{ text: string }> { return this.partials$.asObservable() }
  done(): Observable<StreamDone> { return this.done$.asObservable() }
  errors(): Observable<StreamError> { return this.errors$.asObservable() }

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
    this.open(url, params.projectId)
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

  private open(url: string, projectId?: string): void {
    this.lastUrl = url
    this.lastProjectId = projectId
    const seq = ++this.streamSeq
    const controller = new AbortController()
    this.abortController = controller
    void this.consumeStream(url, controller, seq, projectId)
  }

  private async consumeStream(
    url: string,
    controller: AbortController,
    seq: number,
    projectId?: string,
  ): Promise<void> {
    this.logger.debug('[ChatStreamService] Abrindo fetch-SSE', { url, seq })
    try {
      const headers = buildChatStreamAuthHeaders({ projectId })
      headers.set('Accept', 'text/event-stream')

      const response = await fetch(url, {
        method: 'GET',
        headers,
        signal: controller.signal,
      })

      if (!response.ok) {
        const bodyText = await this.safeReadErrorBody(response)
        this.logger.error('[ChatStreamService] HTTP error no stream', {
          status: response.status,
          bodyText,
        })
        const reason = this.mapHttpErrorReason(response.status, bodyText)
        const retryable = !(response.status === 401 || response.status === 403 || response.status === 404 || response.status === 413 || response.status === 422)
        this.handleError(reason, retryable)
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

      while (true) {
        const { value, done } = await reader.read()
        if (done) break
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

    while (true) {
      const sep = normalized.indexOf('\n\n', cursor)
      if (sep === -1) break
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
          understanding: parsed?.understanding,
        })
        this.stop()
        return
      }
      if (kind === 'error') {
        const parsed = JSON.parse(data || '{}') as { error?: string }
        this.handleError(String(parsed?.error || 'error'))
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

  private handleError(reason: string, retryable = true): void {
    this.attempt += 1
    this.errors$.next({ error: reason, attempt: this.attempt })

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
    setTimeout(() => {
      if (!url) return
      this.status$.next('connecting')
      this.open(url, projectId)
    }, wait)
  }
}
