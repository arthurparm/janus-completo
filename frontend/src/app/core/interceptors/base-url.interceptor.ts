import { HttpInterceptorFn } from '@angular/common/http';
import { API_BASE_URL } from '../../services/api.config';

/**
 * Prepend API_BASE_URL to relative requests.
 * - Skips absolute URLs (http/https)
 * - Avoids double-prepending when path already starts with API_BASE_URL
 * - Keeps profile liveness and static assets outside the API base URL
 */
export const baseUrlInterceptor: HttpInterceptorFn = (req, next) => {
  const isAbsolute = /^https?:\/\//i.test(req.url);
  let url = req.url;

  if (!isAbsolute) {
    const normalizedBase = API_BASE_URL.endsWith('/') ? API_BASE_URL.slice(0, -1) : API_BASE_URL;
    const normalizedUrl = url.startsWith('/') ? url : `/${url}`;

    const skipExact = ['/favicon.ico'];
    const skipPrefix = ['/assets/', '/healthz/'];
    const skipExt = ['.csv'];
    const hasSkipExt = skipExt.some(ext => normalizedUrl.toLowerCase().endsWith(ext));
    const shouldSkip = skipExact.some((p) => normalizedUrl === p || normalizedUrl.startsWith(p + '?')) 
      || skipPrefix.some((p) => normalizedUrl.startsWith(p))
      || hasSkipExt;

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
