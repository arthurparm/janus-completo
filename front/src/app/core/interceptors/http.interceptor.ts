/**
 * Interceptors HTTP para tratamento global de erros e loading
 * Implementa tratamento centralizado de erros e estados de carregamento
 */

import { Injectable, inject } from '@angular/core';
import { HttpInterceptor, HttpRequest, HttpHandler, HttpEvent, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError, finalize, catchError, timeout } from 'rxjs';
import { LoadingStateService } from '../services/loading-state.service';
import { NotificationService } from '../notifications/notification.service';

import { Router } from '@angular/router';

@Injectable()
export class LoadingInterceptor implements HttpInterceptor {
  private loadingStateService = inject(LoadingStateService);
  private activeRequests = 0;

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    // Não mostrar loading para requisições específicas
    if (this.shouldSkipLoading(req)) {
      return next.handle(req);
    }

    this.activeRequests++;
    if (this.activeRequests === 1) {
      this.loadingStateService.startLoading('http-request', 'Carregando...');
    }

    return next.handle(req).pipe(
      finalize(() => {
        this.activeRequests--;
        if (this.activeRequests === 0) {
          this.loadingStateService.stopLoading('http-request');
        }
      })
    );
  }

  private shouldSkipLoading(req: HttpRequest<any>): boolean {
    // Skip loading for specific endpoints
    const skipUrls = [
      '/api/notifications',
      '/api/health',
      '/api/ping'
    ];

    return skipUrls.some(url => req.url.includes(url));
  }
}

@Injectable()
export class ErrorInterceptor implements HttpInterceptor {
  private notificationService = inject(NotificationService);

  private router = inject(Router);

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    return next.handle(req).pipe(
      catchError((error: HttpErrorResponse) => {
        this.handleError(error);
        return throwError(() => error);
      })
    );
  }

  private handleError(error: HttpErrorResponse): void {
    let message = 'Ocorreu um erro inesperado';
    let title = 'Erro';

    switch (error.status) {
      case 400:
        title = 'Requisição Inválida';
        message = error.error?.message || 'Dados inválidos fornecidos';
        break;

      case 401:
        title = 'Não Autorizado';
        message = 'Sessão expirada. Por favor, faça login novamente.';
        this.handleUnauthorized();
        break;

      case 403:
        title = 'Acesso Negado';
        message = 'Você não tem permissão para realizar esta ação.';
        break;

      case 404:
        title = 'Não Encontrado';
        message = 'O recurso solicitado não foi encontrado.';
        break;

      case 409:
        title = 'Conflito';
        message = error.error?.message || 'Conflito com o estado atual do recurso.';
        break;

      case 422:
        title = 'Entidade Não Processável';
        message = error.error?.message || 'Os dados fornecidos não puderam ser processados.';
        break;

      case 429:
        title = 'Muitas Requisições';
        message = 'Você excedeu o limite de requisições. Por favor, aguarde.';
        break;

      case 500:
        title = 'Erro do Servidor';
        message = 'Ocorreu um erro no servidor. Por favor, tente novamente.';
        break;

      case 502:
      case 503:
      case 504:
        title = 'Serviço Indisponível';
        message = 'O serviço está temporariamente indisponível. Por favor, tente novamente.';
        break;

      default:
        if (error.status >= 400 && error.status < 500) {
          title = 'Erro de Cliente';
          message = error.error?.message || 'Ocorreu um erro na requisição.';
        } else if (error.status >= 500) {
          title = 'Erro do Servidor';
          message = 'Ocorreu um erro no servidor. Por favor, tente novamente.';
        }
        break;
    }

    this.notificationService.notifyError(title, message);
  }

  private handleUnauthorized(): void {
    // Limpar dados de autenticação
    // Limpar autenticação local
    localStorage.removeItem('token');
    localStorage.removeItem('user');

    // Redirecionar para login com mensagem
    this.router.navigate(['/login'], {
      queryParams: {
        message: 'Sessão expirada. Por favor, faça login novamente.'
      }
    });
  }
}

@Injectable()
export class TimeoutInterceptor implements HttpInterceptor {
  private readonly DEFAULT_TIMEOUT = 30000; // 30 segundos

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    const timeoutValue = req.headers.get('timeout') || this.DEFAULT_TIMEOUT;
    const timeoutMs = typeof timeoutValue === 'string' ? parseInt(timeoutValue, 10) : timeoutValue;

    return next.handle(req).pipe(
      timeout(timeoutMs),
      catchError(error => {
        if (error.name === 'TimeoutError') {
          const notificationService = inject(NotificationService);
          notificationService.notifyWarning('Tempo Limite Excedido', 'A requisição demorou muito tempo para responder.');
        }
        return throwError(() => error);
      })
    );
  }
}

@Injectable()
export class RetryInterceptor implements HttpInterceptor {
  private readonly MAX_RETRIES = 3;
  private readonly RETRY_DELAY = 1000; // 1 segundo

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    return this.handleRequest(req, next, 0);
  }

  private handleRequest(req: HttpRequest<any>, next: HttpHandler, retryCount: number): Observable<HttpEvent<any>> {
    return next.handle(req).pipe(
      catchError((error: HttpErrorResponse) => {
        if (this.shouldRetry(error, retryCount)) {
          return this.delay(this.RETRY_DELAY).pipe(
            switchMap(() => this.handleRequest(req, next, retryCount + 1))
          );
        }
        return throwError(() => error);
      })
    );
  }

  private shouldRetry(error: HttpErrorResponse, retryCount: number): boolean {
    // Não tentar novamente se já atingiu o limite
    if (retryCount >= this.MAX_RETRIES) {
      return false;
    }

    // Não tentar novamente para erros de cliente (4xx)
    if (error.status >= 400 && error.status < 500) {
      return false;
    }

    // Tentar novamente para erros de servidor (5xx) e erros de rede
    return error.status >= 500 || !error.status;
  }

  private delay(ms: number): Observable<void> {
    return new Observable<void>(observer => {
      setTimeout(() => {
        observer.next();
        observer.complete();
      }, ms);
    });
  }
}

// Import necessário para o switchMap
import { switchMap } from 'rxjs/operators';