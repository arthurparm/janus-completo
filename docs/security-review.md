# Relatório de Revisão de Segurança Semanal

**Data:** 2026-02-14
**Responsável:** Janus (Automated Scan)
**Foco:** Segurança de Código e Configuração (Backend & Frontend)

## Resumo Executivo

A varredura semanal identificou **4 riscos principais** que requerem atenção imediata. O risco mais crítico envolve a exposição potencial de tokens de redefinição de senha via API, o que pode levar a um comprometimento total de contas de usuário. Além disso, foram encontrados segredos com valores padrão hardcoded e dependências desatualizadas.

## Checklist de Verificação

| Categoria | Status | Observações |
|---|---|---|
| **Segredos Hardcoded** | ⚠️ Risco Alto | Valores padrão inseguros encontrados em `janus/app/config.py`. |
| **Autenticação & AuthZ** | ❌ Crítico | Endpoint de reset de senha retorna token na resposta sob certas condições. |
| **Logs & Monitoramento** | ⚠️ Risco Médio | Logs do `ChatService` podem conter PII e conteúdo de mensagens. |
| **Dependências** | ⚠️ Risco Médio | `tiktoken==0.12.0` está desatualizado (versão atual > 0.7). |
| **Rate Limiting** | ❓ Não Implementado | Ausência de proteção contra força bruta em endpoints de auth (`/login`, `/reset`). |
| **Validação de Entrada** | ✅ OK | Uso extensivo de Pydantic para validação de schemas. |

## Detalhamento dos Achados

### 1. [CRÍTICO] Exposição de Token de Reset de Senha
- **Arquivo:** `janus/app/api/v1/endpoints/auth.py`
- **Descrição:** O endpoint `POST /local/request-reset` retorna o `reset_token` no corpo da resposta JSON se a variável `AUTH_RESET_RETURN_TOKEN` for `True` ou se o ambiente não for `production`.
- **Risco:** Um atacante pode solicitar a redefinição de senha de qualquer usuário (se souber o email) e obter o token imediatamente para alterar a senha, assumindo o controle da conta.
- **Trecho de Código:**
  ```python
  if getattr(settings, "AUTH_RESET_RETURN_TOKEN", False) or settings.ENVIRONMENT != "production":
      return LocalResetResponse(status="ok", reset_token=token)
  ```
- **Recomendação:** Remover incondicionalmente o retorno do token na resposta da API. O token deve ser enviado apenas por email (ou logado no console apenas em ambiente de desenvolvimento local explícito, nunca em homologação/produção).

### 2. [ALTO] Segredos com Valores Padrão (Hardcoded)
- **Arquivo:** `janus/app/config.py`
- **Descrição:** A classe `AppSettings` define valores padrão para variáveis sensíveis como `POSTGRES_PASSWORD`, `RABBITMQ_PASSWORD`, etc.
- **Risco:** Se as variáveis de ambiente não forem carregadas corretamente (falha no `.env` ou orquestrador), a aplicação iniciará com credenciais conhecidas e inseguras, facilitando acesso não autorizado.
- **Recomendação:** Remover valores padrão para segredos críticos e obrigar a falha na inicialização (`Field(..., min_length=1)`) se a variável de ambiente estiver ausente.

### 3. [MÉDIO] Potencial Log de PII e Conteúdo Sensível
- **Arquivo:** `janus/app/services/chat_service.py` e outros serviços.
- **Descrição:** Uso de `logger.info` para registrar fluxo de chat. Embora o payload completo não tenha sido confirmado como logado em todas as chamadas, há risco de vazamento de dados do usuário (LGPD) nos logs de aplicação.
- **Recomendação:** Implementar um `RedactingFormatter` no `structlog` para mascarar padrões de CPF, Email e Cartão de Crédito, e evitar logar o corpo de mensagens de usuário (`content`) em nível INFO.

### 4. [MÉDIO] Dependências Desatualizadas e Vulneráveis
- **Arquivo:** `janus/requirements.txt`
- **Descrição:**
  - `tiktoken==0.12.0` (Antiga, possível problema de performance/segurança).
  - Outras libs com versões pinadas muito antigas.
- **Recomendação:** Atualizar `tiktoken` para versão recente e rodar `pip-audit` ou `safety` periodicamente no CI.

## Plano de Ação Imediato

1. **[P0]** Refatorar `local_request_reset` para nunca retornar o token no corpo da resposta.
2. **[P1]** Remover defaults inseguros de `config.py`.
3. **[P1]** Adicionar Rate Limiting (via `slowapi` ou Nginx) nas rotas de `/auth`.
4. **[P2]** Atualizar dependências críticas.
