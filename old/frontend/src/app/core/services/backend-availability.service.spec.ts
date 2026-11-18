import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { AppLoggerService } from './app-logger.service';
import { BackendAvailabilityService } from './backend-availability.service';

describe('BackendAvailabilityService', () => {
  let http: HttpTestingController;
  let service: BackendAvailabilityService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [{ provide: AppLoggerService, useValue: { info: vi.fn() } }],
    });
    http = TestBed.inject(HttpTestingController);
    service = TestBed.inject(BackendAvailabilityService);
  });

  afterEach(() => {
    http.verify();
  });

  it('confirms recovery through the real user health endpoint', async () => {
    const result = service.checkNow();
    expect(service.snapshot().state).toBe('checking');
    expect(service.hasIssue()).toBe(true);
    const request = http.expectOne('/healthz/user');
    expect(request.request.method).toBe('GET');
    request.flush('ok');

    await expect(result).resolves.toBe(true);
    expect(service.snapshot().state).toBe('available');
    expect(service.snapshot().checkedAt).toBeInstanceOf(Date);
  });

  it('coalesces concurrent retries into one backend probe', async () => {
    const first = service.checkNow();
    const second = service.checkNow();
    expect(second).toBe(first);

    http.expectOne('/healthz/user').flush('ok');
    await expect(first).resolves.toBe(true);
  });

  it('distinguishes backend degradation from a transport failure', async () => {
    const degraded = service.checkNow();
    http
      .expectOne('/healthz/user')
      .flush('unavailable', { status: 503, statusText: 'Unavailable' });
    await expect(degraded).resolves.toBe(false);
    expect(service.snapshot().state).toBe('degraded');

    const unreachable = service.checkNow();
    http.expectOne('/healthz/user').error(new ProgressEvent('network error'));
    await expect(unreachable).resolves.toBe(false);
    expect(service.snapshot().state).toBe('unreachable');
  });

  it('treats an authenticated error response as proof of reachability', async () => {
    const result = service.checkNow();
    http
      .expectOne('/healthz/user')
      .flush('unauthorized', { status: 401, statusText: 'Unauthorized' });

    await expect(result).resolves.toBe(true);
    expect(service.snapshot().state).toBe('available');
  });
});
