## Objetivo
Concluir a instrumentação e operação da observabilidade em todo o pipeline (RAG, produtividade, documentos), com deploy simples da stack (Tempo/Loki/Grafana/Collector/Promtail), dashboards adicionais e controles de governança (RBAC/consentimentos).

## Escopo
- Pipeline RAG por etapa: spans e métricas detalhadas
- Dashboards Grafana complementares (RAG Pipeline, SLO/Alertas)
- Deploy operacional: compose e parâmetros
- Governança: RBAC/consentimentos e retenção

## Implementações
### 1) RAG por Etapa
- Instrumentar upload → parse → chunk → embeddings → busca (vetor/híbrida) com spans `rag.upload`, `rag.parse`, `rag.chunk`, `rag.embed`, `rag.search_vec`, `rag.search_hybrid`.
- Métricas: `rag_stage_latency_seconds{stage}`, `rag_stage_requests_total{stage,status}`.
- Propagar `user_id/session_id/project_id` em spans e logs.

### 2) Dashboards Grafana
- “RAG Pipeline Latency”: heatmaps por estágio, contadores por status.
- “SLO/Alertas”: latência p95/p99 por endpoint crítico (docs upload/search/status, rag, produtividade), erro por minuto, disponibilidade.
- “Audit by User”: eventos por ação/status/top endpoints com filtros por usuário.

### 3) Deploy Observabilidade
- Completar docker-compose com instruções de uso (Tempo/Loki/Grafana/Collector/Promtail) e volumes persistentes.
- Documentar variáveis: `OTEL_ENABLED`, `OTEL_OTLP_ENDPOINT`, `OTEL_SERVICE_NAME`, `LOG_SAMPLING_RATE`, `AUDIT_PURGE_INTERVAL_SECONDS`, `AUDIT_RETENTION_DAYS`.
- Passos de verificação: abrir Grafana, validar datasources, rodar requisições e observar métricas/traces/logs.

### 4) Governança e Retenção
- RBAC no endpoint de auditoria por escopos/roles (admin vs usuário).
- Job de retenção já criado: documentar parâmetros e adicionar alertas se purge falha.
- Consentimentos de produtividade: registrar escopo e evento de consentimento; painel simples de consentimentos por usuário.

### 5) Front-End
- Expor setters de contexto (project/session/conversation) já criados para páginas relevantes (chat/documentos/produtividade) e validar propagação.
- Adicionar opcionalmente traço de request no UI (exibir `X-Request-ID`).

## Validação
- Geração de tráfego sintético: upload de documento, buscas RAG, produtividade (calendar/mail), verificar:
  - Logs com `trace_id/user_id/session_id/project_id`
  - Traces no Tempo com atributos `janus.*`
  - Métricas Prometheus atualizadas (latência, contadores por status)
  - Dashboards Grafana populados

## Entregáveis
- Código de instrumentação RAG por etapa
- Dashboards Grafana (RAG Pipeline, SLO/Alertas, Audit by User)
- Compose e configs (Tempo/Loki/Grafana/Collector/Promtail)
- Documentação de variáveis e checklist de verificação

## Riscos
- Cardinalidade alta em métricas por usuário: usar agregados globais e limitar labels; aplicar amostragem quando necessário.
- Custos de storage (Loki/Tempo): ajustar retenção e compressão.

## Próximo Passo
Após aprovação, implemento RAG por etapa, crio dashboards adicionais e finalizo a documentação/compose de observabilidade, com verificação fim-a-fim.