import { Routes, CanMatchFn, Router } from '@angular/router';
import { MainLayout } from './core/layout/main-layout/main-layout';
import { inject } from '@angular/core'
import { AUTH_TOKEN_KEY } from './services/api.config'
import { decodeTokenUserId, decodeTokenExp } from './services/auth.utils'
import { DashboardResolver, ChatResolver, SettingsResolver, UserResolver } from './core/guards'

export const authGuard: CanMatchFn = () => {
  const r = inject(Router)
  // BYPASS: Authentication disabled by user request
  console.log('[AuthGuard] Bypassing auth check (Dev Mode)')
  return true
}

export const loginRedirectGuard: CanMatchFn = () => {
  const r = inject(Router)
  // BYPASS: Redirect to home as login is disabled
  console.log('[LoginRedirectGuard] Auth disabled, redirecting to home')
  return r.parseUrl('/')
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
        loadComponent: () => import('./pages/documentacao/documentacao').then(m => m.DocumentacaoComponent),
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

      {
        path: 'autonomy',
        loadComponent: () => import('./pages/autonomy/autonomy').then(m => m.AutonomyComponent),
        data: {
          title: 'Autonomia',
          description: 'Torre de Controle do Agente',
          roles: ['admin'] // Restricted
        }
      },
      {
        path: 'ops',
        loadComponent: () => import('./pages/ops/ops').then(m => m.OpsComponent),
        data: {
          title: 'LLMOps',
          description: 'Factory de Modelos e Experimentação',
          roles: ['admin', 'dev']
        }
      },
      {
        path: 'tools',
        loadComponent: () => import('./pages/tools/tools').then(m => m.ToolsComponent),
        data: {
          title: 'Ferramentas',
          description: 'Ferramentas disponíveis do sistema'
        }
      },
      {
        path: 'brain',
        loadComponent: () => import('./pages/brain/brain').then(m => m.BrainComponent),
        data: {
          title: 'The Brain',
          description: 'Central de Memória e Conhecimento'
        }
      },
      {
        path: 'memory',
        redirectTo: 'brain',
        pathMatch: 'full'
      },
      {
        path: 'senses',
        loadComponent: () => import('./pages/senses/senses').then(m => m.SensesComponent),
        data: {
          title: 'Senses',
          description: 'Interfaces de Entrada Multimodal'
        }
      },
      {
        path: 'documents',
        loadComponent: () => import('./pages/documents/documents').then(m => m.DocumentsComponent),
        data: {
          title: 'Documentos',
          description: 'Gerenciamento de documentos indexados'
        }
      },
      { path: '**', redirectTo: '' }
    ]
  }
];
