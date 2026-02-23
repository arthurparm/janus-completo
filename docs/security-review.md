# Auditoria de Segurança Semanal (Security Review)

**Data da Última Varredura:** 25/02/2026
**Responsável:** Janus (Automated Agent)
**Status Geral:** 🟡 Atenção Requerida

Este documento centraliza os achados das auditorias de segurança semanais, focando em proteção de dados, controle de acesso e vulnerabilidades conhecidas.

## Checklist Semanal

- [x] **Varredura de PII/Segredos:** Executar `scripts/security_scan.py` para identificar logs sensíveis ou segredos hardcoded.
- [x] **Revisão de AuthZ:** Verificar se novos endpoints possuem `Depends(get_current_user)` ou equivalente.
- [x] **Rate Limiting:** Confirmar se endpoints sensíveis (auth, reset, pagamento) possuem limitação de taxa.
- [x] **Dependências:** Verificar `requirements.txt` e `package.json` por pacotes desatualizados ou com CVEs conhecidos.
- [x] **Permissões de Arquivo:** Revisar criação de arquivos temporários e permissões de execução.
- [x] **Configurações Default:** Garantir que segredos não estão usando valores padrão em produção.

## Achados e Gaps (25/02/2026)

### 1. Ausência de Autenticação (AuthZ) 🔴 Crítico
Foram identificados endpoints críticos sem verificação de autenticação explícita. Isso permite que qualquer usuário com acesso à rede chame estas funções.

*   **Arquivo:** `janus/app/api/v1/endpoints/workspace.py`
    *   `POST /add_artifact`
    *   `GET /get_artifact`
    *   `POST /send_message`
    *   `GET /get_messages_for`
    *   `POST /shutdown_system` (Risco Extremo)
*   **Arquivo:** `janus/app/api/v1/endpoints/meta.py`
    *   `GET /get_status` (Pode ser intencional, mas requer validação)

### 2. Rate Limiting Ausente 🟠 Alto
Endpoints sensíveis de autenticação não parecem ter decoradores de rate limit aplicados, facilitando ataques de força bruta.

*   **Arquivo:** `janus/app/api/v1/endpoints/auth.py`
    *   Login, Refresh Token e possivelmente fluxos de recuperação de senha.

### 3. Log de PII (LGPD) 🟡 Médio
Alguns logs estão registrando metadados que podem identificar usuários ou expor comunicações privadas.

*   **Arquivo:** `janus/app/core/tools/productivity_tools.py:42`
    *   `logger.info("[EMAIL]", extra={"user_id": user_id, "to": to, "subject": subject})`
    *   O assunto do email e o destinatário são dados pessoais. Devem ser mascarados ou removidos dos logs de produção.
*   **Arquivo:** `janus/app/core/autonomy/policy_engine.py:207`
    *   `logger.warning(..., token=token)` - Verificar se este token é um segredo ou apenas um identificador opaco.

### 4. Uso de Funções Perigosas (Exec/Eval) 🟡 Médio
O uso de `exec` e `subprocess` é esperado no contexto de *Sandboxing*, mas deve ser monitorado estritamente.

*   **Execução Dinâmica:** `janus/app/core/infrastructure/python_sandbox.py`, `janus/app/core/workers/sandbox_agent_worker.py` usam `exec`. Certificar-se de que o input é sanitizado ou roda em container isolado (Docker).
*   **Código de Teste em Prod?** `janus/app/core/tools/faulty_tools.py` usa `eval`. Se este arquivo for carregado em produção, representa um risco desnecessário.

### 5. Dependências
*   As dependências principais (`fastapi`, `sqlalchemy`, `pydantic`, `angular`) estão atualizadas.
*   Recomendação: Adicionar `pip-audit` e `npm audit` ao pipeline de CI.

## Recomendações Acionáveis

1.  **Imediato (P0):** Adicionar `Depends(get_current_user)` a todos os endpoints de `workspace.py`, especialmente `shutdown_system`.
2.  **Imediato (P0):** Aplicar Rate Limiting no endpoint de login em `auth.py`.
3.  **Curto Prazo (P1):** Refatorar `productivity_tools.py` para mascarar emails e assuntos nos logs (ex: `s*****@domain.com`).
4.  **Curto Prazo (P1):** Verificar se `faulty_tools.py` é necessário no build de produção e removê-lo se não for.
5.  **Médio Prazo (P2):** Implementar testes automatizados que falham se uma rota pública não for explicitamente marcada como tal (allowlist).

---
*Gerado automaticamente via `scripts/security_scan.py` e análise manual.*
