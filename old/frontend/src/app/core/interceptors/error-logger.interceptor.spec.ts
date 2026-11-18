import { HttpContext, HttpErrorResponse, HttpRequest } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { firstValueFrom, throwError } from 'rxjs';
import { vi } from 'vitest';

import { AppLoggerService } from '../services/app-logger.service';
import { SUPPRESS_HTTP_ERROR_LOG, errorLoggerInterceptor } from './error-logger.interceptor';

describe('errorLoggerInterceptor', () => {
  let logger: { warn: ReturnType<typeof vi.fn> };

  beforeEach(() => {
    logger = {
      warn: vi.fn(),
    };

    TestBed.configureTestingModule({
      providers: [{ provide: AppLoggerService, useValue: logger }],
    });
  });

  it('deve registrar erro HTTP por padrao', async () => {
    const req = new HttpRequest('GET', '/api/v1/chat/history');
    const next = vi.fn(() =>
      throwError(() => new HttpErrorResponse({ status: 500, statusText: 'Server Error' }))
    );

    const out$ = TestBed.runInInjectionContext(() => errorLoggerInterceptor(req, next));

    await expect(firstValueFrom(out$)).rejects.toBeInstanceOf(HttpErrorResponse);
    expect(logger.warn).toHaveBeenCalledWith(
      '[HTTP ERROR]',
      expect.objectContaining({
        status: 500,
        statusText: 'Server Error',
        url: '/api/v1/chat/history',
      })
    );
  });

  it('deve suprimir log global quando a requisicao controla o proprio erro', async () => {
    const req = new HttpRequest('GET', '/api/v1/system/status', {
      context: new HttpContext().set(SUPPRESS_HTTP_ERROR_LOG, true),
    });
    const next = vi.fn(() =>
      throwError(() => new HttpErrorResponse({ status: 0, statusText: 'Unknown Error' }))
    );

    const out$ = TestBed.runInInjectionContext(() => errorLoggerInterceptor(req, next));

    await expect(firstValueFrom(out$)).rejects.toBeInstanceOf(HttpErrorResponse);
    expect(logger.warn).not.toHaveBeenCalled();
  });
});
