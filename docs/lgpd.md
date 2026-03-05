# Relatório de Conformidade LGPD - Janus

Data de criação: 2026-03-01
Objetivo: Mapear fluxos de dados sensíveis e riscos de privacidade dentro do sistema.

## 1. Inventário de Dados e PII (Informações Pessoais Identificáveis)
Atualmente o sistema processa e interage com as seguintes informações pessoais (PII):
- E-mails (Remetente e Destinatários via Productivity Tools)
- Números de telefone (Redação parcial no backend)
- Identificadores governamentais (CPF, CNPJ, IPs mapeados em `memory/security.py`)
- Dados Biométricos de Áudio (Comandos de voz capturados pela interface Janus Daemon)
- Interações diretas no Chat (Conversas, histórico e "thought streams" guardados em banco de dados).

## 2. Pontos de Risco Atuais (Achados da Auditoria)
- **Vazamento por Logging:** O `ChatEventPublisher`, `CollaborationService` e `ChatCommandHandler` estão gravando partes do conteúdo dos usuários, como prévias (100 caracteres) e meta-dados de e-mail e payloads, de forma não ofuscada nos arquivos de log estáticos da aplicação (`janus.log`).
- **Retenção Descontrolada:** Embora exista o `DataRetentionService`, ele depende de execuções assíncronas falhas acopladas a transações síncronas (`sync_events.py`) e falta um cron job para varrer e aplicar expurgo estruturado. Ademais, os logs gravados em disco (`janus.log`) não contam com política de rotação.
- **Vazamento em In-Memory (Feito):** As `ProductivityTools` mantinham globais (_notes, _calendar_events) na memória volátil que constituíam risco não-persistente. As variáveis globais foram removidas e os dados agora são armazenados de forma isolada em arquivos JSON no diretório seguro de workspaces (`WORKSPACE_DIR`).

## 3. Próximos Passos (Plano de Mitigação)
1. Estender a camada de ofuscação (`app.core.memory.security`) para injetar um redator diretamente nas configurações do `structlog` (`logging_config.py`).
2. Programar limpeza cronológica (Job diário) do `DataRetentionService`.
3. Adicionar política de Log Rotation aos volumes configurados nos containers ou injetados na runtime do sistema operacional.
- **Registros Indevidos de E-mails (Logging Tools) (Feito):** A ferramenta de envio de email `send_email` em `backend/app/core/tools/productivity_tools.py` não registra mais os metadados de correspondência de destinatário (`to`) e assunto (`subject`) no logger em modo informativo.
- **Armazenamento Temporal de Memória Global (Feito):** O isolamento de arquivos por `user_id` mitigou o risco associado ao vazamento de dados de notas (`_notes`) e eventos de calendário (`_calendar_events`).

## 4. Recomendações Recentes
1. Continuar monitorando novos logs para introduzir políticas estritas de "Scrubbing/Masking" usando a camada de ofuscação em metadados injetados dinamicamente nos logs gerais da aplicação.
