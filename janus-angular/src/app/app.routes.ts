import {Routes} from '@angular/router';
import {MainLayout} from './core/layout/main-layout/main-layout';

export const routes: Routes = [
  {
    path: '',
    component: MainLayout,
    children: [
      {path: '', pathMatch: 'full', loadComponent: () => import('./pages/home/home').then(m => m.HomeComponent)},
      {path: 'arquitetura', loadComponent: () => import('./pages/arquitetura/arquitetura').then(m => m.Arquitetura)},
      {path: 'sprints', loadComponent: () => import('./pages/sprints/sprints').then(m => m.Sprints)},
      {path: 'painel', loadComponent: () => import('./features/dashboard/dashboard/dashboard').then(m => m.Dashboard)},
      {
        path: 'documentacao',
        loadComponent: () => import('./pages/documentacao/documentacao').then(m => m.Documentacao)
      },
      {path: '**', redirectTo: ''}
    ]
  }
];
