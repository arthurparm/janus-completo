import { HttpInterceptorFn } from '@angular/common/http';
import { API_BASE_URL, PUBLIC_API_BASE_URL } from '../../services/api.config';

const normalizeBase = (base: string): string =>
  base.endsWith('/') ? base.slice(0, -1) : base;

const API_BASES = [API_BASE_URL, PUBLIC_API_BASE_URL]
  .map(normalizeBase)
  .filter((base) => base.length > 0);

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
    const normalizedBase = normalizeBase(API_BASE_URL);
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
    } else if (
      API_BASES.some((base) => normalizedUrl === base || normalizedUrl.startsWith(`${base}/`))
    ) {
      url = normalizedUrl; // preserve requests already scoped to a private or public API
    } else {
      url = normalizedBase + normalizedUrl;
    }
  }

  return next(req.clone({ url }));
};
