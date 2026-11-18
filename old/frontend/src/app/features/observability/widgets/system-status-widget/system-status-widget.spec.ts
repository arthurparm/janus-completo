import { ComponentFixture, TestBed } from '@angular/core/testing';
import { BehaviorSubject } from 'rxjs';

import { SystemStatusService } from '../../../../core/services/system-status.service';
import { SystemStatusWidgetComponent } from './system-status-widget';

describe('SystemStatusWidgetComponent', () => {
    let fixture: ComponentFixture<SystemStatusWidgetComponent>;
    let component: SystemStatusWidgetComponent;
    const status$ = new BehaviorSubject({
        app_name: 'Janus',
        version: '0.5.44',
        environment: 'test',
        status: 'ok',
        uptime_seconds: 125,
    });
    const health$ = new BehaviorSubject({
        services: [
            { key: 'agent', name: 'Agent Service', status: 'ok' as const, metric_text: 'Agentes: 1' },
        ],
    });
    const statusServiceStub = {
        getSystemStatus: vi.fn(() => status$.asObservable()),
        getServicesHealth: vi.fn(() => health$.asObservable()),
    };

    beforeEach(async () => {
        statusServiceStub.getSystemStatus.mockClear();
        statusServiceStub.getServicesHealth.mockClear();

        await TestBed.configureTestingModule({
            imports: [SystemStatusWidgetComponent],
            providers: [
                { provide: SystemStatusService, useValue: statusServiceStub },
            ],
        }).compileComponents();

        fixture = TestBed.createComponent(SystemStatusWidgetComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('deve consumir status e health pelo SystemStatusService compartilhado', () => {
        expect(statusServiceStub.getSystemStatus).toHaveBeenCalledTimes(1);
        expect(statusServiceStub.getServicesHealth).toHaveBeenCalledTimes(1);
        expect(component.systemStatus()?.app_name).toBe('Janus');
        expect(component.services()[0]?.name).toBe('Agent Service');
        expect(component.loading()).toBe(false);
    });

    it('deve renderizar status e servicos recebidos', () => {
        const text = fixture.nativeElement.textContent as string;

        expect(text).toContain('System Status');
        expect(text).toContain('Janus v0.5.44');
        expect(text).toContain('Agent Service');
        expect(text).toContain('Agentes: 1');
    });

    it('deve tratar uptime indisponivel no status degradado', () => {
        status$.next({
            app_name: 'Janus',
            version: '0.5.44',
            environment: 'test',
            status: 'DEGRADED',
            uptime_seconds: null,
        });
        fixture.detectChanges();

        expect(component.formatUptime(component.systemStatus()?.uptime_seconds)).toBe('N/A');
        expect(component.getStatusColor(component.systemStatus()?.status)).toBe('yellow');
    });
});
