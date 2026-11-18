import { HttpErrorResponse, HttpRequest, HttpResponse } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { firstValueFrom, of, throwError } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { NotificationService } from '../notifications/notification.service';
import { BackendAvailabilityService } from '../services/backend-availability.service';
import { errorMappingInterceptor } from './error-mapping.interceptor';

describe('errorMappingInterceptor', () => {
  const backendAvailability = {
    markAvailable: vi.fn(),
    markDegraded: vi.fn(),
    markUnreachable: vi.fn(),
  };
  const notifications = { notify: vi.fn() };

  beforeEach(() => {
    vi.clearAllMocks();
    TestBed.configureTestingModule({
      providers: [
        { provide: BackendAvailabilityService, useValue: backendAvailability },
        { provide: NotificationService, useValue: notifications },
      ],
    });
  });

  async function run(url: string, responseStatus = 200): Promise<void> {
    const request = new HttpRequest('GET', url);
    const next =
      responseStatus >= 200 && responseStatus < 400
        ? () => of(new HttpResponse({ status: responseStatus, url }))
        : () => throwError(() => new HttpErrorResponse({ status: responseStatus, url }));

    await firstValueFrom(
      TestBed.runInInjectionContext(() => errorMappingInterceptor(request, next)),
    );
  }

  it('clears a stale availability failure after a successful backend response', async () => {
    await run('/api/v1/users/me');

    expect(backendAvailability.markAvailable).toHaveBeenCalledOnce();
  });

  it('marks the backend unreachable when a Janus transport fails', async () => {
    await expect(run('/healthz/user', 0)).rejects.toBeInstanceOf(HttpErrorResponse);

    expect(backendAvailability.markUnreachable).toHaveBeenCalledOnce();
    expect(notifications.notify).not.toHaveBeenCalled();
  });

  it('tracks an absolute Janus API URL after base-url rewriting', async () => {
    const url = new URL('/api/v1/users/me', globalThis.location.origin).toString();
    await expect(run(url, 502)).rejects.toBeInstanceOf(HttpErrorResponse);

    expect(backendAvailability.markUnreachable).toHaveBeenCalledOnce();
  });

  it('does not label an application-level HTTP 500 as a disconnected backend', async () => {
    await expect(run('/api/v1/optional-widget', 500)).rejects.toBeInstanceOf(HttpErrorResponse);

    expect(backendAvailability.markUnreachable).not.toHaveBeenCalled();
    expect(backendAvailability.markAvailable).toHaveBeenCalledOnce();
    expect(notifications.notify).toHaveBeenCalledOnce();
  });

  it('reports HTTP 503 as degraded instead of disconnected', async () => {
    await expect(run('/api/v1/optional-widget', 503)).rejects.toBeInstanceOf(HttpErrorResponse);

    expect(backendAvailability.markDegraded).toHaveBeenCalledOnce();
    expect(backendAvailability.markUnreachable).not.toHaveBeenCalled();
    expect(notifications.notify).toHaveBeenCalledOnce();
  });

  it('does not let an external identity-provider failure control backend status', async () => {
    await expect(run('http://identity.example/api/token', 503)).rejects.toBeInstanceOf(
      HttpErrorResponse,
    );

    expect(backendAvailability.markUnreachable).not.toHaveBeenCalled();
    expect(backendAvailability.markAvailable).not.toHaveBeenCalled();
    expect(backendAvailability.markDegraded).not.toHaveBeenCalled();
  });
});
