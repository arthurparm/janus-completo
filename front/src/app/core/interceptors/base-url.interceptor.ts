import { HttpInterceptorFn } from '@angular/common/http';
import { API_BASE_URL } from '../../services/api.config';

/**
 * Prepend API_BASE_URL to relative requests.
 * - Skips absolute URLs (http/https)
 * - Avoids double-prepending when path already starts with API_BASE_URL
 */
export const baseUrlInterceptor: HttpInterceptorFn = (req, next) => {
  const isAbsolute = /^https?:\/\//i.test(req.url);
  let url = req.url;

  if (!isAbsolute) {
    const normalizedBase = API_BASE_URL.endsWith('/') ? API_BASE_URL.slice(0, -1) : API_BASE_URL;
    const normalizedUrl = url.startsWith('/') ? url : `/${url}`;

    // Avoid prepend if already starts with base
    if (normalizedUrl.startsWith(normalizedBase + '/')) {
      url = normalizedUrl; // ensure single leading slash
    } else {
      url = normalizedBase + normalizedUrl;
    }
  }

  return next(req.clone({ url }));
};