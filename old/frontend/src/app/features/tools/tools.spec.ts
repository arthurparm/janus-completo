import { TestBed } from '@angular/core/testing'
import { HttpClientTestingModule } from '@angular/common/http/testing'
import { provideRouter } from '@angular/router'
import { of, throwError } from 'rxjs'
import { vi } from 'vitest'

import { AuthService } from '../../core/auth/auth.service'
import { BackendApiService } from '../../services/backend-api.service'
import { ToolsComponent } from './tools'

describe('ToolsComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HttpClientTestingModule, ToolsComponent],
      providers: [
        {
          provide: BackendApiService,
          useValue: {
            tools: {
              getTools: () => of({ tools: [] }),
              getToolStats: () => of({ tool_usage: {}, total_calls: 0, success_rate: 0 }),
            },
            productivity: {
              googleOAuthStatus: () => of({
                local_status: 'configured',
                capabilities: { calendar: true, mail: false },
                provider_verified: false,
              }),
              googleOAuthStart: () => of({
                authorize_url: 'https://accounts.google.com/o/oauth2/v2/auth',
                state: 'opaque-state',
              }),
              googleOAuthDisconnect: () => of({
                status: 'disconnected',
                provider_revoked: true,
                retry_required: false,
                warning: null,
              }),
            },
            observability: {
              listAuditEvents: () =>
                of({
                  total: 4,
                  events: [
                    {
                      id: 1,
                      tool: 'pending_actions',
                      endpoint: '/api/v1/pending_actions/action/approve',
                      action: 'approve',
                      status: 'approved',
                      trace_id: 'trace-approve-12345678',
                      created_at: 1710000000,
                    },
                    {
                      id: 2,
                      endpoint: 'chat_event:conv-1',
                      action: 'agent_thought',
                      status: 'published',
                      trace_id: 'trace-chat-abcdef12',
                      created_at: 1710000001,
                    },
                    {
                      id: 3,
                      tool: 'codex_read_file',
                      endpoint: '/api/v1/observability/audit/events',
                      action: 'read',
                      status: 'ok',
                      created_at: 1710000002,
                    },
                  ],
                }),
              listPendingActions: () => of([]),
              getPendingActionsLegacyResidue: () =>
                of({
                  total_without_owner: 2,
                  pending_without_owner: 2,
                  sample_limit: 10,
                  legacy_runtime_fallback_enabled: false,
                  message:
                    'Operational legacy is extinct. Historical pending_actions without persisted owner remain blocked as administrative backlog until controlled sanitation; new ownerless records are rejected.',
                  items: [
                    {
                      action_id: 41,
                      status: 'pending',
                      tool_name: 'tool_x',
                      created_at: '2026-06-22T12:00:00',
                      conversation_id: 'conv-legacy-1',
                    },
                  ],
                }),
              approvePendingAction: () => of({}),
              rejectPendingAction: () => of({}),
            },
          },
        },
        {
          provide: AuthService,
          useValue: {
            isAdmin: () => true,
          },
        },
        provideRouter([]),
      ],
    }).compileComponents()
  })

  it('destaca apenas eventos criticos de chat e pending actions na trilha de auditoria', () => {
    const fixture = TestBed.createComponent(ToolsComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    expect(component.criticalAuditEvents().map((event) => event.id)).toEqual([1, 2])
    expect(component.auditTraceLabel(component.criticalAuditEvents()[0]!)).toContain('...')
  })

  it('interpreta detalhe estruturado retornado pelo backend', () => {
    const fixture = TestBed.createComponent(ToolsComponent)
    const component = fixture.componentInstance

    const message = (component as any).extractApiErrorMessage(
      {
        error: {
          detail: {
            code: 'PENDING_ACTION_OWNER_REQUIRED',
            message: 'Pending action owner is not persisted; legacy actions are blocked.',
          },
        },
      },
      'Falha ao aprovar a acao.',
    )

    expect(message).toContain('[PENDING_ACTION_OWNER_REQUIRED]')
    expect(message).toContain('legacy actions are blocked')
  })

  it('exibe resumo administrativo do legado bloqueado sem reabrir fallback operacional', () => {
    const fixture = TestBed.createComponent(ToolsComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()
    const element = fixture.nativeElement as HTMLElement
    const legacySection = element.querySelector('#legacy-residue') as HTMLElement | null

    expect(component.hasLegacyPendingResidue()).toBe(true)
    expect(component.legacyResidueSummary()?.legacy_runtime_fallback_enabled).toBe(false)
    expect(component.legacyResidueItemLabel(0)).toContain('#41')
    expect(component.legacyResidueItemLabel(0)).toContain('conv-legacy-1')
    expect(legacySection?.textContent).toContain('Passivo historico bloqueado')
    expect(legacySection?.textContent).toContain('Backlog administrativo sem owner')
    expect(legacySection?.textContent).toContain('Novos registros sem owner persistido sao rejeitados na origem')
    expect(legacySection?.querySelector('button')).toBeNull()
  })

  it('mostra o estado local Google sem alegar validação remota', () => {
    const fixture = TestBed.createComponent(ToolsComponent)
    fixture.detectChanges()
    const section = fixture.nativeElement.querySelector('#google-integration') as HTMLElement

    expect(section.textContent).toContain('Configuração local ativa')
    expect(section.textContent).toContain('Agenda: autorizada')
    expect(section.textContent).toContain('E-mail: não autorizado')
    expect(section.textContent).toContain('validade no Google é verificada quando a capacidade é usada')
  })

  it('exige confirmação antes de desconectar o Google', () => {
    const fixture = TestBed.createComponent(ToolsComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    component.requestGoogleDisconnect()
    fixture.detectChanges()

    expect(component.confirmGoogleDisconnect()).toBe(true)
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Confirmar desconexão')
  })

  it('não apresenta falha do backend como catálogo realmente vazio', () => {
    const api = TestBed.inject(BackendApiService)
    vi.spyOn(api.tools, 'getTools').mockReturnValue(
      throwError(() => new Error('backend unavailable'))
    )
    const fixture = TestBed.createComponent(ToolsComponent)
    fixture.detectChanges()

    expect(fixture.componentInstance.loadFailures()).toContain('catálogo de ferramentas')
    expect(fixture.componentInstance.error()).toContain('Os valores vazios dessas seções não foram confirmados')
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Tentar novamente')
  })
})
