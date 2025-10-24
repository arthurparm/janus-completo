import {ApplicationConfig, provideBrowserGlobalErrorListeners, provideZonelessChangeDetection} from '@angular/core';
import {provideRouter, withInMemoryScrolling, PreloadAllModules, withViewTransitions} from '@angular/router';
import {provideHttpClient, withInterceptors} from '@angular/common/http';
import {provideServiceWorker} from '@angular/service-worker';
import {baseUrlInterceptor} from './core/interceptors/base-url.interceptor';
import {errorLoggerInterceptor} from './core/interceptors/error-logger.interceptor';
import { errorMappingInterceptor } from './core/interceptors/error-mapping.interceptor';

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
    provideHttpClient(withInterceptors([baseUrlInterceptor, errorLoggerInterceptor, errorMappingInterceptor])),
    // Registra SW apenas em produção (isDevMode=false)
    provideServiceWorker('ngsw-worker.js', { registrationStrategy: 'registerWhenStable:30000' })
  ]
};
