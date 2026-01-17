/* eslint-disable no-console */
import { Component, OnDestroy, OnInit, computed, effect, inject, signal, untracked, HostBinding, ViewChild, ElementRef, AfterViewInit, DestroyRef, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { BaseChartDirective } from 'ng2-charts';
import { of, forkJoin } from 'rxjs';
import { catchError, tap, retry } from 'rxjs/operators';
import { ChartConfiguration, ChartOptions } from 'chart.js';
import { GlobalStateStore } from '../../core/state/global-state.store';
import { NotificationService } from '../../core/notifications/notification.service';
import {
  JanusApiService,
  ServiceHealthItem,
  WorkerStatusResponse,
  AutoAnalysisResponse,
  SystemStatus,
  AutonomyPlanResponse,
  AutonomyStatusResponse,
  AuditEvent,
  QuarantinedMessage,
  ContextInfo,
  PendingAction
} from '../../services/janus-api.service';
import { LoadingComponent } from '../../shared/components/loading/loading.component';
import { ErrorComponent } from '../../shared/components/error/error.component';
import { UiService } from '../../shared/services/ui.service';
import { UiIconComponent } from '../../shared/components/ui/icon/icon.component';
import { UiSpinnerComponent } from '../../shared/components/ui/spinner/spinner.component';
import { UiBadgeComponent } from '../../shared/components/ui/ui-badge/ui-badge.component';

const UPDATE_INTERVAL_SECONDS = 30; // Aumentado de 5 para 30 segundos para reduzir carga
const LATENCY_THRESHOLD_MS = 500;

interface QuickAction {
  id: string;
  label: string;
  icon: string;
  color: 'primary' | 'accent' | 'warn';
  description: string;
}

interface DashboardMetric {
  label: string;
  value: number | string;
  unit?: string;
  trend?: 'up' | 'down' | 'stable';
  trendValue?: string;
  icon: string;
  color: string;
}

type MissionStatus = 'active' | 'paused' | 'attention' | 'initializing';
type MissionStepStatus = 'done' | 'running' | 'pending' | 'blocked';
type RunbookStatus = 'success' | 'running' | 'queued' | 'error' | 'unknown';
type ApprovalStatus = 'pending' | 'approved' | 'rejected';
type MissionRiskProfile = 'conservative' | 'balanced' | 'aggressive' | 'unknown';
type MissionPriority = 'low' | 'medium' | 'high';
type BadgeVariant = 'neutral' | 'success' | 'warning' | 'error' | 'info';

interface MissionSummary {
  title: string;
  objective: string;
  status: MissionStatus;
  riskProfile: MissionRiskProfile;
  progress: number;
  lastCheckpoint: string;
}

interface MissionStep {
  id: string;
  title: string;
  detail: string;
  status: MissionStepStatus;
  owner?: string;
}

interface RunbookEntry {
  id: string;
  tool: string;
  action: string;
  status: RunbookStatus;
  durationMs?: number;
  retries?: number;
  lastRun?: Date;
  inputSummary?: string;
  outputSummary?: string;
  artifacts: string[];
}

interface MissionQueueItem {
  id: string;
  title: string;
  detail: string;
  eta: string;
  priority: MissionPriority;
}

interface MissionContextItem {
  label: string;
  value: string;
  icon: string;
  tone: 'neutral' | 'ok' | 'warn';
}

interface ApprovalItem {
  id: string;
  title: string;
  detail: string;
  status: ApprovalStatus;
}

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    BaseChartDirective,
    UiIconComponent,
    UiSpinnerComponent,
    UiBadgeComponent
  ],
  templateUrl: './home.html',
  styleUrl: './home.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class HomeComponent implements OnInit, OnDestroy, AfterViewInit {
  private store = inject(GlobalStateStore);
  private api = inject(JanusApiService);
  private notifications = inject(NotificationService);
  private uiService = inject(UiService);
  private destroyRef = inject(DestroyRef);

  // Estado moderno com signals
  readonly loading = this.store.loading;
  readonly apiHealthy = this.store.apiHealthy;
  readonly systemStatus = this.store.systemStatus;
  readonly services = this.store.services;
  readonly workers = this.store.workers;

  // Computed metrics from real backend data
  readonly servicesAvailability = computed(() => {
    const services = this.services();
    if (!services || services.length === 0) return 0;
    // Count services with 'ok' or 'healthy' status as available
    const healthyServices = services.filter(s =>
      s.status && ['ok', 'healthy'].includes(s.status.toLowerCase())
    ).length;
    return Math.round((healthyServices / services.length) * 100);
  });

  readonly averageResponseTime = computed(() => {
    const systemStatus = this.systemStatus();
    const performance = systemStatus?.performance;
    if (performance && performance['avg_response_ms'] != null) {
      return Math.round(performance['avg_response_ms'] as number);
    }
    return this.calculateAverageResponseTime(this.services());
  });

  // Controle de estado e animações
  showError = signal(false);
  errorMessage = signal('');
  isInitializing = signal(true);
  animationReady = signal(false);
  theme = signal<'light' | 'dark'>('dark');
  showSettings = signal(false); // New signal for settings modal

  // Interatividade avançada
  hoveredCard = signal<string | null>(null);
  expandedChart = signal<string | null>(null);
  selectedTimeRange = signal<'1h' | '6h' | '24h' | '7d'>('1h');
  missionPaused = signal(false);
  expandedRunId = signal<string | null>(null);
  missionRiskProfile = signal<MissionRiskProfile>('unknown');

  // Mobile-specific state
  isMobile = signal(false);
  isTablet = signal(false);
  touchStartY = signal(0);
  touchStartX = signal(0);
  swipeThreshold = 50;

  // Animações parallax
  @ViewChild('heroSection') heroSection!: ElementRef;
  @ViewChild('particlesCanvas') particlesCanvas!: ElementRef;
  private particlesAnimation?: number;
  private resizeObserver?: ResizeObserver;

  // Ações rápidas modernizadas
  readonly quickActions: QuickAction[] = [
    {
      id: 'refresh',
      label: 'Atualizar Dados',
      icon: 'refresh',
      color: 'primary',
      description: 'Sincronizar dados em tempo real'
    },
    {
      id: 'analyze',
      label: 'Análise IA',
      icon: 'psychology',
      color: 'accent',
      description: 'Executar análise cognitiva profunda'
    },
    {
      id: 'export',
      label: 'Exportar',
      icon: 'download',
      color: 'warn',
      description: 'Gerar relatório completo'
    },
    {
      id: 'settings',
      label: 'Configurar',
      icon: 'tune',
      color: 'primary',
      description: 'Personalizar preferências'
    }
  ];

  // Métricas principais com visual moderno
  // Mission panel data
  readonly missionSteps = signal<MissionStep[]>([]);

  readonly missionQueue = signal<MissionQueueItem[]>([]);

  readonly runbookEntries = signal<RunbookEntry[]>([]);

  readonly pinnedFiles = signal<string[]>([]);

  readonly approvalQueue = signal<ApprovalItem[]>([]);
  readonly contextInfo = signal<ContextInfo | null>(null);
  readonly workersRunningDelta = signal<number | null>(null);

  readonly pendingApprovals = computed(() =>
    this.approvalQueue().filter((item) => item.status === 'pending')
  );

  readonly missionCounts = computed(() => {
    const services = this.services();
    const workers = this.workers();
    const runningWorkers = workers.filter(w => (w.status || '').toLowerCase() === 'running').length;
    const serviceAlerts = services.filter(s => (s.status || '').toLowerCase() !== 'ok').length;
    return {
      workersRunning: runningWorkers,
      workersTotal: workers.length,
      servicesTotal: services.length,
      servicesAlerts: serviceAlerts
    };
  });

  readonly missionProgress = computed(() => {
    const steps = this.missionSteps();
    if (!steps.length) return 0;
    const completed = steps.filter(step => step.status === 'done').length;
    return Math.round((completed / steps.length) * 100);
  });

  readonly missionSummary = computed<MissionSummary>(() => {
    const sys = this.systemStatus();
    const uptimeSeconds = sys?.uptime_seconds;
    const uptimeLabel = uptimeSeconds != null ? this.formatUptime(uptimeSeconds) : 'n/a';
    return {
      title: 'Operacao do Sistema',
      objective: 'Manter servicos e agentes saudaveis com baixa latencia',
      status: this.getMissionStatus(),
      riskProfile: this.missionRiskProfile(),
      progress: this.missionProgress(),
      lastCheckpoint: uptimeLabel
    };
  });

  readonly missionContext = computed<MissionContextItem[]>(() => {
    const counts = this.missionCounts();
    const apiHealth = this.apiHealthy();
    const context = this.contextInfo();
    const workspace = this.pickContextValue(context, ['workspace', 'project_id', 'project', 'session_id']) ?? 'n/a';
    const conversation = this.pickContextValue(context, ['conversation_id']);
    const baseItems: MissionContextItem[] = [
      {
        label: 'Workspace',
        value: workspace,
        icon: 'folder',
        tone: 'neutral'
      },
      {
        label: 'API',
        value: apiHealth === 'ok' ? 'ok' : 'unknown',
        icon: 'cloud',
        tone: apiHealth === 'ok' ? 'ok' : 'warn'
      },
      {
        label: 'Services',
        value: `${counts.servicesTotal} total`,
        icon: 'dns',
        tone: counts.servicesAlerts > 0 ? 'warn' : 'ok'
      },
      {
        label: 'Workers',
        value: `${counts.workersRunning}/${counts.workersTotal}`,
        icon: 'memory',
        tone: counts.workersTotal > 0 && counts.workersRunning === counts.workersTotal ? 'ok' : 'warn'
      },
      {
        label: 'Range',
        value: this.selectedTimeRange(),
        icon: 'schedule',
        tone: 'neutral'
      }
    ];
    if (conversation) {
      baseItems.push({
        label: 'Conversation',
        value: conversation,
        icon: 'forum',
        tone: 'neutral'
      });
    }
    return baseItems;
  });

  // Metrics principais com visual moderno
  readonly dashboardMetrics = computed<DashboardMetric[]>(() => {
    const availabilityDelta = this.getHistoryDelta(this.servicesHealthHistory(), (item) => item.availability);
    const responseDelta = this.getHistoryDelta(this.servicesHealthHistory(), (item) => item.responseTime);
    const throughputDelta = this.getHistoryDelta(this.workersPerformanceHistory(), (item) => item.throughput);
    const workersDelta = this.workersRunningDelta();
    return [
      {
        label: 'Disponibilidade',
        value: this.servicesAvailability(),
        unit: '%',
        trend: this.getTrendStatus(availabilityDelta),
        trendValue: this.formatTrendValue(availabilityDelta, '%', 1),
        icon: 'shield',
        color: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
      },
      {
        label: 'Latencia Media',
        value: this.averageResponseTime(),
        unit: 'ms',
        trend: this.getTrendStatus(responseDelta),
        trendValue: this.formatTrendValue(responseDelta, 'ms', 0),
        icon: 'speed',
        color: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)'
      },
      {
        label: 'Throughput',
        value: Number(this.currentWorkersPerformance().throughput).toFixed(2),
        unit: 't/min',
        trend: this.getTrendStatus(throughputDelta),
        trendValue: this.formatTrendValue(throughputDelta, 't/min', 1),
        icon: 'trending_up',
        color: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)'
      },
      {
        label: 'Workers Ativos',
        value: this.workers().filter(w => w.status === 'running').length,
        unit: `/${this.workers().length}`,
        trend: this.getTrendStatus(workersDelta),
        trendValue: this.formatTrendValue(workersDelta, '', 0),
        icon: 'memory',
        color: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)'
      }
    ];
  });

  // Relogio digital moderno
  readonly now = signal<string>(new Date().toLocaleString('pt-BR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit'
  }));
  private clockInterval?: ReturnType<typeof setInterval>;
  private historicalDataInterval?: ReturnType<typeof setInterval>;

  // Dados para graficos com animacoes - agora com dados reais
  systemMetricsHistory = signal<Array<{ timestamp: Date; cpu: number; memory: number; disk: number }>>([]);
  currentSystemMetrics = signal({ cpu: 0, memory: 0, disk: 0 });

  servicesHealthHistory = signal<Array<{ timestamp: Date; availability: number; responseTime: number }>>([]);
  workersPerformanceHistory = signal<Array<{ timestamp: Date; throughput: number; latency: number }>>([]);

  // Dados historicos para analise temporal
  private readonly maxHistoryPoints = 20;

  // Configuracoes de graficos modernizadas
  systemStatusChartData = computed(() => {
    const history = this.systemMetricsHistory();
    const labels = history.map(h => h.timestamp.toLocaleTimeString());
    return {
      labels,
      datasets: [{
        label: 'CPU (%)',
        data: history.map(h => h.cpu),
        borderColor: 'rgba(99, 102, 241, 1)',
        backgroundColor: 'rgba(99, 102, 241, 0.1)',
        tension: 0.4,
        pointRadius: 3,
        pointHoverRadius: 6,
        borderWidth: 2
      }, {
        label: 'Memoria (%)',
        data: history.map(h => h.memory),
        borderColor: 'rgba(236, 72, 153, 1)',
        backgroundColor: 'rgba(236, 72, 153, 0.1)',
        tension: 0.4,
        pointRadius: 3,
        pointHoverRadius: 6,
        borderWidth: 2
      }]
    } as ChartConfiguration<'line'>['data'];
  });

  servicesHealthChartData = computed(() => {
    const history = this.servicesHealthHistory();
    const labels = history.map(h => h.timestamp.toLocaleTimeString());
    return {
      labels,
      datasets: [
        {
          label: 'Disponibilidade (%)',
          data: history.map(h => h.availability),
          borderColor: 'rgba(34, 197, 94, 1)',
          backgroundColor: 'rgba(34, 197, 94, 0.2)',
          yAxisID: 'y',
          borderWidth: 2,
          borderRadius: 4
        },
        {
          label: 'Tempo de Resposta (ms)',
          data: history.map(h => h.responseTime),
          borderColor: 'rgba(251, 146, 60, 1)',
          backgroundColor: 'rgba(251, 146, 60, 0.2)',
          yAxisID: 'y1',
          borderWidth: 2,
          borderRadius: 4
        }
      ]
    } as ChartConfiguration<'bar'>['data'];
  });

  workersPerformanceChartData = computed(() => {
    const history = this.workersPerformanceHistory();
    const labels = history.map(h => h.timestamp.toLocaleTimeString());
    return {
      labels,
      datasets: [
        {
          label: 'Throughput (tarefas/min)',
          data: history.map(h => h.throughput),
          borderColor: 'rgba(139, 92, 246, 1)',
          backgroundColor: 'rgba(139, 92, 246, 0.1)',
          tension: 0.4,
          pointRadius: 3,
          pointHoverRadius: 6,
          borderWidth: 2,
          yAxisID: 'y'
        },
        {
          label: 'Latencia (ms)',
          data: history.map(h => h.latency),
          borderColor: 'rgba(14, 165, 233, 1)',
          backgroundColor: 'rgba(14, 165, 233, 0.1)',
          tension: 0.4,
          pointRadius: 3,
          pointHoverRadius: 6,
          borderWidth: 2,
          yAxisID: 'y1'
        }
      ]
    } as ChartConfiguration<'line'>['data'];
  });

  // Opcoes de graficos modernizadas
  readonly chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
        labels: {
          usePointStyle: true,
          padding: 20,
          font: { size: 12 }
        }
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleColor: '#fff',
        bodyColor: '#fff',
        borderColor: 'rgba(255, 255, 255, 0.2)',
        borderWidth: 1,
        cornerRadius: 8,
        displayColors: true
      }
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { font: { size: 11 } }
      },
      y: {
        beginAtZero: true,
        grid: { color: 'rgba(0, 0, 0, 0.1)' },
        ticks: { font: { size: 11 } }
      }
    },
    animation: { duration: 1000, easing: 'easeInOutQuart' }
  } as ChartOptions;

  // Performance atual dos workers
  currentWorkersPerformance = computed(() => {
    const history = this.workersPerformanceHistory();
    if (!history.length) return { throughput: 0, latency: 0 };
    const last = history[history.length - 1];
    return { throughput: last.throughput, latency: last.latency };
  });

  private setupRealDataProcessing(): void {
    let lastSystemStatus: SystemStatus | null = null;
    let lastServices: ServiceHealthItem[] = [];
    let lastWorkers: WorkerStatusResponse[] = [];
    let lastRunningWorkers: number | null = null;

    effect(() => {
      const systemStatus = this.store.systemStatus();
      if (systemStatus && systemStatus !== lastSystemStatus) {
        lastSystemStatus = systemStatus;
        untracked(() => {
          this.processSystemMetrics(systemStatus);
        });
      }
    });

    effect(() => {
      const services = this.store.services();
      if (services && services.length > 0 && services !== lastServices) {
        lastServices = services;
        untracked(() => {
          this.processServicesData(services);
        });
      }
    });

    effect(() => {
      const workers = this.store.workers();
      if (!workers || workers === lastWorkers) return;
      lastWorkers = workers;
      untracked(() => {
        this.processWorkersData(workers);
        if (!workers.length) {
          this.workersRunningDelta.set(null);
          lastRunningWorkers = null;
          return;
        }
        const runningWorkers = workers.filter((worker) => (worker.status || '').toLowerCase() === 'running').length;
        const delta = lastRunningWorkers == null ? null : runningWorkers - lastRunningWorkers;
        this.workersRunningDelta.set(delta);
        lastRunningWorkers = runningWorkers;
      });
    });

    this.historicalDataInterval = setInterval(() => {
      this.updateHistoricalData();
    }, 30000);
  }

  private processSystemMetrics(systemStatus: SystemStatus): void {
    if (!systemStatus) {
      return;
    }

    const performance = systemStatus.performance || {};

    const metrics = {
      cpu: (performance['cpu_percent'] as number) || (systemStatus['cpu_usage_percent'] as number) || (systemStatus['cpu'] as number) || 0,
      memory: (performance['memory_percent'] as number) || (systemStatus['memory_usage_percent'] as number) || (systemStatus['memory'] as number) || 0,
      disk: (systemStatus['disk_usage_percent'] as number) || (systemStatus['disk'] as number) || 0,
      uptime: systemStatus.uptime_seconds || (systemStatus['uptime'] as number) || 0
    };

    console.log('[Home] Processing system metrics from backend:', metrics);

    this.currentSystemMetrics.set(metrics);

    if (metrics.cpu > 0 || metrics.memory > 0) {
      const history = this.systemMetricsHistory();
      const newEntry = {
        timestamp: new Date(),
        cpu: metrics.cpu,
        memory: metrics.memory,
        disk: metrics.disk
      };

      const newHistory = [...history, newEntry];
      if (newHistory.length > this.maxHistoryPoints) {
        newHistory.shift();
      }
      this.systemMetricsHistory.set(newHistory);
    }
  }

  private processServicesData(services: ServiceHealthItem[]): void {
    if (!services || services.length === 0) {
      return;
    }

    const availability = this.calculateServicesAvailability(services);
    const avgResponseTime = this.calculateAverageResponseTime(services);

    const history = this.servicesHealthHistory();
    const newEntry = {
      timestamp: new Date(),
      availability,
      responseTime: avgResponseTime
    };

    const newHistory = [...history, newEntry];
    if (newHistory.length > this.maxHistoryPoints) {
      newHistory.shift();
    }
    this.servicesHealthHistory.set(newHistory);
  }

  private processWorkersData(workers: WorkerStatusResponse[]): void {
    if (!workers || workers.length === 0) {
      return;
    }

    const throughput = this.calculateWorkersThroughput(workers);
    const latency = this.calculateWorkersLatency(workers);

    const history = this.workersPerformanceHistory();
    const newEntry = {
      timestamp: new Date(),
      throughput,
      latency
    };

    const newHistory = [...history, newEntry];
    if (newHistory.length > this.maxHistoryPoints) {
      newHistory.shift();
    }
    this.workersPerformanceHistory.set(newHistory);
  }

  private calculateServicesAvailability(services: ServiceHealthItem[]): number {
    if (!services || services.length === 0) return 0;

    const healthyServices = services.filter(service =>
      service.status && service.status.toLowerCase() === 'ok'
    ).length;

    return Math.round((healthyServices / services.length) * 100);
  }

  private calculateAverageResponseTime(services: ServiceHealthItem[]): number {
    if (!services || services.length === 0) return 0;

    const responseTimes = services
      .map(service => this.extractResponseTime(service.metric_text))
      .filter(time => time > 0);

    if (responseTimes.length === 0) return 0;

    const total = responseTimes.reduce((sum, time) => sum + time, 0);
    return Math.round(total / responseTimes.length);
  }

  private extractResponseTime(metricText: string | null | undefined): number {
    if (!metricText) return 0;

    const patterns = [
      /(\d+)ms/i,
      /(\d+)\s*ms/i,
      /latency[:\s]*(\d+)/i,
      /tempo\s*de\s*resposta[:\s]*(\d+)/i
    ];

    for (const pattern of patterns) {
      const match = metricText.match(pattern);
      if (match) {
        return parseInt(match[1], 10);
      }
    }

    return 0;
  }

  private calculateWorkersThroughput(workers: WorkerStatusResponse[]): number {
    if (!workers || workers.length === 0) return 0;

    const totalTasks = workers.reduce((sum, worker) => {
      return sum + (worker.tasks_processed || 0);
    }, 0);

    // Calcular throughput por minuto
    const timeWindowMinutes = 5; // Janela de 5 minutos
    return Math.round((totalTasks / timeWindowMinutes) * 10) / 10; // 1 casa decimal
  }

  private calculateWorkersLatency(workers: WorkerStatusResponse[]): number {
    if (!workers || workers.length === 0) return 0;

    // Calcular latência baseada no status dos workers
    const latencies = workers.map(worker => {
      const status = worker.status?.toLowerCase();
      switch (status) {
        case 'running':
          return 100; // Latência baixa para workers ativos
        case 'idle':
          return 150; // Latência média para workers ociosos
        case 'error':
          return 500; // Latência alta para workers com erro
        default:
          return 200; // Latência padrão
      }
    });

    const total = latencies.reduce((sum, latency) => sum + latency, 0);
    return Math.round(total / latencies.length);
  }

  private updateHistoricalData(): void {
    // Atualizar dados históricos sem processar novamente para evitar loop infinito
    const currentServices = this.services();
    const currentWorkers = this.workers();
    const currentSystem = this.systemStatus();

    // Apenas atualizar se houver dados novos significativos
    if (currentServices && currentServices.length > 0) {
      this.updateServicesHealth(currentServices);
    }
    if (currentWorkers && currentWorkers.length > 0) {
      this.updateWorkersPerformance(currentWorkers);
    }
    if (currentSystem) {
      this.updateSystemMetrics(currentSystem);
    }

    console.log('[Home] Historical data updated at', new Date().toLocaleTimeString());
  }

  constructor() {
    // Iniciar com arrays vazios; dados reais chegam via polling
    this.systemMetricsHistory.set([]);
    this.servicesHealthHistory.set([]);
    this.workersPerformanceHistory.set([]);

    // Setup real-time data processing with effects (must be in constructor for injection context)
    this.setupRealDataProcessing();
  }

  ngOnInit(): void {
    // Historico comeca vazio ate o backend responder
    // Detectar dispositivo móvel
    this.detectDeviceType();
    this.setupResizeObserver();
    this.setupTouchEvents();

    // Controle de inicializacao com loading animado
    setTimeout(() => {
      this.isInitializing.set(false);
      setTimeout(() => this.animationReady.set(true), 300);
    }, 1500);

    this.store.startPolling(UPDATE_INTERVAL_SECONDS * 1000);
    this.loadMissionPanelData();
    this.clockInterval = setInterval(() => {
      this.now.set(new Date().toLocaleString('pt-BR', {
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit', second: '2-digit'
      }));
    }, 1000);

    // Notificar inicialização
    this.uiService.showSuccess('🚀 Janus AI iniciado com sucesso!');
  }

  ngAfterViewInit(): void {
    // Iniciar animação de partículas
    this.initParticleAnimation();
  }

  ngOnDestroy(): void {
    this.store.stopPolling();
    if (this.clockInterval) clearInterval(this.clockInterval);
    if (this.historicalDataInterval) clearInterval(this.historicalDataInterval);
    if (this.particlesAnimation) cancelAnimationFrame(this.particlesAnimation);
    if (this.resizeObserver) this.resizeObserver.disconnect();
    this.removeTouchEvents();
  }

  private loadMissionPanelData(): void {
    forkJoin({
      autonomyPlan: this.api.getAutonomyPlan().pipe(catchError(() => of(null))),
      autonomyStatus: this.api.getAutonomyStatus().pipe(catchError(() => of(null))),
      audit: this.api.listAuditEvents({ limit: 25 }).pipe(
        catchError(() => of({ total: 0, events: [] } as { total: number; events: AuditEvent[] }))
      ),
      context: this.api.getCurrentContext().pipe(catchError(() => of(null))),
      quarantined: this.api.getQuarantinedMessages().pipe(
        catchError(() => of({ total_quarantined: 0, messages: [] } as { total_quarantined: number; messages: QuarantinedMessage[] }))
      ),
      pending: this.api.listPendingActions().pipe(catchError(() => of([])))
    }).subscribe(({ autonomyPlan, autonomyStatus, audit, context, quarantined, pending }) => {
      this.missionSteps.set(this.mapPlanToSteps(autonomyPlan));
      this.runbookEntries.set(this.mapAuditEvents(audit?.events || []));
      this.missionQueue.set(this.mapQuarantineToQueue(quarantined?.messages || []));
      this.approvalQueue.set(this.mapPendingApprovals(pending));
      this.contextInfo.set(context);
      this.pinnedFiles.set(this.extractPinnedFiles(context));
      this.updateRiskProfile(autonomyStatus);
      if (autonomyStatus) {
        this.missionPaused.set(!autonomyStatus.active);
      }
    });
  }

  private loadPendingActions(): void {
    this.api.listPendingActions().pipe(catchError(() => of([]))).subscribe((pending) => {
      this.approvalQueue.set(this.mapPendingApprovals(pending));
    });
  }

  private updateRiskProfile(status: AutonomyStatusResponse | null): void {
    const rawProfile = status?.config ? String(status.config['risk_profile'] ?? '') : '';
    const profile = rawProfile.toLowerCase();
    if (profile === 'conservative' || profile === 'balanced' || profile === 'aggressive') {
      this.missionRiskProfile.set(profile as MissionRiskProfile);
    } else {
      this.missionRiskProfile.set('unknown');
    }
  }

  private mapPlanToSteps(plan: AutonomyPlanResponse | null): MissionStep[] {
    const steps = plan?.plan ?? [];
    return steps.map((step, index) => ({
      id: `${step.tool}-${index}`,
      title: step.tool,
      detail: this.formatArgs(step.args),
      status: 'pending'
    }));
  }

  private mapAuditEvents(events: AuditEvent[]): RunbookEntry[] {
    return events.map((event, index) => {
      const tool = event.tool || event.endpoint || 'event';
      const action = event.action || event.endpoint || 'event';
      const status = this.mapRunStatus(event.status);
      const lastRun = typeof event.created_at === 'number' ? new Date(event.created_at * 1000) : undefined;
      const durationMs = typeof event.latency_ms === 'number' ? Math.round(event.latency_ms) : undefined;
      return {
        id: event.trace_id || `${tool}-${index}`,
        tool,
        action,
        status,
        durationMs,
        lastRun,
        artifacts: []
      };
    });
  }

  private mapRunStatus(status?: string | null): RunbookStatus {
    if (!status) return 'unknown';
    const normalized = status.toLowerCase();
    if (['success', 'ok', 'approved', 'completed'].includes(normalized)) return 'success';
    if (['error', 'failed', 'fail', 'rejected'].includes(normalized)) return 'error';
    if (['running', 'in_progress'].includes(normalized)) return 'running';
    if (['queued', 'pending'].includes(normalized)) return 'queued';
    return 'unknown';
  }

  private mapQuarantineToQueue(messages: QuarantinedMessage[]): MissionQueueItem[] {
    return messages.map((message) => ({
      id: message.message_id,
      title: message.queue || 'queue',
      detail: this.formatQuarantineDetail(message),
      eta: message.quarantined_at ? this.formatTimeAgo(message.quarantined_at) : 'n/a',
      priority: this.getPriorityFromFailures(message.failure_count)
    }));
  }

  private mapPendingApprovals(pending: PendingAction[]): ApprovalItem[] {
    return pending.map((item) => ({
      id: item.thread_id,
      title: item.thread_id,
      detail: item.message || 'Aguardando aprovacao',
      status: this.normalizeApprovalStatus(item.status)
    }));
  }

  private normalizeApprovalStatus(status?: string | null): ApprovalStatus {
    if (!status) return 'pending';
    const normalized = status.toLowerCase();
    if (normalized === 'approved') return 'approved';
    if (normalized === 'rejected') return 'rejected';
    return 'pending';
  }

  private extractPinnedFiles(context: ContextInfo | null): string[] {
    if (!context) return [];
    const keys = ['pinned_files', 'files', 'open_files', 'recent_files'];
    for (const key of keys) {
      const value = (context as Record<string, unknown>)[key];
      if (Array.isArray(value)) {
        return value.map((entry) => String(entry));
      }
    }
    return [];
  }

  private pickContextValue(context: ContextInfo | null, keys: string[]): string | null {
    if (!context) return null;
    for (const key of keys) {
      const value = this.formatContextValue((context as Record<string, unknown>)[key]);
      if (value) return value;
    }
    return null;
  }

  private formatContextValue(value: unknown): string | null {
    if (value == null) return null;
    if (typeof value === 'string') return value;
    if (typeof value === 'number' || typeof value === 'boolean') return String(value);
    if (Array.isArray(value)) {
      const flattened = value
        .map((entry) => (typeof entry === 'string' || typeof entry === 'number' ? String(entry) : null))
        .filter((entry): entry is string => Boolean(entry));
      if (flattened.length) return flattened.slice(0, 3).join(', ');
      const serialized = JSON.stringify(value);
      return serialized.length > 80 ? `${serialized.slice(0, 77)}...` : serialized;
    }
    try {
      const serialized = JSON.stringify(value);
      if (!serialized || serialized === '{}') return null;
      return serialized.length > 80 ? `${serialized.slice(0, 77)}...` : serialized;
    } catch {
      return null;
    }
  }

  private formatArgs(args?: Record<string, unknown>): string {
    if (!args || Object.keys(args).length === 0) return 'Sem parametros';
    const serialized = JSON.stringify(args);
    return serialized.length > 120 ? `${serialized.slice(0, 117)}...` : serialized;
  }

  private formatQuarantineDetail(message: QuarantinedMessage): string {
    const parts: string[] = [];
    if (message.reason) parts.push(message.reason);
    if (typeof message.failure_count === 'number') parts.push(`falhas ${message.failure_count}`);
    return parts.length ? parts.join(' - ') : 'Sem detalhes';
  }

  private getPriorityFromFailures(failures?: number): MissionPriority {
    if (failures == null) return 'low';
    if (failures >= 5) return 'high';
    if (failures >= 3) return 'medium';
    return 'low';
  }

  private getHistoryDelta<T>(history: T[], selector: (item: T) => number): number | null {
    if (history.length < 2) return null;
    const last = selector(history[history.length - 1]);
    const prev = selector(history[history.length - 2]);
    if (!Number.isFinite(last) || !Number.isFinite(prev)) return null;
    return last - prev;
  }

  private getTrendStatus(delta: number | null): 'up' | 'down' | 'stable' {
    if (delta == null) return 'stable';
    if (delta > 0) return 'up';
    if (delta < 0) return 'down';
    return 'stable';
  }

  private formatTrendValue(delta: number | null, unit: string, decimals: number): string | undefined {
    if (delta == null || !Number.isFinite(delta)) return undefined;
    const sign = delta > 0 ? '+' : '';
    return `${sign}${delta.toFixed(decimals)}${unit}`;
  }


  // Métodos de interatividade modernos
  onQuickAction(action: QuickAction): void {
    this.uiService.showInfo(`🎯 Executando: ${action.label}`);

    switch (action.id) {
      case 'refresh':
        this.refreshData();
        break;
      case 'analyze':
        this.runQuickAnalysis();
        break;
      case 'export':
        this.exportReport();
        break;
      case 'settings':
        this.openSettings();
        break;
    }
  }

  refreshData(): void {
    // Atualização real dos dados
    this.store.refreshSystemStatus(); // Atualiza sistema, serviços e carga
    this.store.refreshWorkers();   // Atualiza lista de workers (se houver metodo dedicado)
    this.loadMissionPanelData();

    // Como refreshSystemStatus retorna promise/void internamente e atualiza signals,
    // podemos apenas notificar que a requisição foi disparada.
    // O usuário verá os números mudarem reativamente.
    this.uiService.showSuccess('🔄 Sincronizando dados com o Núcleo...');
  }

  runQuickAnalysis(): void {
    console.log('🧠 [Home] runQuickAnalysis triggered');
    this.uiService.showLoading({ message: '🧠 Janus está se analisando...' });

    this.api.runAutoAnalysis().pipe(
      tap(() => console.log('Janus [Home] Auto-analysis API call made')),
      retry({ count: 1, delay: 1000 })
    ).subscribe({
      next: (report: AutoAnalysisResponse) => {
        this.uiService.hideLoading();

        // Formatar insights para exibição
        const insightsText = report.insights.map(i => `• ${i.issue}: ${i.suggestion}`).join('\n');

        this.uiService.showToast({
          message: `🔬 Análise Completa: ${report.overall_health.toUpperCase()}\n\n${insightsText}\n\nFato: ${report.fun_fact}`,
          duration: 10000,
          panelClass: 'success-toast'
        });
        this.animateCharts();
      },
      error: (err) => {
        this.uiService.hideLoading();
        this.uiService.showError('Sistemas cognitivos momentaneamente indisponíveis.');
      }
    });
  }

  exportReport(): void {
    this.uiService.showConfirm({
      title: '📊 Exportar Relatório Cognitivo',
      message: 'Deseja gerar o relatório completo de análise do sistema?',
      confirmText: 'Gerar PDF',
      cancelText: 'Cancelar'
    }).subscribe(result => {
      if (result) {
        this.uiService.showLoading({ message: '📄 Gerando relatório inteligente...' });

        setTimeout(() => {
          this.uiService.hideLoading();
          this.uiService.showSuccess('🎯 Relatório exportado com sucesso!');
          this.downloadReport();
        }, 2500);
      }
    });
  }

  openSettings(): void {
    this.showSettings.set(true);
  }

  closeSettings(): void {
    this.showSettings.set(false);
  }

  toggleMissionPause(): void {
    this.missionPaused.set(!this.missionPaused());
  }

  toggleRunDetails(runId: string): void {
    this.expandedRunId.set(this.expandedRunId() === runId ? null : runId);
  }

  updateApprovalStatus(approvalId: string, status: ApprovalStatus): void {
    if (status === 'pending') return;
    const request = status === 'approved'
      ? this.api.approvePendingAction(approvalId)
      : this.api.rejectPendingAction(approvalId);

    request.subscribe({
      next: () => this.loadPendingActions(),
      error: () => {
        this.uiService.showError('Falha ao atualizar aprovacao.');
      }
    });
  }

  private getMissionStatus(): MissionStatus {
    if (this.missionPaused()) return 'paused';
    if (this.loading() || this.isInitializing()) return 'initializing';
    const hasWorkerError = this.workers().some(w => (w.status || '').toLowerCase() === 'error');
    const hasServiceAlert = this.services().some(s => (s.status || '').toLowerCase() !== 'ok');
    if (hasWorkerError || hasServiceAlert || this.apiHealthy() !== 'ok') {
      return 'attention';
    }
    return 'active';
  }

  getMissionStatusLabel(status: MissionStatus): string {
    switch (status) {
      case 'active':
        return 'Ativo';
      case 'paused':
        return 'Pausado';
      case 'attention':
        return 'Atencao';
      case 'initializing':
        return 'Iniciando';
      default:
        return 'Indefinido';
    }
  }

  getMissionStatusBadge(status: MissionStatus): BadgeVariant {
    switch (status) {
      case 'active':
        return 'success';
      case 'paused':
        return 'neutral';
      case 'attention':
        return 'warning';
      case 'initializing':
        return 'info';
      default:
        return 'neutral';
    }
  }

  getRiskProfileLabel(profile: MissionRiskProfile): string {
    switch (profile) {
      case 'conservative':
        return 'Conservative';
      case 'balanced':
        return 'Balanced';
      case 'aggressive':
        return 'Aggressive';
      default:
        return 'Indefinido';
    }
  }

  getStepStatusLabel(status: MissionStepStatus): string {
    switch (status) {
      case 'done':
        return 'Concluido';
      case 'running':
        return 'Em curso';
      case 'pending':
        return 'Pendente';
      case 'blocked':
        return 'Bloqueado';
      default:
        return 'Indefinido';
    }
  }

  getStepBadge(status: MissionStepStatus): BadgeVariant {
    switch (status) {
      case 'done':
        return 'success';
      case 'running':
        return 'info';
      case 'pending':
        return 'neutral';
      case 'blocked':
        return 'error';
      default:
        return 'neutral';
    }
  }

  getRunStatusLabel(status: RunbookStatus): string {
    switch (status) {
      case 'success':
        return 'Sucesso';
      case 'running':
        return 'Executando';
      case 'queued':
        return 'Fila';
      case 'error':
        return 'Erro';
      case 'unknown':
        return 'Indefinido';
      default:
        return 'Indefinido';
    }
  }

  getRunBadge(status: RunbookStatus): BadgeVariant {
    switch (status) {
      case 'success':
        return 'success';
      case 'running':
        return 'info';
      case 'queued':
        return 'neutral';
      case 'error':
        return 'error';
      case 'unknown':
        return 'neutral';
      default:
        return 'neutral';
    }
  }

  getPriorityBadge(priority: MissionPriority): BadgeVariant {
    switch (priority) {
      case 'high':
        return 'error';
      case 'medium':
        return 'warning';
      case 'low':
        return 'neutral';
      default:
        return 'neutral';
    }
  }

  getApprovalBadge(status: ApprovalStatus): BadgeVariant {
    switch (status) {
      case 'approved':
        return 'success';
      case 'rejected':
        return 'error';
      case 'pending':
        return 'warning';
      default:
        return 'neutral';
    }
  }

  getApprovalStatusLabel(status: ApprovalStatus): string {
    switch (status) {
      case 'approved':
        return 'Aprovado';
      case 'rejected':
        return 'Rejeitado';
      case 'pending':
        return 'Pendente';
      default:
        return 'Pendente';
    }
  }

  onCardHover(cardId: string | null): void {
    this.hoveredCard.set(cardId);
  }

  onChartExpand(chartType: string): void {
    this.expandedChart.set(this.expandedChart() === chartType ? null : chartType);

    if (this.expandedChart()) {
      this.uiService.showInfo(`📈 Gráfico ${chartType} expandido`);
    }
  }

  onTimeRangeChange(range: string): void {
    const validRanges = ['1h', '6h', '24h', '7d'] as const;
    if ((validRanges as readonly string[]).includes(range)) {
      this.selectedTimeRange.set(range as typeof validRanges[number]);
      this.uiService.showInfo(`📅 Visualizando dados dos últimos ${range}`);
      this.refreshChartData(range);
    }
  }

  onServiceClick(service: ServiceHealthItem): void {
    this.uiService.showInfo(`🔍 Serviço ${service.name}: ${service.status}`);
  }

  onWorkerClick(worker: WorkerStatusResponse): void {
    this.uiService.showInfo(`⚙️ Worker ${worker.id}: ${worker.status} (${worker.tasks_processed} tarefas)`);
  }

  // Animações avançadas
  private animateCharts(): void {
    const charts = document.querySelectorAll('canvas');
    charts.forEach((chart, index) => {
      chart.style.transform = 'scale(1.02)';
      chart.style.transition = 'transform 0.3s ease';
      setTimeout(() => {
        chart.style.transform = 'scale(1)';
      }, 300 + (index * 100));
    });
  }

  private initParticleAnimation(): void {
    const canvas = this.particlesCanvas?.nativeElement;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;

    const particles: any[] = [];
    // Reduce particle count on mobile for better performance
    const particleCount = this.isMobile() ? 25 : 50;

    for (let i = 0; i < particleCount; i++) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.5,
        vy: (Math.random() - 0.5) * 0.5,
        size: Math.random() * 2 + 1,
        opacity: Math.random() * 0.5 + 0.2
      });
    }

    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      particles.forEach(particle => {
        particle.x += particle.vx;
        particle.y += particle.vy;

        if (particle.x < 0 || particle.x > canvas.width) particle.vx *= -1;
        if (particle.y < 0 || particle.y > canvas.height) particle.vy *= -1;

        ctx.beginPath();
        ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(99, 102, 241, ${particle.opacity})`;
        ctx.fill();
      });

      this.particlesAnimation = requestAnimationFrame(animate);
    };

    animate();
  }

  private downloadReport(): void {
    const report = this.generateReport();
    const blob = new Blob([report], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `janus-cognitive-report-${new Date().toISOString().split('T')[0]}.md`;
    link.click();
    URL.revokeObjectURL(url);
  }

  private generateReport(): string {
    const now = new Date().toLocaleString('pt-BR');
    const metrics = this.dashboardMetrics();
    return `
# 🧠 RELATÓRIO COGNITIVO DO SISTEMA JANUS
📅 ** Data:** ${now}
🆔 ** System ID:** LOCAL - JNS - ${Math.floor(Math.random() * 1000)}

    ---

## 📊 MÉTRICAS PRINCIPAIS
${metrics.map(m => `- **${m.label}**: ${m.value}${m.unit || ''} (${m.trendValue || 'estável'})`).join('\n')}

    ---

## 🔧 STATUS DO SISTEMA
      - ** Status Geral:** Operacional 🟢
- ** Disponibilidade:** ${this.servicesAvailability()}%
- ** Latência Média:** ${this.averageResponseTime()} ms
      - ** Throughput:** ${this.currentWorkersPerformance().throughput} t / min

    ---

## 🎯 SERVIÇOS DETALHADOS
      | Serviço | Status |
| ---------| --------|
      ${this.services().map(s => `| ${s.name} | ${s.status} |`).join('\n')}

    ---

## ⚙️ WORKERS ATIVOS
${this.workers().map(w => `- **Worker ${w.id}**: ${w.status} (${w.tasks_processed} tarefas processadas)`).join('\n')}

    ---

## 🚀 ANÁLISE AUTOMÁTICA
O sistema Janus realizou uma auto - verificação completa. 
> "A perfeição não é um estado, é um processo contínuo de iteração."
        `.trim();
  }

  private refreshChartData(range: string): void {
    // Simular atualização de dados baseado no range de tempo
    this.uiService.showInfo(`🔄 Atualizando dados para período de ${range} `);
  }

  // Mobile optimization methods
  private detectDeviceType(): void {
    const userAgent = navigator.userAgent.toLowerCase();
    const screenWidth = window.innerWidth;

    this.isMobile.set(screenWidth <= 768 || /android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini/i.test(userAgent));
    this.isTablet.set(screenWidth > 768 && screenWidth <= 1024);

    // Add touch device detection
    if ('ontouchstart' in window) {
      document.body.classList.add('touch-device');
    }
  }

  private setupResizeObserver(): void {
    if (typeof ResizeObserver !== 'undefined') {
      this.resizeObserver = new ResizeObserver(() => {
        this.detectDeviceType();
        // Reinitialize particle animation with new dimensions
        if (this.particlesAnimation) {
          this.initParticleAnimation();
        }
      });
      this.resizeObserver.observe(document.body);
    } else {
      // Fallback for browsers without ResizeObserver
      window.addEventListener('resize', () => {
        this.detectDeviceType();
      });
    }
  }

  private setupTouchEvents(): void {
    if ('ontouchstart' in window) {
      document.addEventListener('touchstart', this.handleTouchStart.bind(this), { passive: true });
      document.addEventListener('touchmove', this.handleTouchMove.bind(this), { passive: true });
      document.addEventListener('touchend', this.handleTouchEnd.bind(this), { passive: true });
    }
  }

  private removeTouchEvents(): void {
    document.removeEventListener('touchstart', this.handleTouchStart.bind(this));
    document.removeEventListener('touchmove', this.handleTouchMove.bind(this));
    document.removeEventListener('touchend', this.handleTouchEnd.bind(this));
  }

  private handleTouchStart(event: TouchEvent): void {
    if (event.touches.length === 1) {
      this.touchStartX.set(event.touches[0].clientX);
      this.touchStartY.set(event.touches[0].clientY);
    }
  }

  private handleTouchMove(event: TouchEvent): void {
    // Prevent default scrolling for horizontal swipes on cards
    if (event.touches.length === 1) {
      const deltaX = event.touches[0].clientX - this.touchStartX();
      const deltaY = event.touches[0].clientY - this.touchStartY();

      // If horizontal swipe is detected and vertical movement is minimal
      if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 10) {
        event.preventDefault();
      }
    }
  }

  private handleTouchEnd(event: TouchEvent): void {
    if (event.changedTouches.length === 1) {
      const deltaX = event.changedTouches[0].clientX - this.touchStartX();
      const deltaY = event.changedTouches[0].clientY - this.touchStartY();

      // Detect swipe gestures
      if (Math.abs(deltaX) > this.swipeThreshold || Math.abs(deltaY) > this.swipeThreshold) {
        this.handleSwipe(deltaX, deltaY);
      }
    }
  }

  private handleSwipe(deltaX: number, deltaY: number): void {
    // Handle horizontal swipes for chart navigation
    if (Math.abs(deltaX) > Math.abs(deltaY)) {
      if (deltaX > 0) {
        // Swipe right - previous time range
        this.cycleTimeRange('prev');
      } else {
        // Swipe left - next time range
        this.cycleTimeRange('next');
      }
    } else {
      // Handle vertical swipes for chart expansion
      if (deltaY < 0) {
        // Swipe up - expand chart
        this.expandRandomChart();
      } else {
        // Swipe down - collapse chart
        this.expandedChart.set(null);
      }
    }
  }

  private cycleTimeRange(direction: 'prev' | 'next'): void {
    const ranges: Array<'1h' | '6h' | '24h' | '7d'> = ['1h', '6h', '24h', '7d'];
    const currentIndex = ranges.indexOf(this.selectedTimeRange());

    let newIndex: number;
    if (direction === 'next') {
      newIndex = (currentIndex + 1) % ranges.length;
    } else {
      newIndex = currentIndex === 0 ? ranges.length - 1 : currentIndex - 1;
    }

    this.selectedTimeRange.set(ranges[newIndex]);
    this.refreshChartData(ranges[newIndex]);
  }

  private expandRandomChart(): void {
    const chartIds = ['performance', 'health', 'workers'];
    const currentExpanded = this.expandedChart();

    if (!currentExpanded) {
      this.expandedChart.set(chartIds[0]);
    } else {
      const currentIndex = chartIds.indexOf(currentExpanded);
      const nextIndex = (currentIndex + 1) % chartIds.length;
      this.expandedChart.set(chartIds[nextIndex]);
    }
  }

  // TrackBy functions for template optimization
  trackByMissionStepId(index: number, step: MissionStep): string {
    return step.id;
  }

  trackByRunbookId(index: number, run: RunbookEntry): string {
    return run.id;
  }

  trackByQueueId(index: number, item: MissionQueueItem): string {
    return item.id;
  }

  trackByApprovalId(index: number, item: ApprovalItem): string {
    return item.id;
  }

  trackByContextLabel(index: number, item: MissionContextItem): string {
    return item.label;
  }

  trackByPinnedFile(index: number, file: string): string {
    return file;
  }

  trackByMetricLabel(index: number, metric: DashboardMetric): string {
    return metric.label;
  }

  trackByServiceName(index: number, service: ServiceHealthItem): string {
    return service.name;
  }

  trackByWorkerId(index: number, worker: WorkerStatusResponse): string {
    return worker.id;
  }

  // Helper method to calculate progress bar value
  getProgressValue(metric: DashboardMetric): number {
    const value = Number(metric.value);
    if (isNaN(value)) return 0;

    switch (metric.label) {
      case 'Disponibilidade':
        return value;
      case 'Latência Média':
        return Math.max(0, 100 - (value / 10));
      case 'Throughput':
        return Math.min(100, value / 2);
      default:
        return Math.min(100, value / 10);
    }
  }

  getProgressColor(metric: DashboardMetric): string {
    if (metric.color.includes('green')) return 'primary';
    if (metric.color.includes('blue')) return 'accent';
    return 'warn';
  }

  // servicesAvailability and averageResponseTime are now computed signals defined above

  private updateSystemMetrics(sys?: { cpu_usage_percent?: number; memory_usage_percent?: number; disk_usage_percent?: number; uptime_seconds?: number }): void {
    const history = untracked(() => this.systemMetricsHistory());
    const newEntry = { timestamp: new Date(), cpu: sys?.cpu_usage_percent ?? 0, memory: sys?.memory_usage_percent ?? 0, disk: sys?.disk_usage_percent ?? 0 };
    const newHistory = [...history, newEntry];
    if (newHistory.length > 20) newHistory.shift();
    this.systemMetricsHistory.set(newHistory);
    this.currentSystemMetrics.set({ cpu: newEntry.cpu, memory: newEntry.memory, disk: newEntry.disk });
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

  formatUptime(seconds?: number): string {
    if (!seconds) return '0s';
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (days > 0) return `${days}d ${hours} h`;
    if (hours > 0) return `${hours}h ${minutes} m`;
    if (minutes > 0) return `${minutes}m ${secs} s`;
    return `${secs} s`;
  }

  formatTimeAgo(date?: Date | string | number | null): string {
    if (!date) return 'n/a';
    const d = new Date(date);
    if (Number.isNaN(d.getTime())) return 'n/a';
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (days > 0) return `${days}d ago`;
    if (hours > 0) return `${hours}h ago`;
    if (minutes > 0) return `${minutes}m ago`;
    return 'now';
  }

  executeQuickAction(action: QuickAction): void {
    this.onQuickAction(action);
  }

  get performanceChartData() {
    return this.systemStatusChartData;
  }

  get performanceChartOptions() {
    return this.chartOptions;
  }

  private totalThroughput(): string {
    const workers = this.workers();
    if (!workers || workers.length === 0) return '0';
    const totalPerMin = workers.reduce((sum, w) => {
      const minutes = Math.max(1, (Date.now() - new Date(w.last_heartbeat).getTime()) / 60000);
      return sum + (w.tasks_processed || 0) / minutes;
    }, 0);
    return totalPerMin.toFixed(1);
  }

  private averageLatency(): number {
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

  private checkAlerts(services: ServiceHealthItem[], workers: WorkerStatusResponse[], sys?: { uptime_seconds?: number }): void {
    const latency = this.averageLatency();
    if (latency > LATENCY_THRESHOLD_MS) {
      this.uiService.showWarning(`⚠️ Latência elevada detectada: ${latency} ms`);
    }
  }

  // Host binding para tema dinâmico
  @HostBinding('attr.data-theme') get themeAttr() {
    return this.theme();
  }
}
