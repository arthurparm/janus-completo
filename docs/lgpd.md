# Relatório de Conformidade LGPD (Proteção de Dados)

**Data da Última Revisão:** 25/02/2026
**Responsável:** Janus (Automated Agent)
**Status Geral:** 🟡 Atenção Requerida

Este documento foca especificamente na conformidade com a Lei Geral de Proteção de Dados (LGPD), analisando o manuseio de Dados Pessoais (PII) e Dados Sensíveis.

## Checklist Semanal

- [x] **Identificação de PII:** Executar `scripts/security_scan.py` buscando por CPF, Email, Telefone em logs.
- [x] **Retenção de Dados:** Verificar se há política de expurgo para dados antigos (logs, sessões, uploads).
- [x] **Logs de Auditoria:** Garantir que acessos a dados sensíveis gerem trilha de auditoria segura (quem acessou o quê).
- [x] **Consentimento:** Verificar se interfaces de coleta de dados (formulários, chat) possuem aviso de privacidade.
- [x] **Compartilhamento:** Revisar integrações externas (LLMs, APIs) para garantir que apenas dados necessários são enviados.

## Achados e Gaps (25/02/2026)

### 1. Vazamento de Dados Pessoais em Logs (PII) 🔴 Crítico
Logs de aplicação em nível `INFO` ou `DEBUG` podem estar persistindo dados pessoais em texto claro, violando o princípio da Minimização e Segurança.

*   **Identificado:** `janus/app/core/tools/productivity_tools.py:42`
    *   **Dado:** Email do destinatário (`to`) e Assunto (`subject`).
    *   **Risco:** Se logs forem vazados ou acessados indevidamente, revela contatos privados e contexto de comunicação.
    *   **Ação:** Implementar filtro de log ou mascarar dados (`e***@domain.com`).

*   **Identificado:** `janus/app/core/autonomy/policy_engine.py` e `janus/app/services/chat_service.py`
    *   **Dado:** Tokens de sessão e User IDs em logs.
    *   **Risco:** Identificação unívoca do titular e potencial sequestro de sessão.

### 2. Retenção de Dados Indefinida (Storage Limitation) 🟠 Alto
Não foi identificada uma rotina clara de limpeza automática para dados antigos.

*   **Gap:** Logs de aplicação (`janus.log`), uploads temporários em `/app/workspace` e sessões de chat antigas no banco de dados parecem não ter TTL (Time-To-Live) configurado.
*   **Recomendação:** Implementar `janus/app/services/data_retention_service.py` (se existir) com jobs agendados para expurgo conforme política (ex: 90 dias para logs, 30 dias para uploads).

### 3. Compartilhamento com Terceiros (LLMs) 🟡 Médio
O envio de dados para APIs de LLM (OpenAI, Anthropic, Google) deve ser transparente.

*   **Gap:** Verificar se mensagens de usuário contendo PII são sanitizadas antes do envio ao modelo, ou se há contrato de confidencialidade (Zero Data Retention) ativo nas APIs corporativas.
*   **Recomendação:** Implementar middleware de PII Redaction antes da chamada ao LLM para dados sensíveis como CPF/Cartão de Crédito.

### 4. Direito dos Titulares 🟡 Médio
A API atual não parece expor endpoints fáceis para atender solicitações de titulares (Ex: "Exportar meus dados", "Esquecer-me").

*   **Gap:** Falta de endpoints `GET /user/export` e `DELETE /user/forget`.
*   **Recomendação:** Adicionar suporte a exportação de dados (formato portável JSON) e exclusão lógica/física.

## Plano de Ação

1.  **Imediato (P0):** Sanitizar logs em `productivity_tools.py`.
2.  **Curto Prazo (P1):** Definir e implementar política de rotação de logs (Log Rotation) e retenção no banco de dados.
3.  **Médio Prazo (P2):** Criar endpoints de gestão de privacidade para o usuário final (Export/Delete).
4.  **Longo Prazo (P3):** Implementar PII Redaction automático no pipeline de RAG e LLM.

---
*Gerado automaticamente via `scripts/security_scan.py` e análise manual.*
