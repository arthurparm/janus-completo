import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core'
import { CommonModule } from '@angular/common'
import { catchError, finalize, of } from 'rxjs'
import { takeUntilDestroyed } from '@angular/core/rxjs-interop'

import {
  AdminBacklogSprintType,
  AdminCodeQaResponse,
  BackendApiService,
  Citation,
  SelfStudyRun,
  SelfStudyStatusResponse
} from '../../../services/backend-api.service'
import { Header } from '../../../core/layout/header/header'
import { UiBadgeComponent } from '../../../shared/components/ui/ui-badge/ui-badge.component'
import { UiButtonComponent } from '../../../shared/components/ui/button/button.component'

@Component({
  selector: 'app-admin-autonomia',
  standalone: true,
  imports: [CommonModule, Header, UiBadgeComponent, UiButtonComponent],
  templateUrl: './admin-autonomia.html',
  styleUrls: ['./admin-autonomia.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class AdminAutonomiaComponent {
  private readonly api = inject(BackendApiService)
  private readonly destroyRef = inject(DestroyRef)
  private selfStudyPollTimer: ReturnType<typeof setInterval> | null = null
  private readonly selfStudyPollIntervalMs = 1500

  readonly loading = signal(true)
  readonly syncing = signal(false)
  readonly runningStudy = signal(false)
  readonly asking = signal(false)
  readonly error = signal('')
  readonly notice = signal('')

  readonly board = signal<AdminBacklogSprintType[]>([])
  readonly selfStudyStatus = signal<SelfStudyStatusResponse | null>(null)
  readonly selfStudyRuns = signal<SelfStudyRun[]>([])

  readonly question = signal('')
  readonly answer = signal('')
  readonly citations = signal<Citation[]>([])
  readonly selfMemory = signal<Array<{ file_path?: string; summary?: string; updated_at?: string | number }>>([])

  readonly totalTasks = computed(() =>
    this.board().reduce(
      (acc, type) => acc + type.sprints.reduce((inner, sprint) => inner + (sprint.tasks?.length || 0), 0),
      0
    )
  )

  constructor() {
    this.destroyRef.onDestroy(() => this.stopSelfStudyPolling())
    this.refreshAll()
  }

  refreshAll() {
    this.loading.set(true)
    this.error.set('')
    this.notice.set('')
    this.refreshBoard()
    this.refreshSelfStudy()
  }

  refreshBoard() {
    this.api.getAutonomyAdminBoard({ limit: 400 })
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        catchError((err) => {
          this.error.set(this.extractErrorMessage(err, 'Falha ao carregar board de backlog.'))
          return of({ items: [] as AdminBacklogSprintType[] })
        }),
        finalize(() => this.loading.set(false))
      )
      .subscribe((resp) => this.board.set(resp.items || []))
  }

  refreshSelfStudy() {
    this.refreshSelfStudyStatus()
    this.api.listAutonomyAdminSelfStudyRuns(20)
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        catchError((err) => {
          this.error.set(this.extractErrorMessage(err, 'Falha ao carregar historico de autoestudo.'))
          return of({ items: [] as SelfStudyRun[] })
        })
      )
      .subscribe((resp) => this.selfStudyRuns.set(resp.items || []))
  }

  private refreshSelfStudyStatus() {
    this.api.getAutonomyAdminSelfStudyStatus()
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        catchError((err) => {
          this.error.set(this.extractErrorMessage(err, 'Falha ao carregar status de autoestudo.'))
          return of({ recent_runs: [] } as SelfStudyStatusResponse)
        })
      )
      .subscribe((status) => {
        const wasRunning = Boolean(this.selfStudyStatus()?.running)
        const isRunning = Boolean(status.running)
        this.selfStudyStatus.set(status)
        if (isRunning) {
          this.startSelfStudyPolling()
        } else {
          this.stopSelfStudyPolling()
          if (wasRunning) {
            this.refreshSelfStudyRuns()
          }
        }
      })
  }

  private refreshSelfStudyRuns() {
    this.api.listAutonomyAdminSelfStudyRuns(20)
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        catchError((err) => {
          this.error.set(this.extractErrorMessage(err, 'Falha ao carregar historico de autoestudo.'))
          return of({ items: [] as SelfStudyRun[] })
        })
      )
      .subscribe((resp) => this.selfStudyRuns.set(resp.items || []))
  }

  private startSelfStudyPolling() {
    if (this.selfStudyPollTimer) return
    this.selfStudyPollTimer = setInterval(() => this.refreshSelfStudyStatus(), this.selfStudyPollIntervalMs)
  }

  private stopSelfStudyPolling() {
    if (!this.selfStudyPollTimer) return
    clearInterval(this.selfStudyPollTimer)
    this.selfStudyPollTimer = null
  }

  syncBacklog() {
    if (this.syncing()) return
    this.syncing.set(true)
    this.error.set('')
    this.notice.set('')
    this.api.syncAutonomyAdminBacklog()
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.syncing.set(false)),
        catchError((err) => {
          this.error.set(this.extractErrorMessage(err, 'Falha ao sincronizar backlog.'))
          return of(null)
        })
      )
      .subscribe((resp) => {
        if (!resp) return
        this.notice.set(
          `Backlog sincronizado: ${resp.created} criadas, ${resp.deduped} deduplicadas, ${resp.closed} fechadas.`
        )
        this.refreshBoard()
      })
  }

  runStudy(mode: 'incremental' | 'full') {
    if (this.runningStudy()) return
    this.runningStudy.set(true)
    this.error.set('')
    this.notice.set('')
    this.api.runAutonomyAdminSelfStudy({
      mode,
      reason: `admin_panel_${mode}`
    })
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.runningStudy.set(false)),
        catchError((err) => {
          this.error.set(this.extractErrorMessage(err, 'Falha ao iniciar autoestudo.'))
          return of(null)
        })
      )
      .subscribe((resp) => {
        if (!resp) return
        this.notice.set(`Autoestudo iniciado (run #${resp.run_id}).`)
        this.refreshSelfStudy()
      })
  }

  onQuestionChange(value: string) {
    this.question.set(String(value || ''))
  }

  askCode() {
    if (this.asking()) return
    const question = this.question().trim()
    if (!question) return
    this.asking.set(true)
    this.error.set('')
    this.notice.set('')
    this.api.askAutonomyAdminCodeQa({
      question,
      limit: 12,
      citation_limit: 8
    })
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.asking.set(false)),
        catchError((err) => {
          this.error.set(this.extractErrorMessage(err, 'Falha ao consultar codigo.'))
          return of({ answer: '', citations: [], self_memory: [] } as AdminCodeQaResponse)
        })
      )
      .subscribe((resp) => {
        this.answer.set(String(resp.answer || ''))
        this.citations.set(resp.citations || [])
        this.selfMemory.set(resp.self_memory || [])
      })
  }

  private extractErrorMessage(err: unknown, fallback: string): string {
    const detail = (err as { error?: { detail?: unknown } })?.error?.detail
    if (typeof detail === 'string' && detail.trim()) return detail.trim()
    if (typeof err === 'string' && err.trim()) return err.trim()
    return fallback
  }
}
