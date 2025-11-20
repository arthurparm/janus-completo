## Visão Geral
- Entregar um site com UX completa para Janus Chat, com streaming, gestão de conversas, anexos/RAG, painel de ferramentas, mídia WebRTC, acessibilidade/i18n, segurança, observabilidade e escalabilidade.
- Detalhamento abaixo por fase: objetivos, entregáveis, tarefas técnicas, testes/aceite, riscos e mitigação.

## Fase 1 — Fundamentos de UX e Streaming
- Objetivos
  - Implementar streaming SSE no frontend para respostas do LLM e estados de digitação.
  - Padronizar contratos e estados de conversa; melhorar feedback de carregamento/erros.
  - Listagem e gestão básica de conversas (listar, renomear, apagar) no UI.
- Entregáveis
  - Serviço SSE: cliente resiliente com reconexão e backoff.
  - `ChatComponent` integrado ao SSE; fallback para REST.
  - Página “Minhas conversas” com filtros e ações.
  - Métricas de UX (TTFT, P95) coletadas e expostas.
- Tarefas técnicas (Frontend)
  - Criar `chat-stream.service` (SSE):
    - Conectar a `GET /api/v1/chat/stream/{conversation_id}` `janus/app/api/v1/endpoints/chat.py:188-212`.
    - Eventos: `message`, `error`, `open`, `retry` com controle de backoff exponencial.
    - API: `start(conversationId, text, role, priority)` e `stop()`; emitir chunks e estado `typing`.
  - `ChatComponent`:
    - Integrar `chat-stream.service` no fluxo de envio; alternar entre REST/SSE por feature flag.
    - Estados: `typing`, `streaming`, `error`, `reconnect`.
    - Melhorar UX de input: `Enter` para enviar, `Shift+Enter` para nova linha, bloqueios durante streaming.
  - Gestão de conversas:
    - Nova rota `/conversations` com grid/lista; chamar `GET /conversations`, `PUT /rename`, `DELETE /{id}`.
    - Busca por título/última mensagem; paginação e ordenação.
  - Observabilidade de UX:
    - Instrumentar TTFT (tempo até primeiro token), latência total e taxas de erro.
    - Emissão para endpoint de métricas ou logs estruturados.
- Tarefas técnicas (Backend)
  - Validar `ChatService.stream_message` performance e timeouts; limitar tamanho de mensagens.
  - Padronizar SSE com prefixo de evento (`event: token`, `event: done`, `event: error`).
  - Garantir CORS e proxy para `/stream/*`.
- Testes e Aceite
  - Testes de unidade: serviço SSE e estados do componente.
  - Testes de integração: fluxo SSE e fallback REST, renomear/apagar/listar.
  - Critérios: TTFT < 1.5s, latência P95 < 5s; reconexão funcional; gestão de conversas completa.
- Riscos/Mitigação
  - Browsers sem SSE: fallback REST; pollyfills se necessário.
  - Timeouts longos: keep-alive e heartbeats; cancelamento pelo cliente.
  - Contratos divergentes: validação de DTOs e mapeadores no frontend.

## Fase 2 — Conteúdo, Contexto e RAG
- Objetivos
  - Suporte a anexos (arquivos/imagens/URLs) para enriquecer contexto.
  - Exibir citações (citations) e prévias das fontes usadas no RAG.
  - Melhorar busca/filtragem de conversas e contexto persistente (personas/roles/priority).
- Entregáveis
  - Upload de anexos com validações; página de gerenciamento de anexos.
  - Painel de citações na resposta (fonte, trecho, confiança, link).
  - Filtros e busca avançada nas conversas.
  - Controles de persona/role/priority no UI; persistência por conversa/sessão.
- Tarefas técnicas (Frontend)
  - UI de upload:
    - Componente de arrastar/soltar, limite de tamanho/tipos, barra de progresso.
    - Associações de anexos ao `conversation_id` e preview.
  - Renderização de rich messages:
    - Markdown com code highlight; blocos colapsáveis; copiar código.
    - Seção de citations: cards com fonte, labels, confiança, link.
  - Busca/filtragem:
    - Campos de busca por texto, período; filtros por persona/projeto; paginação.
  - Controles de sessão:
    - Dropdown de persona; toggles de role/priority; persistência local e nos headers (`X-Project-Id`, etc.).
- Tarefas técnicas (Backend)
  - Endpoints de anexos: upload, listagem, deleção, vinculação; sanitização e DLP.
  - Indexação: extrair texto, embutir vetores; armazenar metadados (fonte/tipo/usuário/confiança).
  - RAG com citations: retornar fontes e trechos; padronizar formato (id, título, url, snippet, score).
  - Busca: endpoint para pesquisar em conversas/anexos com filtros e paginação.
- Testes e Aceite
  - Testes de carga de upload e indexação; limites e validações.
  - Verificação de segurança (tipos de arquivos, malware scanning opcional).
  - Critérios: citações corretas e clicáveis; anexos indexados e buscáveis; controls de persona persistem.
- Riscos/Mitigação
  - Arquivos grandes: chunked upload, limites e compressão.
  - Qualidade de RAG: thresholds e feedback do usuário; re-ranking.
  - Privacidade: remoção/redação de PII e consentimentos por escopo.

## Fase 3 — Mídia (WebRTC), Acessibilidade e i18n
- Objetivos
  - Evoluir mídia: lobby com seleção de dispositivos, indicadores e fallback.
  - Acessibilidade (ARIA, navegação por teclado, contraste) e internacionalização (pt-BR/EN).
- Entregáveis
  - Lobby de mídia com teste de áudio/vídeo e rede.
  - Controles de dispositivos e estados; logs de erros de WebRTC amigáveis.
  - i18n com traduções; tema claro/escuro e alto contraste.
- Tarefas técnicas (Frontend)
  - Lobby e controles:
    - Componente de seleção de dispositivo; teste de eco; persistência de preferências.
    - Indicadores: conectividade, bitrate e pacotes perdidos; fallback para só áudio.
  - A11y/i18n:
    - Labels/roles ARIA; ordem tabulável; atalhos; foco visível.
    - Mecanismo de tradução e carregamento dinâmico.
- Tarefas técnicas (Backend)
  - Otimizar STUN/TURN; logs e métricas de sessão.
  - Endpoints de diagnóstico de mídia (opcional): estatísticas de sessão.
- Testes e Aceite
  - Testes de cross-browser (Chrome/Firefox/Edge/Safari) e dispositivos.
  - Critérios: chamada estável; i18n completo; contraste e navegação acessível.
- Riscos/Mitigação
  - NAT/Firewall: TURN gerenciado; fallback.
  - Acessibilidade: auditorias com ferramentas e correções iterativas.

## Fase 4 — Performance, Escala e Segurança
- Objetivos
  - Tunar API/LLM e filas; adicionar caching, rate limiting e resiliência.
  - SSO/OAuth2, RBAC, auditoria, DLP e políticas de retenção.
- Entregáveis
  - Cache de prompts/respostas e de resultados RAG.
  - Rate limit global/por usuário; quotas de produtividade.
  - Autenticação SSO; papéis/roles; trilha de auditoria e exportação.
  - Políticas de retenção e redação de PII; consentimentos configuráveis.
- Tarefas técnicas (Backend)
  - Cache: definir chaves (prompt+persona+tools), TTLs e invalidação.
  - Rate limiting: middleware com limites por IP/usuário/chaves.
  - Auth: OAuth2/OIDC; tokens; RBAC nos endpoints de chat e anexos.
  - Auditoria: eventos com trace_id, latência e status; export CSV.
  - Data policies: retenção por escopo e redaction; DLP nos uploads.
- Tarefas técnicas (Frontend)
  - Interceptadores de auth; exibição de limites/quota; mensagens de bloqueio.
  - UI de consentimentos e políticas; exportação e visualização de auditoria.
- Infra/Observabilidade
  - Horizontal scale (Uvicorn workers); autoscaling de workers.
  - Dashboards (TTFT, P95, erros, throughput, falhas de fila, WebRTC health).
- Testes e Aceite
  - Carga/stress, chaos e segurança (SAST/DAST); testes de RBAC.
  - Critérios: P95 estável sob carga; sem achados críticos; quotas e rate limit eficazes.
- Riscos/Mitigação
  - Hotspots de cache: monitoramento e fallbacks.
  - Complexidade de auth: uso de lib/IDP consolidado e testes integrados.

## Fase 5 — Go-live, Hardening e Documentação
- Objetivos
  - Preparar lançamento, endurecimento de segurança, DR e documentação completa.
- Entregáveis
  - Playbooks de deploy/rollback; backups e DR.
  - Políticas de privacidade e termos; guia do usuário e manual técnico.
  - Plano de monitoramento/alertas e resposta a incidentes.
- Tarefas técnicas
  - Revisões finais de segurança/compliance e testes de recuperação.
  - Documentação: arquitetura, APIs, fluxos (REST/SSE/WebRTC), procedimentos de operação.
  - Observabilidade: alertas de TTFT/erros; SLOs definidos.
- Testes e Aceite
  - Checklist de lançamento; simulações de incidentes.
  - Critérios: documentação completa; SLOs/SLAs definidos; planos de DR validados.
- Riscos/Mitigação
  - Mudanças de última hora: congelamento de código; janela de release e plano de rollback.

## Equipe e Esforço (indicativo)
- FTEs: 1 FE + 1 BE + 0.2 DevOps + 0.2 QA; apoio eventual de segurança/UX.
- Duração: ~10–12 semanas no total (por fases); ajustes conforme escopo e prioridade.

## Métricas Globais de Sucesso
- TTFT < 1.5s (SSE), P95 latência < 5s; taxa de erro < 1%.
- CSAT ≥ 4.3/5; deflexão ≥ 25%; retenção semanal ≥ 35%.
- Zero achados críticos de segurança; conformidade de PII/consentimentos.

Se concordar, iniciaremos pela Fase 1 com o setup de streaming SSE, gestão de conversas e métricas de UX, seguindo esta decomposição detalhada.