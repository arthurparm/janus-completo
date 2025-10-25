import {Component, OnDestroy, OnInit, computed, effect, inject, signal, untracked} from '@angular/core';
import {CommonModule, NgIf} from '@angular/common';
import {RouterModule} from '@angular/router';
import {BaseChartDirective} from 'ng2-charts';
import {ChartConfiguration, ChartOptions} from 'chart.js';
import {GlobalStateStore} from '../../core/state/global-state.store';
import {NotificationBanner} from '../../core/notifications/notification-banner';
import {NotificationService} from '../../core/notifications/notification.service';
import {JanusApiService, ServiceHealthItem, WorkerStatusResponse} from '../../services/janus-api.service';

const UPDATE_INTERVAL_SECONDS = 5;
const LATENCY_THRESHOLD_MS = 500;

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule, RouterModule, NgIf, BaseChartDirective, NotificationBanner],
  templateUrl: './home.html',
  styleUrl: './home.scss'
})
export class HomeComponent implements OnInit, OnDestroy {
  private store = inject(GlobalStateStore);
  private api = inject(JanusApiService);
  private notifications = inject(NotificationService);

  private lastLatencyWarningTs?: number;

  readonly loading = this.store.loading;
  readonly apiHealthy = this.store.apiHealthy;
  readonly systemStatus = this.store.systemStatus;
  readonly services = this.store.services;
  readonly workers = this.store.workers;

  readonly now = signal<string>(new Date().toLocaleString('pt-BR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit'
  }));
  private clockInterval?: any;

  // System metrics
  systemMetricsHistory = signal<Array<{timestamp: Date, cpu: number, memory: number, disk: number}>>([]);
  currentSystemMetrics = signal({cpu: 0, memory: 0, disk: 0});

  // Services health
  servicesHealthHistory = signal<Array<{timestamp: Date, availability: number, responseTime: number}>>([]);

  // Workers performance
  workersPerformanceHistory = signal<Array<{timestamp: Date, throughput: number, latency: number}>>([]);

  systemStatusChartData = computed(() => {
    const history = this.systemMetricsHistory();
    const labels = history.map(h => h.timestamp.toLocaleTimeString());
    return {
      labels,
      datasets: [{
        label: 'CPU (%)',
        data: history.map(h => h.cpu),
        borderColor: 'rgba(75, 192, 192, 1)',
        backgroundColor: 'rgba(75, 192, 192, 0.15)',
        tension: 0.3,
        pointRadius: 2
      }]
    } as ChartConfiguration<'line'>['data'];
  });

  private readonly servicesColors = {
    availabilityBorder: 'rgba(54, 162, 235, 1)',
    availabilityBackground: 'rgba(54, 162, 235, 0.3)',
    responseBorder: 'rgba(255, 99, 132, 1)',
    responseBackground: 'rgba(255, 99, 132, 0.15)'
  };
  servicesHealthChartData = computed(() => {
    const history = this.servicesHealthHistory();
    const labels = history.map(h => h.timestamp.toLocaleTimeString());
    return {
      labels,
      datasets: [
        {
          label: 'Disponibilidade (%)',
          data: history.map(h => h.availability),
          borderColor: this.servicesColors.availabilityBorder,
          backgroundColor: this.servicesColors.availabilityBackground,
          yAxisID: 'y'
        },
        {
          label: 'Tempo de Resposta (ms)',
          data: history.map(h => h.responseTime),
          borderColor: this.servicesColors.responseBorder,
          backgroundColor: this.servicesColors.responseBackground,
          yAxisID: 'y1'
        }
      ]
    } as ChartConfiguration<'bar'>['data'];
  });

  private readonly workersColors = {
    throughputBorder: 'rgba(153, 102, 255, 1)',
    throughputBackground: 'rgba(153, 102, 255, 0.2)',
    latencyBorder: 'rgba(255, 159, 64, 1)',
    latencyBackground: 'rgba(255, 159, 64, 0.15)'
  };
  workersPerformanceChartData = computed(() => {
    const history = this.workersPerformanceHistory();
    const labels = history.map(h => h.timestamp.toLocaleTimeString());
    return {
      labels,
      datasets: [
        {
          label: 'Throughput (tarefas/min)',
          data: history.map(h => h.throughput),
          borderColor: this.workersColors.throughputBorder,
          backgroundColor: this.workersColors.throughputBackground,
          tension: 0.3,
          pointRadius: 2,
          yAxisID: 'y'
        },
        {
          label: 'Latência (ms)',
          data: history.map(h => h.latency),
          borderColor: this.workersColors.latencyBorder,
          backgroundColor: this.workersColors.latencyBackground,
          tension: 0.3,
          pointRadius: 2,
          yAxisID: 'y1'
        }
      ]
    } as ChartConfiguration<'line'>['data'];
  });

  servicesHealthChartOptions: ChartOptions<'bar'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { position: 'top' } },
    scales: {
      y: { type: 'linear', display: true, position: 'left', beginAtZero: true, max: 100, ticks: { callback: (v:any) => v + '%' } },
      y1: { type: 'linear', display: true, position: 'right', beginAtZero: true, ticks: { callback: (v:any) => v + 'ms' }, grid: { drawOnChartArea: false } }
    },
    animation: { duration: 750, easing: 'easeInOutQuart' }
  };

  systemStatusChartOptions: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { position: 'top' } },
    scales: {
      y: { type: 'linear', display: true, position: 'left', beginAtZero: true, max: 100, ticks: { callback: (v:any) => v + '%' } },
      y1: { type: 'linear', display: true, position: 'right', beginAtZero: true, ticks: { callback: (v:any) => v + 'ms' }, grid: { drawOnChartArea: false } }
    },
    animation: { duration: 750, easing: 'easeInOutQuart' }
  };

  workersPerformanceChartOptions: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { position: 'top' } },
    scales: {
      y: { type: 'linear', display: true, position: 'left', beginAtZero: true, ticks: { callback: (v:any) => v + ' t/min' } },
      y1: { type: 'linear', display: true, position: 'right', beginAtZero: true, ticks: { callback: (v:any) => v + 'ms' }, grid: { drawOnChartArea: false } }
    },
    animation: { duration: 750, easing: 'easeInOutQuart' }
  };

  // Valor atual para resumo dos workers
  currentWorkersPerformance = computed(() => {
    const h = this.workersPerformanceHistory();
    if (!h.length) return { throughput: 0, latency: 0 };
    const last = h[h.length - 1];
    return { throughput: last.throughput, latency: last.latency };
  });

  constructor() {
    effect(() => {
      const svc = this.services();
      const workers = this.workers();
      const sys = this.systemStatus();
      this.updateSystemMetrics(sys);
      this.updateServicesHealth(svc);
      this.updateWorkersPerformance(workers);
      this.checkAlerts(svc, workers, sys);
    });
  }

  ngOnInit(): void {
    this.store.startPolling(UPDATE_INTERVAL_SECONDS * 1000);
    this.clockInterval = setInterval(() => {
      this.now.set(new Date().toLocaleString('pt-BR', {
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit', second: '2-digit'
      }));
    }, 1000);
  }
  ngOnDestroy(): void { 
    this.store.stopPolling(); 
    if (this.clockInterval) clearInterval(this.clockInterval);
  }

  private updateSystemMetrics(sys?: { cpu_usage_percent?: number; memory_usage_percent?: number; disk_usage_percent?: number; uptime_seconds?: number }): void {
    const history = untracked(() => this.systemMetricsHistory());
    const newEntry = { timestamp: new Date(), cpu: sys?.cpu_usage_percent ?? 0, memory: sys?.memory_usage_percent ?? 0, disk: sys?.disk_usage_percent ?? 0 };
    const newHistory = [...history, newEntry];
    if (newHistory.length > 20) newHistory.shift();
    this.systemMetricsHistory.set(newHistory);
    this.currentSystemMetrics.set({ cpu: newEntry.cpu, memory: newEntry.memory, disk: newEntry.disk });
  }

  public servicesAvailability(): number {
    const services = this.services();
    if (!services || services.length === 0) return 0;
    const healthy = services.filter(s => (s.status || '').toLowerCase() === 'ok').length;
    return Math.round((healthy / services.length) * 100);
  }

  public averageResponseTime(): number {
    const services = this.services();
    if (!services || services.length === 0) return 0;
    const times = services.map(s => {
      const m = s.metric_text || '';
      const match = /(?:latency|tempo\s*de\s*resposta)\s*[:=]?\s*(\d+)/i.exec(String(m));
      return match ? Number(match[1]) : 0;
    }).filter(t => t > 0);
    if (times.length === 0) return 0;
    const total = times.reduce((sum, t) => sum + t, 0);
    return Math.round(total / times.length);
  }

  public totalThroughput(): string {
    const workers = this.workers();
    if (!workers || workers.length === 0) return '0';
    const totalPerMin = workers.reduce((sum, w) => {
      const minutes = Math.max(1, (Date.now() - new Date(w.last_heartbeat).getTime()) / 60000);
      return sum + (w.tasks_processed || 0) / minutes;
    }, 0);
    return totalPerMin.toFixed(1);
  }

  public averageLatency(): number {
    const workers = this.workers();
    if (!workers || workers.length === 0) return 0;
    const latencies = workers.map(w => {
      const status = (w.status || '').toLowerCase();
      if (status === 'running') return 120;
      if (status === 'error') return 600;
      return 220;
    });
    const total = latencies.reduce((sum, l) => sum + l, 0);
    return Math.round(total / latencies.length);
  }

  private updateServicesHealth(services: ServiceHealthItem[]): void {
    const availability = this.servicesAvailability();
    const responseTime = this.averageResponseTime();
    const history = untracked(() => this.servicesHealthHistory());
    const newHistory = [...history, { timestamp: new Date(), availability, responseTime }];
    if (newHistory.length > 20) newHistory.shift();
    this.servicesHealthHistory.set(newHistory);
  }

  private updateWorkersPerformance(workers: WorkerStatusResponse[]): void {
    const throughput = parseFloat(this.totalThroughput());
    const latency = this.averageLatency();
    const history = untracked(() => this.workersPerformanceHistory());
    const newHistory = [...history, { timestamp: new Date(), throughput, latency }];
    if (newHistory.length > 20) newHistory.shift();
    this.workersPerformanceHistory.set(newHistory);
  }

  private checkAlerts(services: ServiceHealthItem[], workers: WorkerStatusResponse[], sys?: { uptime_seconds?: number }): void {
    const latency = this.averageLatency();
    if (latency > LATENCY_THRESHOLD_MS) {
      const now = Date.now();
      if (!this.lastLatencyWarningTs || (now - this.lastLatencyWarningTs) > 60_000) {
        this.notifications.notify({ type: 'warning', message: `Latência média dos workers acima de ${LATENCY_THRESHOLD_MS}ms` });
        this.lastLatencyWarningTs = now;
      }
    }
  }
}
