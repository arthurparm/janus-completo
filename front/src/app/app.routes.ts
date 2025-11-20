import {Routes} from '@angular/router';
import { MainLayout } from './core/layout/main-layout/main-layout';

export const routes: Routes = [
  {
    path: '',
    component: MainLayout,
    children: [
      {path: '', pathMatch: 'full', loadComponent: () => import('./pages/home/home').then(m => m.HomeComponent)},
      {path: 'arquitetura', loadComponent: () => import('./pages/arquitetura/arquitetura').then(m => m.Arquitetura)},
      {path: 'sprints', loadComponent: () => import('./pages/sprints/sprints').then(m => m.Sprints)},
      {path: 'chat/:conversationId', loadComponent: () => import('./features/chat/chat/chat').then(m => m.ChatComponent) },
      {path: 'login', loadComponent: () => import('./features/auth/login/login').then(m => m.LoginComponent) },
      {path: 'hitl', loadComponent: () => import('./features/hitl/hitl/hitl').then(m => m.HitlComponent) },
      {path: 'conversations', loadComponent: () => import('./features/chat/conversations/conversations').then(m => m.ConversationsComponent) },
      {path: 'gaps-janus', loadComponent: () => import('./pages/janus-gaps/janus-gaps').then(m => m.JanusGapsComponent) },
      // Dashboard removido
      {
        path: 'documentacao',
        loadComponent: () => import('./pages/documentacao/documentacao').then(m => m.Documentacao)
      },
      {path: 'ux', loadComponent: () => import('./pages/ux-dashboard/ux-dashboard').then(m => m.UxDashboardComponent) },
      {path: '**', redirectTo: ''}
    ]
  }
];
