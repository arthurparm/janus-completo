import { Component, OnInit, inject } from '@angular/core';
import { DemoService } from '../../core/services/demo.service'
import { JanusApiService, SystemStatus, ServiceHealthItem, WorkersStatusItem, CircuitBreakerStatus, MetricsSummary, QuarantinedMessagesResponse } from '../../services/janus-api.service';

import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-arquitetura',
  imports: [CommonModule, MatIconModule],
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

  private demoService = inject(DemoService)

  constructor(private api: JanusApiService) { }

  ngOnInit(): void {
    this.refreshAll()
  }

  refreshAll(): void {
    this.loading = true

    // If already offline, skip API calls and load mock data
    if (this.demoService.isOffline()) {
      this.loadOfflineData();
      return;
    }

    // Wrap API calls safely
    this.api.health().subscribe({
      next: (h) => (this.apiHealthy = h.status === 'ok' ? 'ok' : 'unknown'),
      error: () => this.handleError()
    })

    this.api.getSystemStatus().subscribe({
      next: (s) => (this.systemStatus = s),
      error: () => this.handleError()
    })

    this.api.getServicesHealth().subscribe({
      next: (resp) => (this.services = resp.services || []),
      error: () => this.handleError()
    })

    this.api.getWorkersStatus().subscribe({
      next: (resp) => (this.workers = resp.workers || []),
      error: () => this.handleError()
    })

    // LLM subsystem
    this.api.listLLMProviders().subscribe({ next: (p) => (this.llmProviders = p), error: () => { } })
    this.api.getLLMHealth().subscribe({ next: (h) => (this.llmHealth = h), error: () => { } })
    this.api.getLLMCircuitBreakers().subscribe({ next: (cb) => (this.llmCircuitBreakers = cb), error: () => { } })
    this.api.getLLMCacheStatus().subscribe({ next: (cs) => (this.llmCacheTotal = cs.total_cached || 0), error: () => { } })

    // Observability
    this.api.getObservabilitySystemHealth().subscribe({ next: (oh) => (this.observabilitySystemHealth = oh), error: () => { } })
    this.api.getObservabilityMetricsSummary().subscribe({ next: (ms) => (this.metricsSummary = ms), error: () => { } })

    // Context
    this.api.getCurrentContext().subscribe({ next: (ctx) => (this.contextInfo = ctx), error: () => { } })

    // Extras de observabilidade
    this.refreshObservabilityExtras()

    // Safety timeout to stop spinner
    setTimeout(() => {
      this.loading = false
      if (this.demoService.isOffline() && !this.systemStatus) {
        this.loadOfflineData()
      }
    }, 1000)
  }

  private handleError() {
    // If we are getting errors, we might be offline.
    // The interceptor might have already triggered it.
    if (this.demoService.isOffline()) {
      this.loadOfflineData();
    }
  }

  private loadOfflineData() {
    // Mock Data for "Perfect Documentation" appearance
    this.apiHealthy = 'ok';
    this.systemStatus = {
      app_name: 'Janus Platform',
      environment: 'offline-demo',
      status: 'healthy',
      timestamp: new Date().toISOString(),
      version: '2.0.0-DEMO'
    };
    this.services = [
      { key: 'core_api', name: 'Core API', status: 'running', metric_text: 'Uptime: 99.9%' },
      { key: 'llm_engine', name: 'LLM Engine', status: 'running', metric_text: 'Active Models: 2' },
      { key: 'context_service', name: 'Context Service', status: 'running', metric_text: 'Indexed: 100%' }
    ];
    this.workers = [
      { id: 'coder-01', status: 'idle', tasks_processed: 124, last_heartbeat: new Date().toISOString() },
      { id: 'reviewer-01', status: 'idle', tasks_processed: 56, last_heartbeat: new Date().toISOString() }
    ];
    this.loading = false;
  }

  startWorkers(): void {
    if (this.demoService.isOffline()) return;
    this.api.startAllWorkers().subscribe({ next: () => this.refreshWorkers(), error: () => { } })
  }

  stopWorkers(): void {
    if (this.demoService.isOffline()) return;
    this.api.stopAllWorkers().subscribe({ next: () => this.refreshWorkers(), error: () => { } })
  }

  cleanupQuarantine(): void {
    if (this.demoService.isOffline()) return;
    this.api.cleanupQuarantine().subscribe({ next: () => this.refreshObservabilityExtras(), error: () => { } })
  }

  private refreshWorkers(): void {
    if (this.demoService.isOffline()) return;
    this.api.getWorkersStatus().subscribe({ next: (resp) => (this.workers = resp.workers || []), error: () => { } })
  }

  private refreshObservabilityExtras(): void {
    if (this.demoService.isOffline()) return;
    this.api.getQuarantinedMessages().subscribe({ next: (qm) => (this.quarantinedMessages = qm), error: () => { } })
    this.api.getPoisonPillStats().subscribe({ next: (pps) => (this.poisonPillStats = pps), error: () => { } })
  }
}
