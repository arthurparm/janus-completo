import { Injectable, inject } from '@angular/core'
import { BehaviorSubject, Observable, Subject } from 'rxjs'
import { API_BASE_URL, SSE_MAX_RETRIES, SSE_RETRY_MAX_SECONDS } from './api.config'
import { ChatUnderstanding, Citation } from './backend-api.service'
import { AppLoggerService } from '../core/services/app-logger.service'

type StreamStatus = 'idle' | 'connecting' | 'open' | 'streaming' | 'retrying' | 'closed' | 'error'

export interface StreamDone {
  conversation_id?: string;
  provider?: string;
  model?: string;
  citations?: Citation[];
  understanding?: ChatUnderstanding;
}
export interface StreamError { error: string; attempt: number }
export interface StartParams { conversationId: string; text: string; role?: string; priority?: string; timeoutSeconds?: number }

@Injectable({ providedIn: 'root' })
export class ChatStreamService {
  private readonly logger = inject(AppLoggerService)
  private es?: EventSource
  private lastUrl?: string
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
    const role = params.role || 'orchestrator'
    const priority = params.priority || 'fast_and_cheap'
    const qs = new URLSearchParams({
      message: params.text,
      role,
      priority,
    })
    if (typeof params.timeoutSeconds !== 'undefined') qs.set('timeout_seconds', String(params.timeoutSeconds))
    const url = `${API_BASE_URL}/v1/chat/stream/${encodeURIComponent(params.conversationId)}?${qs.toString()}`
    this.logger.debug('[ChatStreamService] URL construída', { url })
    this.open(url)
  }

  stop(): void {
    if (this.es) { this.es.close(); this.es = undefined }
    this.status$.next('closed')
    this.typing$.next(false)
  }

  private open(url: string): void {
    this.lastUrl = url
    this.logger.debug('[ChatStreamService] Abrindo EventSource', { url })
    this.es = new EventSource(url)

    this.es.onopen = () => {
      this.logger.info('[ChatStreamService] EventSource conectado com sucesso')
      this.status$.next('open')
    }

    this.es.onerror = (error) => {
      this.logger.error('[ChatStreamService] EventSource erro', error)
      this.handleError('connection_error')
    }

    this.es.onmessage = (ev) => {
      this.logger.debug('[ChatStreamService] Mensagem recebida', { data: ev.data })
      this.handleMessage('message', ev.data)
    }

    this.es.addEventListener('start', () => {
      this.logger.debug('[ChatStreamService] Evento start recebido')
      this.status$.next('open')
    })

    this.es.addEventListener('ack', (ev: MessageEvent) => {
      this.logger.debug('[ChatStreamService] Evento ack recebido', { data: ev.data })
      this.handleMessage('ack', ev.data)
    })

    this.es.addEventListener('partial', (ev: MessageEvent) => {
      this.logger.debug('[ChatStreamService] Evento partial recebido', { data: ev.data })
      this.handleMessage('partial', ev.data)
    })

    this.es.addEventListener('token', (ev: MessageEvent) => {
      this.logger.debug('[ChatStreamService] Evento token recebido', { data: ev.data })
      this.handleMessage('token', ev.data)
    })

    this.es.addEventListener('done', (ev: MessageEvent) => {
      this.logger.debug('[ChatStreamService] Evento done recebido', { data: ev.data })
      this.handleMessage('done', ev.data)
    })

    this.es.addEventListener('error', (ev: MessageEvent) => {
      this.logger.error('[ChatStreamService] Evento error recebido', { data: ev.data })
      this.handleMessage('error', ev.data)
    })

    this.es.addEventListener('heartbeat', (_ev: MessageEvent) => {
      this.logger.debug('[ChatStreamService] Heartbeat recebido')
      /* keep-alive noop */
    })

    this.es.addEventListener('protocol', (ev: MessageEvent) => {
      this.logger.debug('[ChatStreamService] Evento protocol recebido', { data: ev.data })
      /* future: inspect version */
    })

    this.es.addEventListener('message', (ev: MessageEvent) => {
      this.logger.debug('[ChatStreamService] Mensagem genérica recebida', { type: ev.type, data: ev.data })
    })

    this.logger.debug('[ChatStreamService] EventSource configurado com listeners')

    setTimeout(() => {
      this.logger.debug('[ChatStreamService] Status após 5 segundos', {
        status: this.status$.value,
        readyState: this.es?.readyState,
      })
    }, 5000)
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
        this.logger.debug('[ChatStreamService] Processando partial message')
        this.status$.next('streaming')
        this.typing$.next(true)
        const parsed = JSON.parse(data || '{}') as { text?: string }
        this.logger.debug('[ChatStreamService] Partial parsed', parsed)
        if (!this.ttftCaptured) { this.ttftCaptured = true }
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
        this.logger.debug('[ChatStreamService] Enviando partial text', { text })
        this.partials$.next({ text })
        return
      }
      if (kind === 'done') {
        this.logger.debug('[ChatStreamService] Processando done message')
        this.typing$.next(false)
        const parsed = JSON.parse(data || '{}') as {
          conversation_id?: string;
          provider?: string;
          model?: string;
          citations?: Citation[];
          understanding?: ChatUnderstanding;
        }
        this.logger.debug('[ChatStreamService] Done parsed', parsed)
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
        this.logger.debug('[ChatStreamService] Processando error message')
        const parsed = JSON.parse(data || '{}') as { error?: string }
        this.handleError(String(parsed?.error || 'error'))
        return
      }
      if (kind === 'ack') {
        this.logger.debug('[ChatStreamService] Processando ack message')
        return
      }
      this.logger.warn('[ChatStreamService] Tipo de mensagem não reconhecido', { kind })
    } catch (e) {
      this.logger.error('[ChatStreamService] Erro ao processar mensagem', e)
      this.handleError('parse_error')
    }
  }

  private handleError(reason: string): void {
    this.attempt += 1
    this.errors$.next({ error: reason, attempt: this.attempt })
    if (this.attempt >= Math.max(1, SSE_MAX_RETRIES)) {
      this.status$.next('error')
      this.typing$.next(false)
      const es = this.es
      if (es) { es.close(); this.es = undefined }
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
    const es = this.es
    if (es) { es.close(); this.es = undefined }
    const url = this.lastUrl
    setTimeout(() => {
      if (!url) return
      this.status$.next('connecting')
      this.open(url)
    }, wait)
  }
}
