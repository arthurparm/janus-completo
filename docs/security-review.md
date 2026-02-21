# Auditoria de Seguranca Semanal

**Data:** 2026-03-01
**Responsavel:** Jules (AI Software Engineer)
**Escopo:** janus/app, front/src, docs/ (Excluindo BMAD)

## Resumo Executivo
A auditoria desta semana focou em padroes de risco comuns: logs com PII, validacao de entrada, permissoes, endpoints sem autenticacao, segredos hardcoded e limitacao de taxa.

**Resultados Principais:**
- **Critico (P0):** Bypass de autenticacao possivel via header `X-User-Id` em `auth.py`.
- **Alta (P0):** Endpoints criticos (`workspace`, `llm`) sem `Depends(get_current_user)` ou equivalente, confiando apenas em servicos injetados sem contexto de usuario verificado.
- **Alta (P0):** Logs contendo PII (conteudo de email) em `productivity_tools.py`.
- **Media (P1):** Ausencia de varredura automatizada de dependencias vulneraveis.
- **Media (P1):** Rate limiting com falha "open" (se Redis cair, libera tudo) e dependente de IP/API Key nao obrigatoria.

---

## 1. Checklist de Verificacao

| Categoria | Item | Status | Observacao |
|---|---|---|---|
| **Logs & Auditoria** | Logs livres de PII/Tokens | 🔴 FALHA | `productivity_tools.py` loga emails e assuntos. |
| | Rotacao de logs configurada | 🟡 PARCIAL | Log file definido, mas sem politica de rotacao clara no codigo. |
| **Autenticacao (AuthN)** | Tokens validados criptograficamente | 🟡 ALERTA | Token customizado (nao-JWT padrao). Assinatura HMAC ok, mas formato proprietario. |
| | Segredos de assinatura seguros | 🟡 ALERTA | Fallback para segredo efemero em dev/teste. Prod exige env var. |
| | Protecao contra impersonation | 🔴 FALHA | `get_actor_user_id` confia cegamente em `X-User-Id` se header `Authorization` estiver ausente. |
| **Autorizacao (AuthZ)** | Endpoints protegidps por padrao | 🔴 FALHA | Diversos endpoints (`/workspace`, `/llm`) nao validam usuario logado. |
| | RBAC/Scopes implementados | 🟡 PARCIAL | `Consents` tem escopo, mas uso pratico limitado. |
| **Seguranca de Dados** | Segredos hardcoded removidos | 🟢 OK | Maioria em `settings` ou env vars. Falsos positivos em chaves de dicionario. |
| | Validacao de input (Pydantic) | 🟢 OK | Uso extensivo de Pydantic models. |
| **Infraestrutura** | Rate Limiting ativo | 🟡 PARCIAL | Middleware existe, mas falha aberto e nao cobre endpoints sem auth de forma robusta. |
| | Dependencias atualizadas | 🟡 ALERTA | Sem scanner automatico (Snyk/Dependabot) configurado no CI. |

---

## 2. Detalhe dos Gaps Encontrados

### [SEG-001] Auth Bypass via `X-User-Id`
**Local:** `janus/app/core/infrastructure/auth.py`
**Descricao:** A funcao `get_actor_user_id` aceita o header `X-User-Id` sem validacao se o token JWT estiver ausente.
**Risco:** Qualquer atacante pode impersonar qualquer usuario (incluindo admin) enviando este header.
**Recomendacao:** Remover a leitura de `X-User-Id` ou validar se a requisicao vem de um gateway confiavel (mTLS/IP allowlist) que ja tenha validado o token.

### [SEG-002] Endpoints Criticos sem Autenticacao
**Local:** `janus/app/api/v1/endpoints/workspace.py`, `janus/app/api/v1/endpoints/llm.py`
**Descricao:** Endpoints como `/workspace/artifacts/add` e `/llm/invoke` nao exigem `Depends(get_current_user)`.
**Risco:** Uso nao autorizado de recursos computacionais (LLM custa dinheiro) e manipulacao de estado do workspace.
**Recomendacao:** Adicionar `user: dict = Depends(get_current_user)` em todos os routers publicos.

### [SEG-003] Vazamento de PII em Logs
**Local:** `janus/app/core/tools/productivity_tools.py`
**Descricao:** `logger.info("[EMAIL]", extra={"user_id": user_id, "to": to, "subject": subject})`
**Risco:** Exposicao de enderecos de email e assuntos confidenciais em logs que podem ser indexados (Splunk/ELK) ou vazados.
**Recomendacao:** Mascarar emails (`j***@example.com`) e nao logar o assunto, ou usar nivel `DEBUG` e garantir que debug logs nao vao para producao/retencao longa.

### [SEG-004] Rate Limiting "Fail Open"
**Local:** `janus/app/core/infrastructure/rate_limit_middleware.py`
**Descricao:** Se o Redis falhar ou script Lua nao carregar, a requisicao passa (`call_next`).
**Risco:** Ataques de DDOS ou brute-force podem derrubar o servico se o Redis for o ponto de falha.
**Recomendacao:** Avaliar "Fail Closed" para endpoints criticos ou implementar in-memory fallback com limites mais baixos.

---

## 3. Plano de Acao Imediato

1. **Hotfix:** Remover leitura de `X-User-Id` em `auth.py` (ou restringir drasticamente).
2. **Refatoracao:** Adicionar dependencia de seguranca mandatoria nos routers de `workspace` e `llm`.
3. **Cleanup:** Sanitizar logs de email.
4. **CI:** Adicionar step de `pip-audit` ou `safety` no pipeline de CI.
