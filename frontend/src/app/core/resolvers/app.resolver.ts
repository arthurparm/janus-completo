/**
 * Resolvers para pré-carregamento de dados antes da ativação de rotas
 * Implementa carregamento inteligente de dados para melhorar performance
 */

import { Injectable, inject } from '@angular/core';
import { Resolve, ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';
import { Observable, of, catchError, tap } from 'rxjs';
import { LoadingStateService } from '../services/loading-state.service';
import { NotificationService } from '../notifications/notification.service';
import { ChatMessage } from '../../services/backend-api.service';

/**
 * Interface base para resolvers com loading e tratamento de erros
 */
export interface BaseResolver<T> {
  resolve(
    route: ActivatedRouteSnapshot,
    state: RouterStateSnapshot
  ): Observable<T> | Promise<T> | T;
}

export interface DashboardMetric {
  label: string;
  value: string | number;
  trend: 'up' | 'down' | 'stable';
}

export interface DashboardWidget {
  id: string;
  type: 'chart' | 'metric';
  title: string;
}

export interface DashboardData {
  metrics: DashboardMetric[];
  widgets: DashboardWidget[];
  notifications: unknown[];
}

/**
 * Resolver de dashboard com pré-carregamento de dados principais
 */
@Injectable({
  providedIn: 'root'
})
export class DashboardResolver implements Resolve<DashboardData | null> {
  private loadingState = inject(LoadingStateService);
  private notificationService = inject(NotificationService);

  resolve(
    _route: ActivatedRouteSnapshot,
    _state: RouterStateSnapshot
  ): Observable<DashboardData | null> {
    this.loadingState.startLoading('dashboard', { message: 'Carregando dashboard...' });

    // Simular carregamento de dados do dashboard
    return of({
      metrics: this.loadDashboardMetrics(),
      widgets: this.loadDashboardWidgets(),
      notifications: this.loadNotifications()
    }).pipe(
      tap(() => this.loadingState.stopLoading('dashboard')),
      catchError(_error => {
        this.loadingState.stopLoading('dashboard');
        this.notificationService.notifyError('Erro ao carregar dashboard', 'Não foi possível carregar os dados do dashboard');
        return of(null);
      })
    );
  }

  private loadDashboardMetrics(): DashboardMetric[] {
    // Implementar carregamento real de métricas
    return [
      { label: 'Total de Conversas', value: 1234, trend: 'up' },
      { label: 'Taxa de Sucesso', value: '98.5%', trend: 'stable' },
      { label: 'Tempo Médio', value: '2.3s', trend: 'down' }
    ];
  }

  private loadDashboardWidgets(): DashboardWidget[] {
    // Implementar carregamento real de widgets
    return [
      { id: 'chat', type: 'chart', title: 'Conversas por Hora' },
      { id: 'performance', type: 'metric', title: 'Performance do Sistema' }
    ];
  }

  private loadNotifications(): unknown[] {
    // Implementar carregamento real de notificações
    return [];
  }
}

export interface ChatResolverData {
  conversation: { id: string; title: string } | null;
  messages: ChatMessage[];
}

/**
 * Resolver de chat com pré-carregamento de histórico
 */
@Injectable({
  providedIn: 'root'
})
export class ChatResolver implements Resolve<ChatResolverData> {
  private loadingState = inject(LoadingStateService);
  private notificationService = inject(NotificationService);

  resolve(
    route: ActivatedRouteSnapshot,
    _state: RouterStateSnapshot
  ): Observable<ChatResolverData> {
    const conversationId = route.paramMap.get('conversationId');

    if (!conversationId) {
      return of({ conversation: null, messages: [] });
    }

    this.loadingState.startLoading('chat', { message: 'Carregando conversa...' });

    // Simular carregamento de dados da conversa
    return of({
      conversation: { id: conversationId, title: 'Conversa #' + conversationId },
      messages: this.loadMessages(conversationId)
    }).pipe(
      tap(() => this.loadingState.stopLoading('chat')),
      catchError(_error => {
        this.loadingState.stopLoading('chat');
        this.notificationService.notifyError('Erro ao carregar conversa', 'Não foi possível carregar os dados da conversa');
        return of({ conversation: null, messages: [] });
      })
    );
  }

  private loadMessages(_conversationId: string): ChatMessage[] {
    // Implementar carregamento real de mensagens
    return [];
  }
}

export interface SettingsData {
  userSettings: Record<string, unknown>;
  systemSettings: Record<string, unknown>;
  preferences: Record<string, unknown>;
}

/**
 * Resolver de configurações com pré-carregamento
 */
@Injectable({
  providedIn: 'root'
})
export class SettingsResolver implements Resolve<SettingsData> {
  private loadingState = inject(LoadingStateService);
  private notificationService = inject(NotificationService);

  resolve(
    _route: ActivatedRouteSnapshot,
    _state: RouterStateSnapshot
  ): Observable<SettingsData> {
    this.loadingState.startLoading('settings', { message: 'Carregando configurações...' });

    // Simular carregamento de configurações
    return of({
      userSettings: this.loadUserSettings(),
      systemSettings: this.loadSystemSettings(),
      preferences: this.loadPreferences()
    }).pipe(
      tap(() => this.loadingState.stopLoading('settings')),
      catchError(_error => {
        this.loadingState.stopLoading('settings');
        this.notificationService.notifyError('Erro ao carregar configurações', 'Não foi possível carregar as configurações');
        return of({ userSettings: {}, systemSettings: {}, preferences: {} });
      })
    );
  }

  private loadUserSettings(): Record<string, unknown> {
    // Implementar carregamento real de configurações do usuário
    return {
      theme: 'dark',
      language: 'pt-BR',
      notifications: true
    };
  }

  private loadSystemSettings(): Record<string, unknown> {
    // Implementar carregamento real de configurações do sistema
    return {
      apiUrl: 'https://api.example.com',
      timeout: 30000,
      retries: 3
    };
  }

  private loadPreferences(): Record<string, unknown> {
    // Implementar carregamento real de preferências
    return {
      autoRefresh: true,
      showNotifications: true,
      soundEnabled: false
    };
  }
}

export interface UserData {
  profile: Record<string, unknown> | null;
  permissions: string[];
  roles: string[];
}

/**
 * Resolver de dados de usuário
 */
@Injectable({
  providedIn: 'root'
})
export class UserResolver implements Resolve<UserData> {
  private loadingState = inject(LoadingStateService);
  private notificationService = inject(NotificationService);

  resolve(
    _route: ActivatedRouteSnapshot,
    _state: RouterStateSnapshot
  ): Observable<UserData> {
    this.loadingState.startLoading('user', { message: 'Carregando dados do usuário...' });

    // Simular carregamento de dados do usuário
    return of({
      profile: this.loadUserProfile(),
      permissions: this.loadUserPermissions(),
      roles: this.loadUserRoles()
    }).pipe(
      tap(() => this.loadingState.stopLoading('user')),
      catchError(_error => {
        this.loadingState.stopLoading('user');
        this.notificationService.notifyError('Erro ao carregar dados do usuário', 'Não foi possível carregar os dados do usuário');
        return of({ profile: null, permissions: [], roles: [] });
      })
    );
  }

  private loadUserProfile(): Record<string, unknown> {
    // Implementar carregamento real de perfil do usuário
    return {
      id: '1',
      name: 'Usuário',
      email: 'usuario@example.com',
      avatar: 'assets/avatar.png'
    };
  }

  private loadUserPermissions(): string[] {
    // Implementar carregamento real de permissões
    return ['read', 'write'];
  }

  private loadUserRoles(): string[] {
    // Implementar carregamento real de roles
    return ['user'];
  }
}
