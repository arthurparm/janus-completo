# Weekly LGPD & Privacy Review

## Data de Revisão
*Automated Review*

## Checklist
- [x] PII em logs de aplicação
- [x] PII não ofuscada em base de dados/memória
- [x] Retenção excessiva e falta de expurgo (purge)
- [x] Vazamento de dados em endpoints

## Gaps Encontrados

1. **Retenção de Dados Sensíveis em Logs de Serviços Críticos**
   - O `ChatEventPublisher` em `backend/app/services/chat_event_publisher.py` (função `_publish_to_log`) está gerando previews de mensagens ("content_preview"), que expõem conversas e contexto de usuários de forma persistente.
   - O `CollaborationService` e o `ChatService` também mantêm níveis de registro que incluem trocas entre agentes não filtradas.
   - O daemon loga entradas de comandos de voz, elevando os riscos de LGPD/PII (transcrições de voz).

2. **Exposição de Informações nas Ferramentas (backend/app/core/tools/productivity_tools.py)**
   - O método `send_email` registra `[EMAIL]` com campos explícitos de "to" e "subject".
   - Variáveis globais em memória como `_notes` e `_calendar_events` retêm dados de usuários sem suporte a persistência segura ou mecanismo de expiração.

3. **Ciclo de Vida da Memória Inadequado**
   - Retenção indevida ou infinita de logs da aplicação (`janus.log`). Atualmente não há políticas de rotação de log ou purga automatizada dos arquivos e tabelas de auditoria associadas.
   - O `DataRetentionService` (apesar de correções em execuções assíncronas) carece de um agendamento robusto e periódico em background para varrer dados obsoletos.

4. **Retorno do Token de Reset Opcional (backend/app/api/v1/endpoints/auth.py)**
   - O objeto `LocalResetResponse` permite que o token seja retornado com base em `AUTH_RESET_RETURN_TOKEN`. O retorno de tokens na resposta de reset de senha caracteriza um risco se ativado acidentalmente.

## Recomendações Acionáveis
1. Ajustar serviços como `ChatEventPublisher` para não logar `content_preview` ou qualquer propriedade de contexto livre, logando apenas as metainformações (ID da conversa, data, tipo do evento).
2. Substituir armazenamentos globais na memória de ferramentas (`_notes`, `_calendar_events`) por integrações de banco de dados locais compatíveis com LGPD (ofuscados ou anonimizados).
3. Configurar e automatizar a expurgação (`purge`) e a rotação de todos os logs para não ultrapassarem retenção mínima necessária à estabilidade/auditoria (por ex., 7-30 dias).
4. Forçar o default `AUTH_RESET_RETURN_TOKEN=False` a ser inflexível via código para prevenir leaks de tokens de redefinição de senha em responses HTTP.
5. Empregar ferramentas sistemáticas para sanitização (Regex com patterns de e-mails, telefone, CPF definidos em `memory/security.py`) durante as interceptações de log, atenuando imediatamente riscos nos prints da infraestrutura.
