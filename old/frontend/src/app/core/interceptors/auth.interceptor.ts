import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { getStoredAuthToken } from '../../services/auth.utils';
import { AppLoggerService } from '../services/app-logger.service';

/**
 * Opcionalmente anexa Authorization: Bearer <token> quando disponivel.
 * - Lê token de localStorage/sessionStorage
 * - Não sobrescreve cabeçalhos Authorization existentes
 * - Não impõe credenciais; requests anônimas continuam funcionando
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const logger = inject(AppLoggerService);
  try {
    const token = getStoredAuthToken();
    const setHeaders: Record<string, string> = {};

    if (!req.headers.has('Authorization') && token) {
      setHeaders['Authorization'] = `Bearer ${token}`;
    }

    // Debug: Log requests to chat history
    if (req.url.includes('/api/v1/chat/') && req.url.includes('/history')) {
      logger.debug('[AuthInterceptor] Chat history request', {
        url: req.url,
        hasAuthHeader: req.headers.has('Authorization'),
        headers: req.headers.keys(),
        method: req.method
      });
    }

    if (Object.keys(setHeaders).length > 0) {
      const cloned = req.clone({ setHeaders });
      return next(cloned);
    }

    return next(req);
  } catch {
    return next(req);
  }
};
