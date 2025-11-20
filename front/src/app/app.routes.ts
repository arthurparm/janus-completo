import {Routes, CanMatchFn, Router} from '@angular/router';
import { MainLayout } from './core/layout/main-layout/main-layout';
import { inject } from '@angular/core'
import { AUTH_TOKEN_KEY } from './services/api.config'
import { decodeTokenUserId, decodeTokenExp } from './services/auth.utils'
import { DashboardResolver, ChatResolver, SettingsResolver, UserResolver } from './core/guards'

export const authGuard: CanMatchFn = () => {
  const r = inject(Router)
  const tok = localStorage.getItem(AUTH_TOKEN_KEY)
  console.log('[AuthGuard] Checking token:', { hasToken: !!tok })
  
  if (!tok) {
    console.log('[AuthGuard] No token found, redirecting to login')
    return r.parseUrl('/login')
  }
  
  const uid = decodeTokenUserId(tok)
  const exp = decodeTokenExp(tok)
  const now = Math.floor(Date.now() / 1000)
  const valid = !!uid && !!exp && exp > now
  
  console.log('[AuthGuard] Token validation:', { uid, exp, now, valid })
  
  if (!valid) {
    console.log('[AuthGuard] Invalid token, redirecting to login')
    // Clear invalid token to prevent loops
    localStorage.removeItem(AUTH_TOKEN_KEY)
    return r.parseUrl('/login')
  }
  
  console.log('[AuthGuard] Token valid, allowing access')
  return true
}

export const loginRedirectGuard: CanMatchFn = () => {
  const r = inject(Router)
  const tok = localStorage.getItem(AUTH_TOKEN_KEY)
  
  if (tok) {
    const uid = decodeTokenUserId(tok)
    const exp = decodeTokenExp(tok)
    const now = Math.floor(Date.now() / 1000)
    const valid = !!uid && !!exp && exp > now
    
    if (valid) {
      console.log('[LoginRedirectGuard] User is authenticated, redirecting to home')
      return r.parseUrl('/')
    }
  }
  
  console.log('[LoginRedirectGuard] User is not authenticated, allowing access to login')
  return true
}

export const routes: Routes = [
  { 
    path: 'login', 
    loadComponent: () => import('./features/auth/login/login').then(m => m.LoginComponent), 
    canMatch: [loginRedirectGuard] 
  },
  { 
    path: 'auth/callback', 
    loadComponent: () => import('./features/auth/callback/auth-callback').then(m => m.AuthCallbackComponent) 
  },
  {
    path: '',
    component: MainLayout,
    canMatch: [authGuard],
    resolve: {
      dashboard: DashboardResolver,
      user: UserResolver
    },
    children: [
      {
        path: '', 
        pathMatch: 'full', 
        loadComponent: () => import('./pages/home/home').then(m => m.HomeComponent),
        resolve: { dashboard: DashboardResolver }
      },
      {
        path: 'arquitetura', 
        loadComponent: () => import('./pages/arquitetura/arquitetura').then(m => m.Arquitetura),
        data: { 
          title: 'Arquitetura',
          description: 'Visualização da arquitetura do sistema'
        }
      },
      {
        path: 'sprints', 
        loadComponent: () => import('./pages/sprints/sprints').then(m => m.Sprints),
        data: { 
          title: 'Sprints',
          description: 'Gestão de sprints e tarefas'
        }
      },
      {
        path: 'chat/:conversationId', 
        loadComponent: () => import('./features/chat/chat/chat').then(m => m.ChatComponent),
        resolve: { chat: ChatResolver },
        data: { 
          title: 'Chat',
          description: 'Conversa com Janus AI'
        }
      },
      {
        path: 'hitl', 
        loadComponent: () => import('./features/hitl/hitl/hitl').then(m => m.HitlComponent),
        data: { 
          title: 'HITL',
          description: 'Human-in-the-loop',
          roles: ['admin', 'operator']
        }
      },
      {
        path: 'conversations', 
        loadComponent: () => import('./features/chat/conversations/conversations').then(m => m.ConversationsComponent),
        data: { 
          title: 'Conversas',
          description: 'Histórico de conversas'
        }
      },

      {
        path: 'documentacao',
        loadComponent: () => import('./pages/documentacao/documentacao').then(m => m.Documentacao),
        data: { 
          title: 'Documentação',
          description: 'Documentação do sistema'
        }
      },
      {
        path: 'ux', 
        loadComponent: () => import('./pages/ux-dashboard/ux-dashboard').then(m => m.UxDashboardComponent),
        data: { 
          title: 'UX Dashboard',
          description: 'Dashboard de experiência do usuário'
        }
      },
      {
        path: 'ui-demo', 
        loadComponent: () => import('./shared/components/demo/ui-components-demo.component').then(m => m.UiComponentsDemoComponent),
        data: { 
          title: 'UI Demo',
          description: 'Demonstração de componentes UI'
        }
      },
      {
        path: 'supabase-config', 
        loadComponent: () => import('./shared/components/supabase-config/supabase-config.component').then(m => m.SupabaseConfigComponent),
        data: { 
          title: 'Configuração Supabase',
          description: 'Configuração do Supabase',
          roles: ['admin']
        }
      },
      {
        path: 'auto-analysis', 
        loadComponent: () => import('./features/auto-analysis/auto-analysis.component').then(m => m.AutoAnalysisComponent),
        data: { 
          title: 'Análise Automática',
          description: 'Análise automática de dados'
        }
      },
      {path: '**', redirectTo: ''}
    ]
  }
];
