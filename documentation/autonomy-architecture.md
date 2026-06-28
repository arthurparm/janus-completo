# Arquitetura da Área de Autonomia — Janus

## Visão Geral
A área de autonomia do Janus implementa um ciclo contínuo de auto-aperfeiçoamento baseado no modelo Perceber → Planejar → Executar → Refletir → Otimizar. O sistema analisa seu próprio código-fonte, identifica oportunidades de melhoria, gera novas ferramentas, valida-as em ambiente isolado (JanusLab) e as promove para produção com deploy canário.

## Componentes

### Core Loop
- **AutonomyService** (`backend/app/services/autonomy_service.py`, 670+ linhas): Orquestrador principal do ciclo de autonomia. Gerencia metas, planos, execução de ações e métricas.
- **GoalManager** (`backend/app/core/autonomy/goal_manager.py`): Ciclo de vida de metas com hierarquia parent/child (profundidade máx 3).
- **Planner** (`backend/app/core/autonomy/planner.py`): Geração de planos de execução via LLM a partir de metas.
- **PolicyEngine** (`backend/app/core/autonomy/policy_engine.py`): Motor de políticas com veto permanente e validação de segurança.

### Self-Study
- **AutonomyAdminService** (`backend/app/services/autonomy_admin_service.py`, 1854 linhas): Análise offline de código-fonte via AST (Python) e regex (JS/TS). Modos incremental (git diff) e full.
- **ReflectorAgent** (`backend/app/core/evolution/reflector_agent.py`, 324 linhas): Auto-consciência — analisa experiências passadas, detecta padrões de falha, calcula health_score (0-1).
- **LogAwareReflector** (`backend/app/core/memory/log_aware_reflector.py`, 453 linhas): Extensão que lê logs reais da aplicação além da memória Qdrant.

### Evolution
- **EvolutionManager** (`backend/app/core/evolution/evolution_manager.py`, 329 linhas): Pipeline de criação de ferramentas: spec → code generation → validation → registration.
- **EvolutionSandbox** (`backend/app/core/evolution/evolution_sandbox.py`): Sandbox Docker verificável com validação AST, bloqueio de imports perigosos e assinatura SHA-256.
- **SafeEvolutionManager** (`backend/app/core/evolution/safe_evolution_manager.py`, 359 linhas): Evolução segura com validação em Lab isolado + deploy canário.
- **JanusLab** (`backend/app/core/evolution/janus_lab.py`, 366 linhas): Contêiner Docker isolado para teste de ferramentas antes da produção.

### Segurança
- **SafetyPlanValidator** (`backend/app/core/autonomy/safety_plan_validator.py`): Valida planos gerados por LLM contra política de segurança.
- **PromptSanitizer** (`backend/app/core/autonomy/prompt_sanitizer.py`): Sanitização de input antes da decomposição por LLM.
- **GoalConflictDetector** (`backend/app/core/autonomy/goal_conflict_detector.py`): Detecção de conflitos entre metas concorrentes.
- **ActionRegistry** (`backend/app/core/tools/action_module.py`): Registro de ferramentas com namespace isolation (core/evolution/user), assinatura SHA-256 e provenance tracking.

### Resiliência
- **DomainCircuitBreaker** (`backend/app/core/autonomy/domain_circuit_breaker.py`): Circuit breakers independentes por domínio (code, knowledge, tools, deployment). Threshold: 3 falhas, recovery: 300s.
- **Rollback automático**: Ferramentas evolution com falha são revertidas automaticamente para versão anterior.
- **Quarentena de entidades**: Entidades extraídas por LLM sem corroboração de código fonte recebem label `Quarantine`.

### Observabilidade
- **Auditoria imutável**: Toda decisão do AutonomyService gera evento no audit ledger.
- **GoalMetrics** (`backend/app/core/autonomy/goal_metrics.py`): Métricas de eficácia por meta (success_rate, time_efficiency, tool_accuracy, recovery_rate).
- **SLO de autonomia**: success_rate > 80%, p95 latency < 5s, rollback recovery < 30s.
- **Dashboard**: Painel admin com 5 seções: metas ativas, ferramentas evolutivas, timeline, saúde de domínios, métricas.

### Escala
- **AutonomyLockService** (`backend/app/services/autonomy_lock_service.py`): Lock distribuído via Redis SET NX PX com fallback para memória.
- **KnowledgeFederation** (`backend/app/core/autonomy/knowledge_federation.py`): Federação de conhecimento entre instâncias via Redis pub/sub.

## Ciclo de Vida

1. **Perceber**: ReflectorAgent analisa experiências passadas e logs. Se health_score < 0.8, inicia evolução.
2. **Planejar**: Planner gera plano de passos via LLM. SafetyPlanValidator valida o plano. GoalConflictDetector verifica conflitos.
3. **Executar**: AutonomyService executa passos sequencialmente. PolicyEngine aplica veto permanente. DomainCircuitBreaker pausa domínios com falha.
4. **Refletir**: Resultados são registrados no audit ledger. Métricas são computadas.
5. **Otimizar**: EvolutionManager gera novas ferramentas. EvolutionSandbox valida e assina. SafeEvolutionManager testa no Lab e promove com canário.

## SLOs

| Métrica | Threshold | Janela |
|---------|-----------|--------|
| Goal success rate | > 80% | 24h |
| Cycle P95 latency | < 5000ms | 1h |
| Rollback recovery | < 30s | pontual |
| Circuit breaker recovery | < 300s | pontual |
| Autonomy error rate | < 10% | 24h |

## Endpoints Principais

| Método | Path | Descrição |
|--------|------|-----------|
| POST | `/autonomy/start` | Inicia loop de autonomia |
| POST | `/autonomy/stop` | Para loop de autonomia |
| GET | `/autonomy/status` | Status do loop |
| GET | `/autonomy/health` | Saúde agregada de todos os subsistemas |
| GET | `/autonomy/goals` | Lista metas |
| GET | `/autonomy/goals/{id}` | Detalhes da meta |
| GET | `/autonomy/goals/{id}/metrics` | Métricas de eficácia da meta |
| POST | `/autonomy/admin/self-study/run` | Executa self-study |
| GET | `/autonomy/admin/self-study/status` | Status do self-study |
| POST | `/autonomy/admin/tools/{name}/rollback` | Rollback de ferramenta evolutiva |
| GET | `/autonomy/admin/tools/{name}/provenance` | Provenance de ferramenta |
| POST | `/autonomy/admin/knowledge/quarantine/review` | Revisão de entidade em quarentena |
| POST | `/autonomy/admin/throttle/reset` | Reset de throttle |

## Troubleshooting
Consulte os runbooks em `documentation/runbooks/`:
- `autonomy-loop-stuck.md` — Loop de autonomia travado
- `evolution-tool-failure.md` — Ferramenta evolutiva com falha
- `quarantined-entity-review.md` — Entidades em quarentena
