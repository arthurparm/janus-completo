import { Injectable } from '@angular/core'
import { BehaviorSubject, Observable, Subject } from 'rxjs'
import { API_BASE_URL, SSE_RETRY_MAX_SECONDS } from './api.config'

type StreamStatus = 'idle' | 'connecting' | 'open' | 'streaming' | 'retrying' | 'closed' | 'error'

export interface StreamDone { conversation_id?: string; provider?: string; model?: string; citations?: any[] }
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
    this.open(url)
  }

  stop(): void {
    if (this.es) { this.es.close(); this.es = undefined }
    this.status$.next('closed')
    this.typing$.next(false)
  }

  private open(url: string): void {
    this.lastUrl = url
    this.es = new EventSource(url)
    this.es.onopen = () => { this.status$.next('open') }
    this.es.onerror = () => { this.handleError('connection_error') }
    this.es.onmessage = (ev) => { this.handleMessage('message', ev.data) }
    this.es.addEventListener('start', () => { this.status$.next('open') })
    this.es.addEventListener('ack', (ev: MessageEvent) => { this.handleMessage('ack', ev.data) })
    this.es.addEventListener('partial', (ev: MessageEvent) => { this.handleMessage('partial', ev.data) })
    this.es.addEventListener('done', (ev: MessageEvent) => { this.handleMessage('done', ev.data) })
    this.es.addEventListener('error', (ev: MessageEvent) => { this.handleMessage('error', ev.data) })
    this.es.addEventListener('heartbeat', (ev: MessageEvent) => { /* keep-alive noop */ })
    this.es.addEventListener('protocol', (ev: MessageEvent) => { /* future: inspect version */ })
  }

  private handleMessage(kind: string, data: any): void {
    try {
      if (kind === 'partial') {
        this.status$.next('streaming')
        this.typing$.next(true)
        const parsed = JSON.parse(String(data || '{}'))
        if (!this.ttftCaptured) { this.ttftCaptured = true }
        this.partials$.next({ text: String(parsed?.text || '') })
        return
      }
      if (kind === 'done') {
        this.typing$.next(false)
        const parsed = JSON.parse(String(data || '{}'))
        this.done$.next({ conversation_id: parsed?.conversation_id, provider: parsed?.provider, model: parsed?.model, citations: parsed?.citations })
        this.stop()
        return
      }
      if (kind === 'error') {
        const parsed = JSON.parse(String(data || '{}'))
        this.handleError(String(parsed?.error || 'error'))
        return
      }
      if (kind === 'ack') {
        return
      }
    } catch (e) {
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
