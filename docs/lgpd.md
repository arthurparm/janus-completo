# Relatório de Conformidade LGPD - Janus

Data de criação: 2026-03-07
Objetivo: Mapear fluxos de dados sensíveis e riscos de privacidade dentro do sistema.

## Checklist de Privacidade Semanal
- [ ] Revisar logs de backend para vazamento inadvertido de PII (e-mails, telefones, CPFs, nomes).
- [ ] Checar ferramentas de observabilidade e métricas quanto a dados confidenciais incluídos nas tags.
- [ ] Revisar uso e armazenamento temporal de variáveis globais contendo estado do usuário ou sessão.
- [ ] Auditar rotinas de retenção e expurgo de dados sensíveis.
- [ ] Garantir ofuscação de áudio e transcrições armazenadas ou enviadas a provedores externos.

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

## 3. Próximos Passos (Plano de Mitigação)
1. Estender a camada de ofuscação (`app.core.memory.security`) para injetar um redator diretamente nas configurações do `structlog` (`logging_config.py`).
2. Programar limpeza cronológica (Job diário) do `DataRetentionService`.
3. Adicionar política de Log Rotation aos volumes configurados nos containers ou injetados na runtime do sistema operacional.
- **Registros Indevidos de User IDs e E-mails (Logging Tools):** A ferramenta de envio de email `send_email` em `backend/app/core/tools/productivity_tools.py` registra abertamente metadados de correspondência, como remetente (`user_id`), destinatário (`to`) e assunto (`subject`), no logger em modo informativo, consolidando um ponto de vazamento PII não mascarado de forma contínua.
- **Armazenamento Temporal de Memória Global:** A `backend/app/core/tools/productivity_tools.py` continua armazenando notas (`_notes`) e eventos de calendário (`_calendar_events`) em variáveis globais. Na ausência de isolamento, vazamentos cruciais de rotina de diferentes `user_id` podem ser lidos entre sessões se houver exploração de agentes maliciosos no espaço local.
- **Vazamento de PII em Serviço de Chat:** O `ChatService` (`backend/app/services/chat_service.py`) usa `logger.info` para gravar conteúdo que pode incluir PII ou mensagens sensíveis não sanitizadas.
- **Risco Biométrico e de Áudio no Janus Daemon:** A interface `backend/app/interfaces/daemon/daemon.py` grava abertamente comandos de voz e transcrições de áudio nos logs de entrada.

## 4. Recomendações Recentes
1. Introduzir uma política estrita de "Scrubbing/Masking" para metadados de email (Destinatários e Assuntos) passando por uma heurística segura antes de ser jogado nos arquivos `janus.log` ou ser interceptado pelo structlog.
2. Refatorar as listas globais (`_notes` e `_calendar_events`) e mover esse estado transitório para repositórios transacionais atrelados a banco (Postgres/Redis) onde AuthZ e encriptação de disco possam intervir, prevenindo compartilhamentos temporais entre requests.
3. Sanitizar as entradas loggadas em `backend/app/services/chat_service.py` via módulo `memory.security` para ocultar PII.
4. Anonimizar os logs de comandos de voz na interface Janus Daemon (`backend/app/interfaces/daemon/daemon.py`).
