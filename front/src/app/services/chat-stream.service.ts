import { Injectable } from '@angular/core'
import { BehaviorSubject, Observable, Subject } from 'rxjs'
import { API_BASE_URL, SSE_RETRY_MAX_SECONDS } from './api.config'
import { Citation } from './janus-api.service'

type StreamStatus = 'idle' | 'connecting' | 'open' | 'streaming' | 'retrying' | 'closed' | 'error'

export interface StreamDone { conversation_id?: string; provider?: string; model?: string; citations?: Citation[] }
export interface StreamError { error: string; attempt: number }
export interface StartParams { conversationId: string; text: string; role?: string; priority?: string; timeoutSeconds?: number }

@Injectable({ providedIn: 'root' })
export class ChatStreamService {
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

  status(): Observable<StreamStatus> { return this.status$.asObservable() }
  typing(): Observable<boolean> { return this.typing$.asObservable() }
  partials(): Observable<{ text: string }> { return this.partials$.asObservable() }
  done(): Observable<StreamDone> { return this.done$.asObservable() }
  errors(): Observable<StreamError> { return this.errors$.asObservable() }

  start(params: StartParams): void {
    console.log('[ChatStreamService] Iniciando stream com params:', params)
    this.stop()
    this.status$.next('connecting')
    this.typing$.next(false)
    this.attempt = 0
    this.startTs = Date.now()
    this.ttftCaptured = false
    const role = params.role || 'orchestrator'
    const priority = params.priority || 'fast_and_cheap'
    const qs = new URLSearchParams({
      message: params.text,
      role,
      priority,
    })
    if (typeof params.timeoutSeconds !== 'undefined') qs.set('timeout_seconds', String(params.timeoutSeconds))
    const url = `${API_BASE_URL}/v1/chat/stream/${encodeURIComponent(params.conversationId)}?${qs.toString()}`
    console.log('[ChatStreamService] URL construída:', url)
    this.open(url)
  }

  stop(): void {
    if (this.es) { this.es.close(); this.es = undefined }
    this.status$.next('closed')
    this.typing$.next(false)
  }

  private open(url: string): void {
    this.lastUrl = url;    console.log('[ChatStreamService] Abrindo EventSource para URL:', url)
    this.es = new EventSource(url)

    this.es.onopen = () => {
      console.log('[ChatStreamService] EventSource conectado com sucesso')
      this.status$.next('open')
    }

    this.es.onerror = (error) => {
      console.error('[ChatStreamService] EventSource erro:', error)
      this.handleError('connection_error')
    }

    this.es.onmessage = (ev) => {
      console.log('[ChatStreamService] Mensagem recebida:', ev.data)
      this.handleMessage('message', ev.data)
    }

    this.es.addEventListener('start', () => {
      console.log('[ChatStreamService] Evento start recebido')
      this.status$.next('open')
    })

    this.es.addEventListener('ack', (ev: MessageEvent) => {
      console.log('[ChatStreamService] Evento ack recebido:', ev.data)
      this.handleMessage('ack', ev.data)
    })

    this.es.addEventListener('partial', (ev: MessageEvent) => {
      console.log('[ChatStreamService] Evento partial recebido:', ev.data)
      this.handleMessage('partial', ev.data)
    })

    this.es.addEventListener('token', (ev: MessageEvent) => {
      console.log('[ChatStreamService] Evento token recebido:', ev.data)
      this.handleMessage('partial', ev.data)
    })

    this.es.addEventListener('done', (ev: MessageEvent) => {
      console.log('[ChatStreamService] Evento done recebido:', ev.data)
      this.handleMessage('done', ev.data)
    })

    this.es.addEventListener('error', (ev: MessageEvent) => {
      console.error('[ChatStreamService] Evento error recebido:', ev.data)
      this.handleMessage('error', ev.data)
    })

    this.es.addEventListener('heartbeat', (ev: MessageEvent) => {
      console.log('[ChatStreamService] Heartbeat recebido')
      /* keep-alive noop */
    })

    this.es.addEventListener('protocol', (ev: MessageEvent) => {
      console.log('[ChatStreamService] Evento protocol recebido:', ev.data)
      /* future: inspect version */
    })

    // Adicionar listener genérico para debug
    this.es.addEventListener('message', (ev: MessageEvent) => {
      console.log('[ChatStreamService] Mensagem genérica recebida:', ev.type, ev.data)
    })

    // Listener para qualquer mensagem que não tenha event type específico
    this.es.onmessage = (ev) => {
      console.log('[ChatStreamService] onmessage chamado:', ev.data)
    }

    console.log('[ChatStreamService] EventSource configurado com listeners')

    // Timeout para verificar se está recebendo dados
    setTimeout(() => {
      console.log('[ChatStreamService] Status após 5 segundos:', this.status$.value)
      console.log('[ChatStreamService] EventSource prontoState:', this.es?.readyState)
    }, 5000)
  }

  private handleMessage(kind: string, data: string): void {
    console.log('[ChatStreamService] Processando mensagem tipo:', kind, 'dados:', data)
    try {
      if (kind === 'partial') {
        console.log('[ChatStreamService] Processando partial message')
        this.status$.next('streaming')
        this.typing$.next(true)
        const parsed = JSON.parse(data || '{}') as { text?: string }
        console.log('[ChatStreamService] Partial parsed:', parsed)
        if (!this.ttftCaptured) { this.ttftCaptured = true }
        const text = String(parsed?.text || '')
        console.log('[ChatStreamService] Enviando partial text:', text)
        this.partials$.next({ text: text })
        return
      }
      if (kind === 'done') {
        console.log('[ChatStreamService] Processando done message')
        this.typing$.next(false)
        const parsed = JSON.parse(data || '{}') as { conversation_id?: string; provider?: string; model?: string; citations?: Citation[] }
        console.log('[ChatStreamService] Done parsed:', parsed)
        this.done$.next({ conversation_id: parsed?.conversation_id, provider: parsed?.provider, model: parsed?.model, citations: parsed?.citations })
        this.stop()
        return
      }
      if (kind === 'error') {
        console.log('[ChatStreamService] Processando error message')
        const parsed = JSON.parse(data || '{}') as { error?: string }
        this.handleError(String(parsed?.error || 'error'))
        return
      }
      if (kind === 'ack') {
        console.log('[ChatStreamService] Processando ack message')
        return
      }
      console.log('[ChatStreamService] Tipo de mensagem não reconhecido:', kind)
    } catch (e) {
      console.error('[ChatStreamService] Erro ao processar mensagem:', e)
      this.handleError('parse_error')
    }
  }

  private handleError(reason: string): void {
    this.status$.next('error')
    this.typing$.next(false)
    this.attempt += 1
    this.errors$.next({ error: reason, attempt: this.attempt })
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
