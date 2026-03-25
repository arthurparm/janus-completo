---
tipo: dominio
dominio: backend
camada: seguranca
fonte-de-verdade: codigo
status: ativo
---

# Segurança e Infra

## Objetivo
Mapear os guardrails transversais do backend.

## Responsabilidades
- Cobrir autenticação, autorização, rate limits e headers.
- Mostrar mecanismos de proteção na superfície chat/tooling.

## Entradas
- JWT/local auth.
- Middleware e guards.
- Configuração de segredos.

## Saídas
- Plano de proteção operacional do backend.

## Dependências
- [[04 - Fluxos End-to-End/Login e Identidade]]
- [[04 - Fluxos End-to-End/Ferramentas e Sandbox]]
- [[05 - Infra e Operação/Healthchecks e Contratos Operacionais]]

## Componentes
- `secret_validator`: só bloqueia o boot quando `ENVIRONMENT=production` e algum segredo crítico ainda está em valor default inseguro conhecido.
- Auth endpoints: emissão de token, local auth, troca com providers.
- `auth_rate_limiter` e `RateLimitMiddleware`.
- `SecurityHeadersMiddleware`.
- Guards de request e pending actions para risco/consentimento.
- Políticas de tool execution, sandbox e quotas de memória.

## Arquivos-fonte
- `backend/app/api/v1/endpoints/auth.py`
- `backend/app/core/security/*`
- `backend/app/core/infrastructure/auth.py`
- `backend/app/core/infrastructure/rate_limit_middleware.py`
- `backend/app/core/middleware/security_headers.py`

## Fluxos relacionados
- [[06 - Qualidade e Testes/Contratos Cobertos]]
- [[07 - Glossário e Inventários/Inventário de Integrações Externas]]

## Riscos/Lacunas
- A segurança é espalhada por endpoint, middleware e serviços.
- O sistema combina auth clássica e governança baseada em confirmação/risco, exigindo leitura contextual.
