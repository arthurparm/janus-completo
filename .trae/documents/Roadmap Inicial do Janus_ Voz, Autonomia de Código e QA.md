## Objetivos
- Elevar Janus a um assistente/autômato com personalidade, memória e autonomia real de desenvolvimento
- Priorizar operação local estável, geração de código com testes e observabilidade
- Postergar visão computacional para fase futura, mantendo o escopo controlado

## O Que Falta (prioridades)
1. Voz completa: captura de áudio, ASR e TTS (inexistentes hoje)
2. Autonomia de desenvolvimento: gerar mudanças reais no workspace com testes (hoje o Code Agent só retorna string de código, não escreve nem valida; ver `janus/app/core/workers/code_agent_worker.py:50-85`)
3. QA automatizado: geração/execução de testes unitários/integrados, cobertura e mutação (sandbox só executa código isolado; ver `janus/app/core/workers/sandbox_agent_worker.py:20-93`)
4. Correções no grafo/memória: bug no `dedupe_concepts` (uso de `${...}` ao invés de tipo de relacionamento correto) em `janus/app/repositories/knowledge_repository.py:102`; duplicidade de `find_entity_relationships`; registro de relações além de `MENTIONS`
5. Ferramentas de desenvolvimento: linter/formatter, análise estática, gerenciador de dependências, diff/patch seguro
6. Governança/segurança: política de ferramentas com permissões finas, revisões HITL para mudanças sensíveis

## Viabilidade no Hardware
- i9 13900F + 64GB + RTX 4060 Ti 16GB é suficiente para rodar toda a stack (FastAPI, RabbitMQ, Neo4j, Qdrant, MySQL, Angular) localmente
- LLMs: iniciar com provedores remotos (OpenAI/Gemini) já suportados; opcionalmente rodar modelos 7B–13B quantizados na GPU (você terá latências aceitáveis para protótipos)
- ASR/TTS local é possível depois (Whisper pequeno/medium quantizado, Piper/Coqui para TTS), mas comece com APIs remotas para foco no core

## Fase 0 — Correções Rápidas (Estabilidade)
- Corrigir `dedupe_concepts` para usar `GraphRelationship.RELATES_TO` nos dois sentidos e remover duplicidades de função
- Registrar tipos de relacionamento usados (`CALLS`, `IMPLEMENTS`, `RELATES_TO`) em `ensure_basic_constraints`
- Adicionar métricas/auditoria aos métodos de dedupe e consolidar contagens

## Fase 1 — Operação Local (Stack)
- Subir serviços: `rabbitmq`, `neo4j`, `qdrant`, `mysql`, API Janus e frontend Angular
- Configurar variáveis (`OPENAI_*`, `NEO4J_*`, `QDRANT_*`, `MYSQL_*`) e health checks
- Usar `/api/v1/workers/start-all` para iniciar orquestração (ver `janus/app/core/workers/orchestrator.py:38-81`)

## Fase 2 — Autonomia de Desenvolvimento (Código + Testes)
- Adicionar `FilePatchTool` ao módulo de ferramentas (`janus/app/core/tools/agent_tools.py:1-29`) para aplicar diffs seguros no workspace
- Estender Code Agent: gerar patch + incluir testes; encaminhar ao Professor para revisão curta; se OK, Sandbox executa, depois Router consolida conhecimento (`janus/app/core/workers/router_worker.py:67-112`)
- Incluir `TestRunnerTool` (pytest) e `StaticAnalysisTool` (ruff/mypy) com políticas de permissão
- Fazer o Router publicar consolidação paralela quando uma tarefa é concluída com conteúdo útil (já há base, `router_worker.py:70-110`)

## Fase 3 — Voz (Interação)
- Frontend Angular: captura com `getUserMedia`/`MediaRecorder`, streaming por WebSocket/SSE
- Backend: endpoints `POST /audio/asr` e `POST /audio/tts` com provedores remotos inicialmente
- Ferramentas: `MicCaptureTool`, `ASRTool`, `TTSTool` integradas ao `agent_tools`

## Fase 4 — Avaliação e Reflexão
- Harness de testes/e2e, métricas de qualidade e regressão; integração com `Meta-Agent` para recomendações acionáveis (`janus/app/core/agents/meta_agent.py:480-508, 577-606`)
- Loops de melhora: detectar falhas, abrir tarefas para agentes Tester/Optimizer (`janus/app/core/agents/multi_agent_system.py:171-206, 732-740`)

## Fase 5 — Visão (Futuro)
- OCR/leitura de tela com Google Cloud Vision (planejado em docs), integração com `gui_automator`
- Ferramentas: `ScreenCaptureTool`, `OCRTool`, `VisionAnalyzeTool` com quotas e consentimentos

## Ferramentas Prioritárias a Implementar
- Voz: `MicCaptureTool`, `ASRTool`, `TTSTool`
- Dev & QA: `FilePatchTool`, `TestRunnerTool`, `StaticAnalysisTool`, `PackageManagerTool`
- Memória/RAG: `GraphAuditTool` (dedupe/consistência), `KnowledgeIngestTool` (docs), `MemoryExportTool`
- Autonomia: `GoalPlannerTool`, `ChangeProposalTool` (gera plano+patch), `SafeOpsTool` (dry-run/rollback), `ExperimentRunnerTool`
- Conectores: ampliar para Notion/Jira/Drive conforme necessidade

## Entregáveis
- Correções no repositório de conhecimento e registro de relações
- Conjunto de ferramentas novas sob `core/tools` com políticas
- Pipeline de agentes com escrita de arquivos, teste e consolidação
- Endpoints e UI básicos para voz
- Métricas e relatórios do Meta-Agent orientados a ação