import {ApplicationConfig, provideBrowserGlobalErrorListeners, provideZonelessChangeDetection, isDevMode} from '@angular/core';
import {provideRouter, withInMemoryScrolling, PreloadAllModules, withViewTransitions} from '@angular/router';
import {provideHttpClient, withInterceptors} from '@angular/common/http';
import {provideServiceWorker} from '@angular/service-worker';
import {baseUrlInterceptor} from './core/interceptors/base-url.interceptor';
import {errorLoggerInterceptor} from './core/interceptors/error-logger.interceptor';
import { errorMappingInterceptor } from './core/interceptors/error-mapping.interceptor';
import { authInterceptor } from './core/interceptors/auth.interceptor';

import {routes} from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideZonelessChangeDetection(),
    provideRouter(
      routes,
      withInMemoryScrolling({ scrollPositionRestoration: 'enabled' }),
      withViewTransitions()
    ),
    provideHttpClient(withInterceptors([baseUrlInterceptor, authInterceptor, errorLoggerInterceptor, errorMappingInterceptor])),
    // Service Worker habilitado apenas em produção para evitar cache e abortos em dev
    provideServiceWorker('ngsw-worker.js', { enabled: !isDevMode(), registrationStrategy: 'registerWhenStable:30000' })
  ]
};
