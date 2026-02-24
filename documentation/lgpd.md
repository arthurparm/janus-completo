# Avaliação de Conformidade LGPD

**Data da Revisão:** 16/10/2023 (Semana Atual)
**Escopo:** Proteção de Dados Pessoais em Módulos Internos

## 1. Visão Geral

Este documento mapeia os pontos de tratamento de dados pessoais identificados na varredura automatizada (`tooling/security_scan.py`) e revisão manual. O objetivo é garantir conformidade com a Lei Geral de Proteção de Dados (LGPD - Lei nº 13.709/2018).

## 2. Mapeamento de Dados e Riscos

### 2.1 Ferramentas de Produtividade (`productivity_tools.py`)

-   **Dado Pessoal:** Endereço de e-mail (`to`) e assunto (`subject`).
-   **Contexto:** Ferramenta `send_email`.
-   **Risco (Alto):** O conteúdo do destinatário e do assunto está sendo registrado em logs de aplicação (`logger.info`).
-   **Violação LGPD:** Princípio da Necessidade e Segurança. Logs de aplicação geralmente têm retenção mais longa e acesso mais amplo que o necessário para depuração de envio de emails.
-   **Ação Recomendada:** Remover ou ofuscar o e-mail nos logs. Manter apenas status de sucesso/falha e ID interno.

### 2.2 Gestão de Usuários do Sistema (`system_user_service.py`)

-   **Dado Pessoal:** E-mail de administrador (`SYSTEM_USER_EMAIL`), Hash de Senha.
-   **Contexto:** Inicialização de conta de sistema.
-   **Risco (Médio):** A lógica de manipulação de credenciais está próxima a chamadas de log. Embora a senha não seja logada explicitamente, qualquer alteração futura neste arquivo requer revisão de segurança rigorosa.
-   **Conformidade:** O armazenamento de senha utiliza hash (`hash_password`), o que está em conformidade com boas práticas.
-   **Ação Recomendada:** Adicionar comentário de alerta no código para evitar logs futuros acidentais.

### 2.3 Logs de Tokens (`rate_limiter.py`, `client.py`)

-   **Dado Pessoal:** Nenhum (Tokens de LLM).
-   **Análise:** O termo "token" refere-se à contagem de uso de modelos de IA, não a dados pessoais ou de autenticação.
-   **Status:** Conforme.

## 3. Gaps de Conformidade

| Item | Descrição | Status | Prioridade |
| :--- | :--- | :--- | :--- |
| **Sanitização de Logs** | Falta de mecanismo automático para ofuscar PII (CPF, E-mail) em logs. | 🔴 Crítico | Alta |
| **Retenção de Dados** | Política de retenção de logs de aplicação não definida formalmente no código. | 🟡 Atenção | Média |
| **Consentimento** | Ferramentas de e-mail/calendário operam sob permissão do usuário, mas o registro em log excede o escopo. | 🔴 Crítico | Alta |

## 4. Plano de Ação LGPD

1.  **Imediato:** Remover log de e-mail em `backend/app/core/tools/productivity_tools.py`.
2.  **Curto Prazo:** Implementar middleware de sanitização de logs para PII.
3.  **Médio Prazo:** Revisar todos os endpoints que recebem dados de usuário para garantir que apenas o estritamente necessário seja processado e armazenado.
