import { Routes } from '@angular/router';
import { AuthGuard, RoleGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () => import('./features/auth/login/login').then(m => m.LoginComponent)
  },
  {
    path: 'conversations',
    loadComponent: () => import('./features/conversations/conversations').then(m => m.ConversationsComponent),
    canActivate: [AuthGuard],
    pathMatch: 'full'
  },
  {
    path: 'conversations/:conversationId',
    loadComponent: () => import('./features/conversations/conversations').then(m => m.ConversationsComponent),
    canActivate: [AuthGuard]
  },
  {
    path: 'tools',
    loadComponent: () => import('./features/tools/tools').then(m => m.ToolsComponent),
    canActivate: [AuthGuard]
  },
  {
    path: 'observability',
    loadComponent: () => import('./features/observability/observability').then(m => m.ObservabilityComponent),
    canActivate: [AuthGuard]
  },
  {
    path: 'admin/autonomia',
    loadComponent: () => import('./features/admin/autonomia/admin-autonomia').then(m => m.AdminAutonomiaComponent),
    canActivate: [AuthGuard, RoleGuard],
    data: { roles: ['admin'] }
  },
  {
    path: '',
    loadComponent: () => import('./features/home/home').then(m => m.HomeComponent),
    canActivate: [AuthGuard]
  },
  {
    path: 'home',
    redirectTo: '',
    pathMatch: 'full'
  },
  {
    path: 'registro',
    loadComponent: () => import('./features/auth/register/register').then(m => m.RegisterComponent)
  },
  {
    path: 'register',
    redirectTo: 'registro',
    pathMatch: 'full'
  },
  {
    path: '**',
    redirectTo: 'login'
  }
];
