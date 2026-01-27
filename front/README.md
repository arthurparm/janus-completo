# Janus Frontend

This directory contains the Angular 20 frontend for the Janus AI Architect.

## 📌 Documentation
Please refer to the **[Root README](../README.md)** for full project documentation and architecture details.

## 🚀 Local Setup

1. **Install Dependencies**
   ```bash
   npm install
   ```

2. **Start Development Server**
   ```bash
   npm start
   ```
   - **URL**: http://localhost:4200
   - **Proxy**: `/api` and `/healthz` are proxied to `http://localhost:8000`.

## 🛠️ Scripts
- `npm run lint`: Check code with ESLint.
- `npm run format`: Format code with Prettier.
- `npm run build`: Production build.

## 🌍 Environment (Vite)
Environment variables follow the Vite standard (`import.meta.env`).
Copy `.env.example` to `.env` to configure `VITE_API_BASE_URL`.
