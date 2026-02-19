# Janus Frontend (Angular)

Este diretório contém o código-fonte do frontend do sistema Janus, construído com Angular 20, RxJS e TailwindCSS. Ele é responsável pela interface de usuário (Chat, Dashboards de Observabilidade, Ferramentas).

## 📋 Pré-requisitos

*   **Node.js 20+**
*   **Angular CLI** (opcional, pode usar `npm run ng`)

---

## 🚀 Configuração do Ambiente de Desenvolvimento

### 1. Instalar Dependências
```bash
npm install
```

### 2. Configurar Variáveis de Ambiente
O frontend consome variáveis do arquivo `src/environments/environment.ts`. Se necessário, copie `environment.ts` para `environment.local.ts` (se existir configuração local customizada).

**Atenção:** Nunca commite chaves de API secretas (como OpenAI) no frontend. O frontend deve se comunicar apenas com o backend do Janus (`janus-api`).

---

## ▶️ Executando a Aplicação

Para iniciar o servidor de desenvolvimento:

```bash
npm start
```
Acesse em: **http://localhost:4200/**

O servidor irá recarregar automaticamente se você alterar qualquer arquivo de origem.

---

## 🏗️ Build

Para compilar o projeto para produção:

```bash
npm run build
```

Os artefatos de build serão armazenados no diretório `dist/`.

---

## 🧪 Testes

O projeto utiliza `jasmine` e `karma` (ou `vitest` se configurado) para testes unitários.

```bash
# Rodar testes unitários
npm test

# Rodar testes end-to-end (se configurado)
npm run e2e
```

---

## 📂 Estrutura do Código

*   `src/app/features/`: Módulos principais da aplicação (Auth, Chat, Tools, Observability).
*   `src/app/core/`: Serviços e utilitários globais (Guards, Interceptors, Config).
*   `src/app/shared/`: Componentes reutilizáveis (UI Kit, Pipes, Directives).
*   `src/app/services/`: Serviços de API (`JanusApiService`).

Para mais detalhes sobre a arquitetura do frontend, consulte o **[Manual de Arquitetura](../docs/MANUAL_ARQUITETURA.md)** na raiz do projeto.
