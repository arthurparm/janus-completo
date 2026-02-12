# Development Guide - Frontend (`front`)

## Pre-requisitos

- Node.js 20
- npm
- Angular CLI (`npm i -g @angular/cli`)

## Setup Local

```bash
cd front
npm install
npm start
```

Servidor dev padrao: `http://localhost:4200`

## Scripts Principais

- `npm start` - sobe app com proxy `proxy.conf.json`
- `npm run start:tailscale` - sobe com proxy tailscale
- `npm run build` - build de producao
- `npm run test` - executa vitest
- `npm run lint` - lint em `src`
- `npm run format` - prettier em `src/**/*.{ts,html,scss}`

## Ambiente e Config

- `src/environments/environment.ts`
- `src/environments/environment.prod.ts`
- `src/app/services/api.config.ts` (base API e flags)

## Testes

- Unit/spec files em `src/**/*.spec.ts`
- Runner principal: Vitest

## Boas Praticas

- Evitar logica de negocio pesada em componentes.
- Centralizar chamadas HTTP em servicos.
- Preferir Signals/RxJS para estado observavel.

---

_Gerado pelo workflow BMAD `document-project`_
