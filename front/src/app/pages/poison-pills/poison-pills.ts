import { Component, OnInit, inject } from '@angular/core'
import { CommonModule, DatePipe } from '@angular/common'
import { FormsModule } from '@angular/forms'
import { JanusApiService, QuarantinedMessage, PoisonPillStats } from '../../services/janus-api.service'
import { DemoService } from '../../core/services/demo.service'

@Component({
  selector: 'app-poison-pills',
  standalone: true,
  imports: [CommonModule, FormsModule, DatePipe],
  templateUrl: './poison-pills.html',
  styleUrl: './poison-pills.scss'
})
export class PoisonPillsComponent implements OnInit {
  private api = inject(JanusApiService)
  private demoService = inject(DemoService)

  messages: QuarantinedMessage[] = []
  stats?: PoisonPillStats
  selectedQueue = ''
  search = ''
  loading = false
  error = ''
  private pendingRequests = 0

  ngOnInit(): void {
    this.loadData()
  }

  get queues(): string[] {
    if (!this.stats || !this.stats.by_queue) return []
    return Object.keys(this.stats.by_queue)
  }

  get filteredMessages(): QuarantinedMessage[] {
    let result = this.messages
    const query = this.search.trim().toLowerCase()
    if (query) {
      result = result.filter(m =>
        m.message_id.toLowerCase().includes(query) ||
        m.queue.toLowerCase().includes(query) ||
        m.reason.toLowerCase().includes(query)
      )
    }
    return result
  }

  get totalQuarantined(): number {
    return this.stats?.total ?? this.messages.length
  }

  get uniqueQueuesCount(): number {
    return this.queues.length
  }

  get lastQuarantinedAt(): string | null {
    if (!this.stats || !this.stats.by_queue) return null
    const timestamps: string[] = []
    for (const value of Object.values(this.stats.by_queue)) {
      if (value && value.last_quarantined_at) {
        timestamps.push(value.last_quarantined_at)
      }
    }
    if (!timestamps.length) return null
    const latest = timestamps.reduce((max, ts) => (ts > max ? ts : max), timestamps[0])
    const date = new Date(latest)
    return isNaN(date.getTime()) ? latest : date.toLocaleString('pt-BR')
  }

  reload(): void {
    this.loadData()
  }

  onQueueChange(queue: string): void {
    this.selectedQueue = queue
    this.loadData()
  }

  clearFilters(): void {
    this.selectedQueue = ''
    this.search = ''
    this.loadData()
  }

  cleanup(): void {
    if (this.demoService.isOffline()) return
    this.loading = true
    this.error = ''
    this.api.cleanupQuarantine().subscribe({
      next: () => this.loadData(),
      error: () => {
        this.loading = false
        this.error = 'Falha ao limpar quarentena'
      }
    })
  }

  private loadData(): void {
    if (this.demoService.isOffline()) {
      this.messages = []
      this.stats = undefined
      this.loading = false
      this.error = ''
      return
    }
    this.loading = true
    this.error = ''
    this.pendingRequests = 2
    const queueParam = this.selectedQueue || undefined
    this.api.getQuarantinedMessages(queueParam).subscribe({
      next: resp => {
        this.messages = resp.messages || []
        this.finishRequest()
      },
      error: () => {
        this.messages = []
        this.error = 'Falha ao carregar mensagens em quarentena'
        this.finishRequest()
      }
    })
    this.api.getPoisonPillStats(queueParam).subscribe({
      next: stats => {
        this.stats = stats
        this.finishRequest()
      },
      error: () => {
        this.stats = undefined
        this.finishRequest()
      }
    })
  }

  private finishRequest(): void {
    this.pendingRequests -= 1
    if (this.pendingRequests <= 0) {
      this.loading = false
    }
  }
}

