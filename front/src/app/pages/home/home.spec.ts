import {ComponentFixture, TestBed} from '@angular/core/testing';
import {signal} from '@angular/core';
import {HomeComponent} from './home';
import {GlobalStateStore} from '../../core/state/global-state.store';
import {NotificationService} from '../../core/notifications/notification.service';
import {JanusApiService} from '../../services/janus-api.service';
import {UiService} from '../../shared/services/ui.service';
import {of} from 'rxjs';

class MockGlobalStateStore {
  loading = signal(true);
  apiHealthy = signal<'ok' | 'unknown'>('ok');
  systemStatus = signal<{cpu_usage_percent?: number; memory_usage_percent?: number; disk_usage_percent?: number; uptime_seconds?: number}>({
    cpu_usage_percent: 10,
    memory_usage_percent: 20,
    disk_usage_percent: 30,
    uptime_seconds: 123
  });
  services = signal<any[]>([]);
  workers = signal<any[]>([]);
  startPolling = (_ms: number) => {};
  stopPolling = () => {};
}

class MockNotificationService {
  notify(_n: { type: string; message: string }) {}
}

class MockJanusApiService {
  getAutonomyPlan() {
    return of({ status: 'ok', active: false, steps_count: 0, plan: [] });
  }

  getAutonomyStatus() {
    return of({ active: false, cycle_count: 0, config: {} });
  }

  listAuditEvents(_params?: { limit?: number }) {
    return of({ total: 0, events: [] });
  }

  getCurrentContext() {
    return of(null);
  }

  getQuarantinedMessages() {
    return of({ total_quarantined: 0, messages: [] });
  }

  listPendingActions() {
    return of([]);
  }

  approvePendingAction(thread_id: string) {
    return of({ thread_id, status: 'approved' });
  }

  rejectPendingAction(thread_id: string) {
    return of({ thread_id, status: 'rejected' });
  }

  runAutoAnalysis() {
    return of({ timestamp: '', overall_health: 'ok', insights: [], fun_fact: '' });
  }
}

class MockUiService {
  showSuccess(_message: string) {}
  showInfo(_message: string) {}
  showWarning(_message: string) {}
  showToast(_config: { message: string }) {}
  showLoading(_config?: { message?: string }) { return { close: () => {} } as any; }
  hideLoading() {}
  showConfirm(_data: { title: string; message: string }) { return of(false); }
}

describe('HomeComponent', () => {
  let component: HomeComponent;
  let fixture: ComponentFixture<HomeComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HomeComponent],
      providers: [
        { provide: GlobalStateStore, useClass: MockGlobalStateStore },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: JanusApiService, useClass: MockJanusApiService },
        { provide: UiService, useClass: MockUiService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(HomeComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should compute services availability', () => {
    expect(component.servicesAvailability()).toBeGreaterThanOrEqual(0);
  });
});
