# Janus Frontend (Angular)

Web interface for Janus AI Architect, built with Angular 20 and Vite.

For full project context and architecture, please refer to the **[Root README](../README.md)**.

## 🛠️ Setup

### Prerequisites
*   Node.js 20+
*   Backend service running at `http://localhost:8000` (for API proxy).

### Installation

1.  Navigate to this directory:
    ```bash
    cd front
    ```

2.  Install dependencies:
    ```bash
    npm install
    ```

### Running the Application

Start the development server:

```bash
npm start
```

*   **App URL**: `http://localhost:4200/`
*   **Proxy**: Requests to `/api` and `/healthz` are proxied to `http://localhost:8000`.

## 📦 Build & Lint

*   **Lint**: `npm run lint`
*   **Fix Lint**: `npm run lint:fix`
*   **Format**: `npm run format`
*   **Build**: `npm run build`

## ⚙️ Environment

Environment variables are managed via Vite.
To customize, copy `.env.example` to `.env`.

```
VITE_API_BASE_URL=/api
```
