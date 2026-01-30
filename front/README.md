# Janus Angular — Frontend

Janus AI Architect Web Interface, built with Angular 20.

> **Note**: For the main project documentation, architecture, and roadmap, please refer to the [Root README](../README.md).

## Overview
- Built with `@angular/build:application` (Vite under the hood)
- Assets served from `public/`
- Development proxy for backend via `proxy.conf.json`
- Linting with ESLint and formatting with Prettier
- CI on GitHub Actions (lint and build)

## Requirements
- Node.js 20
- Angular CLI (`npm i -g @angular/cli`)

## Setup
```bash
cd front
npm install
npm start
```
- Dev server: `http://localhost:4200/`
- Active Proxy: requests to `/api` and `/healthz` are forwarded to `http://localhost:8000`

## Scripts
- `npm run lint` — checks code with ESLint
- `npm run lint:fix` — fixes lint issues automatically
- `npm run format` — formats code with Prettier (`src/**/*.{ts,html,scss}`)
- `npm run build` — production build

## Environments (Vite)
Environment variables follow the Vite standard (`import.meta.env`).

1) Copy `.env.example` to `.env` and adjust as needed:
```
VITE_API_BASE_URL=/api
```
2) Access in code via exported util:
```ts
// src/app/services/api.config.ts
export const API_BASE_URL: string = import.meta.env?.VITE_API_BASE_URL ?? '/api';
```

Notes:
- In development, with proxy, using `/api` is usually sufficient.
- In production, point to the real host (e.g., `https://janus.example.com/api`).

## Structure
- `src/app` — components, services, and organization by pages/features
- `public/` — public statics (e.g., `favicon.ico`)
- `src/styles.scss` — global styles
- `src/app/services/api.config.ts` — API base URL
- (Optional) `src/app/core/` and `src/app/shared/` for organization by responsibility

## Code Quality
- ESLint configured in `.eslintrc.json` ignoring `dist/`, `node_modules/` and `*.d.ts`
- Prettier configured in `package.json` and `.prettierignore`
- It is recommended to enable `strict` in `tsconfig.json` for greater robustness

## Commits and PRs
- Follow Conventional Commits (e.g., `feat(ui): add performance chart`)
- CI validates the Pull Request title following this pattern

## CI
- Workflow `ci.yml` (GitHub Actions):
  - Installs dependencies
  - Runs `npm run lint`
  - Runs `npm run build`
  - Validates PR title (Conventional Commits)

## Next Steps (optional)
- Add `@angular-eslint` for template rules
- Create `src/app/core/` and `src/app/shared/` with internal guides
- Enable `strict` in TypeScript and adjust types
