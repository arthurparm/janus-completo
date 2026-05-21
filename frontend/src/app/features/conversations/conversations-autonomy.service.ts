import { Injectable, inject } from '@angular/core'
import { forkJoin, of } from 'rxjs'
import { catchError, map } from 'rxjs/operators'

import type { Goal, Tool } from '../../models'
import { BackendApiService } from '../../services/backend-api.service'
import { ConversationStateFacade } from './conversations-state.facade'
import type { GoalStatus } from './conversations.types'
import { ConversationsNoticeService } from './conversations-notice.service'
import { extractErrorMessage } from './conversations.utils'

@Injectable({ providedIn: 'root' })
export class ConversationsAutonomyService {
  private api = inject(BackendApiService)
  private state = inject(ConversationStateFacade)
  private notices = inject(ConversationsNoticeService)

  loadAutonomyContext(): void {
    this.state.autonomyLoading.set(true)
    forkJoin({
      status: this.api.autonomy.getAutonomyStatus().pipe(catchError(() => of(null))),
      goals: this.api.autonomy.listGoals().pipe(catchError(() => of([] as Goal[]))),
      tools: this.api.tools.getTools().pipe(
        map((resp) => resp.tools || []),
        catchError(() => of([] as Tool[]))
      )
    }).subscribe((result) => {
      this.state.autonomyStatus.set(result.status)
      this.state.autonomyGoals.set(result.goals)
      this.state.autonomyTools.set(result.tools)
      this.state.autonomyLoading.set(false)
    })
  }

  onGoalCreateTitleInput(event: Event): void {
    const target = event.target as HTMLInputElement | null
    this.state.goalCreateTitle.set(target?.value || '')
  }

  onGoalCreateDescriptionInput(event: Event): void {
    const target = event.target as HTMLTextAreaElement | null
    this.state.goalCreateDescription.set(target?.value || '')
  }

  createGoal(): void {
    const title = this.state.goalCreateTitle().trim()
    const description = this.state.goalCreateDescription().trim()
    if (!title) {
      this.state.goalCreateError.set('Informe um título para a meta.')
      return
    }
    this.state.goalCreateError.set('')
    this.notices.clear('autonomy')
    this.state.goalCreateLoading.set(true)
    this.api.autonomy.createGoal({
      title,
      description,
      priority: 2
    })
      .pipe(catchError((err) => {
        this.state.goalCreateError.set(extractErrorMessage(err, 'Falha ao criar meta.'))
        this.state.goalCreateLoading.set(false)
        return of(null)
      }))
      .subscribe((goal) => {
        this.state.goalCreateLoading.set(false)
        if (!goal) return
        this.state.goalCreateTitle.set('')
        this.state.goalCreateDescription.set('')
        this.state.autonomyGoals.update((items) => [goal, ...items])
        this.notices.set('autonomy', 'success', 'Meta criada.')
      })
  }

  refreshAutonomy(): void {
    this.loadAutonomyContext()
  }

  toggleAutonomyLoop(): void {
    if (this.state.autonomySaving()) return
    this.state.autonomySaving.set(true)
    this.state.autonomyError.set('')
    this.notices.clear('autonomy')
    const active = Boolean(this.state.autonomyStatus()?.active)
    const request$ = active
      ? this.api.autonomy.stopAutonomy()
      : this.api.autonomy.startAutonomy({
        interval_seconds: 60,
        risk_profile: 'balanced',
        user_id: this.userIdString()
      })
    request$
      .pipe(catchError((err) => {
        this.state.autonomyError.set(extractErrorMessage(err, 'Falha ao atualizar autonomia.'))
        return of(null)
      }))
      .subscribe(() => {
        this.state.autonomySaving.set(false)
        this.notices.set('autonomy', 'success', active ? 'Loop autônomo interrompido.' : 'Loop autônomo iniciado.')
        this.loadAutonomyContext()
      })
  }

  markGoalStatus(goal: Goal, status: GoalStatus): void {
    if (!goal?.id || this.state.autonomySaving()) return
    this.state.autonomySaving.set(true)
    this.state.autonomyError.set('')
    this.notices.clear('autonomy')
    this.api.autonomy.updateGoalStatus(goal.id, status)
      .pipe(catchError((err) => {
        this.state.autonomyError.set(extractErrorMessage(err, 'Falha ao atualizar meta.'))
        return of(null)
      }))
      .subscribe((updated) => {
        if (updated) {
          this.state.autonomyGoals.update((items) => items.map((item) => item.id === updated.id ? updated : item))
          this.notices.set('autonomy', 'success', 'Status da meta atualizado.')
        }
        this.state.autonomySaving.set(false)
      })
  }

  goalStatusLabel(goal: Goal): string {
    if (goal.status === 'in_progress') return 'Em andamento'
    if (goal.status === 'completed') return 'Concluida'
    if (goal.status === 'failed') return 'Falhou'
    return 'Pendente'
  }

  private userIdString(): string | undefined {
    const id = this.state.user()?.id
    return id != null ? String(id) : undefined
  }
}
