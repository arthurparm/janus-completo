# Janus Angular — Frontend

Frontend interface for Janus AI Architect, built with Angular 20.

See [Root README](../README.md) for architecture overview.

## Requirements
- Node.js 20
- Angular CLI (`npm i -g @angular/cli`)

## Setup

```bash
cd front
npm install
npm start
```

*   **Dev server**: `http://localhost:4200/`
*   **Proxy**: Requests to `/api` and `/healthz` are proxied to `http://localhost:8000` (backend).

## Scripts

*   `npm run lint` — Check code with ESLint.
*   `npm run lint:fix` — Fix lint issues automatically.
*   `npm run format` — Format code with Prettier.
*   `npm run build` — Production build.

## Environments (Vite)

Environment variables follow the Vite standard (`import.meta.env`).

1.  Copy `.env.example` to `.env` and adjust if necessary:
    ```
    VITE_API_BASE_URL=/api
    ```
2.  Access in code via exported util:
    ```ts
    // src/app/services/api.config.ts
    export const API_BASE_URL: string = import.meta.env?.VITE_API_BASE_URL ?? '/api';
    ```

**Notes**:
*   In development (with proxy), using `/api` is usually sufficient.
*   In production, point to the real host (e.g., `https://janus.example.com/api`).

## Structure

*   `src/app` — Components, services, and feature organization.
*   `public/` — Public static assets.
*   `src/styles.scss` — Global styles.

## Code Quality

*   **ESLint**: Configured in `.eslintrc.json`.
*   **Prettier**: Configured in `package.json` and `.prettierignore`.
*   **CI**: GitHub Actions runs lint and build. Commits must follow [Conventional Commits](https://www.conventionalcommits.org/).
