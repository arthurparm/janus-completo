import { Component, OnInit, inject, ChangeDetectorRef, OnDestroy, HostListener } from '@angular/core'
import { CommonModule } from '@angular/common'
import { FormsModule } from '@angular/forms'
import { JanusApiService, Goal } from '../../services/janus-api.service'
import { DemoService } from '../../core/services/demo.service'
import { UiIconComponent } from '../../shared/components/ui/icon/icon.component'
import { Firestore, collection, collectionData, query } from '@angular/fire/firestore';
import { Subscription, filter, take } from 'rxjs';
import { AuthService } from '../../core/auth/auth.service';

@Component({
    selector: 'app-goals',
    standalone: true,
    imports: [CommonModule, FormsModule, UiIconComponent],
    templateUrl: './goals.html',
    styleUrl: './goals.scss'
})
export class GoalsComponent implements OnInit, OnDestroy {
    private api = inject(JanusApiService)
    private cdr = inject(ChangeDetectorRef)
    private demoService = inject(DemoService)
    private firestore = inject(Firestore)
    private authService = inject(AuthService)

    goals: Goal[] = []
    filteredGoals: Goal[] = []
    loading = true
    error: string | null = null
    private goalsSub?: Subscription;

    // Filters
    statusFilter: '' | 'pending' | 'in_progress' | 'completed' | 'failed' = ''
    searchQuery = ''
    sortBy: 'priority' | 'created_at' | 'deadline_ts' = 'priority'
    sortDir: 'asc' | 'desc' = 'desc'
    activeMenuGoalId: string | null = null

    get isOffline() {
        return this.demoService.isOffline()
    }

    // New Goal Form
    showNewGoalForm = false
    newGoal = {
        title: '',
        description: '',
        priority: 5,
        success_criteria: '',
        deadline: ''
    }

    saving = false
    // Triggering rebuild
    usingFallback = false

    ngOnInit() {
        this.loadGoals()
    }

    ngOnDestroy() {
        this.goalsSub?.unsubscribe();
    }

    loadGoals() {
        this.loading = true
        this.error = null

        if (this.demoService.isOffline()) {
            this.loading = false
            this.goals = []
            this.filteredGoals = []
            return
        }

        // Wait for Firebase Auth to be ready before connecting to Firestore
        this.authService.firebaseAuthReady$.pipe(
            filter(ready => ready),
            take(1)
        ).subscribe(() => {
            this.connectToFirestore()
        })
    }

    connectToFirestore() {
        try {
            const goalsCollection = query(collection(this.firestore, 'goals'));
            // Usamos collectionData para ouvir mudanças em tempo real
            this.goalsSub = collectionData(goalsCollection, { idField: 'id' }).subscribe({
                next: (data) => {
                    this.goals = data as Goal[];
                    this.applyFilters();
                    this.loading = false;
                    this.usingFallback = false;
                    this.cdr.detectChanges();
                },
                error: (err) => {
                    console.error('Error listening to goals (Realtime):', err);
                    console.warn('Switching to API Fallback mode...');
                    this.loadGoalsFromApi();
                }
            });
        } catch (err) {
            console.error('Error initializing Firestore query (Sync):', err);
            console.warn('Switching to API Fallback mode (Sync Error)...');
            this.loadGoalsFromApi();
        }
    }

    loadGoalsFromApi() {
        this.usingFallback = true;
        this.api.listGoals().subscribe({
            next: (data) => {
                this.goals = data;
                this.applyFilters();
                this.loading = false;
                this.error = null; // Clear error if API works
                this.cdr.detectChanges();
            },
            error: (err) => {
                console.error('Error loading goals from API:', err);
                this.error = 'Falha ao carregar metas (API & Realtime)';
                this.loading = false;
                this.cdr.detectChanges();
            }

        })
    }

    applyFilters() {
        let result = [...this.goals]

        // Status filter
        if (this.statusFilter) {
            result = result.filter(g => g.status === this.statusFilter)
        }

        // Search filter
        if (this.searchQuery.trim()) {
            const query = this.searchQuery.toLowerCase()
            result = result.filter(g =>
                g.title.toLowerCase().includes(query) ||
                g.description.toLowerCase().includes(query)
            )
        }

        // Sort
        result.sort((a, b) => {
            let aVal: number, bVal: number

            if (this.sortBy === 'priority') {
                aVal = a.priority
                bVal = b.priority
            } else if (this.sortBy === 'deadline_ts') {
                aVal = a.deadline_ts || Number.MAX_SAFE_INTEGER
                bVal = b.deadline_ts || Number.MAX_SAFE_INTEGER
            } else {
                aVal = a.created_at
                bVal = b.created_at
            }

            return this.sortDir === 'asc' ? aVal - bVal : bVal - aVal
        })

        this.filteredGoals = result
    }

    toggleSort(key: 'priority' | 'created_at' | 'deadline_ts') {
        if (this.sortBy === key) {
            this.sortDir = this.sortDir === 'asc' ? 'desc' : 'asc'
        } else {
            this.sortBy = key
            this.sortDir = 'desc'
        }
        this.applyFilters()
    }

    openNewGoalForm() {
        this.showNewGoalForm = true
        this.newGoal = {
            title: '',
            description: '',
            priority: 5,
            success_criteria: '',
            deadline: ''
        }
    }

    cancelNewGoal() {
        this.showNewGoalForm = false
    }

    saveNewGoal() {
        if (!this.newGoal.title.trim() || !this.newGoal.description.trim()) {
            return
        }

        this.saving = true

        const deadline_ts = this.newGoal.deadline
            ? new Date(this.newGoal.deadline).getTime() / 1000
            : undefined

        this.api.createGoal({
            title: this.newGoal.title.trim(),
            description: this.newGoal.description.trim(),
            priority: this.newGoal.priority,
            success_criteria: this.newGoal.success_criteria.trim() || undefined,
            deadline_ts
        }).subscribe({
            next: () => {
                this.saving = false
                this.showNewGoalForm = false
                // No need to reload, listener will catch update
            },
            error: (err) => {
                console.error('Error creating goal:', err)
                this.saving = false
                this.error = 'Falha ao criar meta'
                this.cdr.detectChanges()
            }
        })
    }

    updateStatus(goal: Goal, newStatus: 'pending' | 'in_progress' | 'completed' | 'failed') {
        this.api.updateGoalStatus(goal.id, newStatus).subscribe({
            next: () => {
                // No need to reload
            },
            error: (err) => {
                console.error('Error updating goal status:', err)
                this.error = 'Falha ao atualizar status'
                this.cdr.detectChanges()
            }
        })
    }

    deleteGoal(goal: Goal) {
        if (!confirm(`Excluir meta "${goal.title}"?`)) {
            return
        }

        this.api.deleteGoal(goal.id).subscribe({
            next: () => {
                // No need to reload
            },
            error: (err) => {
                console.error('Error deleting goal:', err)
                this.error = 'Falha ao excluir meta'
                this.cdr.detectChanges()
            }
        })
    }

    getStatusLabel(status: string): string {
        const labels: Record<string, string> = {
            'pending': 'Pendente',
            'in_progress': 'Em Progresso',
            'completed': 'Concluída',
            'failed': 'Falhou'
        }
        return labels[status] || status
    }

    getStatusIcon(status: string): string {
        const icons: Record<string, string> = {
            'pending': 'schedule',
            'in_progress': 'autorenew',
            'completed': 'check_circle',
            'failed': 'error'
        }
        return icons[status] || 'help'
    }

    getPriorityClass(priority: number): string {
        if (priority >= 8) return 'priority-high'
        if (priority >= 5) return 'priority-medium'
        return 'priority-low'
    }

    formatDate(timestamp: number): string {
        if (!timestamp) return ''
        return new Date(timestamp * 1000).toLocaleDateString('pt-BR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric'
        })
    }

    formatDeadline(timestamp?: number): string {
        if (!timestamp) return 'Sem prazo'

        const deadline = new Date(timestamp * 1000)
        const now = new Date()
        const diffDays = Math.ceil((deadline.getTime() - now.getTime()) / (1000 * 60 * 60 * 24))

        if (diffDays < 0) return 'Vencida'
        if (diffDays === 0) return 'Hoje'
        if (diffDays === 1) return 'Amanhã'
        if (diffDays <= 7) return `Em ${diffDays} dias`

        return deadline.toLocaleDateString('pt-BR')
    }

    isOverdue(goal: Goal): boolean {
        if (!goal.deadline_ts) return false
        if (goal.status === 'completed' || goal.status === 'failed') return false
        return goal.deadline_ts * 1000 < Date.now()
    }

    getCompletionPercentage(): number {
        if (this.goals.length === 0) return 0
        const completed = this.goals.filter(g => g.status === 'completed').length
        return Math.round((completed / this.goals.length) * 100)
    }

    getStats() {
        return {
            total: this.goals.length,
            pending: this.goals.filter(g => g.status === 'pending').length,
            inProgress: this.goals.filter(g => g.status === 'in_progress').length,
            completed: this.goals.filter(g => g.status === 'completed').length,
            failed: this.goals.filter(g => g.status === 'failed').length
        }
    }

    toggleMenu(goalId: string, event: Event): void {
        event.stopPropagation()
        this.activeMenuGoalId = this.activeMenuGoalId === goalId ? null : goalId
    }

    @HostListener('document:click')
    closeMenu(): void {
        this.activeMenuGoalId = null
    }
}
