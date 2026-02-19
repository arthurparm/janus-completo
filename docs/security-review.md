# Auditoria de Segurança - Relatório Semanal

**Data da Auditoria:** 12/02/2026
**Auditor:** Jules (AI Assistant)

## Resumo Executivo

A auditoria desta semana focou em padrões de risco, segredos hardcoded, validação de entradas, controle de acesso e dependências vulneráveis. Foram identificados pontos críticos relacionados à configuração padrão de segredos e exposição de tokens em ambientes de desenvolvimento.

## Principais Descobertas

### 1. Segredos Hardcoded e Configurações Padrão Fracas
**Local:** `janus/app/config.py`
**Risco:** Alto (P0)
**Detalhes:**
- Senhas padrão definidas no código: `NEO4J_PASSWORD="password"`, `POSTGRES_PASSWORD="janus_pass"`, `RABBITMQ_PASSWORD="janus_pass"`.
- `AUTH_JWT_SECRET` é anulável, o que pode levar a configurações inseguras se não for forçado via env var.
- `CORS_ALLOW_ORIGINS` configurado como `["*"]` por padrão, permitindo requisições de qualquer origem.

### 2. Exposição de Token de Reset de Senha
**Local:** `janus/app/api/v1/endpoints/auth.py`
**Risco:** Médio (P1)
**Detalhes:**
- O endpoint `/local/request-reset` retorna o token de reset no corpo da resposta se `AUTH_RESET_RETURN_TOKEN` for `True` ou se o ambiente não for produção. Isso facilita testes, mas é um risco se habilitado acidentalmente em produção.

### 3. Ausência de Rate Limiting em Autenticação
**Local:** `janus/app/api/v1/endpoints/auth.py`
**Risco:** Médio (P1)
**Detalhes:**
- Endpoints de login e registro não possuem limitação de taxa explícita, expondo o sistema a ataques de força bruta e negação de serviço.

### 4. Logging de Informações Sensíveis (Potencial)
**Local:** `janus/app/interfaces/daemon/daemon.py`
**Risco:** Baixo/Médio (P2)
**Detalhes:**
- O daemon de voz loga o comando recebido (`logger.info(f"Command received: {command}")`). Se o comando contiver senhas ou dados pessoais ditados, isso ficará gravado nos logs.

## Checklist de Verificação Semanal

- [ ] **Segredos:** Verificar se novos segredos foram commitados no código.
- [ ] **Logs:** Buscar por PII ou tokens em logs recentes (`grep -r "logger.info" .`).
- [ ] **Dependências:** Verificar `janus/requirements.txt` e `front/package.json` por pacotes desatualizados ou vulneráveis.
- [ ] **AuthZ:** Confirmar que novos endpoints possuem decoradores de segurança (`@login_required` ou dependências de usuário).
- [ ] **Validação:** Checar se novas queries SQL ou comandos de sistema usam parametrização correta.
- [ ] **CORS:** Validar se a política de CORS está restrita aos domínios necessários.

## Recomendações Acionáveis

1.  **Remover Defaults Fracos:** Alterar `janus/app/config.py` para não ter senhas padrão ou forçar erro se as variáveis de ambiente não estiverem definidas em produção.
2.  **Restringir CORS:** Configurar `CORS_ALLOW_ORIGINS` para aceitar apenas domínios confiáveis (ex: frontend local, domínio de produção).
3.  **Rate Limiting:** Implementar middleware de rate limiting (ex: `slowapi`) nos endpoints de autenticação.
4.  **Mascaramento de Logs:** Implementar filtro de logs para mascarar dados sensíveis (PII) antes da escrita.
5.  **Revisão de Dependências:** Pinning estrito de versões em `janus/requirements.txt` e auditoria periódica com ferramentas como `safety` ou `npm audit`.

---
*Este documento deve ser atualizado semanalmente com novos achados e status das correções.*
