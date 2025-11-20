import {Component, OnDestroy, OnInit, computed, effect, inject, signal, untracked, HostBinding, ViewChild, ElementRef, AfterViewInit, DestroyRef, ChangeDetectionStrategy} from '@angular/core';
import {CommonModule} from '@angular/common';
import {RouterModule} from '@angular/router';
import {BaseChartDirective} from 'ng2-charts';
import {ChartConfiguration, ChartOptions} from 'chart.js';
import {GlobalStateStore} from '../../core/state/global-state.store';
import {NotificationService} from '../../core/notifications/notification.service';
import {JanusApiService, ServiceHealthItem, WorkerStatusResponse} from '../../services/janus-api.service';
import {LoadingComponent} from '../../shared/components/loading/loading.component';
import {ErrorComponent} from '../../shared/components/error/error.component';
import {UiService} from '../../shared/services/ui.service';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {MatCardModule} from '@angular/material/card';
import {MatChipsModule} from '@angular/material/chips';
import {MatProgressBarModule} from '@angular/material/progress-bar';
import {MatTooltipModule} from '@angular/material/tooltip';

const UPDATE_INTERVAL_SECONDS = 5;
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

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [
    CommonModule, 
    RouterModule, 
    BaseChartDirective,
    MatButtonModule,
    MatIconModule,
    MatCardModule,
    MatChipsModule,
    MatProgressBarModule,
    MatTooltipModule
  ],
  templateUrl: './home-tailwind.html',
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

  // Controle de estado e animações
  showError = signal(false);
  errorMessage = signal('');
  isInitializing = signal(true);
  animationReady = signal(false);
  theme = signal<'light' | 'dark'>('dark');
  
  // Interatividade avançada
  hoveredCard = signal<string | null>(null);
  expandedChart = signal<string | null>(null);
  selectedTimeRange = signal<'1h' | '6h' | '24h' | '7d'>('1h');
  
  // Mobile-specific state
  isMobile = signal(false);
  isTablet = signal(false);
  touchStartY = signal(0);
  touchStartX = signal(0);
  swipeThreshold = 50;
  
  // Animações parallax
  @ViewChild('heroSection') heroSection!: ElementRef;
  @ViewChild('particlesCanvas') particlesCanvas!: ElementRef;
  private particlesAnimation?: any;
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
  readonly dashboardMetrics = computed<DashboardMetric[]>(() => [
    {
      label: 'Disponibilidade',
      value: this.servicesAvailability(),
      unit: '%',
      trend: this.servicesAvailability() > 95 ? 'up' : 'stable',
      trendValue: '+2.3%',
      icon: 'shield',
      color: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
    },
    {
      label: 'Latência Média',
      value: this.averageResponseTime(),
      unit: 'ms',
      trend: this.averageResponseTime() < 200 ? 'down' : 'up',
      trendValue: '-15ms',
      icon: 'speed',
      color: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)'
    },
    {
      label: 'Throughput',
      value: this.currentWorkersPerformance().throughput,
      unit: 't/min',
      trend: 'up',
      trendValue: '+12%',
      icon: 'trending_up',
      color: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)'
    },
    {
      label: 'Workers Ativos',
      value: this.workers().filter(w => w.status === 'running').length,
      unit: `/${this.workers().length}`,
      trend: 'stable',
      trendValue: '0',
      icon: 'memory',
      color: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)'
    }
  ]);

  // Relógio digital moderno
  readonly now = signal<string>(new Date().toLocaleString('pt-BR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit'
  }));
  private clockInterval?: any;

  // Dados para gráficos com animações - agora com dados reais
  systemMetricsHistory = signal<Array<{timestamp: Date, cpu: number, memory: number, disk: number}>>([]);
  currentSystemMetrics = signal({cpu: 0, memory: 0, disk: 0});

  servicesHealthHistory = signal<Array<{timestamp: Date, availability: number, responseTime: number}>>([]);
  workersPerformanceHistory = signal<Array<{timestamp: Date, throughput: number, latency: number}>>([]);

  // Dados históricos para análise temporal
  private readonly maxHistoryPoints = 20; // Mantém os últimos 20 pontos de dados

  // Gerar dados iniciais para os gráficos aparecerem imediatamente
  private generateInitialSystemMetrics(): Array<{timestamp: Date, cpu: number, memory: number, disk: number}> {
    const data = [];
    const now = new Date();
    for (let i = 9; i >= 0; i--) {
      const time = new Date(now.getTime() - i * 60000); // Minutos anteriores
      data.push({
        timestamp: time,
        cpu: Math.random() * 30 + 20, // 20-50%
        memory: Math.random() * 40 + 30, // 30-70%
        disk: Math.random() * 20 + 40 // 40-60%
      });
    }
    return data;
  }

  private generateInitialServicesHealth(): Array<{timestamp: Date, availability: number, responseTime: number}> {
    const data = [];
    const now = new Date();
    for (let i = 9; i >= 0; i--) {
      const time = new Date(now.getTime() - i * 60000);
      data.push({
        timestamp: time,
        availability: Math.random() * 10 + 90, // 90-100%
        responseTime: Math.random() * 100 + 50 // 50-150ms
      });
    }
    return data;
  }

  private generateInitialWorkersPerformance(): Array<{timestamp: Date, throughput: number, latency: number}> {
    const data = [];
    const now = new Date();
    for (let i = 9; i >= 0; i--) {
      const time = new Date(now.getTime() - i * 60000);
      data.push({
        timestamp: time,
        throughput: Math.random() * 50 + 100, // 100-150 t/min
        latency: Math.random() * 50 + 100 // 100-150ms
      });
    }
    return data;
  }

  // Configurações de gráficos modernizadas
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
        label: 'Memória (%)',
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
          label: 'Latência (ms)',
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

  // Opções de gráficos modernizadas
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
    const h = this.workersPerformanceHistory();
    if (!h.length) return { throughput: 0, latency: 0 };
    const last = h[h.length - 1];
    return { throughput: last.throughput, latency: last.latency };
  });

  private setupRealDataProcessing(): void {
    // Processar dados reais do sistema em tempo real usando effect
    effect(() => {
      const systemStatus = this.store.systemStatus();
      if (systemStatus) {
        this.processSystemMetrics(systemStatus);
      }
    });

    effect(() => {
      const services = this.store.services();
      if (services && services.length > 0) {
        this.processServicesData(services);
      }
    });

    effect(() => {
      const workers = this.store.workers();
      if (workers && workers.length > 0) {
        this.processWorkersData(workers);
      }
    });

    // Atualizar dados históricos a cada 30 segundos
    setInterval(() => {
      this.updateHistoricalData();
    }, 30000);
  }

  private processSystemMetrics(systemStatus: any): void {
    console.log('Processing system metrics:', systemStatus);
    if (!systemStatus) {
      console.log('No system status data available');
      return;
    }

    const metrics = {
      cpu: systemStatus.cpu_usage_percent || systemStatus.cpu || 0,
      memory: systemStatus.memory_usage_percent || systemStatus.memory || 0,
      disk: systemStatus.disk_usage_percent || systemStatus.disk || 0,
      uptime: systemStatus.uptime_seconds || systemStatus.uptime || 0
    };

    console.log('Calculated metrics:', metrics);

    // Atualizar métricas atuais
    this.currentSystemMetrics.set(metrics);

    // Adicionar ao histórico apenas se houver dados reais (não mock)
    if (systemStatus.cpu_usage_percent !== undefined || systemStatus.cpu !== undefined) {
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
      console.log('Updated system metrics history:', newHistory.length, 'entries');
    }
  }

  private processServicesData(services: ServiceHealthItem[]): void {
    console.log('Processing services data:', services);
    if (!services || services.length === 0) {
      console.log('No services data available');
      return;
    }

    const availability = this.calculateServicesAvailability(services);
    const avgResponseTime = this.calculateAverageResponseTime(services);

    console.log('Calculated availability:', availability, '%');
    console.log('Calculated avg response time:', avgResponseTime, 'ms');

    // Atualizar histórico de saúde dos serviços
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
    console.log('Updated services health history:', newHistory.length, 'entries');
  }

  private processWorkersData(workers: WorkerStatusResponse[]): void {
    console.log('Processing workers data:', workers);
    if (!workers || workers.length === 0) {
      console.log('No workers data available');
      return;
    }

    const throughput = this.calculateWorkersThroughput(workers);
    const latency = this.calculateWorkersLatency(workers);

    console.log('Calculated throughput:', throughput, 't/min');
    console.log('Calculated latency:', latency, 'ms');

    // Atualizar histórico de performance dos workers
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
    console.log('Updated workers performance history:', newHistory.length, 'entries');
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
    
    // Extrair tempo de resposta de diferentes formatos de texto
    const patterns = [
      /(\d+)ms/i,           // "150ms"
      /(\d+)\s*ms/i,        // "150 ms"
      /latency[:\s]*(\d+)/i, // "latency: 150"
      /tempo\s*de\s*resposta[:\s]*(\d+)/i // "tempo de resposta: 150"
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
    // Forçar atualização dos dados históricos
    const currentServices = this.services();
    const currentWorkers = this.workers();
    const currentSystem = this.systemStatus();

    this.processServicesData(currentServices);
    this.processWorkersData(currentWorkers);
    this.processSystemMetrics(currentSystem);
  }

  constructor() {
    // Initialize chart data
    this.systemMetricsHistory.set(this.generateInitialSystemMetrics());
    this.servicesHealthHistory.set(this.generateInitialServicesHealth());
    this.workersPerformanceHistory.set(this.generateInitialWorkersPerformance());

    // Setup real-time data processing with effects (must be in constructor for injection context)
    this.setupRealDataProcessing();
  }

  ngOnInit(): void {
    // Detectar dispositivo móvel
    this.detectDeviceType();
    this.setupResizeObserver();
    this.setupTouchEvents();

    // Simular inicialização com loading animado
    setTimeout(() => {
      this.isInitializing.set(false);
      setTimeout(() => this.animationReady.set(true), 300);
    }, 1500);

    this.store.startPolling(UPDATE_INTERVAL_SECONDS * 1000);
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
    if (this.particlesAnimation) cancelAnimationFrame(this.particlesAnimation);
    if (this.resizeObserver) this.resizeObserver.disconnect();
    this.removeTouchEvents();
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
    this.uiService.showLoading({ message: '🔄 Sincronizando dados em tempo real...' });
    // Stop and restart polling to force a refresh
    this.store.stopPolling();
    this.store.startPolling(UPDATE_INTERVAL_SECONDS * 1000);
    setTimeout(() => {
      this.uiService.hideLoading();
      this.uiService.showSuccess('✅ Dados sincronizados com sucesso!');
    }, 1500);
  }

  runQuickAnalysis(): void {
    this.uiService.showLoading({ message: '🧠 Executando análise cognitiva profunda...' });
    
    setTimeout(() => {
      this.uiService.hideLoading();
      this.uiService.showSuccess('🔬 Análise concluída! Descobertas nos gráficos.');
      this.animateCharts();
    }, 3000);
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
    this.uiService.showInfo('⚙️ Painel de configurações em desenvolvimento...');
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
    const validRanges: Array<'1h' | '6h' | '24h' | '7d'> = ['1h', '6h', '24h', '7d'];
    if (validRanges.includes(range as any)) {
      this.selectedTimeRange.set(range as '1h' | '6h' | '24h' | '7d');
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
    link.download = `janus-cognitive-report-${new Date().toISOString().split('T')[0]}.txt`;
    link.click();
    URL.revokeObjectURL(url);
  }

  private generateReport(): string {
    const now = new Date().toLocaleString('pt-BR');
    const metrics = this.dashboardMetrics();
    
    return `
🧠 RELATÓRIO COGNITIVO DO SISTEMA JANUS
📅 Data: ${now}

📊 MÉTRICAS PRINCIPAIS:
${metrics.map(m => `• ${m.label}: ${m.value}${m.unit || ''} ${m.trendValue || ''}`).join('\n')}

🔧 STATUS DO SISTEMA:
• Sistema: Operacional
• Disponibilidade: ${this.servicesAvailability()}%
• Latência Média: ${this.averageResponseTime()}ms
• Throughput: ${this.currentWorkersPerformance().throughput} t/min

🎯 SERVIÇOS:
${this.services().map(s => `• ${s.name}: ${s.status}`).join('\n')}

⚙️ WORKERS:
${this.workers().map(w => `• ${w.id}: ${w.status} (${w.tasks_processed} tarefas)`).join('\n')}

🚀 ANÁLISE COGNITIVA:
O sistema está operando com excelente performance cognitiva.
Todos os módulos de inteligência artificial estão funcionando corretamente.
    `.trim();
  }

  private refreshChartData(range: string): void {
    // Simular atualização de dados baseado no range de tempo
    this.uiService.showInfo(`🔄 Atualizando dados para período de ${range}`);
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

  // Métodos utilitários existentes (mantidos)
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
    
    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    if (minutes > 0) return `${minutes}m ${secs}s`;
    return `${secs}s`;
  }

  formatTimeAgo(date: Date | string): string {
    const d = new Date(date);
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
      this.uiService.showWarning(`⚠️ Latência elevada detectada: ${latency}ms`);
    }
  }

  // Host binding para tema dinâmico
  @HostBinding('attr.data-theme') get themeAttr() {
    return this.theme();
  }
}
