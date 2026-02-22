# Relatório de Adequação LGPD (Lei Geral de Proteção de Dados)

**Data:** 2026-03-03
**Status:** Revisão Inicial (Gap Analysis)
**Responsável:** Janus Security Agent

## 1. Inventário de Dados Pessoais (Data Mapping)

Com base na análise estática do código fonte, o sistema processa e armazena os seguintes tipos de Dados Pessoais:

| Dado | Fonte | Finalidade | Armazenamento | Risco Identificado |
|---|---|---|---|---|
| **User ID** | JWT, Headers | Identificação única do titular | Logs, BD (Postgres/Neo4j), Memória | **Alto:** Logado excessivamente em texto claro. |
| **Conteúdo de Chat** | Input do Usuário | Prestação do serviço de IA | Postgres, Neo4j, Qdrant | **Médio:** Pode conter PII não estruturada sensível. |
| **E-mail (Metadados)** | Ferramentas (`productivity_tools.py`) | Envio de notificações | Logs (INFO) | **Alto:** Endereço de e-mail e Assunto logados. |
| **Eventos de Calendário** | Ferramentas (`productivity_tools.py`) | Gestão de agenda | Memória (Global Var) | **Médio:** Armazenamento volátil sem expurgo definido. |
| **Notas Pessoais** | Ferramentas (`productivity_tools.py`) | Anotações do usuário | Memória (Global Var) | **Médio:** Armazenamento volátil sem expurgo definido. |

## 2. Lacunas de Conformidade (Gaps)

### 2.1 Princípio da Minimização de Dados (Art. 6º, III)
**Situação:** O sistema registra identificadores de usuário (`user_id`) e metadados de comunicação (E-mail `to`, `subject`) nos logs de aplicação (`janus.log`).
**Violação:** Coleta e retenção de dados além do estritamente necessário para a finalidade de auditoria técnica, expondo dados pessoais em infraestrutura de observabilidade.

### 2.2 Princípio da Segurança (Art. 6º, VII)
**Situação:** Vulnerabilidade crítica em `janus/app/core/infrastructure/auth.py` permite a personificação de usuários via header `X-User-Id`.
**Violação:** Falha em garantir a confidencialidade e integridade dos dados, permitindo acesso não autorizado a dados pessoais de terceiros (vazamento de dados).

### 2.3 Princípio da Necessidade e Retenção (Art. 15 e 16)
**Situação:** Embora exista um esboço de serviço `DataRetentionService`, não foi identificada configuração ativa ou agendamento (cron/worker) para a eliminação automática de dados após o término do tratamento.
**Violação:** Manutenção de dados pessoais por tempo indeterminado ("forever storage") sem base legal que justifique.

### 2.4 Armazenamento em Memória Global
**Situação:** O módulo `productivity_tools.py` armazena notas e eventos em dicionários globais (`_notes`, `_calendar_events`) que crescem indefinidamente enquanto o processo roda.
**Violação:** Risco de vazamento massivo em caso de despejo de memória (core dump) e falta de isolamento adequado entre sessões/tenants se a lógica falhar.

## 3. Plano de Ação (Remediação)

| ID | Ação | Prioridade | Prazo Sugerido |
|---|---|---|---|
| **L-01** | **Sanitização de Logs:** Remover log de `email` e `subject` em `productivity_tools.py`. Mascarar `user_id` em logs não essenciais. | **Imediato (P0)** | 1 semana |
| **L-02** | **Correção de Auth:** Eliminar bypass de `X-User-Id` para prevenir acesso cruzado a dados. | **Imediato (P0)** | 1 semana |
| **L-03** | **Política de Retenção:** Operacionalizar o `DataRetentionService` com job agendado para expurgo de chats > X dias (conforme Termos de Uso). | **Alta (P1)** | 2 semanas |
| **L-04** | **Persistência Segura:** Migrar armazenamento de Notas/Calendário de memória global para Banco de Dados com criptografia em repouso e controle de acesso (RLS). | **Média (P2)** | 1 mês |
| **L-05** | **Gestão de Consentimento:** Revisar endpoints de `/consents` para garantir que revogações tenham efeito imediato no processamento (ex: parar indexação em Qdrant). | **Média (P2)** | 1 mês |
