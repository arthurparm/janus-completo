# Mapeamento do Backlog Janus para BMAD (Epics/Stories)

Fonte: `_bmad-output/planning-artifacts/backlog-janus-prioridades.md`  
Base de stories: `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Mapeamento Direto

| ID | Prioridade | Epic/Stories alvo (BMAD) | Cobertura atual | Ação recomendada |
|---|---|---|---|---|
| JNS-001 | P0 | `6-1-registro-versionado-de-contratos-rest-e-eventos`, `6-2-portal-de-mudancas-e-depreciacao-de-contratos` | Parcial (produto cobre contratos/versionamento; saneamento documental e shard não está explícito como story) | Criar enabler de documentação via `correct-course` (Story nova em Epic 6) |
| JNS-002 | P0 | Cross-cutting em todas as stories + foco em `5-1-trilha-de-auditoria-imutavel-para-acoes-e-decisoes` | Parcial | Criar enabler transversal de rastreabilidade FR/NFR por story |
| JNS-003 | P0 | Fluxos críticos em `3-*`, `4-*`, `5-*` | Parcial | Aplicar hardening de AC em lote nas stories críticas (edit stories + QA criteria) |
| JNS-004 | P0 | `3-2-fluxo-de-consentimento-explicito-para-acoes-sensiveis`, `3-3-aprovacao-humana-obrigatoria-para-alto-risco`, `3-4-orquestracao-de-execucao-multi-etapas-com-estado-rastreavel`, `3-5-cancelamento-controlado-recuperacao-e-fallback-operacional`, `4-5-recuperacao-operacional-em-bloqueios-de-integracao` | Alta | Priorizar execução nessas stories (ordem sugerida: 3-2 -> 3-3 -> 3-4 -> 3-5 -> 4-5) |
| JNS-005 | P0 | `6-1-registro-versionado-de-contratos-rest-e-eventos`, `6-2-portal-de-mudancas-e-depreciacao-de-contratos` + CI | Parcial/Alta | Expandir ACs para gate de CI com contract tests REST/SSE + `problem+json` |
| JNS-006 | P0 | Processo BMAD (não funcional de produto) | Gap de processo | Formalizar DoR/DoD/handoffs em artefato operacional do sprint (enabler de processo) |
| JNS-007 | P1 | `3-1-planejamento-de-execucao-com-classificacao-de-risco-por-acao`, `3-4-orquestracao-de-execucao-multi-etapas-com-estado-rastreavel`, `3-6-resultado-final-verificavel-com-evidencias-e-proximos-passos` | Alta | Tratar como trilha de implementação do kernel de orquestração |
| JNS-008 | P1 | `2-2-memoria-contextual-persistente-e-retomada-de-contexto`, `2-5-registro-auditavel-do-contexto-de-decisao-proativa` | Alta | Priorizar `2-2` antes de features proativas avançadas |
| JNS-009 | P1 | `6-1-registro-versionado-de-contratos-rest-e-eventos`, `5-3-evidencia-explicavel-de-decisoes-automaticas` | Alta | Definir contrato v1 de runtime no escopo dessas stories |
| JNS-010 | P1 | `2-1-composer-conversacional-continuo-no-painel-central`, `5-2-painel-de-auditoria-com-filtros-e-detalhe-de-evidencias` | Alta | Executar UI 3 painéis + timeline como entrega conjunta UX+Dev |
| JNS-011 | P1 | `3-1-planejamento-de-execucao-com-classificacao-de-risco-por-acao`, `3-2-fluxo-de-consentimento-explicito-para-acoes-sensiveis`, `3-3-aprovacao-humana-obrigatoria-para-alto-risco`, `6-1-registro-versionado-de-contratos-rest-e-eventos` | Alta | Inserir quality gates por risco em AC + testes automatizados |
| JNS-012 | P2 | `2-3-sugestoes-proativas-de-proxima-melhor-acao`, `2-5-registro-auditavel-do-contexto-de-decisao-proativa`, `5-3-evidencia-explicavel-de-decisoes-automaticas`, `6-4-gestao-de-incidentes-operacionais-vinculados-as-capacidades` | Média/Alta | Planejar como fase evolutiva pós-core (após P0/P1) |

## Itens que Precisam de Enabler Novo

1. JNS-001: saneamento canônico de artefatos e shards.
2. JNS-002: matriz explícita FR/NFR por story.
3. JNS-003: padronização de AC mensurável em stories críticas.
4. JNS-006: cadência BMAD multi-agente (DoR/DoD + handoffs).

## Próximo Passo BMAD (recomendado)

1. Rodar `bmad-bmm-correct-course` para inserir os 4 enablers acima no backlog formal de stories.
2. Reexecutar `bmad-bmm-sprint-planning` para refletir as novas stories no `sprint-status.yaml`.
3. Continuar execução por prioridade P0 com `bmad-bmm-create-story` e `bmad-bmm-dev-story`.
