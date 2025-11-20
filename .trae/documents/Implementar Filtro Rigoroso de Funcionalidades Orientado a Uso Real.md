## Objetivo
- Aplicar um filtro estrito baseado em uso real e tarefas frequentes para priorizar apenas o que é útil e prático na rotina.
- Incluir auditoria das funcionalidades já implementadas e desativar/remover as que forem inúteis, redundantes ou de baixo impacto.

## Critérios e Garantias
- Incluir somente se: resolve necessidade comprovada, utilidade prática clara, acesso simples, sem sobrecarga.
- Excluir/ocultar se: baixa adoção, redundante, não resolve problema concreto, gera ruído ou atrito.

## Dados e Instrumentação
- Uso real: eventos por página/ação (visitas, tempo, sucesso/erro) em todos os módulos.
- Pesquisa representativa: ranking de utilidade/frequência por perfil.
- Tarefas frequentes: taxonomia de tarefas → mapeamento de rotas e componentes.

## Pontuação e Decisão
- Score (0–1): uso real (0.4) + pesquisa (0.25) + tarefa frequente (0.25) − redundância (0.1).
- Faixas: Core (≥0.7) visível; Contextual (0.5–0.69) acessível via “Explorar/Busca”; Oculta (<0.5) escondida.
- Thresholds parametrizáveis e cache.

## Auditoria de Funcionalidades Existentes
- Levantamento: catálogo de features (nome, rota, módulo, propósito, dependências).
- Medição: coletar métricas por 1–2 semanas (ou histórico disponível).
- Classificação: aplicar score e marcar candidates para:
  - Merge (redundantes)
  - Hide (ocultar por padrão)
  - Deprecate (remover com fallback)

## Execução do Filtro
- Backend: serviço de catálogo e API `GET /api/v1/system/features/allowed` (com classificação e razões).
- Front: montar navegação dinamicamente com Core; mover Contextual para “Explorar/Pesquisa”; ocultar Oculta.
- Flags: chaves de feature por grupo para gating rápido.

## Remoção de Redundâncias
- Matriz de equivalência e merge (ex.: export CSV/JSON unificar; relatórios similares consolidar).
- Descontinuar componentes duplicados mantendo o de maior utilidade.

## UX e Acessibilidade
- Sidebar/Header minimalistas com Core.
- Busca/Command Palette para acesso rápido às Contextuais.
- Feedback in-app leve para ajustes contínuos.

## Entregáveis
- Backend: coleta/consulta de métricas, cálculo de score, catálogo e API de decisão, flags e thresholds.
- Front: serviço de resolução, navegação dinâmica, instrumentação de uso, UI de pesquisa/priorização.
- Documentação de deprecação: lista de itens ocultos/removidos com justificativa e migração.

## Validação
- Metas: reduzir tempo por tarefa, cliques até ação, erros; aumentar taxa de conclusão.
- A/B: full vs filtrado; monitorar TTFT/latência/engajamento.
- Privacidade: opt‑in, anonimização, retenção limitada.

## Rollout
- Fase 1: instrumentação + pesquisa.
- Fase 2: score + catálogo + API.
- Fase 3: gating no front + UI simplificada.
- Fase 4: merge/deprecação e otimização contínua.

Posso prosseguir com a implementação conforme este plano, incluindo a auditoria e deprecação de funcionalidades já existentes?