# Janus Angular — Frontend

**For full project documentation and architecture, please refer to the [Root README](../README.md).**

Interface web do Janus AI Architect, construída com Angular 20.

## Visão Geral
- Build com `@angular/build:application` (Vite under the hood)
- Assets servidos a partir de `public/`
- Proxy de desenvolvimento para backend via `proxy.conf.json`
- Lint com ESLint e formatação com Prettier
- CI no GitHub Actions (lint e build)

## Requisitos
- Node.js 20
- Angular CLI (`npm i -g @angular/cli`)

## Setup
```bash
cd front
npm install
npm start
```
- Dev server: `http://localhost:4200/`
- Proxy ativo: requests para `/api` e `/healthz` são encaminhadas para `http://localhost:8000`

## Scripts
- `npm run lint` — checa código com ESLint
- `npm run lint:fix` — corrige problemas de lint automaticamente
- `npm run format` — formata código com Prettier (`src/**/*.{ts,html,scss}`)
- `npm run build` — build de produção

## Ambientes (Vite)
Variáveis de ambiente seguem o padrão Vite (`import.meta.env`).

1) Copie `.env.example` para `.env` e ajuste conforme necessário:
```
VITE_API_BASE_URL=/api
```
2) Acesse no código via util exportado:
```ts
// src/app/services/api.config.ts
export const API_BASE_URL: string = import.meta.env?.VITE_API_BASE_URL ?? '/api';
```

Notas:
- Em desenvolvimento, com proxy, usar `/api` normalmente é suficiente.
- Em produção, aponte para o host real (ex.: `https://janus.example.com/api`).

## Estrutura
- `src/app` — componentes, serviços e organização por páginas/features
- `public/` — estáticos públicos (ex.: `favicon.ico`)
- `src/styles.scss` — estilos globais
- `src/app/services/api.config.ts` — base URL de API
- (Opcional) `src/app/core/` e `src/app/shared/` para organização por responsabilidade

## Qualidade de Código
- ESLint configurado em `.eslintrc.json` e ignorando `dist/`, `node_modules/` e `*.d.ts`
- Prettier configurado em `package.json` e `.prettierignore`
- Recomenda-se habilitar `strict` em `tsconfig.json` para maior robustez

## Commits e PRs
- Siga Conventional Commits (ex.: `feat(ui): adicionar gráfico de desempenho`)
- O CI valida o título dos Pull Requests seguindo esse padrão

## CI
- Workflow `ci.yml` (GitHub Actions):
  - Instala dependências
  - Roda `npm run lint`
  - Roda `npm run build`
  - Valida título de PR (Conventional Commits)

## Próximos Passos (opcionais)
- Adicionar `@angular-eslint` para regras de templates
- Criar `src/app/core/` e `src/app/shared/` com guias internos
- Habilitar `strict` no TypeScript e ajustar tipos
