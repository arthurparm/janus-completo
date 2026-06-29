import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { firstValueFrom } from 'rxjs';

import { SystemStatusService } from './system-status.service';
import { AppLoggerService } from './app-logger.service';
import { API_BASE_URL } from '../../services/api.config';
import { SUPPRESS_HTTP_ERROR_LOG } from '../interceptors/error-logger.interceptor';

describe('SystemStatusService', () => {
  let service: SystemStatusService;
  let http: HttpTestingController;
  let logger: { error: ReturnType<typeof vi.fn>; warn: ReturnType<typeof vi.fn> };
  const servicesHealthUrl = `${API_BASE_URL}/v1/system/health/services`;
  const systemStatusUrl = `${API_BASE_URL}/v1/system/status`;

  beforeEach(() => {
    logger = {
      error: vi.fn(),
      warn: vi.fn(),
    };

    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [
        {
          provide: AppLoggerService,
          useValue: logger,
        },
      ],
    });
    service = TestBed.inject(SystemStatusService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('deve manter o sistema saudavel quando todos os servicos estao ok', async () => {
    const states: boolean[] = [];
    const healthSubscription = service.isSystemHealthy$.subscribe(value => states.push(value));
    const responsePromise = firstValueFrom(service.getServicesHealth());

    await new Promise(resolve => setTimeout(resolve, 0));

    const req = http.expectOne(servicesHealthUrl);
    expect(req.request.method).toBe('GET');
    expect(req.request.context.get(SUPPRESS_HTTP_ERROR_LOG)).toBe(true);
    req.flush({
      services: [
        { key: 'agents', name: 'Agent Orchestrator', status: 'ok', metric_text: 'Ativo' },
        { key: 'memory', name: 'Memory Service', status: 'ok', metric_text: 'Uso: 128 MB' },
      ],
    });

    await responsePromise;
    expect(states.at(-1)).toBe(true);
    healthSubscription.unsubscribe();
  });

  it('deve compartilhar o polling de health entre assinantes simultaneos', async () => {
    const firstResponsePromise = firstValueFrom(service.getServicesHealth());
    const secondResponsePromise = firstValueFrom(service.getServicesHealth());

    await new Promise(resolve => setTimeout(resolve, 0));

    const req = http.expectOne(servicesHealthUrl);
    expect(req.request.method).toBe('GET');
    http.expectNone(servicesHealthUrl);
    req.flush({
      services: [
        { key: 'agent', name: 'Agent Service', status: 'ok', metric_text: 'Agentes: 1' },
      ],
    });

    const [first, second] = await Promise.all([firstResponsePromise, secondResponsePromise]);
    expect(first).toEqual(second);
  });

  it('deve marcar o sistema como nao saudavel para estados degraded ou unknown', async () => {
    const states: boolean[] = [];
    const healthSubscription = service.isSystemHealthy$.subscribe(value => states.push(value));
    const responsePromise = firstValueFrom(service.getServicesHealth());

    await new Promise(resolve => setTimeout(resolve, 0));

    const req = http.expectOne(servicesHealthUrl);
    req.flush({
      services: [
        { key: 'agents', name: 'Agent Orchestrator', status: 'degraded', metric_text: 'N/A' },
        { key: 'memory', name: 'Memory Service', status: 'unknown', metric_text: 'Uso: indisponivel' },
      ],
    });

    await responsePromise;
    expect(states.at(-1)).toBe(false);
    healthSubscription.unsubscribe();
  });

  it('deve marcar o sistema como nao saudavel quando a lista de servicos vier vazia', async () => {
    const states: boolean[] = [];
    const healthSubscription = service.isSystemHealthy$.subscribe(value => states.push(value));
    const responsePromise = firstValueFrom(service.getServicesHealth());

    await new Promise(resolve => setTimeout(resolve, 0));

    const req = http.expectOne(servicesHealthUrl);
    req.flush({ services: [] });

    await responsePromise;
    expect(states.at(-1)).toBe(false);
    healthSubscription.unsubscribe();
  });

  it('deve tratar backend desconectado como warning de conectividade, nao erro de aplicacao', async () => {
    const responsePromise = firstValueFrom(service.getServicesHealth());

    await new Promise(resolve => setTimeout(resolve, 0));

    const req = http.expectOne(servicesHealthUrl);
    req.flush(null, { status: 0, statusText: 'Unknown Error' });

    const response = await responsePromise;
    expect(response.services).toEqual([]);
    expect(logger.warn).toHaveBeenCalledWith(
      '[SystemStatusService] Backend indisponivel ao buscar saude dos servicos',
      expect.anything()
    );
    expect(logger.error).not.toHaveBeenCalled();
  });

  it('deve manter erro para falha HTTP real do endpoint de health', async () => {
    const responsePromise = firstValueFrom(service.getServicesHealth());

    await new Promise(resolve => setTimeout(resolve, 0));

    const req = http.expectOne(servicesHealthUrl);
    req.flush({ detail: 'boom' }, { status: 500, statusText: 'Internal Server Error' });

    const response = await responsePromise;
    expect(response.services).toEqual([]);
    expect(logger.warn).not.toHaveBeenCalled();
    expect(logger.error).toHaveBeenCalled();
  });

  it('deve normalizar payload de health sem lista de servicos para estado sem telemetria', async () => {
    const states: boolean[] = [];
    const healthSubscription = service.isSystemHealthy$.subscribe(value => states.push(value));
    const responsePromise = firstValueFrom(service.getServicesHealth());

    await new Promise(resolve => setTimeout(resolve, 0));

    const req = http.expectOne(servicesHealthUrl);
    req.flush({ status: 'ok' });

    const response = await responsePromise;
    expect(response.services).toEqual([]);
    expect(states.at(-1)).toBe(false);
    healthSubscription.unsubscribe();
  });

  it('deve normalizar item malformado como unknown para impedir falso saudavel', async () => {
    const states: boolean[] = [];
    const healthSubscription = service.isSystemHealthy$.subscribe(value => states.push(value));
    const responsePromise = firstValueFrom(service.getServicesHealth());

    await new Promise(resolve => setTimeout(resolve, 0));

    const req = http.expectOne(servicesHealthUrl);
    req.flush({
      services: [
        { key: 'agent', name: 'Agent Service', status: 'ok', metric_text: 'Ativo' },
        { key: 'broken', name: '', status: 'operational', metric_text: 42 },
      ],
    });

    const response = await responsePromise;
    expect(response.services).toEqual([
      {
        key: 'agent',
        name: 'Agent Service',
        status: 'ok',
        metric_text: 'Ativo',
        capability: undefined,
        user_impact: undefined,
        recommended_action: undefined,
      },
      {
        key: 'broken',
        name: 'Servico sem nome',
        status: 'unknown',
        metric_text: undefined,
        capability: undefined,
        user_impact: undefined,
        recommended_action: undefined,
      },
    ]);
    expect(states.at(-1)).toBe(false);
    healthSubscription.unsubscribe();
  });

  it('deve preservar impacto operacional de IA/ML quando o backend enviar o contrato enriquecido', async () => {
    const responsePromise = firstValueFrom(service.getServicesHealth());

    await new Promise(resolve => setTimeout(resolve, 0));

    const req = http.expectOne(servicesHealthUrl);
    req.flush({
      services: [
        {
          key: 'llm',
          name: 'LLM Gateway',
          status: 'degraded',
          metric_text: 'CB Abertos: 1, Cache: 0',
          capability: 'Chat, raciocinio e modelos',
          user_impact: 'Chat pode responder com latencia maior ou fallback de modelo.',
          recommended_action: 'Verificar provedores, circuit breakers, rate limits e modelo local.',
        },
      ],
    });

    const response = await responsePromise;
    expect(response.services[0]).toEqual({
      key: 'llm',
      name: 'LLM Gateway',
      status: 'degraded',
      metric_text: 'CB Abertos: 1, Cache: 0',
      capability: 'Chat, raciocinio e modelos',
      user_impact: 'Chat pode responder com latencia maior ou fallback de modelo.',
      recommended_action: 'Verificar provedores, circuit breakers, rate limits e modelo local.',
    });
  });

  it('deve preservar health de workers como capacidade operacional do HUD', async () => {
    const responsePromise = firstValueFrom(service.getServicesHealth());

    await new Promise(resolve => setTimeout(resolve, 0));

    const req = http.expectOne(servicesHealthUrl);
    req.flush({
      services: [
        {
          key: 'workers',
          name: 'Workers',
          status: 'degraded',
          metric_text: 'Workers ativos: 0, parados: 1, desabilitados: 0, erros: 0, desconhecidos: 0',
          capability: 'Workers e operacoes assincronas',
          user_impact: 'Algumas rotinas assincronas podem atrasar ou ficar indisponiveis.',
          recommended_action: 'Verificar workers parados/desabilitados e iniciar filas antes de cargas longas.',
        },
      ],
    });

    const response = await responsePromise;
    expect(response.services[0]).toEqual({
      key: 'workers',
      name: 'Workers',
      status: 'degraded',
      metric_text: 'Workers ativos: 0, parados: 1, desabilitados: 0, erros: 0, desconhecidos: 0',
      capability: 'Workers e operacoes assincronas',
      user_impact: 'Algumas rotinas assincronas podem atrasar ou ficar indisponiveis.',
      recommended_action: 'Verificar workers parados/desabilitados e iniciar filas antes de cargas longas.',
    });
  });

  it('deve deduplicar warning de conectividade do status ate haver resposta valida', async () => {
    const firstPromise = firstValueFrom(service.getSystemStatus());

    await new Promise(resolve => setTimeout(resolve, 0));

    const firstReq = http.expectOne(systemStatusUrl);
    expect(firstReq.request.context.get(SUPPRESS_HTTP_ERROR_LOG)).toBe(true);
    firstReq.flush(null, { status: 0, statusText: 'Unknown Error' });
    const retryReq = http.expectOne(systemStatusUrl);
    retryReq.flush(null, { status: 0, statusText: 'Unknown Error' });
    const response = await firstPromise;

    expect(logger.warn).toHaveBeenCalledTimes(1);
    expect(logger.warn).toHaveBeenCalledWith(
      '[SystemStatusService] Backend indisponivel ao buscar status do sistema',
      expect.anything()
    );
    expect(response.uptime_seconds).toBeNull();
  });

  it('deve normalizar payload malformado de status do sistema', async () => {
    const responsePromise = firstValueFrom(service.getSystemStatus());

    await new Promise(resolve => setTimeout(resolve, 0));

    const req = http.expectOne(systemStatusUrl);
    req.flush({
      app_name: '',
      version: null,
      environment: 42,
      status: 'operational',
      uptime_seconds: 'NaN',
      performance: 'invalid',
    });

    const response = await responsePromise;
    expect(response).toEqual({
      app_name: 'Janus',
      version: 'unknown',
      environment: 'unknown',
      status: 'OPERATIONAL',
      uptime_seconds: null,
      performance: undefined,
    });
  });
});
