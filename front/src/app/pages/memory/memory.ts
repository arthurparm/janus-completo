import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core'
import { CommonModule } from '@angular/common'
import { FormsModule } from '@angular/forms'
import { JanusApiService } from '../../services/janus-api.service'
import { DemoService } from '../../core/services/demo.service'
import { UiIconComponent } from '../../shared/components/ui/icon/icon.component'

export interface Memory {
    id?: string
    content: string
    timestamp?: number
    score?: number
    metadata?: Record<string, any>
    type?: string
}

@Component({
    selector: 'app-memory',
    standalone: true,
    imports: [CommonModule, FormsModule, UiIconComponent],
    templateUrl: './memory.html',
    styleUrl: './memory.scss'
})
export class MemoryComponent implements OnInit {
    private api = inject(JanusApiService)
    private cdr = inject(ChangeDetectorRef)
    private demoService = inject(DemoService)

    memories: Memory[] = []
    loading = false
    error: string | null = null

    // Search filters
    searchQuery = ''
    startDate = ''
    endDate = ''
    limit = 20
    minScore = 0.5

    // Timeline visualization
    groupedMemories: Map<string, Memory[]> = new Map()

    get isOffline() {
        return this.demoService.isOffline()
    }

    ngOnInit() {
        // Set default date range (last 7 days)
        const now = new Date()
        const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)

        this.endDate = now.toISOString().split('T')[0]
        this.startDate = weekAgo.toISOString().split('T')[0]

        this.loadTimeline()
    }

    loadTimeline() {
        this.loading = true
        this.error = null

        if (this.demoService.isOffline()) {
            this.loading = false
            this.memories = []
            this.groupedMemories = new Map()
            return
        }

        const params: any = {
            limit: this.limit
        }

        if (this.startDate) {
            params.start_date = new Date(this.startDate).toISOString()
        }
        if (this.endDate) {
            params.end_date = new Date(this.endDate).toISOString()
        }
        if (this.searchQuery.trim()) {
            params.query = this.searchQuery.trim()
        }
        if (this.minScore > 0) {
            params.min_score = this.minScore
        }

        this.api.getMemoryTimeline(params).subscribe({
            next: (memories: Memory[]) => {
                this.memories = memories || []
                this.groupMemoriesByDate()
                this.loading = false
                this.cdr.detectChanges()
            },
            error: (err: any) => {
                console.error('Error loading memories:', err)
                if (err.status === 0 || err.status === 504) {
                    this.demoService.enableOfflineMode();
                    this.loading = false
                    this.memories = []
                    this.groupedMemories = new Map()
                } else {
                    this.error = 'Falha ao carregar memórias'
                    this.loading = false
                }
                this.cdr.detectChanges()
            }
        })
    }

    groupMemoriesByDate() {
        this.groupedMemories = new Map()

        this.memories.forEach(memory => {
            const date = memory.timestamp
                ? new Date(memory.timestamp).toLocaleDateString('pt-BR', {
                    weekday: 'long',
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric'
                })
                : 'Data desconhecida'

            if (!this.groupedMemories.has(date)) {
                this.groupedMemories.set(date, [])
            }
            this.groupedMemories.get(date)!.push(memory)
        })
    }

    search() {
        this.loadTimeline()
    }

    clearFilters() {
        this.searchQuery = ''
        this.minScore = 0.5
        const now = new Date()
        const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
        this.endDate = now.toISOString().split('T')[0]
        this.startDate = weekAgo.toISOString().split('T')[0]
        this.loadTimeline()
    }

    formatTime(timestamp?: number): string {
        if (!timestamp) return ''
        return new Date(timestamp).toLocaleTimeString('pt-BR', {
            hour: '2-digit',
            minute: '2-digit'
        })
    }

    getScoreClass(score?: number): string {
        if (!score) return 'score-unknown'
        if (score >= 0.8) return 'score-high'
        if (score >= 0.5) return 'score-medium'
        return 'score-low'
    }

    getScorePercent(score?: number): number {
        return Math.round((score || 0) * 100)
    }

    getTypeIcon(type?: string): string {
        const icons: Record<string, string> = {
            'conversation': 'chat',
            'document': 'description',
            'action': 'play_circle',
            'observation': 'visibility',
            'insight': 'lightbulb',
            'decision': 'gavel'
        }
        return icons[type || ''] || 'memory'
    }

    getTypeLabel(type?: string): string {
        const labels: Record<string, string> = {
            'conversation': 'Conversa',
            'document': 'Documento',
            'action': 'Ação',
            'observation': 'Observação',
            'insight': 'Insight',
            'decision': 'Decisão'
        }
        return labels[type || ''] || 'Memória'
    }

    truncateContent(content: string, maxLength: number = 200): string {
        if (content.length <= maxLength) return content
        return content.substring(0, maxLength) + '...'
    }

    setDateRange(days: number) {
        const now = new Date()
        const past = new Date(now.getTime() - days * 24 * 60 * 60 * 1000)
        this.endDate = now.toISOString().split('T')[0]
        this.startDate = past.toISOString().split('T')[0]
        this.loadTimeline()
    }
}
