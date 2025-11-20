## Objetivo
Criar uma tela de login moderna e responsiva (Dev/Prod), alinhada ao design system atual (SCSS customizado), com autenticação por email/senha e SSO (Google/GitHub), validações em tempo real, animações sutis, suporte a modo escuro/claro, e requisitos de segurança e testes.

## UI/UX
- Layout
  - Página standalone `LoginComponent` com grid responsivo (mobile/tablet/desktop) usando SCSS e variáveis de tema existentes (`front/src/styles.scss`).
  - Logo da plataforma e mensagem de boas-vindas com destaque de diferenciais.
- Campos
  - Email com validação de formato e feedback inline.
  - Senha com toggle mostrar/ocultar (ícone com `aria-pressed`).
  - Checkbox “Lembrar-me”.
- Ações
  - Botão primário “Entrar”.
  - Links “Esqueci minha senha” e “Criar conta”.
  - Botões SSO: “Continuar com Google”, “Continuar com GitHub”.
- Estilo e animações
  - Micro animações: focus/hover nos inputs e botão, fade-in ao carregar, loader sutil ao enviar.
  - Modo escuro/claro: respeitar `prefers-color-scheme` e tokens existentes (`--bg`, `--fg`, `--primary-color`).

## Implementação Técnica
- Componentes/Arquitetura
  - Adicionar `front/src/app/pages/login/login.component.ts|html|scss` (standalone).
  - Atualizar roteamento para `/login` (core router/layout).
  - Serviço `AuthService` (`front/src/app/core/auth/auth.service.ts`) para:
    - Login por email/senha (Supabase SDK ou endpoint existente);
    - SSO Google/GitHub via Supabase; 
    - Persistência de token (Janus ou Supabase) conforme ambiente; 
    - Emissão de eventos de auth (logged in/out).
  - Guard `AuthGuard` para proteger rotas pós-login.
- Integração SSO
  - Dev: utilizar Supabase Auth (`@supabase/supabase-js`) com provedores Google/GitHub.
  - Prod: validar JWT Supabase no backend (ver segurança) ou trocar por token Janus via endpoint `/api/v1/auth/supabase/exchange`.
- Validação em tempo real
  - Reactive Forms com validators (`email`, `required`, `minLength`) e mensagens acessíveis.
- Preferências de tema
  - Detectar `prefers-color-scheme`; permitir toggle manual; persistir escolha.
- Dev vs Prod
  - `.env`:
    - Dev: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`; login direto com Supabase; token do Supabase enviado em `Authorization: Bearer`.
    - Prod: opção A: enviar token Supabase; opção B: trocar por token Janus via endpoint de exchange e continuar com `AUTH_TOKEN_KEY`.

## Segurança
- Brute force
  - Client: debouncing e lock temporário após N falhas; mensagens genéricas.
  - Backend (recomendado): rate limit já presente; adicionar contadores por IP/usuário na rota de login.
- Criptografia
  - Sempre via HTTPS; não armazenar senha localmente; utilizar SDK do IdP para submissão.
- Erros
  - Mensagens genéricas (ex.: “Credenciais inválidas”); logs detalhados somente no servidor.

## Acessibilidade
- WCAG 2.1 AA
  - Labels e `aria-*` apropriados; foco visível; contraste >= 4.5:1; navegação por teclado; anúncios de erro via `aria-live`.

## Testes
- Cross-browser: Chrome, Firefox, Safari, Edge (Smoke + form validation + SSO botões).
- Responsividade: breakpoints mobile/tablet/desktop com screenshots.
- Acessibilidade: Lighthouse + axe-core; verificação de foco/labels/contraste.
- Performance: Lighthouse score > 90; lazy load da página; imagens otimizadas; CSS crítico minimizado.
- Unit: validações do formulário, toggles, estados de loading, AuthService mockado.
- E2E: login por email/senha (mock), login via Google/GitHub (stub de popup/redirecionamento).

## Ajustes Backend (recomendados)
- Validar JWT Supabase em `get_actor_user_id` (carregar JWK público) para mapear `sub/email` → `user_id` interno (criar se não existir).
- Alternativa: criar `POST /api/v1/auth/supabase/exchange` que valida o JWT do Supabase e retorna token Janus, integrando com o front atual.
- Desabilitar fallback `X-User-Id` em produção quando IdP ativo.

## Entregáveis
- Página de login completa e responsiva com SSO.
- Serviço/guard de autenticação e roteamento.
- Variáveis de ambiente e integração Dev/Prod.
- Suite de testes (unit/e2e) e relatório Lighthouse > 90.
- Instruções de configuração (env) e verificação manual.

Confirma que seguimos com esta implementação (Supabase para SSO e fluxo Dev/Prod) e com o endpoint de exchange no backend para Prod?