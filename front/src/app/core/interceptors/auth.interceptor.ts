/* eslint-disable no-console */
import { HttpInterceptorFn } from '@angular/common/http';
import { AUTH_TOKEN_KEY } from '../../services/api.config';
import { decodeTokenUserId } from '../../services/auth.utils';

/**
 * Opcionalmente anexa Authorization: Bearer <token> quando disponível.
 * - Lê token de localStorage pela chave configurável (AUTH_TOKEN_KEY)
 * - Não sobrescreve cabeçalhos Authorization existentes
 * - Não impõe credenciais; requests anônimas continuam funcionando
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  try {
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    const setHeaders: Record<string, string> = {};

    if (!req.headers.has('Authorization') && token) {
      setHeaders['Authorization'] = `Bearer ${token}`;
    }

    if (!req.headers.has('X-User-Id') && token) {
      const uid = decodeTokenUserId(token);
      if (uid !== null) {
        setHeaders['X-User-Id'] = String(uid);
      }
    }

    // Debug: Log requests to chat history
    if (req.url.includes('/api/v1/chat/') && req.url.includes('/history')) {
      console.log('[AuthInterceptor] Chat history request:', {
        url: req.url,
        hasAuthHeader: req.headers.has('Authorization'),
        hasUserIdHeader: req.headers.has('X-User-Id'),
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