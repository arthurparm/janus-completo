import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core'
import { CommonModule } from '@angular/common'
import { ActivatedRoute, RouterLink } from '@angular/router'
import { forkJoin, of } from 'rxjs'
import { catchError, map } from 'rxjs/operators'
import { takeUntilDestroyed } from '@angular/core/rxjs-interop'

import { BackendApiService } from '../../services/backend-api.service'
import {
  AuditEvent,
  PendingAction,
  PendingActionLegacyResidueSummary,
  Tool,
  ToolStats,
  GoogleConnectionStatusResponse
} from '../../models'
import { UiBadgeComponent } from '../../shared/components/ui/ui-badge/ui-badge.component'
import { UiButtonComponent } from '../../shared/components/ui/button/button.component'
import { UiTableComponent } from '../../shared/components/ui/ui-table/ui-table.component'
import { Header } from '../../core/layout/header/header'
import { AuthService } from '../../core/auth/auth.service'
import { SkeletonComponent } from '../../shared/components/skeleton/skeleton.component'

interface ToolsData {
  tools: Tool[]
  toolStats: ToolStats | null
  auditEvents: AuditEvent[]
  pendingActions: PendingAction[]
  legacyResidue: PendingActionLegacyResidueSummary | null
}

@Component({
  selector: 'app-tools',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    UiBadgeComponent,
    UiButtonComponent,
    UiTableComponent,
    Header,
    SkeletonComponent
  ],
  templateUrl: './tools.html',
  styleUrls: ['./tools.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ToolsComponent {
  private api = inject(BackendApiService)
  private auth = inject(AuthService)
  private destroyRef = inject(DestroyRef)
  private route = inject(ActivatedRoute)

  readonly loading = signal(true)
  readonly actionLoading = signal(false)
  readonly error = signal('')
  readonly loadFailures = signal<string[]>([])
  readonly success = signal('')
  readonly googleStatus = signal<GoogleConnectionStatusResponse | null>(null)
  readonly googleStatusLoading = signal(true)
  readonly googleError = signal('')
  readonly googleAction = signal<'calendar' | 'mail' | 'disconnect' | null>(null)
  readonly confirmGoogleDisconnect = signal(false)
  readonly riskFilter = signal<'all' | 'high' | 'medium' | 'low'>('all')
  readonly sourceFilter = signal<'all' | 'sql' | 'langgraph'>('all')
  readonly queryFilter = signal('')
  readonly isAdmin = this.auth.isAdmin
  readonly data = signal<ToolsData>({
    tools: [],
    toolStats: null,
    auditEvents: [],
    pendingActions: [],
    legacyResidue: null
  })

  readonly criticalAuditEvents = computed(() => {
    const events = this.data().auditEvents || []
    return events
      .filter((event) => {
        const endpoint = String(event.endpoint || '').toLowerCase()
        const tool = String(event.tool || '').toLowerCase()
        return (
          tool === 'pending_actions' ||
          endpoint.startsWith('chat_event:') ||
          endpoint.startsWith('/api/v1/pending_actions')
        )
      })
      .slice(0, 12)
  })
  readonly pendingCount = computed(() => this.data().pendingActions.length)
  readonly legacyResidueSummary = computed(() => this.data().legacyResidue)
  readonly hasLegacyPendingResidue = computed(
    () => (this.legacyResidueSummary()?.total_without_owner || 0) > 0
  )
  readonly pendingRiskSummary = computed(() => {
    const actions = this.data().pendingActions || []
    let high = 0
    let medium = 0
    let low = 0
    for (const action of actions) {
      const risk = String(action.risk_level || '').toLowerCase()
      if (risk === 'high') high += 1
      else if (risk === 'medium') medium += 1
      else low += 1
    }
    return { total: actions.length, high, medium, low }
  })
  readonly hasPendingFilters = computed(
    () => this.riskFilter() !== 'all' || this.sourceFilter() !== 'all' || !!this.queryFilter().trim()
  )
  readonly pendingActionsFiltered = computed(() => {
    const riskFilter = this.riskFilter()
    const sourceFilter = this.sourceFilter()
    const query = this.queryFilter().trim().toLowerCase()

    const riskRank = (action: PendingAction): number => {
      const risk = String(action.risk_level || '').toLowerCase()
      if (risk === 'high') return 3
      if (risk === 'medium') return 2
      if (risk === 'low') return 1
      return 0
    }
    const actionTime = (action: PendingAction): number => {
      const raw = String(action.created_at || '').trim()
      const ts = raw ? Date.parse(raw) : 0
      return Number.isFinite(ts) ? ts : 0
    }

    const filtered = (this.data().pendingActions || []).filter((action) => {
      const risk = String(action.risk_level || '').toLowerCase()
      const source = String(action.source || '').toLowerCase()
      if (riskFilter !== 'all' && risk !== riskFilter) return false
      if (sourceFilter !== 'all' && source !== sourceFilter) return false
      if (!query) return true

      const haystack = [
        action.tool_name,
        action.user_id,
        action.message,
        action.args_json,
        action.thread_id,
        typeof action.action_id === 'number' ? String(action.action_id) : ''
      ]
        .map((value) => String(value || '').toLowerCase())
        .join(' ')

      return haystack.includes(query)
    })

    return filtered.sort((a, b) => {
      const riskDiff = riskRank(b) - riskRank(a)
      if (riskDiff !== 0) return riskDiff
      return actionTime(b) - actionTime(a)
    })
  })

  constructor() {
    this.refresh()
    const oauthResult = this.route.snapshot.queryParamMap.get('google_oauth')
    if (oauthResult === 'connected') {
      this.success.set('Integração Google salva. O acesso será validado no primeiro uso.')
    } else if (oauthResult === 'error') {
      this.googleError.set(
        this.route.snapshot.queryParamMap.get('message') ||
        'Não foi possível concluir a integração com o Google.'
      )
    }
  }

  refresh() {
    this.loading.set(true)
    this.error.set('')
    this.loadFailures.set([])
    this.loadGoogleStatus()

    const tools$ = this.api.tools.getTools()
      .pipe(
        map((resp) => resp.tools || []),
        catchError(() => {
          this.recordLoadFailure('catálogo de ferramentas')
          return of([])
        })
      )
    const toolStats$ = this.api.tools.getToolStats()
      .pipe(catchError(() => {
        this.recordLoadFailure('métricas de ferramentas')
        return of(null)
      }))
    const auditEvents$ = this.api.observability.listAuditEvents({ limit: 100 })
      .pipe(
        map((resp) => resp.events || []),
        catchError(() => {
          this.recordLoadFailure('trilha de auditoria')
          return of([])
        })
      )
    const pendingActions$ = this.api.observability.listPendingActions({ include_sql: true, include_graph: false })
      .pipe(catchError(() => {
        this.recordLoadFailure('aprovações pendentes')
        return of([])
      }))
    const legacyResidue$ = this.isAdmin()
      ? this.api.observability.getPendingActionsLegacyResidue(10).pipe(catchError(() => {
          this.recordLoadFailure('passivo histórico')
          return of(null)
        }))
      : of(null)

    forkJoin({
      tools: tools$,
      toolStats: toolStats$,
      auditEvents: auditEvents$,
      pendingActions: pendingActions$,
      legacyResidue: legacyResidue$
    })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (result) => {
          this.data.set(result)
          this.loading.set(false)
        },
        error: (err) => {
          this.error.set(this.extractApiErrorMessage(err, 'Falha ao carregar dados de ferramentas.'))
          this.loading.set(false)
        }
      })
  }

  private recordLoadFailure(source: string) {
    this.loadFailures.update((current) =>
      current.includes(source) ? current : [...current, source]
    )
    this.error.set(
      `Dados parciais: falha ao carregar ${this.loadFailures().join(', ')}. Os valores vazios dessas seções não foram confirmados pelo backend.`
    )
  }

  loadGoogleStatus() {
    this.googleStatusLoading.set(true)
    this.googleError.set('')
    this.api.productivity.googleOAuthStatus()
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        catchError((err) => {
          this.googleError.set(
            this.extractApiErrorMessage(err, 'Falha ao consultar a integração Google.')
          )
          return of(null)
        })
      )
      .subscribe((result) => {
        this.googleStatus.set(result)
        this.googleStatusLoading.set(false)
      })
  }

  connectGoogle(scope: 'calendar' | 'mail') {
    if (this.googleAction()) return
    this.googleAction.set(scope)
    this.googleError.set('')
    this.api.productivity.googleOAuthStart(scope)
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        catchError((err) => {
          this.googleError.set(
            this.extractApiErrorMessage(err, 'Falha ao iniciar a autorização Google.')
          )
          this.googleAction.set(null)
          return of(null)
        })
      )
      .subscribe((result) => {
        if (!result) return
        if (!this.isTrustedGoogleAuthorizationUrl(result.authorize_url)) {
          this.googleError.set('O backend retornou uma URL de autorização Google inválida.')
          this.googleAction.set(null)
          return
        }
        window.location.assign(result.authorize_url)
      })
  }

  requestGoogleDisconnect() {
    if (!this.googleAction()) this.confirmGoogleDisconnect.set(true)
  }

  cancelGoogleDisconnect() {
    this.confirmGoogleDisconnect.set(false)
  }

  disconnectGoogle() {
    if (this.googleAction()) return
    this.googleAction.set('disconnect')
    this.googleError.set('')
    this.api.productivity.googleOAuthDisconnect()
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        catchError((err) => {
          this.googleError.set(
            this.extractApiErrorMessage(err, 'Falha ao desconectar a integração Google.')
          )
          this.googleAction.set(null)
          return of(null)
        })
      )
      .subscribe((result) => {
        if (!result) return
        this.confirmGoogleDisconnect.set(false)
        this.googleAction.set(null)
        this.success.set(
          result.retry_required
            ? 'Acesso local bloqueado. A revogação no Google está pendente; tente desconectar novamente.'
            : 'Integração Google desconectada.'
        )
        this.loadGoogleStatus()
      })
  }

  googleStatusLabel(): string {
    const status = this.googleStatus()?.local_status
    if (status === 'configured') return 'Configuração local ativa'
    if (status === 'inconsistent') return 'Acesso local bloqueado ou incompleto'
    return 'Desconectado'
  }

  private isTrustedGoogleAuthorizationUrl(rawUrl: string): boolean {
    try {
      const url = new URL(rawUrl)
      return url.protocol === 'https:' && url.hostname === 'accounts.google.com'
    } catch {
      return false
    }
  }

  setRiskFilter(value: 'all' | 'high' | 'medium' | 'low') {
    this.riskFilter.set(value)
  }

  setSourceFilter(value: 'all' | 'sql' | 'langgraph') {
    this.sourceFilter.set(value)
  }

  setQueryFilter(value: string) {
    this.queryFilter.set(String(value || ''))
  }

  clearPendingFilters() {
    this.riskFilter.set('all')
    this.sourceFilter.set('all')
    this.queryFilter.set('')
  }

  approve(action: PendingAction) {
    if (!action || this.actionLoading()) return
    this.actionLoading.set(true)
    this.api.observability.approvePendingAction(action)
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        catchError((err) => {
          this.error.set(this.extractApiErrorMessage(err, 'Falha ao aprovar a acao.'))
          this.actionLoading.set(false)
          return of(null)
        })
      )
      .subscribe((resp) => {
        if (resp) {
          this.success.set('Acao aprovada com sucesso. Veja a trilha de auditoria abaixo.')
        }
        this.actionLoading.set(false)
        this.refresh()
      })
  }

  reject(action: PendingAction) {
    if (!action || this.actionLoading()) return
    this.actionLoading.set(true)
    this.api.observability.rejectPendingAction(action)
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        catchError((err) => {
          this.error.set(this.extractApiErrorMessage(err, 'Falha ao rejeitar a acao.'))
          this.actionLoading.set(false)
          return of(null)
        })
      )
      .subscribe((resp) => {
        if (resp) {
          this.success.set('Acao rejeitada com sucesso. Veja a trilha de auditoria abaixo.')
        }
        this.actionLoading.set(false)
        this.refresh()
      })
  }

  formatAuditTimestamp(ts?: number | null): string {
    if (!ts) return 'n/d'
    return new Date(ts * 1000).toLocaleString()
  }

  formatToolTags(tags?: string[]) {
    if (!tags || !tags.length) return '—'
    return tags.join(', ')
  }

  auditActionLabel(event: AuditEvent): string {
    const action = String(event.action || '').trim()
    if (action) return action
    const endpoint = String(event.endpoint || '').trim()
    return endpoint || 'n/d'
  }

  auditEndpointLabel(event: AuditEvent): string {
    const endpoint = String(event.endpoint || '').trim()
    return endpoint || 'n/d'
  }

  auditTraceLabel(event: AuditEvent): string {
    const traceId = String(event.trace_id || '').trim()
    if (!traceId) return 'n/d'
    if (traceId.length <= 16) return traceId
    return `${traceId.slice(0, 8)}...${traceId.slice(-8)}`
  }

  riskVariant(action: PendingAction): 'error' | 'warning' | 'success' | 'neutral' {
    const level = String(action.risk_level || '').toLowerCase()
    if (level === 'high') return 'error'
    if (level === 'medium') return 'warning'
    if (level === 'low') return 'success'
    return 'neutral'
  }

  riskLabel(action: PendingAction): string {
    const level = String(action.risk_level || '').toLowerCase()
    if (level === 'high') return 'Risco alto'
    if (level === 'medium') return 'Risco medio'
    if (level === 'low') return 'Risco baixo'
    return 'Risco n/d'
  }

  argsPreview(action: PendingAction): string {
    const raw = String(action.args_json || '').trim()
    if (!raw) return ''
    if (raw.length <= 180) return raw
    return `${raw.slice(0, 177)}...`
  }

  legacyResidueItemLabel(index: number): string {
    const item = this.legacyResidueSummary()?.items?.[index]
    if (!item) return 'n/d'
    const actionId = typeof item.action_id === 'number' ? `#${item.action_id}` : '#n/d'
    const toolName = String(item.tool_name || 'tool n/d').trim()
    const conversationId = String(item.conversation_id || 'sem conversation_id').trim()
    return `${actionId} · ${toolName} · ${conversationId}`
  }

  sourceLabel(action: PendingAction): string {
    const source = String(action.source || '').toLowerCase()
    if (source === 'sql') return 'SQL'
    if (source === 'langgraph') return 'LangGraph'
    return 'Origem n/d'
  }

  private extractApiErrorMessage(err: unknown, fallback: string): string {
    const body = (err as any)?.error
    const detailValue = body?.detail
    const detail = typeof detailValue === 'string'
      ? detailValue
      : typeof detailValue?.message === 'string'
        ? detailValue.message
        : ''
    const code = typeof detailValue?.code === 'string'
      ? detailValue.code
      : body?.error_code
        ? String(body.error_code)
        : ''
    if (code && detail) return `${fallback} [${code}] ${detail}`
    if (code) return `${fallback} [${code}]`
    if (detail) return `${fallback} ${detail}`
    return fallback
  }
}
