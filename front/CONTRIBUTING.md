# Contribuindo para o Frontend (Janus Angular)

Obrigado por contribuir ao frontend! Este guia cobre setup, convenções e fluxo de trabalho.

## Requisitos
- Node.js 20
- Angular CLI (`npm i -g @angular/cli`)

## Setup
```bash
cd front
npm install
npm start
```

## Scripts úteis
- `npm run lint` — checa código com ESLint
- `npm run lint:fix` — corrige problemas de lint automaticamente
- `npm run format` — formata código com Prettier
- `npm run build` — build de produção

## Padrão de Commits
Siga Conventional Commits:
```
<tipo>(escopo opcional): descrição
```
Tipos: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `build`, `ci`, `chore`, `perf`, `revert`.
Exemplos:
- `feat(ui): adicionar gráfico de desempenho`
- `fix(router): corrigir rota inválida`

O CI valida títulos de PR com esse padrão.

## Estrutura
- `src/app` — componentes, serviços e módulos
- `src/assets` — estáticos (se necessário)
- `public/` — favicon e estáticos públicos
- `dist/` — artefatos de build

## Qualidade de código
- Mantenha componentes pequenos e coesos
- Evite lógica pesada em componentes; use serviços
- Utilize tipagem forte (`strict` no `tsconfig.json` recomendado)

## Pull Requests
Inclua na descrição:
- Objetivo e escopo
- Screenshots (se houver mudanças visuais)
- Checklist:
  - [ ] Lint/format executados
  - [ ] Build passa localmente
  - [ ] Docs atualizados quando necessário