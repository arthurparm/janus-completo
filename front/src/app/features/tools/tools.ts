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
  private destroyRef = inject(DestroyRef)

  readonly loading = signal(true)
  readonly actionLoading = signal(false)
  readonly error = signal('')
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
        error: () => {
          this.error.set('Falha ao carregar dados de ferramentas.')
          this.loading.set(false)
        }
      })
  }

  approve(action: PendingAction) {
    if (!action || this.actionLoading()) return
    this.actionLoading.set(true)
    this.api.approvePendingAction(action)
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        catchError(() => {
          this.error.set('Falha ao aprovar a ação.')
          this.actionLoading.set(false)
          return of(null)
        })
      )
      .subscribe(() => {
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
        catchError(() => {
          this.error.set('Falha ao rejeitar a ação.')
          this.actionLoading.set(false)
          return of(null)
        })
      )
      .subscribe(() => {
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
}
