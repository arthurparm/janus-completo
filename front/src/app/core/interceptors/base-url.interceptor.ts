import { HttpInterceptorFn } from '@angular/common/http';
import { API_BASE_URL } from '../../services/api.config';

/**
 * Prepend API_BASE_URL to relative requests.
 * - Skips absolute URLs (http/https)
 * - Avoids double-prepending when path already starts with API_BASE_URL
 * - Skips well-known root health endpoints (`/healthz`, `/readyz`)
 */
export const baseUrlInterceptor: HttpInterceptorFn = (req, next) => {
  const isAbsolute = /^https?:\/\//i.test(req.url);
  let url = req.url;

  if (!isAbsolute) {
    const normalizedBase = API_BASE_URL.endsWith('/') ? API_BASE_URL.slice(0, -1) : API_BASE_URL;
    const normalizedUrl = url.startsWith('/') ? url : `/${url}`;

    // Do not prepend for root health endpoints
    const skipPaths = ['/healthz', '/readyz'];
    const shouldSkip = skipPaths.some((p) => normalizedUrl === p || normalizedUrl.startsWith(p + '?'));

    if (shouldSkip) {
      url = normalizedUrl; // keep as-is for health checks
    } else if (normalizedUrl.startsWith(normalizedBase + '/')) {
      url = normalizedUrl; // ensure single leading slash when already starts with base
    } else {
      url = normalizedBase + normalizedUrl;
    }
  }

  return next(req.clone({ url }));
};