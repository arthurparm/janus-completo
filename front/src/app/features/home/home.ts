import { ChangeDetectionStrategy, Component, DestroyRef, computed, effect, inject, signal } from '@angular/core'
import { CommonModule } from '@angular/common'
import { RouterLink } from '@angular/router'
import { FormControl, ReactiveFormsModule } from '@angular/forms'
import { forkJoin, of } from 'rxjs'
import { catchError, map } from 'rxjs/operators'
import { takeUntilDestroyed } from '@angular/core/rxjs-interop'
import { Router } from '@angular/router'

import { AuthService } from '../../core/auth/auth.service'
import {
  ConversationMeta,
  DocListItem,
  AuditEvent,
  JanusApiService,
  MemoryItem,
  MetaAgentHeartbeatStatus,
  MetaAgentReport,
  ProductivityLimitsStatusResponse,
  SystemOverviewResponse,
  Tool,
  ToolStats
} from '../../services/janus-api.service'
import { UiBadgeComponent } from '../../shared/components/ui/ui-badge/ui-badge.component'
import { UiButtonComponent } from '../../shared/components/ui/button/button.component'
import { Header } from '../../core/layout/header/header'
import { SkeletonComponent } from '../../shared/components/skeleton/skeleton.component'

interface HomeData {
  overview: SystemOverviewResponse | null
  limits: ProductivityLimitsStatusResponse | null
  conversations: ConversationMeta[]
  documents: DocListItem[]
  tools: Tool[]
  toolStats: ToolStats | null
  auditEvents: AuditEvent[]
  memory: MemoryItem[]
  metaReport: MetaAgentReport | null
  metaHeartbeat: MetaAgentHeartbeatStatus | null
}

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    ReactiveFormsModule,
    UiBadgeComponent,
    UiButtonComponent,
    Header,
    SkeletonComponent
  ],
  templateUrl: './home.html',
  styleUrls: ['./home.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class HomeComponent {
  private api = inject(JanusApiService)
  private auth = inject(AuthService)
  private destroyRef = inject(DestroyRef)
  private router = inject(Router)

  readonly prompt = new FormControl('', { nonNullable: true })
  readonly loading = signal(true)
  readonly actionLoading = signal(false)
  readonly error = signal('')
  readonly notice = signal('')
  readonly data = signal<HomeData>({
    overview: null,
    limits: null,
    conversations: [],
    documents: [],
    tools: [],
    toolStats: null,
    auditEvents: [],
    memory: [],
    metaReport: null,
    metaHeartbeat: null
  })

  readonly user = this.auth.user
  readonly suggestions = [
    'Resumir conversas recentes',
    'Buscar documentos importantes',
    'Revisar memoria ativa',
    'Criar plano de acao rapido'
  ]

  private readonly uptimeTicker = signal(Date.now())
  private autoRefreshStarted = false

  readonly displayName = computed(() => {
    const user = this.user()
    return user?.display_name || user?.username || user?.email || 'Operador'
  })

  readonly systemStatus = computed((): { status: string; label: string; env: string; variant: 'success' | 'warning' | 'error' | 'neutral' } => {
    const rawStatus = String(this.data().overview?.system_status?.status || 'unknown')
    const env = this.data().overview?.system_status?.environment || 'local'
    const normalized = rawStatus.trim().toLowerCase()
    const variant = normalized === 'ok' || normalized === 'operational' || normalized === 'healthy'
      ? 'success'
      : normalized === 'degraded' || normalized === 'warning'
        ? 'warning'
        : normalized === 'error' || normalized === 'unhealthy'
          ? 'error'
          : 'neutral'
    const label = normalized === 'operational' ? 'OPERACIONAL' : normalized === 'healthy' ? 'SAUDAVEL' : rawStatus.toUpperCase()
    return { status: rawStatus, label, env, variant }
  })

  readonly uptimeSeconds = computed(() => {
    const status = this.data().overview?.system_status
    if (!status || typeof status.uptime_seconds !== 'number') return null
    const base = status.uptime_seconds
    const ts = status.timestamp ? Date.parse(status.timestamp) : NaN
    if (!Number.isFinite(ts)) return base
    const elapsed = Math.max(0, (this.uptimeTicker() - ts) / 1000)
    return base + elapsed
  })

  readonly limitSummary = computed(() => {
    const limits = this.data().limits?.limits || {}
    const entries = Object.entries(limits)
    if (!entries.length) return null
    const [key, value] = entries[0]
    const max = value.max_per_day || 0
    const used = value.used || 0
    const infinite = max <= 0
    const remaining = infinite ? null : (value.remaining ?? Math.max(0, max - used))
    const pct = !infinite && max ? Math.min(100, Math.round((used / max) * 100)) : 0
    return { key, max, used, remaining, pct, infinite }
  })

  readonly conversations = computed(() => this.data().conversations.slice(0, 4))
  readonly documents = computed(() => this.data().documents.slice(0, 4))
  readonly tools = computed(() => this.data().tools.slice(0, 6))
  readonly memory = computed(() => this.data().memory.slice(0, 4))
  readonly metaReport = computed(() => this.data().metaReport)
  readonly metaHeartbeat = computed(() => this.data().metaHeartbeat)
  readonly metaStatus = computed(() => {
    const report = this.metaReport()
    const heartbeat = this.metaHeartbeat()
    const active = Boolean(heartbeat?.heartbeat_active)
    const raw = String(report?.overall_status || (active ? 'running' : 'idle')).toLowerCase()
    if (raw.includes('error') || raw.includes('failed') || raw.includes('dead')) {
      return { label: 'ATENCAO', variant: 'warning' as const }
    }
    if (raw.includes('completed') || raw.includes('healthy') || raw.includes('ok')) {
      return { label: 'OK', variant: 'success' as const }
    }
    if (active) return { label: 'ATIVO', variant: 'neutral' as const }
    return { label: 'INATIVO', variant: 'warning' as const }
  })
  readonly metaTasksDone = computed(() => {
    const done = this.metaReport()?.execution_results || []
    return done.slice(0, 4)
  })
  readonly metaTasksInProgress = computed(() => {
    const recs = this.metaReport()?.recommendations || []
    const doneTitles = new Set(
      (this.metaReport()?.execution_results || [])
        .map((item) => String(item?.title || '').trim())
        .filter(Boolean)
    )
    const pending = recs.filter((rec) => !doneTitles.has(String(rec.title || '').trim()))
    return pending.slice(0, 4)
  })
  readonly codexTools = computed(() => this.data().tools.filter((tool) => tool.name?.startsWith('codex_')))
  readonly codexEvents = computed(() => {
    const events = this.data().auditEvents || []
    return events
      .filter((ev) => String(ev.tool || '').startsWith('codex_'))
      .slice(0, 5)
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
  readonly codexStatus = computed(() => {
    const available = this.codexTools().length > 0
    const last = this.codexEvents()[0]
    const lastStatus = String(last?.status || '').toLowerCase()
    if (!available) return { label: 'INATIVO', variant: 'warning' as const }
    if (lastStatus === 'error' || lastStatus === 'failed') return { label: 'ATENCAO', variant: 'warning' as const }
    if (lastStatus === 'success') return { label: 'OK', variant: 'success' as const }
    return { label: 'ATIVO', variant: 'neutral' as const }
  })
  readonly codexWorker = computed(() => {
    const workers = this.data().overview?.workers_status || []
    return workers.find((worker) => String(worker.id || '').toLowerCase().includes('codex'))
  })
  readonly codexWorkerStatus = computed(() => {
    const worker = this.codexWorker()
    const status = String(worker?.status || 'unknown').toLowerCase()
    if (status === 'running') return { label: 'RUNNING', variant: 'success' as const }
    if (status === 'stopped') return { label: 'STOPPED', variant: 'warning' as const }
    if (status === 'error') return { label: 'ERROR', variant: 'error' as const }
    return { label: 'UNKNOWN', variant: 'neutral' as const }
  })

  private loadedOnce = false

  constructor() {
    effect(() => {
      if (this.auth.authReady() && !this.autoRefreshStarted) {
        this.autoRefreshStarted = true
        this.startAutoRefresh()
      }
    })

    const intervalId = setInterval(() => {
      this.uptimeTicker.set(Date.now())
    }, 1000)

    this.destroyRef.onDestroy(() => {
      clearInterval(intervalId)
    })
  }

  applySuggestion(value: string) {
    this.prompt.setValue(value)
  }

  startChat() {
    if (this.actionLoading()) return
    this.actionLoading.set(true)
    this.notice.set('')
    this.error.set('')
    const userId = this.user()?.id ? String(this.user()?.id) : undefined
    this.api.startChat(undefined, undefined, userId)
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        catchError(() => {
          this.error.set('Falha ao iniciar conversa. Tente novamente.')
          this.actionLoading.set(false)
          return of(null)
        })
      )
      .subscribe((resp) => {
        if (resp) {
          this.notice.set(`Conversa criada: ${resp.conversation_id}`)
          this.prompt.setValue('')
          this.loadHome({ silent: true })
          this.router.navigate(['/conversations', resp.conversation_id])
        }
        this.actionLoading.set(false)
      })
  }

  openConversation(conversationId: string) {
    if (!conversationId) return
    this.router.navigate(['/conversations', conversationId])
  }

  refresh() {
    this.loadHome()
  }

  formatLimitLabel(key: string) {
    if (!key) return 'Limite diario'
    return key.replace(/[_-]/g, ' ').toUpperCase()
  }

  formatUptime(seconds?: number | null): string {
    if (!seconds && seconds !== 0) return 'n/d'
    const hrs = Math.floor(seconds / 3600)
    const mins = Math.floor((seconds % 3600) / 60)
    if (hrs > 0) return `${hrs}h ${mins}m`
    return `${mins}m`
  }

  formatAuditTimestamp(ts?: number | null): string {
    if (!ts) return 'n/d'
    return new Date(ts * 1000).toLocaleString()
  }

  formatMetaTimestamp(value?: string | null): string {
    if (!value) return 'n/d'
    const dt = Date.parse(value)
    if (Number.isNaN(dt)) return 'n/d'
    return new Date(dt).toLocaleString()
  }

  private loadHome(options: { silent?: boolean } = {}) {
    const silent = Boolean(options.silent)
    if (!silent || !this.loadedOnce) {
      this.loading.set(true)
    }
    this.error.set('')

    const overview$ = this.api.getSystemOverview().pipe(
      catchError(() => this.api.getSystemStatus().pipe(
        map((system_status) => ({
          system_status,
          services_status: [],
          workers_status: []
        } as SystemOverviewResponse)),
        catchError(() => of(null))
      ))
    )
    const limits$ = this.api.getProductivityLimitsStatusSelf().pipe(catchError(() => of(null)))
    const userId = this.user()?.id ? String(this.user()?.id) : undefined
    const conversations$ = this.api.listConversations(userId ? { user_id: userId, limit: 6 } : { limit: 6 })
      .pipe(
        map((resp) => resp.conversations || []),
        catchError(() => of([]))
      )
    const documents$ = this.api.listDocuments(undefined, userId)
      .pipe(
        map((resp) => resp.items || []),
        catchError(() => of([]))
      )
    const tools$ = this.api.getTools()
      .pipe(
        map((resp) => resp.tools || []),
        catchError(() => of([]))
      )
    const toolStats$ = this.api.getToolStats()
      .pipe(catchError(() => of(null)))
    const auditEvents$ = this.api.listAuditEvents({ limit: 50 })
      .pipe(
        map((resp) => resp.events || []),
        catchError(() => of([]))
      )
    const memory$ = this.api.getMemoryTimeline({ limit: 6, user_id: userId })
      .pipe(catchError(() => of([])))
    const metaReport$ = this.api.getMetaAgentLatestReport()
      .pipe(
        map((resp) => resp.report || null),
        catchError(() => of(null))
      )
    const metaHeartbeat$ = this.api.getMetaAgentHeartbeatStatus()
      .pipe(catchError(() => of(null)))

    forkJoin({
      overview: overview$,
      limits: limits$,
      conversations: conversations$,
      documents: documents$,
      tools: tools$,
      toolStats: toolStats$,
      auditEvents: auditEvents$,
      memory: memory$,
      metaReport: metaReport$,
      metaHeartbeat: metaHeartbeat$
    })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (result) => {
          this.data.set({
            overview: result.overview,
            limits: result.limits,
            conversations: result.conversations,
            documents: result.documents,
            tools: result.tools,
            toolStats: result.toolStats,
            auditEvents: result.auditEvents,
            memory: result.memory,
            metaReport: result.metaReport,
            metaHeartbeat: result.metaHeartbeat
          })
          this.loadedOnce = true
          this.loading.set(false)
        },
        error: () => {
          this.error.set('Falha ao carregar a home. Tente novamente.')
          this.loading.set(false)
        }
      })
  }

  private startAutoRefresh() {
    this.loadHome()
    const refreshInterval = setInterval(() => {
      this.loadHome({ silent: true })
    }, 20000)
    this.destroyRef.onDestroy(() => {
      clearInterval(refreshInterval)
    })
  }
}
