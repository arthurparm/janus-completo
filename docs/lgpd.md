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
- **Vazamento em In-Memory:** As `ProductivityTools` mantêm globais (_notes, _calendar_events) na memória volátil que constituem risco não-persistente.
- **Log Indevido de Áudio/Conversa:** O `ChatService` (refatorado) e a interface Daemon (`interfaces/daemon/daemon.py`) ainda podem estar registrando conteúdo e comandos de voz abertos nos logs da aplicação através de `logger.info`, expondo conversas cruas.

## 3. Próximos Passos (Plano de Mitigação)
1. Estender a camada de ofuscação (`app.core.memory.security`) para injetar um redator diretamente nas configurações do `structlog` (`logging_config.py`).
2. Programar limpeza cronológica (Job diário) do `DataRetentionService`.
3. Adicionar política de Log Rotation aos volumes configurados nos containers ou injetados na runtime do sistema operacional.
- **Registros Indevidos de User IDs e E-mails (Logging Tools):** A ferramenta de envio de email `send_email` em `backend/app/core/tools/productivity_tools.py` registra abertamente metadados de correspondência, como remetente (`user_id`), destinatário (`to`) e assunto (`subject`), no logger em modo informativo, consolidando um ponto de vazamento PII não mascarado de forma contínua.
- **Armazenamento Temporal de Memória Global:** A `backend/app/core/tools/productivity_tools.py` continua armazenando notas (`_notes`) e eventos de calendário (`_calendar_events`) em variáveis globais. Na ausência de isolamento, vazamentos cruciais de rotina de diferentes `user_id` podem ser lidos entre sessões se houver exploração de agentes maliciosos no espaço local.

## 4. Recomendações Recentes
1. Introduzir uma política estrita de "Scrubbing/Masking" para metadados de email (Destinatários e Assuntos) passando por uma heurística segura antes de ser jogado nos arquivos `janus.log` ou ser interceptado pelo structlog.
2. Refatorar as listas globais (`_notes` e `_calendar_events`) e mover esse estado transitório para repositórios transacionais atrelados a banco (Postgres/Redis) onde AuthZ e encriptação de disco possam intervir, prevenindo compartilhamentos temporais entre requests.
3. Revisar logs no `ChatService` e no `Daemon` para assegurar que transcrições e sentenças cruas passadas via microfone ou frontend sejam tratadas antes de ir ao log ou que não sejam logadas (utilizando PII redaction rules em vez disso).
