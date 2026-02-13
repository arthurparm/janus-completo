import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core'
import { CommonModule } from '@angular/common'
import { RouterLink } from '@angular/router'
import { forkJoin, of } from 'rxjs'
import { catchError, map } from 'rxjs/operators'
import { takeUntilDestroyed } from '@angular/core/rxjs-interop'

import {
  AuditEvent,
  JanusApiService,
  PendingAction,
  Tool,
  ToolStats
} from '../../services/janus-api.service'
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
  private api = inject(JanusApiService)
  private auth = inject(AuthService)
  private destroyRef = inject(DestroyRef)

  readonly loading = signal(true)
  readonly actionLoading = signal(false)
  readonly error = signal('')
  readonly success = signal('')
  readonly riskFilter = signal<'all' | 'high' | 'medium' | 'low'>('all')
  readonly sourceFilter = signal<'all' | 'sql' | 'langgraph'>('all')
  readonly queryFilter = signal('')
  readonly isAdmin = this.auth.isAdmin
  readonly data = signal<ToolsData>({
    tools: [],
    toolStats: null,
    auditEvents: [],
    pendingActions: []
  })

  readonly codexTools = computed(() => this.data().tools.filter((tool) => tool.name?.startsWith('codex_')))
  readonly codexEvents = computed(() => {
    const events = this.data().auditEvents || []
    return events.filter((ev) => String(ev.tool || '').startsWith('codex_')).slice(0, 12)
  })
  readonly codexUsage = computed(() => {
    const usage = this.data().toolStats?.tool_usage || {}
    const entries = Object.entries(usage).filter(([name]) => name.startsWith('codex_'))
    const total = entries.reduce((sum, [, stats]) => sum + (stats?.total || 0), 0)
    const success = entries.reduce((sum, [, stats]) => sum + (stats?.success || 0), 0)
    const avgDuration = entries.length
      ? Math.round(entries.reduce((sum, [, stats]) => sum + (stats?.avg_duration || 0), 0) / entries.length * 1000)
      : 0
    const successRate = total > 0 ? Math.round((success / total) * 100) : 0
    return { total, success, successRate, avgDuration }
  })
  readonly pendingCount = computed(() => this.data().pendingActions.length)
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
  }

  refresh() {
    this.loading.set(true)
    this.error.set('')

    const tools$ = this.api.getTools()
      .pipe(
        map((resp) => resp.tools || []),
        catchError(() => of([]))
      )
    const toolStats$ = this.api.getToolStats()
      .pipe(catchError(() => of(null)))
    const auditEvents$ = this.api.listAuditEvents({ limit: 100 })
      .pipe(
        map((resp) => resp.events || []),
        catchError(() => of([]))
      )
    const pendingActions$ = this.api.listPendingActions({ include_sql: true, include_graph: false })
      .pipe(catchError(() => of([])))

    forkJoin({
      tools: tools$,
      toolStats: toolStats$,
      auditEvents: auditEvents$,
      pendingActions: pendingActions$
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
    this.api.approvePendingAction(action)
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
    this.api.rejectPendingAction(action)
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

  sourceLabel(action: PendingAction): string {
    const source = String(action.source || '').toLowerCase()
    if (source === 'sql') return 'SQL'
    if (source === 'langgraph') return 'LangGraph'
    return 'Origem n/d'
  }

  private extractApiErrorMessage(err: unknown, fallback: string): string {
    const body = (err as any)?.error
    const detail = body?.detail ? String(body.detail) : ''
    const code = body?.error_code ? String(body.error_code) : ''
    if (code && detail) return `${fallback} [${code}] ${detail}`
    if (code) return `${fallback} [${code}]`
    if (detail) return `${fallback} ${detail}`
    return fallback
  }
}
