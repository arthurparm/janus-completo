import { ComponentFixture, TestBed } from '@angular/core/testing';
import { BehaviorSubject, Observable, of } from 'rxjs';

import { SystemHud } from './system-hud';
import { SystemStatusService } from '../../../../core/services/system-status.service';

describe('SystemHud', () => {
  let component: SystemHud;
  let fixture: ComponentFixture<SystemHud>;
  let systemStatus$: Observable<{
    app_name: string;
    version: string;
    environment: string;
    status: string;
    uptime_seconds: number | null;
  }>;
  const healthSubject = new BehaviorSubject({
    services: [
      { key: 'agent', name: 'Agent Service', status: 'ok' as const, metric_text: 'Agentes: 2' },
      {
        key: 'memory',
        name: 'Memory Service',
        status: 'unknown' as const,
        metric_text: 'Uso: indisponivel',
        capability: 'Memoria operacional',
        user_impact: 'Nao ha telemetria confiavel de memoria.',
        recommended_action: 'Restaurar coleta de metricas.',
      },
      {
        key: 'workers',
        name: 'Workers',
        status: 'degraded' as const,
        metric_text: 'Workers ativos: 0, parados: 1, desabilitados: 0, erros: 0, desconhecidos: 0',
        capability: 'Workers e operacoes assincronas',
        user_impact: 'Algumas rotinas assincronas podem atrasar.',
        recommended_action: 'Verificar workers parados.',
      },
    ],
  });

  beforeEach(async () => {
    systemStatus$ = of({
      app_name: 'Janus',
      version: '0.5.44',
      environment: 'test',
      status: 'ok',
      uptime_seconds: 42,
    });

    await TestBed.configureTestingModule({
      imports: [SystemHud],
      providers: [
        {
          provide: SystemStatusService,
          useValue: {
            getSystemStatus: vi.fn(() => systemStatus$),
            getServicesHealth: vi.fn(() => healthSubject.asObservable()),
            isSystemHealthy$: of(false),
          },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(SystemHud);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('deve resumir worker degradado antes de telemetria unknown', () => {
    const summary = component.getHealthSummary(healthSubject.value);

    expect(summary.severity).toBe('degraded');
    expect(summary.label).toBe('Degradado');
    expect(summary.affectedCount).toBe(2);
    expect(summary.totalCount).toBe(3);
  });

  it('deve priorizar estado critico quando qualquer servico esta em erro', () => {
    const summary = component.getHealthSummary({
      services: [
        { key: 'agent', name: 'Agent Service', status: 'degraded', metric_text: 'N/A' },
        { key: 'llm', name: 'LLM Gateway', status: 'error', metric_text: 'CB Abertos: 1' },
      ],
    });

    expect(summary.severity).toBe('critical');
    expect(summary.label).toBe('Critico');
    expect(summary.affectedCount).toBe(2);
  });

  it('deve exibir estado sem telemetria quando nao ha servicos', () => {
    const summary = component.getHealthSummary({ services: [] });

    expect(summary.severity).toBe('unknown');
    expect(summary.label).toBe('Sem telemetria');
    expect(summary.detail).toContain('Nenhum servico');
  });

  it('deve renderizar rotulo operacional no gatilho do HUD', () => {
    const text = fixture.nativeElement.textContent as string;

    expect(text).toContain('Health');
    expect(text).toContain('Degradado');
    expect(text).toContain('2/3');
  });

  it('deve mostrar capacidade afetada, impacto ao usuario e acao recomendada no painel', () => {
    fixture = TestBed.createComponent(SystemHud);
    component = fixture.componentInstance;
    component.isOpen = true;
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Memoria operacional');
    expect(text).toContain('Nao ha telemetria confiavel de memoria.');
    expect(text).toContain('Restaurar coleta de metricas.');
    expect(text).toContain('Workers e operacoes assincronas');
    expect(text).toContain('Verificar workers parados.');
  });

  it('deve usar icone textual especifico para workers', () => {
    expect(component.getIconForService('workers')).toBe('WRK');
  });

  it('deve exibir uptime indisponivel quando status degradado nao traz uptime', () => {
    systemStatus$ = of({
      app_name: 'Janus',
      version: '0.5.44',
      environment: 'test',
      status: 'DEGRADED',
      uptime_seconds: null,
    });
    fixture = TestBed.createComponent(SystemHud);
    component = fixture.componentInstance;
    component.isOpen = true;
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('uptime indisponivel');
    expect(text).not.toContain('s uptime');
  });
});
