import { HttpInterceptorFn } from '@angular/common/http';
import { AUTH_TOKEN_KEY } from '../../services/api.config';

/**
 * Opcionalmente anexa Authorization: Bearer <token> quando disponível.
 * - Lê token de localStorage pela chave configurável (AUTH_TOKEN_KEY)
 * - Não sobrescreve cabeçalhos Authorization existentes
 * - Não impõe credenciais; requests anônimas continuam funcionando
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  // Skip if Authorization already present
  if (req.headers.has('Authorization')) {
    return next(req);
  }

  try {
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    if (!token) {
      return next(req);
    }

    // Attach bearer token
    const authReq = req.clone({
      setHeaders: { Authorization: `Bearer ${token}` }
    });
    return next(authReq);
  } catch {
    // localStorage não disponível (SSR/Private mode); segue sem header
    return next(req);
  }
};