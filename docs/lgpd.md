# Relatório de Conformidade LGPD

## Data da Revisão
2025-02-27

## Checklist LGPD e Riscos de Privacidade

### 1. Coleta e Retenção de Dados Sensíveis (PII)
- [x] **Riscos de Exposição PII em Logs**:
  - `ChatEventPublisher` registra prévias de conteúdo, arriscando PII não tratada.
  - `ChatService` registra logs (`logger.info`) que capturam mensagens do usuário e respostas com PII.
  - O daemon (interface por voz, `backend/app/interfaces/daemon/daemon.py`) exibe e loga comandos de voz dos usuários (`logger.info(message=f"Command received: {command}")`).
  - O serviço `CollaborationService` e `productivity_tools` coletam informações não mascaradas. Ferramentas como email logam `to` e `subject`.
  - O manipulador de respostas de chat loga o feedback de usuários (PII risk no args).
  - *Recomendação*: Aplicar filtros de regex (como em `backend/app/core/memory/security.py`) nos manipuladores de logs centralizados, assegurando sanitização global (`[REDACTED]`) antes da saída do stream.

### 2. Ciclo de Vida do Dado e Armazenamento (Retention Policy)
- [x] **Política de Retenção Falha**:
  - A lógica em `DataRetentionService` (e `backend/app/db/sync_events.py`) repousa em criações "fragile" de tasks (`loop.create_task`) em chamadas de evento síncronas de SQLAlchemy, e carece de cron ou filas automatizadas e robustas.
  - *Recomendação*: Substituir o trigger imediato por um esquema de `background tasks` via Celery/RabbitMQ, a fim de garantir robustez, filas (retries) e políticas de exclusão periódica consistentes de usuários (ex: `soft delete` que escalona para `hard delete` depois de 30 dias).

### 3. Armazenamento e Log Analytics
- [x] **Rotação Ausente**:
  - `janus.log` originado por `main.py` acumula sem política de rotação de logs (`logrotate`) e sem processo agendado de purga (`purge`), podendo armazenar PII indefinidamente, violando a LGPD.
  - *Recomendação*: Configurar logrotate, implementar retenção de no máximo X dias em disco, e certificar de enviar logs anonimizados/mascarados para o backend de observabilidade.
- [x] **In-Memory Leaks**: `productivity_tools.py` guarda e mantém dicts em memória `_notes` e `_calendar_events`. Isto não apenas introduz falhas de consistência (sem resiliência) como é uma retenção de dados temporária potencialmente não controlada e vulnerável a OOM/Dumps de estado.
  - *Recomendação*: Migrar `_notes` e `_calendar_events` para o banco de dados/Postgres ou Vector DB adequado ao usuário (user space).

## Próximos Passos e Ações
Verifique `melhorias-possiveis.md` na seção "4) Ferramentas, Segurança e Governança" para os tickets rastreados a partir deste relatório.
