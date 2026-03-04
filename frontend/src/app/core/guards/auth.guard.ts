/**
 * Guards de autenticação e autorização para rotas Angular
 * Implementa proteção de rotas baseada em autenticação e permissões
 */

import { Injectable, inject } from '@angular/core';
import { CanActivate, CanActivateChild, CanLoad, Router, ActivatedRouteSnapshot, RouterStateSnapshot, Route, UrlSegment } from '@angular/router';
import { Observable, combineLatest, filter, map, take } from 'rxjs';
import { AuthService } from '../auth/auth.service';
import { NotificationService } from '../notifications/notification.service';

@Injectable({
  providedIn: 'root'
})
export class AuthGuard implements CanActivate, CanActivateChild, CanLoad {
  private authService = inject(AuthService);
  private router = inject(Router);
  private notificationService = inject(NotificationService);

  canActivate(
    route: ActivatedRouteSnapshot,
    state: RouterStateSnapshot
  ): Observable<boolean> | Promise<boolean> | boolean {
    return this.checkAuth(route, state);
  }

  canActivateChild(
    route: ActivatedRouteSnapshot,
    state: RouterStateSnapshot
  ): Observable<boolean> | Promise<boolean> | boolean {
    return this.canActivate(route, state);
  }

  canLoad(
    _route: Route,
    _segments: UrlSegment[]
  ): Observable<boolean> | Promise<boolean> | boolean {
    return this.checkAuthForLoad();
  }

  private checkAuth(route?: ActivatedRouteSnapshot, state?: RouterStateSnapshot): Observable<boolean> {
    return combineLatest([this.authService.authReady$, this.authService.isAuthenticated$]).pipe(
      filter(([ready]) => ready),
      take(1),
      map(([, isAuthenticated]) => {
        if (isAuthenticated) {
          return true;
        }

        // Redirecionar para login com URL de retorno
        const returnUrl = state?.url || route?.url?.join('/') || '/';
        this.router.navigate(['/login'], {
          queryParams: { returnUrl },
          replaceUrl: true
        });

        this.notificationService.notifyWarning('Acesso negado', 'Por favor, faça login para acessar esta página');
        return false;
      })
    );
  }

  private checkAuthForLoad(): Observable<boolean> {
    return combineLatest([this.authService.authReady$, this.authService.isAuthenticated$]).pipe(
      filter(([ready]) => ready),
      take(1),
      map(([, isAuthenticated]) => {
        if (!isAuthenticated) {
          this.notificationService.notifyWarning('Acesso negado', 'Por favor, faça login para acessar este módulo');
        }
        return isAuthenticated;
      })
    );
  }
}

@Injectable({
  providedIn: 'root'
})
export class RoleGuard implements CanActivate {
  private authService = inject(AuthService);
  private router = inject(Router);
  private notificationService = inject(NotificationService);

  canActivate(route: ActivatedRouteSnapshot): Observable<boolean> | Promise<boolean> | boolean {
    const requiredRoles = route.data['roles'] as string[];

    if (!requiredRoles || requiredRoles.length === 0) {
      return true;
    }

    return combineLatest([this.authService.authReady$, this.authService.user$]).pipe(
      filter(([ready]) => ready),
      take(1),
      map(([, user]) => {
        if (!user) {
          this.router.navigate(['/login']);
          return false;
        }

        const hasRole = requiredRoles.some(role => user.roles?.includes(role) || false);

        if (!hasRole) {
          this.notificationService.notifyError('Acesso negado', 'Você não tem permissão para acessar esta página');
          this.router.navigate(['/']);
          return false;
        }

        return true;
      })
    );
  }
}

@Injectable({
  providedIn: 'root'
})
export class PermissionGuard implements CanActivate {
  private authService = inject(AuthService);
  private router = inject(Router);
  private notificationService = inject(NotificationService);

  canActivate(route: ActivatedRouteSnapshot): Observable<boolean> | Promise<boolean> | boolean {
    const requiredPermissions = route.data['permissions'] as string[];

    if (!requiredPermissions || requiredPermissions.length === 0) {
      return true;
    }

    return this.authService.user$.pipe(
      take(1),
      map(user => {
        if (!user) {
          this.router.navigate(['/login']);
          return false;
        }

        const hasPermission = requiredPermissions.every(permission =>
          user.permissions?.includes(permission) || false
        );

        if (!hasPermission) {
          this.notificationService.notifyError('Acesso negado', 'Você não tem as permissões necessárias para acessar esta página');
          this.router.navigate(['/']);
          return false;
        }

        return true;
      })
    );
  }
}

@Injectable({
  providedIn: 'root'
})
export class NoAuthGuard implements CanActivate {
  private authService = inject(AuthService);
  private router = inject(Router);

  canActivate(): Observable<boolean> | Promise<boolean> | boolean {
    return combineLatest([this.authService.authReady$, this.authService.isAuthenticated$]).pipe(
      filter(([ready]) => ready),
      take(1),
      map(([, isAuthenticated]) => {
        if (!isAuthenticated) {
          return true;
        }

        // Se já está autenticado, redirecionar para dashboard
        this.router.navigate(['/']);
        return false;
      })
    );
  }
}

/**
 * Guard para verificar se o sistema está pronto
 * Útil para verificar configurações iniciais, conexões, etc.
 */
@Injectable({
  providedIn: 'root'
})
export class SystemReadyGuard implements CanActivate {
  private authService = inject(AuthService);
  private router = inject(Router);
  private notificationService = inject(NotificationService);

  canActivate(): Observable<boolean> | Promise<boolean> | boolean {
    // Verificar se o sistema está configurado e pronto
    return this.checkSystemReadiness().pipe(
      map(isReady => {
        if (!isReady) {
          this.notificationService.notifyWarning('Sistema não pronto', 'O sistema ainda está sendo configurado. Por favor, aguarde.');
          this.router.navigate(['/setup']);
          return false;
        }
        return true;
      })
    );
  }

  private checkSystemReadiness(): Observable<boolean> {
    // Implementar lógica de verificação do sistema
    // Por exemplo: verificar configurações, conexões, etc.
    return this.authService.isAuthenticated$;
  }
}
