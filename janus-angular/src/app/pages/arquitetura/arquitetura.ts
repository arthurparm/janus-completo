import {Component, OnInit} from '@angular/core';
import {NgIf, NgFor, DecimalPipe, JsonPipe} from '@angular/common';
import {HttpClientModule} from '@angular/common/http';
import {JanusApiService, SystemStatus, ServiceHealthItem, WorkersStatusItem, CircuitBreakerStatus, MetricsSummary, QuarantinedMessagesResponse} from '../../services/janus-api.service';

@Component({
  selector: 'app-arquitetura',
  imports: [NgIf, NgFor, HttpClientModule, DecimalPipe, JsonPipe],
  templateUrl: './arquitetura.html',
  styleUrl: './arquitetura.scss'
})
export class Arquitetura implements OnInit {
  // Estado em tempo real
  apiHealthy: 'unknown' | 'ok' = 'unknown'
  systemStatus?: SystemStatus
  services: ServiceHealthItem[] = []
  workers: WorkersStatusItem[] = []
  llmProviders: any = null
  llmHealth: any = null
  llmCircuitBreakers: CircuitBreakerStatus[] = []
  llmCacheTotal = 0
  observabilitySystemHealth: any = null
  metricsSummary?: MetricsSummary
  contextInfo: any = null

  // Observability extra
  quarantinedMessages?: QuarantinedMessagesResponse
  poisonPillStats?: any

  loading = true

  constructor(private api: JanusApiService) {}

  ngOnInit(): void {
    this.refreshAll()
  }

  refreshAll(): void {
    this.loading = true

    // healthz
    this.api.health().subscribe({
      next: (h) => (this.apiHealthy = h.status === 'ok' ? 'ok' : 'unknown'),
      error: () => (this.apiHealthy = 'unknown')
    })

    // system status
    this.api.getSystemStatus().subscribe({
      next: (s) => (this.systemStatus = s),
      error: () => {}
    })

    // services
    this.api.getServicesHealth().subscribe({
      next: (resp) => (this.services = resp.services || []),
      error: () => {}
    })

    // workers
    this.api.getWorkersStatus().subscribe({
      next: (resp) => (this.workers = resp.workers || []),
      error: () => {}
    })

    // LLM subsystem
    this.api.listLLMProviders().subscribe({ next: (p) => (this.llmProviders = p), error: () => {} })
    this.api.getLLMHealth().subscribe({ next: (h) => (this.llmHealth = h), error: () => {} })
    this.api.getLLMCircuitBreakers().subscribe({ next: (cb) => (this.llmCircuitBreakers = cb), error: () => {} })
    this.api.getLLMCacheStatus().subscribe({ next: (cs) => (this.llmCacheTotal = cs.total_cached || 0), error: () => {} })

    // Observability
    this.api.getObservabilitySystemHealth().subscribe({ next: (oh) => (this.observabilitySystemHealth = oh), error: () => {} })
    this.api.getObservabilityMetricsSummary().subscribe({ next: (ms) => (this.metricsSummary = ms), error: () => {} })

    // Context
    this.api.getCurrentContext().subscribe({ next: (ctx) => (this.contextInfo = ctx), error: () => {} })

    // Extras de observabilidade
    this.refreshObservabilityExtras()

    this.loading = false
  }

  startWorkers(): void {
    this.api.startAllWorkers().subscribe({ next: () => this.refreshWorkers(), error: () => {} })
  }

  stopWorkers(): void {
    this.api.stopAllWorkers().subscribe({ next: () => this.refreshWorkers(), error: () => {} })
  }

  cleanupQuarantine(): void {
    this.api.cleanupQuarantine().subscribe({ next: () => this.refreshObservabilityExtras(), error: () => {} })
  }

  private refreshWorkers(): void {
    this.api.getWorkersStatus().subscribe({ next: (resp) => (this.workers = resp.workers || []), error: () => {} })
  }

  private refreshObservabilityExtras(): void {
    this.api.getQuarantinedMessages().subscribe({ next: (qm) => (this.quarantinedMessages = qm), error: () => {} })
    this.api.getPoisonPillStats().subscribe({ next: (pps) => (this.poisonPillStats = pps), error: () => {} })
  }
}
