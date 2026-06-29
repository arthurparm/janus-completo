# Health Critical Audit Log

## Escopo

- Modulo auditado: health/status/automedicacao operacional do Janus.
- Componentes principais: `/health`, `/healthz`, `/api/v1/system/*`, `/api/v1/observability/health/*`, `HealthMonitor` e `AutoHealer`.
- Objetivo tecnico: garantir que sinais de saude usados por deploy, diagnostico e automedicacao sejam disponiveis, consistentes, testaveis e resistentes a regressao.

## Ciclo 1 - `/health` voltou a ser compativel com health checks externos sob `PUBLIC_API_KEY`

### Problema

- Categoria: disponibilidade operacional e contrato de deploy.
- Fato observado: `backend/app/main.py` isentava `/healthz` da API key global, mas nao isentava `/health`.
- Fato observado: documentos de deploy e operacao usam `curl -sf http://localhost:8000/health` como health check de API, liveness/readiness ou gate de rollout.
- Inferencia: quando `PUBLIC_API_KEY` estivesse configurada, load balancers, Docker healthchecks e scripts operacionais que chamam `/health` sem `X-API-Key` poderiam receber `401`.
- Impacto antes: risco de falso negativo de disponibilidade, restart indevido, rollback indevido ou diagnostico incorreto apesar da aplicacao estar viva.

### Hipotese

Acredito que tornar `/health` e `/healthz` isentos por caminho exato preserva compatibilidade operacional de health checks sem abrir rotas sensiveis por prefixo.

### Implementacao

- `backend/app/main.py`: extraida a politica de isencao para `is_public_api_key_exempt_path()`.
- `backend/app/main.py`: `/health` foi adicionado aos caminhos publicos exatos junto com `/healthz`, `/docs`, `/openapi.json`, `/redoc` e `/metrics`.
- `backend/app/main.py`: `/static/` permanece como unica isencao por prefixo.
- `qa/test_health_endpoint_contract.py`: adicionados testes para:
  - `/health` e `/healthz` isentos;
  - `/health/services` e `/healthz/details` nao isentos por prefixo;
  - `/static/app.js` ainda isento por prefixo.

### Metricas

- Baseline antes da correcao:
  - `/healthz` estava isento da API key global.
  - `/health` nao estava isento apesar de ser usado como health check nos guias de deploy/operacao.
- Depois da correcao:
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q qa/test_health_endpoint_contract.py qa/test_system_endpoints_contract.py`: 10 passed.
  - `backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/app/main.py qa/test_health_endpoint_contract.py`: passou.
- Criterio de aceitacao atendido:
  - health check raiz detalhado pode ser chamado sem API key;
  - subrotas potencialmente sensiveis nao foram abertas por prefixo.

### Riscos e limitacoes

- O teste valida a politica de isencao diretamente, nao sobe um app separado com `PUBLIC_API_KEY` dinamico.
- Endpoints de health internos sob `/api/v1/*` continuam protegidos pela politica global quando aplicavel.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para politica de isencao; limitada para ambiente real de proxy por ausencia de teste com container ativo.

## Ciclo 2 - AutoHealer passou a ser idempotente para evitar multiplos loops de automedicacao

### Problema

- Categoria: automedicacao, disponibilidade e seguranca operacional.
- Fato observado: `backend/app/core/monitoring/auto_healer.py::start_auto_healer()` sempre criava uma nova `asyncio.Task` e sobrescrevia `_healer_task`.
- Inferencia: chamadas repetidas poderiam iniciar multiplos loops concorrentes de cura, duplicando reconciliacao de filas, reconexao de broker, limpeza de poison pills, reset de circuit breakers e disparo de meta-agente.
- Impacto antes: risco de tempestade de acoes corretivas, interferencia operacional e diagnostico instavel quando a automedicacao fosse iniciada mais de uma vez.

### Hipotese

Acredito que retornar a task existente enquanto ela ainda estiver ativa torna o AutoHealer idempotente e reduz risco de acoes corretivas duplicadas sem impedir reinicio apos cancelamento/falha.

### Implementacao

- `backend/app/core/monitoring/auto_healer.py`: `start_auto_healer()` agora retorna `_healer_task` quando ela existe e ainda nao terminou.
- `backend/tests/unit/test_auto_healer_idempotency.py`: adicionado teste unitario isolado com `DummyMonitor`, confirmando que duas chamadas consecutivas retornam a mesma task ativa.
- O teste cancela a task no `finally` para nao deixar loop em background.

### Metricas

- Baseline antes da correcao:
  - nao havia teste de idempotencia do AutoHealer;
  - `start_auto_healer()` criava nova task em toda chamada.
- Depois da correcao:
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q qa/test_health_endpoint_contract.py backend/tests/unit/test_auto_healer_idempotency.py qa/test_tasks_observability_contract.py::TestObservabilityContract::test_health_system qa/test_tasks_observability_contract.py::TestObservabilityContract::test_health_check_all qa/test_tasks_observability_contract.py::TestObservabilityContract::test_health_llm_router qa/test_tasks_observability_contract.py::TestObservabilityContract::test_health_multi_agent qa/test_tasks_observability_contract.py::TestObservabilityContract::test_health_poison_pill_handler`: 9 passed.
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q qa/test_health_endpoint_contract.py backend/tests/unit/test_auto_healer_idempotency.py qa/test_system_endpoints_contract.py qa/test_workers_status_contract.py qa/test_dx007_quick_diagnostics_cli.py`: 17 passed.
  - `backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/app/main.py backend/app/core/monitoring/auto_healer.py qa/test_health_endpoint_contract.py backend/tests/unit/test_auto_healer_idempotency.py`: passou.
  - `backend\.venv\Scripts\python.exe -m py_compile backend/app/main.py backend/app/core/monitoring/auto_healer.py qa/test_health_endpoint_contract.py backend/tests/unit/test_auto_healer_idempotency.py`: passou.
- Criterio de aceitacao atendido:
  - chamada repetida nao cria segundo loop enquanto a task atual esta ativa;
  - a automedicacao continua reiniciavel se a task anterior terminar.

### Riscos e limitacoes

- O teste usa monitor e curas dublados; nao executa reconexao real de RabbitMQ, reset real de circuit breaker ou publicacao real para meta-agente.
- Ainda falta evidenciar comportamento em ambiente PC1/PC2 com AutoHealer ativo durante falhas reais.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para idempotencia local do loop; limitada para eficacia da automedicacao real por ausencia de infraestrutura ativa nesta iteracao.

## Ciclo 3 - Componentes criticos degradados nao podem mascarar saude global como healthy

### Problema

- Categoria: automedicacao, disponibilidade e classificacao operacional de falhas.
- Fato observado: `HealthMonitor.get_system_health()` so forcava status global `unhealthy` quando algum componente critico estava `unhealthy`.
- Fato observado: se um componente critico estivesse `degraded` e os demais componentes estivessem `healthy`, o score podia ficar acima de 80 e o status global podia ser `healthy`.
- Fato observado: existem checks criticos que podem retornar `degraded` em cenarios parciais, como resultado inesperado de Neo4j ou degradacao de componentes de memoria/infraestrutura.
- Fato observado: excecoes totais de Neo4j/PostgreSQL ja estao classificadas como `unhealthy` no contrato atual e foram cobertas por teste de regressao nesta iteracao.
- Inferencia: o sistema de saude poderia subestimar degradacoes em dependencias criticas e atrasar diagnostico, rollout rollback ou automedicacao baseada em severidade global.
- Impacto antes: exemplo reproduzido por teste com 1 componente critico `degraded` e 2 componentes saudaveis resultava em score 83; sem a correcao, esse cenario seria elegivel a status global `healthy`.

### Hipotese

Acredito que promover componente critico `degraded` para status global minimo `degraded` torna o sinal de saude mais fiel ao risco operacional sem aumentar a complexidade do monitor.

### Implementacao

- `backend/app/core/monitoring/health_monitor.py`: adicionado calculo de `critical_degraded`.
- `backend/app/core/monitoring/health_monitor.py`: status global agora respeita a ordem:
  - qualquer critico `unhealthy` => sistema `unhealthy`;
  - qualquer critico `degraded` => sistema `degraded`;
  - caso contrario, aplica score agregado.
- `backend/tests/unit/test_health_monitor_critical_classification.py`: adicionados testes de regressao para:
  - critico degradado nao permitir status global `healthy`;
  - preservar contrato de falha de conexao Neo4j como `unhealthy`;
  - preservar contrato de falha de conexao PostgreSQL como `unhealthy`.

### Metricas

- Baseline antes da correcao:
  - 1 critico `degraded` + 2 componentes `healthy` gerava score 83 e podia ser classificado como `healthy`;
  - excecao total em Neo4j/PostgreSQL ja era reportada como `unhealthy`, mas nao havia teste focado nesta matriz de classificacao.
- Depois da correcao:
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_health_monitor_critical_classification.py`: 3 passed.
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_health_monitor_critical_classification.py qa/test_health_endpoint_contract.py backend/tests/unit/test_auto_healer_idempotency.py qa/test_system_endpoints_contract.py qa/test_workers_status_contract.py qa/test_dx007_quick_diagnostics_cli.py`: 20 passed.
  - `backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/app/core/monitoring/health_monitor.py backend/app/core/kernel_health.py backend/tests/unit/test_health_monitor_critical_classification.py`: passou.
  - `backend\.venv\Scripts\python.exe -m py_compile backend/app/core/monitoring/health_monitor.py backend/app/core/kernel_health.py backend/tests/unit/test_health_monitor_critical_classification.py`: passou.
- Criterio de aceitacao atendido:
  - componente critico degradado reduz status global para pelo menos `degraded`;
  - contrato de falha total de conexao em Neo4j/PostgreSQL permanece classificado como `unhealthy`;
  - contratos existentes de health/status continuam passando.

### Riscos e limitacoes

- A mudanca torna o status global mais conservador. Isso pode aumentar alertas em ambientes onde Neo4j/PostgreSQL falham de forma intermitente.
- Os testes simulam falha de conexao; nao executam queda real de PC2, Docker, rede ou credenciais.
- Redis permanece `degraded` em falha, pois esta registrado como nao critico no monitor atual.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para classificacao agregada e contratos unitarios; limitada para comportamento operacional real ate executar fault injection com infraestrutura PC2 ativa.

## Ciclo 4 - Falha de telemetria de memoria nao deve aparecer como servico saudavel

### Problema

- Categoria: usabilidade operacional, observabilidade e confiabilidade do health.
- Fato observado: `/api/v1/system/health/services` derivava o status do `Memory Service` a partir de `OptimizationService`.
- Fato observado: quando `optimization.analyze_system()` falhava, o endpoint tentava `get_metrics_history()`. Se tambem falhasse, o codigo usava `mem_mb = 0.0`.
- Fato observado: `0.0MB` era classificado como `ok`.
- Inferencia: uma falha de coleta de telemetria podia aparecer para UI, operadores e diagnosticos como memoria saudavel.
- Impacto antes: risco de falso saudavel em health operacional; uma perda de observabilidade era confundida com recurso normal.

### Hipotese

Acredito que representar telemetria indisponivel como `unknown`, em vez de `ok`, melhora a fidelidade do health sem interromper o endpoint e sem criar dependencia nova.

### Implementacao

- `backend/app/api/v1/endpoints/system_status.py`: `mem_mb` agora diferencia valor medido de ausencia de medicao usando `float | None`.
- `backend/app/api/v1/endpoints/system_status.py`: quando `analyze_system()` e `get_metrics_history()` falham ou nao retornam memoria, o `Memory Service` passa a responder:
  - `status: "unknown"`;
  - `metric_text: "Uso: indisponivel"`.
- `qa/test_system_endpoints_contract.py`: adicionada regressao para falha dupla de telemetria de memoria.

### Metricas

- Baseline antes da correcao:
  - falha de coleta de memoria podia produzir `status: "ok"` e `metric_text: "Uso: 0MB"`.
- Depois da correcao:
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q qa/test_system_endpoints_contract.py::TestSystemEndpointsContract::test_get_services_health qa/test_system_endpoints_contract.py::TestSystemEndpointsContract::test_get_services_health_reports_unknown_memory_when_telemetry_fails`: 2 passed.
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q qa/test_system_endpoints_contract.py`: 8 passed.
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_health_monitor_critical_classification.py qa/test_health_endpoint_contract.py backend/tests/unit/test_auto_healer_idempotency.py qa/test_system_endpoints_contract.py qa/test_workers_status_contract.py qa/test_dx007_quick_diagnostics_cli.py`: 21 passed.
  - `backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/app/api/v1/endpoints/system_status.py qa/test_system_endpoints_contract.py`: passou.
  - `backend\.venv\Scripts\python.exe -m py_compile backend/app/api/v1/endpoints/system_status.py qa/test_system_endpoints_contract.py`: passou.
- Criterio de aceitacao atendido:
  - falha de telemetria nao e classificada como memoria saudavel;
  - endpoint continua retornando 200 com informacao explicita de indisponibilidade;
  - contratos existentes de `/api/v1/system/*` continuam passando.

### Riscos e limitacoes

- A UI precisa tratar `unknown` como estado nao saudavel ou nao verificavel; se algum componente visual esperava apenas `ok/degraded/error`, pode ser necessario ajustar a camada frontend.
- O teste simula falha dos servicos de metrica; nao mede consumo real de memoria nem valida agente visual em navegador.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para o contrato do endpoint; media para a experiencia visual ate validar o frontend renderizando `unknown`.

## Ciclo 5 - Falhas internas de automedicacao passaram a ser observaveis

### Problema

- Categoria: automedicacao, observabilidade e confiabilidade operacional.
- Fato observado: o loop de `start_auto_healer()` capturava excecoes em etapas internas com `except Exception: pass`.
- Fato observado: as etapas afetadas incluiam reconexao de broker, reconciliacao de politicas de fila, poison pills, LLM router, meta-agente e Codex auto-fix.
- Inferencia: uma falha em etapa de cura podia ser descartada sem log estruturado, dificultando auditoria e diagnostico.
- Impacto antes: risco de falso senso de automedicacao; o loop continuava rodando, mas operadores nao teriam evidencia de que uma etapa corretiva falhou.

### Hipotese

Acredito que encapsular cada etapa em um executor que registra falhas por nome de etapa preserva disponibilidade do loop e torna a automedicacao auditavel.

### Implementacao

- `backend/app/core/monitoring/auto_healer.py`: adicionado `_run_healing_step(step_name, action)`.
- `backend/app/core/monitoring/auto_healer.py`: cada etapa do loop agora chama `_run_healing_step()` com identificador estavel:
  - `message_broker`;
  - `rabbitmq_consolidation_queue_policy`;
  - `poison_pill_handler`;
  - `llm_router`;
  - `meta_agent_cycle`;
  - `codex_auto_fix`.
- `backend/app/core/monitoring/auto_healer.py`: falhas de etapa agora emitem log estruturado `auto_healer_step_failed` com `step`, `error` e `exc_info=True`.
- `backend/tests/unit/test_auto_healer_idempotency.py`: adicionada regressao garantindo que uma falha de etapa e registrada e nao propagada.

### Metricas

- Baseline antes da correcao:
  - 6 blocos internos do loop descartavam excecoes com `pass`.
- Depois da correcao:
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_auto_healer_idempotency.py`: 2 passed.
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_health_monitor_critical_classification.py qa/test_health_endpoint_contract.py backend/tests/unit/test_auto_healer_idempotency.py qa/test_system_endpoints_contract.py qa/test_workers_status_contract.py qa/test_dx007_quick_diagnostics_cli.py`: 22 passed.
  - `backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/app/core/monitoring/auto_healer.py backend/tests/unit/test_auto_healer_idempotency.py`: passou.
  - `backend\.venv\Scripts\python.exe -m py_compile backend/app/core/monitoring/auto_healer.py backend/tests/unit/test_auto_healer_idempotency.py`: passou.
- Criterio de aceitacao atendido:
  - falha de uma etapa de automedicacao nao derruba o loop;
  - falha de uma etapa de automedicacao nao fica silenciosa;
  - evento de erro carrega identificador da etapa falha.

### Riscos e limitacoes

- A correcao melhora observabilidade, mas nao mede sucesso real das curas em infraestrutura PC2.
- Ainda falta uma metrica Prometheus ou contador persistente por etapa para analise historica sem depender apenas de logs.
- O placeholder `_heal_with_codex()` continua sem implementacao funcional; agora, se falhar no futuro, a falha sera registrada pelo wrapper.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para eliminacao de falhas silenciosas no loop; media para eficacia operacional ate validar com fault injection real.

## Ciclo 6 - Falhas de automedicacao passaram a ter metrica agregavel por etapa

### Problema

- Categoria: observabilidade, automedicacao e operacao continua.
- Fato observado: o ciclo anterior passou a registrar `auto_healer_step_failed` em log estruturado.
- Fato observado: nao havia contador Prometheus por etapa para quantificar falhas do Auto-Healer ao longo do tempo.
- Inferencia: depender apenas de logs dificulta alerta, tendencia historica e comparacao antes/depois por etapa de automedicacao.
- Impacto antes: operadores poderiam ver uma falha individual em log, mas nao ter uma metrica agregavel para SLO, dashboard ou alerta.

### Hipotese

Acredito que adicionar um contador Prometheus por `step` melhora a capacidade de detectar degradacao recorrente do Auto-Healer sem alterar o fluxo de cura nem introduzir persistencia nova.

### Implementacao

- `backend/app/core/monitoring/auto_healer.py`: adicionado `AUTO_HEALER_STEP_FAILURES`.
- Metrica exposta:
  - nome: `auto_healer_step_failures_total`;
  - label: `step`.
- `backend/app/core/monitoring/auto_healer.py`: `_run_healing_step()` incrementa o contador antes de registrar o erro estruturado.
- `backend/tests/unit/test_auto_healer_idempotency.py`: regressao atualizada para validar incremento da metrica e log estruturado.

### Metricas

- Baseline antes da correcao:
  - falha de etapa tinha log estruturado, mas nao tinha contador Prometheus.
- Depois da correcao:
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_auto_healer_idempotency.py`: 2 passed.
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_health_monitor_critical_classification.py qa/test_health_endpoint_contract.py backend/tests/unit/test_auto_healer_idempotency.py qa/test_system_endpoints_contract.py qa/test_workers_status_contract.py qa/test_dx007_quick_diagnostics_cli.py`: 22 passed.
  - `backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/app/core/monitoring/auto_healer.py backend/tests/unit/test_auto_healer_idempotency.py`: passou.
  - `backend\.venv\Scripts\python.exe -m py_compile backend/app/core/monitoring/auto_healer.py backend/tests/unit/test_auto_healer_idempotency.py`: passou.
- Criterio de aceitacao atendido:
  - cada falha de etapa incrementa `auto_healer_step_failures_total{step=...}`;
  - o loop continua sem propagar a excecao;
  - o log estruturado do ciclo anterior permanece emitido.

### Riscos e limitacoes

- A metrica conta falhas, mas ainda nao conta sucesso por etapa; taxa de falha por tentativa exigiria contador de tentativas/sucessos.
- A validacao foi unitaria com contador falso; nao foi feita raspagem real de `/metrics` em servidor ativo.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para incremento local da metrica; media para uso operacional ate validar scrape Prometheus no ambiente de execucao.

## Ciclo 7 - Metrica de falha do Auto-Healer passou a cobrir excecoes internas das curas

### Problema

- Categoria: observabilidade, automedicacao e validade da medicao.
- Fato observado: o contador `auto_healer_step_failures_total` era incrementado em `_run_healing_step()`.
- Fato observado: varias funcoes de cura capturavam excecoes internamente, registravam log proprio e retornavam sem propagar erro.
- Inferencia: falhas reais em `_heal_message_broker()`, `_reconcile_queue_policies()`, `_heal_poison_pills()`, `_heal_llm_router()` e `_maybe_trigger_meta_agent()` poderiam nao incrementar a metrica criada no ciclo anterior.
- Impacto antes: a metrica poderia subcontar falhas de automedicacao, criando falso baseline de confiabilidade.

### Hipotese

Acredito que centralizar o registro de falhas em `_record_healing_failure()` e usá-lo tanto no wrapper quanto nos `except` internos torna a metrica consistente com as falhas reais observadas pelo Auto-Healer.

### Implementacao

- `backend/app/core/monitoring/auto_healer.py`: adicionado `_record_healing_failure(step_name, error, message)`.
- `backend/app/core/monitoring/auto_healer.py`: `_run_healing_step()` passou a delegar contagem e log para `_record_healing_failure()`.
- `backend/app/core/monitoring/auto_healer.py`: os `except` internos das curas agora tambem chamam `_record_healing_failure()`:
  - broker;
  - politicas de fila RabbitMQ;
  - poison pills;
  - LLM router;
  - meta-agent cycle.
- `backend/tests/unit/test_auto_healer_idempotency.py`: adicionado teste provando que falha interna em `_heal_message_broker()` incrementa a metrica e emite log estruturado.

### Metricas

- Baseline antes da correcao:
  - falhas que escapavam para `_run_healing_step()` eram contadas;
  - falhas capturadas dentro das funcoes de cura podiam nao ser contadas.
- Depois da correcao:
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_auto_healer_idempotency.py`: 3 passed.
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_health_monitor_critical_classification.py qa/test_health_endpoint_contract.py backend/tests/unit/test_auto_healer_idempotency.py qa/test_system_endpoints_contract.py qa/test_workers_status_contract.py qa/test_dx007_quick_diagnostics_cli.py`: 23 passed.
  - `backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/app/core/monitoring/auto_healer.py backend/tests/unit/test_auto_healer_idempotency.py`: passou.
  - `backend\.venv\Scripts\python.exe -m py_compile backend/app/core/monitoring/auto_healer.py backend/tests/unit/test_auto_healer_idempotency.py`: passou.
- Criterio de aceitacao atendido:
  - falhas internas consumidas pelas curas incrementam `auto_healer_step_failures_total`;
  - falhas que escapam para o wrapper continuam sendo contadas;
  - o loop continua resiliente, sem propagar excecoes de etapa.

### Riscos e limitacoes

- Algumas falhas podem ser contadas por operacao interna, por exemplo uma falha por fila durante reconciliacao; isso e deliberado para medir eventos de falha, nao ciclos de loop.
- Ainda falta contador de tentativas/sucessos por etapa para calcular taxa de falha.
- A validacao segue unitaria; scrape real de `/metrics` ainda nao foi executado.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para consistencia da contagem local; media para uso em dashboards ate validar com servidor ativo e coleta Prometheus.

## Ciclo 8 - Auto-Healer passou a expor denominador para taxa de sucesso por etapa

### Problema

- Categoria: observabilidade, automedicacao e metricas operacionais.
- Fato observado: o Auto-Healer ja expunha `auto_healer_step_failures_total{step=...}`.
- Fato observado: nao havia contador de tentativas nem de sucessos por etapa.
- Inferencia: sem denominador, operadores so conseguiam ver volume absoluto de falhas, nao taxa de falha ou taxa de sucesso por etapa.
- Impacto antes: uma etapa com 10 falhas em 10 tentativas e uma etapa com 10 falhas em 10.000 tentativas pareciam equivalentes se analisadas apenas pelo contador de falhas.

### Hipotese

Acredito que adicionar contadores de tentativas e sucessos por etapa permite calcular taxa de falha/sucesso sem mudar o fluxo de cura nem exigir persistencia adicional.

### Implementacao

- `backend/app/core/monitoring/auto_healer.py`: adicionados contadores:
  - `auto_healer_step_attempts_total{step=...}`;
  - `auto_healer_step_successes_total{step=...}`.
- `backend/app/core/monitoring/auto_healer.py`: `_run_healing_step()` incrementa tentativa antes da execucao da etapa.
- `backend/app/core/monitoring/auto_healer.py`: `_run_healing_step()` incrementa sucesso apenas quando a etapa termina sem excecao propagada.
- `backend/tests/unit/test_auto_healer_idempotency.py`: adicionadas/atualizadas regressoes para:
  - falha: incrementa tentativa e falha, nao sucesso;
  - sucesso: incrementa tentativa e sucesso, nao falha.

### Metricas

- Baseline antes da correcao:
  - havia `auto_healer_step_failures_total`;
  - nao havia `auto_healer_step_attempts_total`;
  - nao havia `auto_healer_step_successes_total`.
- Depois da correcao:
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_auto_healer_idempotency.py`: 4 passed.
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_health_monitor_critical_classification.py qa/test_health_endpoint_contract.py backend/tests/unit/test_auto_healer_idempotency.py qa/test_system_endpoints_contract.py qa/test_workers_status_contract.py qa/test_dx007_quick_diagnostics_cli.py`: 24 passed.
  - `backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/app/core/monitoring/auto_healer.py backend/tests/unit/test_auto_healer_idempotency.py`: passou.
  - `backend\.venv\Scripts\python.exe -m py_compile backend/app/core/monitoring/auto_healer.py backend/tests/unit/test_auto_healer_idempotency.py`: passou.
- Criterio de aceitacao atendido:
  - cada etapa executada pelo wrapper incrementa `auto_healer_step_attempts_total`;
  - etapa concluida sem excecao propagada incrementa `auto_healer_step_successes_total`;
  - etapa com excecao propagada incrementa `auto_healer_step_failures_total` e nao sucesso.

### Riscos e limitacoes

- Uma funcao de cura que captura erro internamente e retorna ainda pode contar tentativa e sucesso no wrapper, alem de falha interna. Isso representa "ciclo continuou", nao "todas as suboperacoes foram bem-sucedidas".
- Para uma taxa estrita de sucesso sem ambiguidades, sera necessario diferenciar sucesso de wrapper, sucesso efetivo da cura e falha parcial interna.
- A validacao segue unitaria; scrape real em `/metrics` ainda nao foi executado.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para denominador por etapa no wrapper; media para interpretacao operacional ate criar semantica separada para sucesso efetivo versus sucesso de execucao.

## Ciclo 9 - Sucesso de etapa nao e mais contado quando ha falha interna parcial

### Problema

- Categoria: validade de metrica, automedicacao e confiabilidade operacional.
- Fato observado: `_run_healing_step()` incrementava `auto_healer_step_successes_total` quando a acao retornava sem excecao propagada.
- Fato observado: algumas funcoes de cura capturam falhas internas, chamam `_record_healing_failure()` e retornam normalmente para manter o loop vivo.
- Inferencia: uma etapa podia registrar falha interna e ainda assim ser contada como sucesso pelo wrapper.
- Impacto antes: taxa de sucesso por etapa podia ser inflada em cenarios de falha parcial.

### Hipotese

Acredito que comparar o numero de falhas registradas por etapa antes e depois da execucao permite contar sucesso apenas quando a etapa termina sem excecao propagada e sem falha interna registrada.

### Implementacao

- `backend/app/core/monitoring/auto_healer.py`: adicionado `_healing_failure_counts` em memoria para rastrear falhas registradas por etapa.
- `backend/app/core/monitoring/auto_healer.py`: `_record_healing_failure()` agora incrementa `_healing_failure_counts`.
- `backend/app/core/monitoring/auto_healer.py`: `_run_healing_step()` salva o total de falhas antes da acao e so incrementa `auto_healer_step_successes_total` se o total nao mudar.
- `backend/tests/unit/test_auto_healer_idempotency.py`: adicionada regressao para etapa que registra falha interna e retorna normalmente.

### Metricas

- Baseline antes da correcao:
  - tentativa incrementava corretamente;
  - falha interna incrementava falha;
  - sucesso tambem podia ser incrementado se a funcao retornasse sem excecao propagada.
- Depois da correcao:
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_auto_healer_idempotency.py`: 5 passed.
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_health_monitor_critical_classification.py qa/test_health_endpoint_contract.py backend/tests/unit/test_auto_healer_idempotency.py qa/test_system_endpoints_contract.py qa/test_workers_status_contract.py qa/test_dx007_quick_diagnostics_cli.py`: 25 passed.
  - `backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/app/core/monitoring/auto_healer.py backend/tests/unit/test_auto_healer_idempotency.py`: passou.
  - `backend\.venv\Scripts\python.exe -m py_compile backend/app/core/monitoring/auto_healer.py backend/tests/unit/test_auto_healer_idempotency.py`: passou.
- Criterio de aceitacao atendido:
  - etapa com falha interna registra tentativa e falha;
  - etapa com falha interna nao registra sucesso;
  - etapa totalmente bem-sucedida continua registrando tentativa e sucesso.

### Riscos e limitacoes

- `_healing_failure_counts` e estado em memoria do processo; ele serve para decisao local do wrapper, nao como fonte historica persistente.
- Em execucoes concorrentes da mesma etapa, a comparacao por contador pode ser conservadora e evitar sucesso se outra execucao registrar falha no mesmo intervalo. O Auto-Healer atual executa etapas sequencialmente no loop principal.
- Ainda falta validar as metricas em `/metrics` com servidor ativo.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para o loop sequencial atual; media para cenarios futuros com execucao concorrente por etapa.

## Ciclo 10 - Metricas do Auto-Healer passaram a ter contrato de registro Prometheus

### Problema

- Categoria: observabilidade, contrato operacional e validacao de metricas.
- Fato observado: os ciclos anteriores adicionaram contadores Prometheus para tentativas, sucessos e falhas por etapa.
- Fato observado: havia testes com contadores dublados, mas nenhum teste confirmava que os nomes reais estavam registrados no `prometheus_client.REGISTRY`.
- Inferencia: uma regressao em nome, import ou inicializacao poderia quebrar dashboards e alertas sem falhar os testes unitarios de comportamento.
- Impacto antes: a equipe podia confiar em metricas que nao estariam necessariamente expostas pelo registry usado por `/metrics`.

### Hipotese

Acredito que um teste de contrato no registry Prometheus reduz risco de regressao em dashboards/alertas sem exigir servidor ativo nem scrape HTTP.

### Implementacao

- `backend/tests/unit/test_auto_healer_idempotency.py`: adicionado `test_auto_healer_prometheus_metrics_are_registered()`.
- O teste valida a presenca dos nomes reais:
  - `auto_healer_step_attempts_total`;
  - `auto_healer_step_successes_total`;
  - `auto_healer_step_failures_total`.

### Metricas

- Baseline antes da correcao:
  - comportamento das metricas era validado por dublês;
  - registro real no `REGISTRY` nao era validado.
- Depois da correcao:
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_auto_healer_idempotency.py`: 6 passed.
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_health_monitor_critical_classification.py qa/test_health_endpoint_contract.py backend/tests/unit/test_auto_healer_idempotency.py qa/test_system_endpoints_contract.py qa/test_workers_status_contract.py qa/test_dx007_quick_diagnostics_cli.py`: 26 passed.
  - `backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/tests/unit/test_auto_healer_idempotency.py backend/app/core/monitoring/auto_healer.py`: passou.
  - `backend\.venv\Scripts\python.exe -m py_compile backend/tests/unit/test_auto_healer_idempotency.py backend/app/core/monitoring/auto_healer.py`: passou.
- Criterio de aceitacao atendido:
  - os tres contadores de Auto-Healer existem no registry Prometheus global;
  - os testes de comportamento das metricas continuam passando;
  - a matriz consolidada de Health permanece verde.

### Riscos e limitacoes

- O teste valida registro no `REGISTRY`, nao um scrape HTTP real de `/metrics`.
- Se o ambiente de producao usar registry customizado ou instrumentacao diferente, ainda sera necessario validar o processo em execucao.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para registro local no Prometheus client; media para exposicao HTTP ate validar com app ativa.

## Ciclo 11 - Metricas do Auto-Healer passaram a aparecer em `/metrics`

### Problema

- Categoria: observabilidade operacional e contrato HTTP de metricas.
- Fato observado: os contadores do Auto-Healer existiam no `prometheus_client.REGISTRY` quando `app.core.monitoring.auto_healer` era importado.
- Fato observado: a app usa carregamento lazy para `auto_healer`; no import padrao de `app.main`, `/metrics` podia responder sem os nomes `auto_healer_step_*`.
- Inferencia: dashboards e alertas baseados em `/metrics` poderiam nao enxergar as metricas ate o worker ser iniciado ou outro caminho importar o modulo.
- Impacto antes: diferenca entre "metricas definidas no modulo" e "metricas expostas no endpoint operacional".

### Hipotese

Acredito que importar explicitamente o modulo de metricas do Auto-Healer durante o bootstrap da app registra os contadores antes da exposicao HTTP de `/metrics`, sem iniciar o worker nem executar curas.

### Implementacao

- `backend/app/main.py`: import explicito de `app.core.monitoring.auto_healer` para registrar os contadores no registry global mesmo quando workers estao desabilitados ou atrasados.
- `qa/test_health_endpoint_contract.py`: adicionado teste ASGI para `GET /metrics` validando:
  - `auto_healer_step_attempts_total`;
  - `auto_healer_step_successes_total`;
  - `auto_healer_step_failures_total`.

### Metricas

- Baseline antes da correcao:
  - inspeção ASGI manual de `/metrics` retornou `200`, mas `auto_healer_step_attempts_total` nao aparecia no texto.
- Depois da correcao:
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q qa/test_health_endpoint_contract.py`: 4 passed.
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_health_monitor_critical_classification.py qa/test_health_endpoint_contract.py backend/tests/unit/test_auto_healer_idempotency.py qa/test_system_endpoints_contract.py qa/test_workers_status_contract.py qa/test_dx007_quick_diagnostics_cli.py`: 27 passed.
  - `backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/app/main.py qa/test_health_endpoint_contract.py`: passou.
  - `backend\.venv\Scripts\python.exe -m py_compile backend/app/main.py qa/test_health_endpoint_contract.py`: passou.
- Criterio de aceitacao atendido:
  - `/metrics` responde `200` em teste ASGI;
  - `/metrics` contem os tres nomes operacionais do Auto-Healer;
  - a mudanca nao inicia o Auto-Healer nem altera o loop de cura.

### Riscos e limitacoes

- O teste usa ASGI in-process, nao servidor real com porta, proxy ou container.
- O import registra metricas no bootstrap da app; se futuramente o modulo ganhar side effects pesados, sera necessario separar definicao de metricas em modulo dedicado.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para exposicao ASGI de `/metrics`; media para ambiente PC1/PC2 ate validar via servidor/container.

## Ciclo 12 - Registro de metricas do Auto-Healer foi desacoplado da logica de cura

### Problema

- Categoria: arquitetura operacional, observabilidade e risco de bootstrap.
- Fato observado: o ciclo anterior garantiu que `/metrics` expunha metricas do Auto-Healer importando `app.core.monitoring.auto_healer` no bootstrap da app.
- Fato observado: `auto_healer.py` contem a logica de cura e importa dependencias operacionais como broker, health monitor, poison pill handler e schemas de fila.
- Inferencia: registrar metricas no bootstrap importando a implementacao inteira do worker aumenta acoplamento e risco de side effects futuros.
- Impacto antes: o caminho de inicializacao da API precisava carregar mais codigo operacional do que o necessario apenas para registrar contadores Prometheus.

### Hipotese

Acredito que mover apenas as definicoes Prometheus para um modulo dedicado preserva exposicao em `/metrics` e reduz o acoplamento entre bootstrap HTTP e execucao do Auto-Healer.

### Implementacao

- `backend/app/core/monitoring/auto_healer_metrics.py`: criado modulo dedicado para:
  - `AUTO_HEALER_STEP_FAILURES`;
  - `AUTO_HEALER_STEP_ATTEMPTS`;
  - `AUTO_HEALER_STEP_SUCCESSES`.
- `backend/app/core/monitoring/auto_healer.py`: passou a importar os contadores do modulo de metricas.
- `backend/app/main.py`: passou a importar `auto_healer_metrics`, nao `auto_healer`, para registrar metricas no bootstrap.

### Metricas

- Baseline antes da correcao:
  - `/metrics` expunha os nomes do Auto-Healer;
  - o bootstrap fazia isso importando a implementacao completa do worker.
- Depois da correcao:
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_auto_healer_idempotency.py qa/test_health_endpoint_contract.py`: 10 passed.
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_health_monitor_critical_classification.py qa/test_health_endpoint_contract.py backend/tests/unit/test_auto_healer_idempotency.py qa/test_system_endpoints_contract.py qa/test_workers_status_contract.py qa/test_dx007_quick_diagnostics_cli.py`: 27 passed.
  - `backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/app/core/monitoring/auto_healer.py backend/app/core/monitoring/auto_healer_metrics.py backend/app/main.py backend/tests/unit/test_auto_healer_idempotency.py qa/test_health_endpoint_contract.py`: passou.
  - `backend\.venv\Scripts\python.exe -m py_compile backend/app/core/monitoring/auto_healer.py backend/app/core/monitoring/auto_healer_metrics.py backend/app/main.py backend/tests/unit/test_auto_healer_idempotency.py qa/test_health_endpoint_contract.py`: passou.
- Criterio de aceitacao atendido:
  - `/metrics` continua coberto pelo teste ASGI do ciclo 11;
  - Auto-Healer continua usando os mesmos contadores;
  - bootstrap registra metricas sem importar a logica completa de cura.

### Riscos e limitacoes

- O modulo de metricas ainda usa o registry global padrao do Prometheus client.
- Nao foi executado teste em servidor/container; a validacao segue in-process.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para reducao de acoplamento local e preservacao dos contratos existentes.

## Ciclo 13 - `/system/overview` deixou de mascarar falha de telemetria de memoria

### Problema

- Categoria: consistencia de health, usabilidade operacional e observabilidade.
- Fato observado: `/api/v1/system/health/services` ja representava telemetria de memoria indisponivel como `unknown`.
- Fato observado: `/api/v1/system/overview` duplicava a logica antiga e ainda usava `mem_mb = 0.0` quando `analyze_system()` e `get_metrics_history()` falhavam.
- Fato observado: `0.0MB` era classificado como `ok`.
- Inferencia: a tela ou store que consome `system/overview` podia exibir memoria saudavel enquanto a coleta de telemetria estava indisponivel.
- Impacto antes: endpoints de Health divergiam para a mesma informacao operacional, criando falso saudavel no painel agregado.

### Hipotese

Acredito que alinhar `/system/overview` com `/system/health/services` elimina o falso saudavel e reduz divergencia entre contratos de Health consumidos pelo frontend.

### Implementacao

- `backend/app/api/v1/endpoints/system_overview.py`: `mem_mb` agora usa `float | None` para diferenciar valor medido de ausencia de medicao.
- `backend/app/api/v1/endpoints/system_overview.py`: quando as duas fontes de telemetria falham ou nao retornam memoria, o item `memory` passa a responder:
  - `status: "unknown"`;
  - `metric_text: "Uso: indisponivel"`.
- `qa/test_system_endpoints_contract.py`: adicionada regressao para `/api/v1/system/overview` com falha dupla de telemetria.

### Metricas

- Baseline antes da correcao:
  - `/system/overview` podia retornar `status: "ok"` e `metric_text: "Uso: 0MB"` em falha de telemetria.
- Depois da correcao:
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q qa/test_system_endpoints_contract.py`: 9 passed.
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_health_monitor_critical_classification.py qa/test_health_endpoint_contract.py backend/tests/unit/test_auto_healer_idempotency.py qa/test_system_endpoints_contract.py qa/test_workers_status_contract.py qa/test_dx007_quick_diagnostics_cli.py`: 28 passed.
  - `backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/app/api/v1/endpoints/system_overview.py qa/test_system_endpoints_contract.py`: passou.
  - `backend\.venv\Scripts\python.exe -m py_compile backend/app/api/v1/endpoints/system_overview.py qa/test_system_endpoints_contract.py`: passou.
- Criterio de aceitacao atendido:
  - `/system/overview` nao classifica ausencia de telemetria como memoria saudavel;
  - `/system/overview` e `/system/health/services` usam a mesma semantica para memoria desconhecida;
  - contratos existentes de System/Health continuam passando.

### Riscos e limitacoes

- Ainda ha duplicacao de logica entre os endpoints. Uma refatoracao futura pode extrair helper compartilhado para reduzir divergencia permanente.
- A validacao e ASGI in-process; nao foi executado frontend visual.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para contrato backend; media para experiencia visual ate validar o painel frontend.

## Ciclo 14 - Endpoints de Health passaram a usar um helper backend compartilhado

### Problema

- Categoria: arquitetura operacional, consistencia de contrato e manutencao.
- Fato observado: `/api/v1/system/health/services` e `/api/v1/system/overview` mantinham logica duplicada para status de agentes, conhecimento, memoria e LLM.
- Fato observado: a duplicacao ja causou divergencia concreta nos ciclos 4 e 13, onde memoria indisponivel podia ser representada de formas diferentes.
- Inferencia: manter dois caminhos manuais para a mesma semantica de Health aumenta a probabilidade de regressao silenciosa.
- Impacto antes: qualquer mudanca de threshold, fallback ou texto operacional precisava ser replicada em dois endpoints.

### Hipotese

Acredito que extrair a montagem dos itens de saude para um helper compartilhado reduz divergencia entre endpoints e preserva o contrato HTTP existente.

### Implementacao

- `backend/app/services/system_health_service.py`: criado helper compartilhado para:
  - coletar saude de agentes, conhecimento, LLM e memoria;
  - diferenciar memoria medida de telemetria indisponivel;
  - aplicar thresholds `8192MB => degraded` e `16384MB => error`;
  - retornar itens serializaveis pelos DTOs ja existentes.
- `backend/app/api/v1/endpoints/system_status.py`: passou a usar `build_service_health_items`.
- `backend/app/api/v1/endpoints/system_overview.py`: passou a usar o mesmo helper e removeu a duplicacao da montagem de `services_status`.

### Metricas

- Baseline antes da correcao:
  - dois endpoints continham logica propria para os mesmos quatro itens de saude;
  - historico recente mostrou divergencia real no estado de memoria.
- Depois da correcao:
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q qa/test_system_endpoints_contract.py qa/test_health_endpoint_contract.py`: 13 passed.
  - `backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/app/services/system_health_service.py backend/app/api/v1/endpoints/system_status.py backend/app/api/v1/endpoints/system_overview.py qa/test_system_endpoints_contract.py qa/test_health_endpoint_contract.py`: passou.
  - `backend\.venv\Scripts\python.exe -m py_compile backend/app/services/system_health_service.py backend/app/api/v1/endpoints/system_status.py backend/app/api/v1/endpoints/system_overview.py`: passou.
- Criterio de aceitacao atendido:
  - `/system/health/services` e `/system/overview` usam a mesma fonte de montagem de servicos;
  - contratos backend existentes continuam passando;
  - ausencia de telemetria continua aparecendo como `unknown`, nao como `ok`.

### Riscos e limitacoes

- O helper ainda retorna dicionarios para compatibilidade com DTOs diferentes nos endpoints; uma etapa futura pode tipar isso com Pydantic compartilhado se houver beneficio real.
- A validacao e ASGI/unitaria; nao foi executado ambiente PC1/PC2 em container.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para reducao de divergencia local e preservacao de contrato.

## Ciclo 15 - Frontend deixou de tratar `degraded` e `unknown` como sistema saudavel

### Problema

- Categoria: usabilidade operacional, contrato frontend/backend e disponibilidade percebida.
- Fato observado: `SystemStatusService.getServicesHealth()` marcava `isSystemHealthy$` como `true` sempre que nenhum servico vinha com `status === "error"`.
- Fato observado: o backend agora usa `unknown` para telemetria indisponivel e `degraded` para degradacao operacional.
- Inferencia: o HUD/frontend podia mostrar o sistema como saudavel quando memoria, agentes, conhecimento ou LLM estavam degradados ou sem telemetria.
- Fato observado adicional: a tela `admin/autonomia` usava `toPromise()` e acessava campos inexistentes nos contratos reais:
  - `/api/v1/autonomy/health` retorna `active_goals_count`, nao `active_goals`;
  - `/api/v1/autonomy/admin/board` retorna `{ items: [...] }`, nao `{ sprints: [...] }`.
- Impacto antes: o build Angular falhava por tipagem, e a UI de Health podia apresentar falso saudavel.

### Hipotese

Acredito que considerar saudavel apenas uma lista nao vazia de servicos com status `ok`, somado ao alinhamento tipado da tela de Autonomia, elimina falso saudavel e remove dependencia de contratos legados inexistentes.

### Implementacao

- `frontend/src/app/core/services/system-status.service.ts`:
  - removeu estado morto `healthCache$`;
  - `isSystemHealthy$` agora recebe `true` somente quando todos os servicos retornados estao `ok`;
  - lista vazia, erro HTTP, `degraded`, `unknown` ou `error` resultam em `false`.
- `frontend/src/app/core/services/system-status.spec.ts`:
  - adicionadas regressoes para lista toda `ok`;
  - regressoes para `degraded`/`unknown`;
  - regressao para lista vazia.
- `frontend/src/app/features/admin/autonomia/admin-autonomia.ts`:
  - substituiu `toPromise()` por `firstValueFrom`;
  - adicionou interfaces estreitas para os contratos consumidos;
  - passou a ler `active_goals_count`;
  - passou a montar ferramentas evolutivas a partir de `boardResp.items[*].sprints[*].tasks`.
- `frontend/src/app/features/admin/autonomia/admin-autonomia.html`:
  - deixou de tentar listar metas que o backend nao retorna;
  - passou a exibir a contagem reportada pelo backend.

### Metricas

- Baseline antes da correcao:
  - `degraded` e `unknown` eram considerados saudaveis no indicador global se nao houvesse `error`;
  - `npx ng build --configuration development` falhava com `TS2339` em `active_goals`, `domain_health` e `sprints` por respostas tipadas como `Object` e campos incorretos.
- Depois da correcao:
  - `npm run test -- src/app/core/services/system-status.spec.ts`: 4 passed.
  - `npm run test`: 30 test files, 140 tests passed.
  - `npm run lint`: passou.
  - `npx ng build --configuration development`: passou.
- Criterio de aceitacao atendido:
  - frontend nao mascara `degraded` ou `unknown` como saudavel;
  - build Angular volta a passar;
  - tela de Autonomia consome os contratos reais de Health/Admin Board sem `toPromise()` legado.

### Riscos e limitacoes

- A validacao foi automatizada, sem screenshot/manual no navegador.
- A tela ainda usa `HttpClient` direto nesse trecho; uma melhoria futura pode mover esses contratos para `AutonomyApiService` se houver reuso.
- `Browserslist` emitiu aviso de base `caniuse-lite` desatualizada, sem falhar os testes.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para contrato frontend e build; media para UX visual ate validacao manual do painel.

## Ciclo 16 - Modo visitante passou a liberar visualizacao operacional de Health sem credenciais

### Problema

- Categoria: usabilidade operacional, disponibilidade percebida e acesso controlado.
- Fato observado: a rota raiz redirecionava para `/login` quando nao havia sessao autenticada.
- Fato observado: o HUD de Health fica no header das rotas autenticadas; sem credenciais, o usuario nao conseguia ver o estado operacional global.
- Fato observado durante validacao renderizada: antes da correcao de ambiente, o app podia ficar em tela vazia por `ReferenceError: process is not defined` no bundle frontend.
- Inferencia: para um sistema de Saude que auxilia automedicacao, bloquear toda percepcao operacional atras de login comum reduz diagnostico inicial e aumenta confusao do usuario.
- Impacto antes: usuario sem credenciais nao conseguia acessar a home nem abrir o HUD de Health; o modo offline/sem backend tambem nao ficava claro a partir do painel global.

### Hipotese

Acredito que um modo visitante explicito, sem token falso e com permissoes reduzidas, permite observar o Health e o estado offline sem enfraquecer rotas administrativas.

### Implementacao

- `frontend/src/app/core/auth/auth.service.ts`:
  - adicionou `enterVisitorMode()`;
  - persiste `JANUS_VISITOR_MODE=1`;
  - cria usuario local sintetico `visitor` com role `visitor` e permissao `read:public`;
  - nao cria token JWT nem refresh token;
  - restaura modo visitante sem chamar `/me`;
  - `logout()` continua limpando a flag de visitante.
- `frontend/src/app/features/auth/login/login.ts`:
  - adicionou acao `enterVisitorMode()` e navegacao para home.
- `frontend/src/app/features/auth/login/login.html` e `.scss`:
  - adicionou botao “Entrar como visitante”;
  - adicionou texto de escopo: acesso limitado, sem credenciais e sem permissoes administrativas.
- `frontend/src/environments/environment.ts` e `environment.prod.ts`:
  - substituiu `process.env` por `import.meta.env` para remover dependencia Node no bundle de navegador.
- Testes:
  - `AuthService`: visitante sem backend/token, restauracao por flag sem `/me`;
  - `LoginComponent`: clique logico de modo visitante navega para home;
  - `SystemHud`: manteve cobertura de percepcao de Health.

### Metricas

- Baseline antes da correcao:
  - navegador em `/` redirecionava para `/login`;
  - Health global inacessivel sem sessao;
  - renderizacao inicial podia falhar com `ReferenceError: process is not defined`.
- Depois da correcao:
  - navegador: `/login?returnUrl=%2F` -> clique em “Entrar como visitante” -> `/`;
  - navegador: home renderizou “Ola, Visitante”;
  - navegador desktop: botao “Health / Sem telemetria” ficou acessivel;
  - navegador desktop: clique no HUD abriu dialog com “Sem telemetria”, “0 de 0 servico(s) requerem atencao” e explicacao de ausencia de dados;
  - `npm run test -- src/app/core/auth/auth.service.spec.ts src/app/features/auth/login/login.spec.ts src/app/shared/components/ui/system-hud/system-hud.spec.ts`: 27 passed;
  - `npm run test`: 30 test files, 147 tests passed;
  - `npm run lint`: passou;
  - `npx ng build --configuration development`: passou.
- Criterio de aceitacao atendido:
  - visitante acessa a home sem token;
  - visitante consegue ver o Health global;
  - admin continua protegido por `RoleGuard`, porque visitante tem apenas role `visitor`;
  - frontend nao depende mais de `process.env` em runtime de navegador.

### Riscos e limitacoes

- O modo visitante libera rotas protegidas por `AuthGuard`, mas nao deve liberar endpoints backend protegidos; chamadas sem token continuam dependendo das politicas de backend/interceptor.
- Validacao visual foi feita com backend indisponivel, entao o HUD mostrou corretamente “Sem telemetria”; nao houve validacao visual com backend real retornando servicos `ok/degraded/error`.
- O console do Browser manteve uma entrada historica antiga de `process is not defined`, mas a aba nova renderizou a aplicacao e os gates de build/test passaram.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para fluxo frontend visitante e acesso ao HUD; media para integracao full-stack ate validar com backend autenticado/PC1 ativo.

## Ciclo 17 - HUD de Health deixou de ficar invisivel em telas mobile

### Problema

- Categoria: usabilidade operacional, responsividade e percepcao de disponibilidade.
- Fato observado: o Header renderizava o HUD dentro de `.system-metrics.desktop-only`.
- Fato observado: em `max-width: 980px`, `.desktop-only` era ocultado com `display: none !important`.
- Fato observado em navegador mobile: modo visitante acessava a home, mas o botao de Health nao aparecia no header; o usuario precisava estar em viewport desktop para ver o estado operacional.
- Inferencia: em celulares ou janelas estreitas, a correcao de modo visitante nao bastava para tornar Health observavel.
- Impacto antes: a saude global ficava invisivel no principal breakpoint de acesso rapido.

### Hipotese

Acredito que manter o HUD no header em todos os breakpoints, com layout compacto em telas estreitas, torna Health observavel sem aumentar superficie de backend nem criar rota nova.

### Implementacao

- `frontend/src/app/core/layout/header/header.html`:
  - removeu a classe `desktop-only` do container `.system-metrics`.
- `frontend/src/app/core/layout/header/header.scss`:
  - ajustou gaps, margens e tamanho da marca em mobile;
  - manteve `.system-metrics` visivel ao lado do menu;
  - ocultou apenas o texto da marca em telas muito estreitas para evitar sobreposicao.
- `frontend/src/app/shared/components/ui/system-hud/system-hud.scss`:
  - adicionou layout compacto para `max-width: 520px`;
  - reposicionou o painel como `fixed` no mobile para caber no viewport;
  - manteve o rotulo textual de estado visivel, nao apenas um ponto colorido.
- `frontend/src/app/core/layout/header/header.spec.ts`:
  - adicionou regressao garantindo que `app-system-hud` permanece no Header.

### Metricas

- Baseline antes da correcao:
  - viewport mobile visitante mostrava home, mas nao tinha botao Health visivel no header.
- Depois da correcao:
  - navegador mobile `390x760`: visitante entrou na home e o DOM exibiu botao com `aria-label="Abrir resumo de saude do sistema"`;
  - navegador mobile: clique no botao abriu o dialog de Health;
  - navegador mobile: painel mostrou “Sem telemetria”, “0 de 0 servico(s) requerem atencao” e explicacao da ausencia de dados;
  - `npm run test -- src/app/core/layout/header/header.spec.ts src/app/shared/components/ui/system-hud/system-hud.spec.ts`: 8 passed;
  - `npm run test`: 30 test files, 148 tests passed;
  - `npm run lint`: passou;
  - `npx ng build --configuration development`: passou.
- Criterio de aceitacao atendido:
  - Health global e visivel no header mobile;
  - HUD abre em mobile sem depender do menu;
  - texto de severidade continua disponivel ao usuario;
  - desktop segue validado pela iteracao anterior e build atual.

### Riscos e limitacoes

- A validacao mobile foi feita com backend indisponivel; estados `ok`, `degraded` e `error` com dados reais ainda precisam de evidencia visual full-stack.
- Em telas extremamente estreitas, a marca textual e ocultada para preservar Health e menu; trade-off aceitavel porque o avatar/marca visual permanece.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para visibilidade mobile do HUD e preservacao dos gates frontend.

## Ciclo 18 - Polling de Health no frontend passou a ser compartilhado

### Problema

- Categoria: desempenho, disponibilidade e custo operacional do Health.
- Fato observado: `SystemStatusService.getServicesHealth()` criava um novo `timer(0, 15000)` a cada chamada.
- Fato observado: o HUD global chama esse metodo no header e outros componentes podem consumir o mesmo servico.
- Inferencia: multiplos consumidores simultaneos podiam multiplicar requisicoes para `/api/v1/system/health/services`, aumentando ruido no backend justamente no endpoint usado para diagnostico.
- Impacto antes: duas assinaturas simultaneas nao tinham contrato garantindo uma unica chamada HTTP inicial.

### Hipotese

Acredito que cachear o Observable de Health com `shareReplay({ bufferSize: 1, refCount: true })` reduz chamadas duplicadas sem alterar o contrato de dados consumido pelo HUD.

### Implementacao

- `frontend/src/app/core/services/system-status.service.ts`:
  - adicionou `healthCache$`;
  - `getServicesHealth()` agora retorna o stream compartilhado quando ja existe;
  - manteve polling de 15 segundos, tratamento de erro e atualizacao de `isSystemHealthy$`.
- `frontend/src/app/core/services/system-status.spec.ts`:
  - adicionou regressao para duas assinaturas simultaneas produzirem apenas uma requisicao HTTP inicial.

### Metricas

- Baseline antes da correcao:
  - cada chamada a `getServicesHealth()` construia um novo polling;
  - nao havia teste impedindo duplicacao de requisicoes simultaneas.
- Depois da correcao:
  - `npm run test -- src/app/core/services/system-status.spec.ts src/app/shared/components/ui/system-hud/system-hud.spec.ts src/app/core/layout/header/header.spec.ts`: 13 passed;
  - `npm run lint`: passou;
  - `npm run test`: 30 test files, 149 tests passed;
  - `npx ng build --configuration development`: passou.
- Criterio de aceitacao atendido:
  - duas assinaturas simultaneas de Health compartilham a mesma requisicao inicial;
  - o contrato de `isSystemHealthy$` continua preservado;
  - HUD e Header continuam cobertos por testes.

### Riscos e limitacoes

- O teste cobre duplicacao simultanea no servico central, nao mede volume real em navegador com backend ativo.
- `BackendApiService.system.getServicesHealth()` usado por widgets de observabilidade ainda e um caminho separado; a mudanca desta iteracao protege o HUD global, que e o consumidor persistente.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para reducao de duplicacao no `SystemStatusService`; media para impacto total em todos os widgets ate unificar o consumo em uma camada unica.

## Ciclo 19 - Widget de Observability passou a consumir o servico central de Health

### Problema

- Categoria: desempenho, consistencia de Health e manutencao frontend.
- Fato observado: `SystemStatusWidgetComponent` usava `BackendApiService` diretamente.
- Fato observado: o widget criava seu proprio `interval(5000)` para `/api/v1/system/status`, separado do cache de `SystemStatusService`.
- Fato observado: o Ciclo 18 compartilhou o polling no `SystemStatusService`, mas o widget de Observability continuava fora desse caminho.
- Inferencia: a tela de Observability podia manter chamadas redundantes e exibir Health com cadencia diferente do HUD global.
- Impacto antes: duas superficies de Health no frontend tinham fontes de polling diferentes.

### Hipotese

Acredito que migrar o widget de Observability para `SystemStatusService` reduz duplicacao de polling e aproxima a semantica visual do HUD global.

### Implementacao

- `frontend/src/app/features/observability/widgets/system-status-widget/system-status-widget.ts`:
  - removeu `BackendApiService`, `interval`, `Subscription`, `switchMap` e polling manual;
  - passou a consumir `getSystemStatus()` e `getServicesHealth()` do `SystemStatusService`;
  - usa `takeUntilDestroyed` para encerrar assinaturas no ciclo de vida do componente;
  - classifica `UNKNOWN` como amarelo, alinhando estado incerto com atencao operacional.
- `frontend/src/app/features/observability/widgets/system-status-widget/system-status-widget.spec.ts`:
  - adicionada cobertura garantindo consumo via `SystemStatusService`;
  - adicionada cobertura de renderizacao de status e servicos.

### Metricas

- Baseline antes da correcao:
  - widget fazia polling proprio de status a cada 5s;
  - widget nao tinha teste dedicado;
  - widget nao se beneficiava do cache do `SystemStatusService`.
- Depois da correcao:
  - `npm run test -- src/app/features/observability/widgets/system-status-widget/system-status-widget.spec.ts src/app/core/services/system-status.spec.ts`: 7 passed;
  - `npm run lint`: passou;
  - `npm run test`: 31 test files, 151 tests passed;
  - `npx ng build --configuration development`: passou.
- Criterio de aceitacao atendido:
  - widget usa o servico central de Health/Status;
  - polling manual duplicado foi removido;
  - widget tem regressao propria;
  - gates frontend continuam verdes.

### Riscos e limitacoes

- Ainda existem outros widgets de Observability com chamadas proprias para seus dominios, como Knowledge/Database; esta iteracao focou o widget de System Health.
- Nao foi medido trafego real em navegador com backend ativo; a evidencia e estrutural e por teste unitario.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para reducao de duplicacao no widget de System Health; media para impacto operacional total ate medir com backend ativo.

## Ciclo 20 - Falha de um subsistema nao derruba mais os endpoints agregados de Health

### Problema

- Categoria: disponibilidade, resiliencia de diagnostico e observabilidade.
- Fato observado: `build_service_health_items()` ja isolava falha de telemetria de memoria.
- Fato observado: chamadas para `observability.get_multi_agent_system_health()`, `knowledge.get_health_status()` e `llm.get_health_status()` nao tinham isolamento local.
- Inferencia: se Knowledge, LLM ou Agent Health levantasse excecao, `/api/v1/system/health/services` e `/api/v1/system/overview` poderiam falhar por completo.
- Impacto antes: o endpoint de Health podia ficar indisponivel justamente quando um subsistema precisava ser diagnosticado.

### Hipotese

Acredito que isolar cada subsistema em um item `unknown` preserva diagnostico parcial e aumenta disponibilidade dos endpoints agregados de Health.

### Implementacao

- `backend/app/services/system_health_service.py`:
  - adicionou helpers isolados para Agent, Knowledge, LLM e Memory;
  - cada falha parcial registra warning estruturado `system_health_subsystem_unavailable`;
  - falha parcial retorna item `status: "unknown"` com `metric_text` explicito;
  - os quatro checks passaram a rodar com `asyncio.gather`, mantendo ordem final `[agent, knowledge, memory, llm]`.
- `qa/test_system_endpoints_contract.py`:
  - adicionou regressao parametrizada para `/system/health/services` e `/system/overview`;
  - simula falha em `KnowledgeService.get_health_status()`;
  - exige HTTP 200, `knowledge.status == "unknown"` e preservacao de `agent.status == "healthy"`.

### Metricas

- Baseline antes da correcao:
  - falha de Knowledge/LLM/Agent Health podia propagar excecao e tornar o endpoint agregado indisponivel;
  - nao havia regressao cobrindo falha parcial de subsistema nao-memoria.
- Depois da correcao:
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q qa/test_system_endpoints_contract.py qa/test_health_endpoint_contract.py`: 15 passed;
  - `backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/app/services/system_health_service.py qa/test_system_endpoints_contract.py`: passou;
  - `backend\.venv\Scripts\python.exe -m py_compile backend/app/services/system_health_service.py qa/test_system_endpoints_contract.py`: passou;
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_health_monitor_critical_classification.py qa/test_health_endpoint_contract.py backend/tests/unit/test_auto_healer_idempotency.py qa/test_system_endpoints_contract.py qa/test_workers_status_contract.py qa/test_dx007_quick_diagnostics_cli.py`: 30 passed.
- Criterio de aceitacao atendido:
  - falha de Knowledge Health nao derruba endpoints agregados;
  - os endpoints retornam diagnostico parcial;
  - outros servicos saudaveis continuam reportados;
  - contratos backend existentes continuam passando.

### Riscos e limitacoes

- A regressao simula Knowledge; a implementacao tambem cobre Agent e LLM, mas sem testes especificos para cada um.
- Os checks rodam em paralelo; se algum provider tiver side effect inesperado por concorrencia, sera necessario medir em ambiente integrado. Pela assinatura atual, sao leituras independentes.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para resiliencia dos endpoints agregados sob falha parcial simulada.

## Ciclo 21 - Contrato de status de Health foi normalizado para o frontend

### Problema

- Categoria: defeito funcional, contrato backend-frontend e experiencia central de Health.
- Fato observado: `SystemStatusService` no frontend tipa `ServiceHealthItem.status` como `ok | degraded | error | unknown`.
- Fato observado: o frontend considera o sistema saudavel apenas quando todos os servicos retornam `status === "ok"`.
- Fato observado: os provedores backend usados no contrato de teste retornavam `status: "healthy"`.
- Inferencia: endpoints agregados podiam reportar subsistemas saudaveis como `healthy`, valor fora do contrato frontend, causando falso estado nao-saudavel na interface.
- Impacto antes: 4 de 4 servicos saudaveis podiam ser interpretados pelo frontend como nao saudaveis por divergencia semantica, nao por falha real.

### Hipotese

Acredito que normalizar os status na fronteira backend de `/api/v1/system/health/services` e `/api/v1/system/overview` elimina falsos negativos no HUD sem flexibilizar o contrato TypeScript do frontend.

### Implementacao

- `backend/app/services/system_health_service.py`:
  - adicionou `_normalize_service_status()`;
  - mapeia aliases saudaveis (`healthy`, `operational`, `up`, `ready`) para `ok`;
  - mapeia aliases de atencao (`warning`, `warn`, `partial`) para `degraded`;
  - mapeia aliases de falha (`unhealthy`, `down`, `failed`, `unavailable`) para `error`;
  - valores vazios, nulos ou desconhecidos viram `unknown`;
  - Agent, Knowledge e LLM agora publicam apenas estados canonicos.
- `qa/test_system_endpoints_contract.py`:
  - atualizou o contrato esperado de `healthy` para `ok`;
  - adicionou regressao para `/system/overview`;
  - adicionou regressao para aliases heterogeneos de provedores: `warning -> degraded`, `unhealthy -> error`, valor nao reconhecido -> `unknown`.

### Metricas

- Baseline antes da correcao:
  - endpoint podia emitir `healthy`, fora do union type do frontend;
  - nao havia teste garantindo estados canonicos para os endpoints agregados;
  - frontend classificava `healthy` como nao saudavel por comparacao estrita com `ok`.
- Depois da correcao:
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q qa/test_system_endpoints_contract.py qa/test_health_endpoint_contract.py`: 17 passed;
  - `backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/app/services/system_health_service.py qa/test_system_endpoints_contract.py`: passou;
  - `backend\.venv\Scripts\python.exe -m py_compile backend/app/services/system_health_service.py qa/test_system_endpoints_contract.py`: passou;
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_health_monitor_critical_classification.py qa/test_health_endpoint_contract.py backend/tests/unit/test_auto_healer_idempotency.py qa/test_system_endpoints_contract.py qa/test_workers_status_contract.py qa/test_dx007_quick_diagnostics_cli.py`: 32 passed;
  - `npm run test -- src/app/core/services/system-status.spec.ts src/app/shared/components/ui/system-hud/system-hud.spec.ts`: 10 passed.
- Criterio de aceitacao atendido:
  - endpoints agregados nao vazam `healthy` para o frontend;
  - todos os servicos saudaveis do fixture passam a retornar `ok`;
  - aliases degradados, criticos e desconhecidos tem comportamento deterministico;
  - HUD e servico frontend continuam cobertos por regressao.

### Riscos e limitacoes

- A normalizacao e conservadora: valores nao reconhecidos viram `unknown`, o que pode exigir mapeamento adicional se novos provedores adotarem outra nomenclatura.
- `unavailable` foi classificado como `error`; se algum provedor usar esse termo para telemetria ausente sem falha operacional, sera preciso ajustar o contrato desse provedor.
- Nao foi executado teste full-stack com backend real nesta iteracao; a evidencia e por contrato ASGI e testes frontend direcionados.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para eliminar falso negativo de Health causado por divergencia `healthy` versus `ok`.

## Ciclo 22 - Worker malformado nao derruba mais `/system/overview`

### Problema

- Categoria: disponibilidade, resiliencia de diagnostico e UX operacional de Health.
- Fato observado: `/api/v1/system/overview` agrega `system_status`, `services_status` e `workers_status`.
- Fato observado: a montagem de `workers_status` assumia que cada item de `app.state.orchestrator_workers` era um dicionario.
- Baseline reproduzida: quando `orchestrator_workers` continha `["malformed-worker"]` junto de um worker valido, o endpoint retornava HTTP 503.
- Evidencia da baseline: regressao nova falhou com `503 != 200` e traceback `AttributeError: 'str' object has no attribute 'get'`.
- Inferencia: um item de worker corrompido podia tornar indisponivel todo o painel de Overview, mesmo com `services_status` e `system_status` disponiveis.

### Hipotese

Acredito que isolar e validar a colecao de workers antes de montar `WorkerStatusResponse` preserva a disponibilidade de `/system/overview` sob falha parcial do estado de workers.

### Implementacao

- `backend/app/api/v1/endpoints/system_overview.py`:
  - adicionou `_build_workers_status(raw_workers, now)`;
  - valida se a colecao de workers e uma lista;
  - ignora itens nao mapeaveis com warning estruturado `system_overview_invalid_worker_item`;
  - converte `name` para string antes de publicar o DTO;
  - se `_task_status()` falhar para um worker especifico, retorna aquele worker como `unknown` em vez de derrubar o endpoint.
- `qa/test_system_endpoints_contract.py`:
  - adicionou regressao com worker valido + item string malformado;
  - exige HTTP 200, preservacao de `services_status` e retorno apenas do worker valido.

### Metricas

- Baseline antes da correcao:
  - teste direcionado reproduziu HTTP 503 para um item malformado em `orchestrator_workers`;
  - o painel agregado ficava indisponivel por falha parcial de uma lista auxiliar.
- Depois da correcao:
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q qa/test_system_endpoints_contract.py::TestSystemEndpointsContract::test_get_system_overview_ignores_malformed_worker_items`: 1 passed;
  - `backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/app/api/v1/endpoints/system_overview.py qa/test_system_endpoints_contract.py`: passou;
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q qa/test_system_endpoints_contract.py qa/test_health_endpoint_contract.py`: 18 passed;
  - `backend\.venv\Scripts\python.exe -m py_compile backend/app/api/v1/endpoints/system_overview.py qa/test_system_endpoints_contract.py`: passou;
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_health_monitor_critical_classification.py qa/test_health_endpoint_contract.py backend/tests/unit/test_auto_healer_idempotency.py qa/test_system_endpoints_contract.py qa/test_workers_status_contract.py qa/test_dx007_quick_diagnostics_cli.py`: 33 passed.
- Criterio de aceitacao atendido:
  - item de worker malformado nao derruba `/system/overview`;
  - dados de Health de servicos seguem disponiveis;
  - worker valido continua sendo reportado;
  - falha parcial fica observavel por warning estruturado.

### Riscos e limitacoes

- Itens de worker invalidos sao ignorados, nao retornados como entradas `unknown`, porque nao ha identificador confiavel para expor ao usuario.
- A validacao e ASGI in-process; nao foi feita injecao em runtime real com workers ativos.
- O endpoint ainda tem um `try` amplo para falhas de `system_status` ou montagem final do DTO; esta iteracao isolou especificamente a lista auxiliar de workers.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para disponibilidade de `/system/overview` sob worker malformado simulado.

## Ciclo 23 - `/workers/status` passou a tolerar registros malformados

### Problema

- Categoria: disponibilidade operacional, diagnostico de workers e Health de automedicacao.
- Fato observado: `/api/v1/workers/status` e usado como contrato operacional para observar workers gerenciados pelo orquestrador.
- Fato observado: o endpoint assumia que cada item de `app.state.orchestrator_workers` tinha chaves `name` e `task`.
- Baseline reproduzida: com `orchestrator_workers = [{"name": "...", "task": ...}, "malformed-worker"]`, o endpoint levantava `TypeError: string indices must be integers`.
- Inferencia: a mesma corrupcao parcial tratada no Overview ainda derrubava a rota primaria de diagnostico dos workers.
- Impacto antes: um registro invalido impedia observar todos os workers, inclusive os validos, prejudicando diagnostico e automedicacao operacional.

### Hipotese

Acredito que validar a colecao de workers na borda dos endpoints de workers preserva observabilidade operacional sob falha parcial sem esconder que dados invalidos foram descartados.

### Implementacao

- `backend/app/api/v1/endpoints/workers.py`:
  - adicionou `_valid_worker_records(raw_workers)`;
  - colecoes nao-lista e itens nao-mapeaveis geram warning estruturado;
  - `start-all`, `stop-all` e `status` passaram a usar apenas registros validos;
  - `/workers/status` agora retorna `ignored` com a contagem de registros descartados;
  - registros mapeaveis incompletos usam `name: "worker"` e `_task_status(None)`, resultando em estado `unknown`.
- `qa/test_workers_status_contract.py`:
  - adicionou regressao com worker valido e item string malformado;
  - exige HTTP 200, `tracked == 1`, `ignored == 1` e preservacao do worker valido.

### Metricas

- Baseline antes da correcao:
  - teste direcionado falhou com excecao `TypeError` em `/workers/status`;
  - endpoint nao retornava diagnostico quando havia item malformado na lista.
- Depois da correcao:
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q qa/test_workers_status_contract.py::test_workers_status_endpoint_ignores_malformed_worker_items`: 1 passed;
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q qa/test_workers_status_contract.py`: 4 passed;
  - `backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/app/api/v1/endpoints/workers.py qa/test_workers_status_contract.py`: passou;
  - `backend\.venv\Scripts\python.exe -m py_compile backend/app/api/v1/endpoints/workers.py qa/test_workers_status_contract.py`: passou;
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_health_monitor_critical_classification.py qa/test_health_endpoint_contract.py backend/tests/unit/test_auto_healer_idempotency.py qa/test_system_endpoints_contract.py qa/test_workers_status_contract.py qa/test_dx007_quick_diagnostics_cli.py`: 34 passed.
- Criterio de aceitacao atendido:
  - registro malformado nao derruba `/workers/status`;
  - workers validos continuam visiveis;
  - quantidade de registros ignorados fica explicita;
  - `start-all` e `stop-all` usam a mesma validacao.

### Riscos e limitacoes

- O campo `ignored` altera a resposta adicionando informacao, mas preserva os campos existentes `tracked` e `workers`.
- Itens invalidos nao sao retornados individualmente por falta de identificador confiavel.
- A validacao e por TestClient local; nao foi executado fluxo real de workers em PC1/PC2.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para resiliencia do endpoint de diagnostico de workers sob corrupcao parcial simulada.

## Ciclo 24 - Shutdown cancela workers validos mesmo com registros corrompidos

### Problema

- Categoria: disponibilidade operacional, encerramento limpo e automedicacao.
- Fato observado: no shutdown da aplicacao, `backend/app/main.py` percorria `app.state.orchestrator_workers` usando `worker.get("task")`.
- Fato observado: o loop de shutdown estava dentro de um unico `try`.
- Inferencia: se um item malformado aparecesse antes de uma task valida, a excecao interromperia o loop e workers validos seguintes poderiam nao ser cancelados.
- Impacto antes: risco de deixar workers/consumidores vivos durante encerramento, reinicio ou deploy, produzindo comportamento operacional indefinido.

### Hipotese

Acredito que validar cada registro de worker no shutdown e continuar apos itens invalidos garante encerramento mais previsivel sem alterar a forma como workers validos sao cancelados.

### Implementacao

- `backend/app/main.py`:
  - adicionou `_cancel_tracked_worker_task(task)` com suporte recursivo para listas/tuplas;
  - adicionou `cancel_tracked_orchestrator_workers(raw_workers)`;
  - valida se a colecao e uma lista;
  - ignora itens nao-mapeaveis com warning estruturado `shutdown_invalid_worker_item`;
  - cancela todas as `asyncio.Task` validas ainda nao canceladas, incluindo tasks compostas em lista/tupla;
  - o shutdown passou a chamar o helper, evitando interrupcao do loop por um item corrompido.
- `qa/test_workers_status_contract.py`:
  - adicionou regressao assincrona com item malformado antes de tasks validas;
  - cobre task simples e task composta;
  - exige `cancelled == 2` e que as tasks validas tenham recebido cancelamento.

### Metricas

- Baseline antes da correcao:
  - por leitura do codigo, `worker.get("task")` em item string levantaria `AttributeError` e sairia do loop de shutdown.
- Depois da correcao:
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q qa/test_workers_status_contract.py::test_shutdown_cancels_valid_workers_after_malformed_items qa/test_workers_status_contract.py::test_workers_status_endpoint_ignores_malformed_worker_items`: 2 passed;
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q qa/test_workers_status_contract.py`: 5 passed;
  - `backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/app/main.py qa/test_workers_status_contract.py`: passou;
  - `backend\.venv\Scripts\python.exe -m py_compile backend/app/main.py qa/test_workers_status_contract.py`: passou;
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_health_monitor_critical_classification.py qa/test_health_endpoint_contract.py backend/tests/unit/test_auto_healer_idempotency.py qa/test_system_endpoints_contract.py qa/test_workers_status_contract.py qa/test_dx007_quick_diagnostics_cli.py`: 35 passed.
- Criterio de aceitacao atendido:
  - item malformado nao impede cancelamento de task valida posterior;
  - worker composto em tupla/lista tambem e cancelado;
  - cancelamento continua restrito a `asyncio.Task`;
  - falha de formato fica observavel por warning estruturado;
  - contratos de workers e Health continuam passando.

### Riscos e limitacoes

- O teste cobre o helper de shutdown, nao executa o lifespan completo da app.
- Nao foi validado em ambiente PC1/PC2 com workers reais ativos.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para corrupcao parcial simples e workers compostos no helper; media para o lifespan completo ate haver teste de shutdown integrado.

## Ciclo 25 - HealthMonitor passou a aceitar status canonicos `ok` e `error`

### Problema

- Categoria: contrato interno de Health, falso negativo operacional e automedicacao.
- Fato observado: ciclos anteriores consolidaram o contrato de servicos como `ok | degraded | error | unknown` nas superficies consumidas pelo frontend.
- Fato observado: `HealthMonitor.check_component()` interpretava o status com `HealthStatus(result.get("status", "healthy"))`, aceitando apenas `healthy | degraded | unhealthy | unknown`.
- Baseline reproduzida: um health check retornando `{"status": "ok"}` era convertido em `HealthStatus.UNHEALTHY` por excecao `ValueError: 'ok' is not a valid HealthStatus`.
- Baseline reproduzida: um health check retornando `{"status": "error", "message": "canonical failure"}` virava erro de parsing e perdia a mensagem operacional original.
- Inferencia: checks que adotassem o contrato canonico novo poderiam gerar falso `unhealthy` no monitor central, afetando `/health`, observability e automedicacao.

### Hipotese

Acredito que normalizar aliases de status dentro do `HealthMonitor` elimina falso negativo para `ok` e preserva semantica de falha para `error`, sem alterar o score agregado.

### Implementacao

- `backend/app/core/monitoring/health_monitor.py`:
  - adicionou `HEALTH_STATUS_ALIASES`;
  - adicionou `normalize_health_status(raw_status)`;
  - mapeia `ok`, `operational`, `up`, `ready` para `HealthStatus.HEALTHY`;
  - mapeia `warning`, `warn`, `partial` para `HealthStatus.DEGRADED`;
  - mapeia `error`, `critical`, `down`, `failed`, `unavailable` para `HealthStatus.UNHEALTHY`;
  - valores vazios, nulos ou desconhecidos viram `HealthStatus.UNKNOWN`;
  - `check_component()` passou a usar a normalizacao antes de montar `HealthCheckResult`.
- `backend/tests/unit/test_health_monitor_critical_classification.py`:
  - adicionou regressao para `ok -> HEALTHY`;
  - adicionou regressao para `error -> UNHEALTHY` preservando a mensagem original.

### Metricas

- Baseline antes da correcao:
  - teste direcionado com `status: "ok"` falhou porque o resultado era `UNHEALTHY` e `error="'ok' is not a valid HealthStatus"`;
  - teste direcionado com `status: "error"` falhou porque a mensagem virou erro de parsing.
- Depois da correcao:
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_health_monitor_critical_classification.py::test_health_monitor_accepts_canonical_ok_status backend/tests/unit/test_health_monitor_critical_classification.py::test_health_monitor_maps_canonical_error_status_to_unhealthy`: 2 passed;
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_health_monitor_critical_classification.py`: 5 passed;
  - `backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/app/core/monitoring/health_monitor.py backend/tests/unit/test_health_monitor_critical_classification.py`: passou;
  - `backend\.venv\Scripts\python.exe -m py_compile backend/app/core/monitoring/health_monitor.py backend/tests/unit/test_health_monitor_critical_classification.py`: passou;
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_health_monitor_critical_classification.py qa/test_health_endpoint_contract.py backend/tests/unit/test_auto_healer_idempotency.py qa/test_system_endpoints_contract.py qa/test_workers_status_contract.py qa/test_dx007_quick_diagnostics_cli.py`: 37 passed.
- Criterio de aceitacao atendido:
  - `ok` nao e mais classificado como falha;
  - `error` e classificado como `UNHEALTHY` sem perder mensagem original;
  - aliases comuns tem comportamento deterministico;
  - suíte ampliada de Health continua passando.

### Riscos e limitacoes

- Valores desconhecidos viram `UNKNOWN`; dependendo do numero de componentes, o score agregado ainda pode resultar em `unhealthy`, o que e conservador.
- A normalizacao agora existe tanto no `HealthMonitor` quanto no helper de endpoints agregados; se a tabela crescer, uma consolidacao futura pode reduzir duplicacao.
- Nao foi executado cenário real de provider externo retornando esses aliases; a evidencia e unitária e por contrato.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para eliminar falso `unhealthy` por alias canonico `ok`; media para cobertura de todos os provedores reais ate observacao em ambiente integrado.

## Ciclo 26 - Componente critico sem resultado nao pode mais mascarar Health global como saudavel

### Problema

- Categoria: classificacao operacional, disponibilidade percebida e automedicacao.
- Fato observado: `HealthMonitor.get_system_health()` calcula score apenas com `last_results`.
- Fato observado: componentes criticos registrados mas ausentes em `last_results` eram tratados como `UNKNOWN` nos checks auxiliares, mas esse estado nao participava da decisao global.
- Baseline reproduzida: com `postgres` critico registrado sem resultado e `worker` nao-critico saudavel, o score era `100` e o status global retornava `healthy`.
- Inferencia: uma lacuna de telemetria em dependencia critica podia ser mascarada como saude global perfeita.
- Impacto antes: dashboards, `/health` agregado e automedicacao poderiam atrasar diagnostico quando um check critico deixasse de reportar.

### Hipotese

Acredito que tratar componente critico ausente ou `UNKNOWN` como status global minimo `degraded` preserva o score como métrica separada, mas impede falso saudavel operacional.

### Implementacao

- `backend/app/core/monitoring/health_monitor.py`:
  - adicionou calculo `critical_unknown`;
  - componentes criticos sem resultado passam a contar como `UNKNOWN` para decisao global;
  - ordem de decisao agora e:
    - critico `UNHEALTHY` => global `unhealthy`;
    - critico `DEGRADED` ou `UNKNOWN` => global `degraded`;
    - caso contrario, usa score agregado.
- `backend/tests/unit/test_health_monitor_critical_classification.py`:
  - adicionou regressao com componente critico registrado e ausente de `last_results`;
  - valida que o score pode permanecer `100`, mas o status global deve ser `degraded`.

### Metricas

- Baseline antes da correcao:
  - teste direcionado falhou com `assert 'healthy' == 'degraded'`;
  - cenario de telemetria critica ausente era publicado como saudavel.
- Depois da correcao:
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_health_monitor_critical_classification.py::test_missing_critical_component_result_prevents_global_healthy_status`: 1 passed;
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_health_monitor_critical_classification.py`: 6 passed;
  - `backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/app/core/monitoring/health_monitor.py backend/tests/unit/test_health_monitor_critical_classification.py`: passou;
  - `backend\.venv\Scripts\python.exe -m py_compile backend/app/core/monitoring/health_monitor.py backend/tests/unit/test_health_monitor_critical_classification.py`: passou;
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_health_monitor_critical_classification.py qa/test_health_endpoint_contract.py backend/tests/unit/test_auto_healer_idempotency.py qa/test_system_endpoints_contract.py qa/test_workers_status_contract.py qa/test_dx007_quick_diagnostics_cli.py`: 38 passed.
- Criterio de aceitacao atendido:
  - componente critico sem resultado nao permite status global `healthy`;
  - score agregado permanece explicito e nao e falsificado;
  - regra de severidade para criticos continua priorizando `UNHEALTHY` sobre `DEGRADED/UNKNOWN`;
  - suíte ampliada de Health continua passando.

### Riscos e limitacoes

- A mudanca pode aumentar alertas `degraded` quando um check critico estiver registrado mas ainda nao executado. Isso e intencionalmente conservador para evitar falso saudavel.
- Nao foi executado teste de ciclo completo do monitor periodico; a evidencia cobre a agregacao deterministica.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para impedir falso saudavel por telemetria critica ausente; media para impacto operacional de alertas ate observacao em ambiente integrado.

## Ciclo 27 - `/health` passou a expor checks criticos ainda sem resultado

### Problema

- Categoria: contrato de deploy, disponibilidade percebida e diagnostico raiz.
- Fato observado: o Ciclo 26 corrigiu `HealthMonitor.get_system_health()`, mas a rota raiz `/health` mantinha agregacao propria em `backend/app/main.py`.
- Fato observado: `_get_dependency_health()` montava `dependencies.checks` apenas a partir de `monitor.last_results`.
- Baseline reproduzida: com `postgres` critico registrado sem resultado e kernel `HEALTHY`, `/health` retornava `status: "healthy"`.
- Fato observado adicional: apos incluir o check ausente como `unknown`, a logica antiga de `/health` promovia qualquer critico nao-healthy para `critical`, divergindo do `HealthMonitor`, que trata `UNKNOWN/DEGRADED` como `degraded`.
- Inferencia: deploys e health checks externos podiam receber falso saudavel ou severidade excessiva por semantica divergente da rota raiz.

### Hipotese

Acredito que incluir checks registrados sem resultado como `unknown` e alinhar a severidade de `/health` com o `HealthMonitor` elimina falso saudavel sem transformar telemetria ausente em falha critica total.

### Implementacao

- `backend/app/main.py`:
  - `_get_dependency_health()` agora inicializa `checks` com todos os `monitor.health_checks` registrados como `unknown`;
  - resultados reais de `monitor.last_results` continuam sobrescrevendo o placeholder;
  - `/health` agora diferencia crítico `unhealthy` de crítico `degraded/unknown`;
  - crítico `unhealthy` gera `status: "critical"`;
  - crítico `degraded` ou `unknown` gera `status: "degraded"`.
- `qa/test_health_endpoint_contract.py`:
  - adicionou regressao direta para `/health`;
  - simula kernel `HEALTHY`, monitor com `postgres` critico registrado e sem resultado;
  - exige `response["status"] == "degraded"` e `dependencies.postgres.status == "unknown"`.

### Metricas

- Baseline antes da correcao:
  - teste direcionado falhou com `assert 'healthy' == 'degraded'`;
  - apos primeira etapa da correcao, a rota retornava `critical`, evidenciando divergencia de severidade.
- Depois da correcao:
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q qa/test_health_endpoint_contract.py::test_root_health_reports_degraded_when_critical_check_is_missing`: 1 passed;
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q qa/test_health_endpoint_contract.py`: 5 passed;
  - `backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/app/main.py qa/test_health_endpoint_contract.py`: passou;
  - `backend\.venv\Scripts\python.exe -m py_compile backend/app/main.py qa/test_health_endpoint_contract.py`: passou;
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_health_monitor_critical_classification.py qa/test_health_endpoint_contract.py backend/tests/unit/test_auto_healer_idempotency.py qa/test_system_endpoints_contract.py qa/test_workers_status_contract.py qa/test_dx007_quick_diagnostics_cli.py`: 39 passed.
- Criterio de aceitacao atendido:
  - `/health` nao mascara check critico ausente como saudavel;
  - `/health` expoe o componente critico ausente no payload;
  - semantica de severidade fica alinhada ao `HealthMonitor`;
  - contratos de Health existentes continuam passando.

### Riscos e limitacoes

- Como no Ciclo 26, ambientes logo apos startup podem aparecer como `degraded` ate os checks criticos reportarem pela primeira vez. Este comportamento e conservador e operacionalmente mais honesto que `healthy`.
- A regressao chama a funcao `health()` diretamente; nao executa uma requisicao ASGI com middleware completo.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para contrato direto da rota raiz; media para comportamento de startup real ate validar em ambiente integrado.

## Ciclo 28 - HealthMonitor passou a iniciar o loop continuo de forma idempotente

### Problema

- Categoria: disponibilidade operacional, desempenho e automedicacao.
- Fato observado: `HealthMonitor.start_monitoring()` sempre criava uma nova `asyncio.Task`.
- Baseline reproduzida: duas chamadas consecutivas geravam duas tasks pendentes diferentes para o mesmo loop de monitoramento.
- Inferencia: chamadas repetidas poderiam duplicar health checks periodicos, escritas de metricas Prometheus, logs e carga sobre dependencias.
- Impacto antes: risco de ruido operacional e diagnostico instavel por multiplos loops concorrentes de Health.

### Hipotese

Acredito que tornar `start_monitoring()` idempotente enquanto uma task ativa existir elimina duplicacao de loops sem impedir reinicio explicito apos `stop_monitoring()`.

### Implementacao

- `backend/app/core/monitoring/health_monitor.py`:
  - `start_monitoring()` agora retorna a task existente quando `_monitoring_task` ainda esta ativa;
  - registra `health_monitor_already_running` nesse caminho;
  - ao criar um novo loop, retorna a task criada;
  - `stop_monitoring()` cancela a task e limpa `_monitoring_task`, permitindo novo start explicito.
- `backend/tests/unit/test_health_monitor_critical_classification.py`:
  - adicionou regressao assíncrona para duas chamadas consecutivas de `start_monitoring()`;
  - valida que ambas preservam a mesma task ativa;
  - cancela e aguarda a task no `finally` para nao deixar loop pendente.

### Metricas

- Baseline antes da correcao:
  - teste direcionado falhou com duas tasks diferentes: `Task-2` e `Task-3`;
  - a segunda chamada sobrescrevia `_monitoring_task`, deixando a primeira ainda pendente.
- Depois da correcao:
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_health_monitor_critical_classification.py::test_health_monitor_start_monitoring_is_idempotent`: 1 passed;
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_health_monitor_critical_classification.py`: 7 passed;
  - `backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/app/core/monitoring/health_monitor.py backend/tests/unit/test_health_monitor_critical_classification.py`: passou;
  - `backend\.venv\Scripts\python.exe -m py_compile backend/app/core/monitoring/health_monitor.py backend/tests/unit/test_health_monitor_critical_classification.py`: passou;
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_health_monitor_critical_classification.py qa/test_health_endpoint_contract.py backend/tests/unit/test_auto_healer_idempotency.py qa/test_system_endpoints_contract.py qa/test_workers_status_contract.py qa/test_dx007_quick_diagnostics_cli.py`: 40 passed.
- Criterio de aceitacao atendido:
  - chamada repetida nao cria segundo loop enquanto o primeiro esta ativo;
  - task existente permanece observavel e retornada;
  - `stop_monitoring()` libera reinicio explicito;
  - suíte ampliada de Health continua passando.

### Riscos e limitacoes

- O teste usa intervalo alto e task local; nao mede carga real em ambiente com checks registrados.
- Se algum chamador dependia implicitamente de sobrescrever a task sem parar a anterior, esse comportamento era inseguro e agora fica bloqueado.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para idempotencia local do loop; media para impacto operacional ate validar com monitor ativo em ambiente integrado.

## Ciclo 29 - Score agregado do HealthMonitor passou a incluir checks registrados sem resultado

### Problema

- Categoria: classificacao operacional, UX de Health e automedicacao.
- Fato observado: o Ciclo 26 impediu que componente critico ausente em `last_results` marcasse o sistema como `healthy`.
- Fato observado: `HealthMonitor.get_system_health()` ainda calculava `score`, `message`, `components` e `last_check` somente a partir de `last_results`.
- Baseline reproduzida: com `postgres` critico registrado sem resultado e `worker` nao-critico saudavel, o monitor retornava `status: "degraded"`, mas `score: 100` e nao incluia `postgres` em `components`.
- Baseline adicional: com checks registrados e nenhum resultado, o monitor retornava `status: "unknown"` e `components: {}`, omitindo que checks criticos ja estavam registrados mas sem telemetria.
- Inferencia: a UI e a automedicacao poderiam receber um status conservador, mas acompanhado de score e inventario inconsistentes, reduzindo a capacidade de diagnostico do usuario.

### Hipotese

Acredito que calcular o agregado sobre `health_checks registrados + last_results reais`, preenchendo lacunas como `unknown`, torna score, mensagem e payload coerentes com a severidade global sem executar checks extras nem criar dependencia nova.

### Implementacao

- `backend/app/core/monitoring/health_monitor.py`:
  - adicionou `_unknown_result(component)`;
  - adicionou `_effective_results()`;
  - `get_system_health()` passou a usar resultados efetivos para `score`, `message`, `components`, `last_check` e classificacao de criticos;
  - resultados reais continuam sobrescrevendo placeholders `unknown`.
- `backend/tests/unit/test_health_monitor_critical_classification.py`:
  - atualizou a regressao de componente critico ausente para exigir `score: 50`;
  - passou a exigir que o componente ausente apareca em `components` como `unknown`;
  - adicionou regressao para checks registrados sem nenhum resultado.

### Metricas

- Baseline antes da correcao:
  - cenario `postgres` critico ausente + `worker` saudavel retornava `score: 100`;
  - o payload nao mostrava o componente critico ausente em `components`;
  - checks registrados sem nenhum resultado eram omitidos do agregado.
- Depois da correcao:
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_health_monitor_critical_classification.py`: 8 passed;
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_health_monitor_critical_classification.py qa/test_health_endpoint_contract.py backend/tests/unit/test_auto_healer_idempotency.py qa/test_system_endpoints_contract.py qa/test_workers_status_contract.py qa/test_dx007_quick_diagnostics_cli.py`: 41 passed;
  - `backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/app/core/monitoring/health_monitor.py backend/tests/unit/test_health_monitor_critical_classification.py`: passou;
  - `backend\.venv\Scripts\python.exe -m py_compile backend/app/core/monitoring/health_monitor.py backend/tests/unit/test_health_monitor_critical_classification.py`: passou.
- Criterio de aceitacao atendido:
  - componente registrado sem resultado participa do score como `unknown`;
  - componente ausente aparece no payload de `components`;
  - status global continua conservador para criticos `unknown`;
  - contratos ampliados de Health, System e Workers continuam passando.

### Riscos e limitacoes

- O score fica mais baixo durante janelas iniciais antes dos primeiros checks reportarem. Essa queda e intencional porque telemetria ausente nao deve parecer saude perfeita.
- A evidencia e unit/contract local; nao mede a percepcao visual do score no HUD com backend real ativo.
- O placeholder usa `checked_at` no momento da leitura, nao o momento em que a lacuna surgiu. Isso evita `null` no contrato, mas nao substitui uma metrica historica de ausencia.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para coerencia do agregado local; media para impacto visual ate validar o HUD conectado a um backend com checks ainda pendentes.

## Ciclo 30 - Health offline deixou de poluir o console como erro recorrente de aplicacao

### Problema

- Categoria: usabilidade operacional, observabilidade frontend e experiencia central de Health.
- Fato observado: validacao no Browser do modo visitante mostrou o HUD renderizando o estado offline, mas o console acumulava mensagens `ERROR` de `SystemStatusService` enquanto o backend estava indisponivel.
- Fato observado: `frontend/src/app/core/services/system-status.service.ts` tratava falha de rede (`HttpErrorResponse.status === 0`) igual a erro HTTP real, usando `logger.error()` em cada polling.
- Inferencia: para o usuario e para QA visual, Health comunicava "Sem telemetria" na UI, mas o console sugeria erro de aplicacao recorrente. Isso reduz confianca no proprio sistema de Health.
- Impacto antes: backend desconectado, que e um estado operacional esperado e ja representado no HUD, gerava ruido de erro a cada ciclo de polling.

### Hipotese

Acredito que classificar falha de conectividade como `warn` deduplicado por janela de outage, mantendo `error` para falhas HTTP reais, melhora a interpretabilidade do Health sem esconder defeitos de backend ou contrato.

### Implementacao

- `frontend/src/app/core/services/system-status.service.ts`:
  - passou a importar `HttpErrorResponse`;
  - adicionou estado interno `statusConnectivityWarningActive` e `healthConnectivityWarningActive`;
  - adicionou `isConnectivityFailure(err)`;
  - adicionou `reportPollingFailure(...)`;
  - falha de conectividade no polling de status/servicos agora registra `warn` apenas uma vez por periodo de falha;
  - respostas bem-sucedidas resetam a deduplicacao;
  - falhas HTTP reais continuam usando `logger.error()`.
- `frontend/src/app/core/services/system-status.spec.ts`:
  - adicionou regressao para `status 0` no endpoint de Health: deve emitir `warn`, retornar `{ services: [] }` e nao chamar `error`;
  - adicionou regressao para HTTP 500: deve continuar chamando `error`.

### Metricas

- Baseline antes da correcao:
  - Browser em `http://127.0.0.1:4200/` mostrava HUD offline, mas console continha entradas recorrentes `[ERROR] [SystemStatusService] Erro ao buscar saude dos servicos`;
  - o servico nao diferenciava indisponibilidade de rede de erro HTTP real.
- Depois da correcao:
  - `npm run test -- --run src/app/core/services/system-status.spec.ts`: 7 passed;
  - `npm run test -- --run src/app/core/services/system-status.spec.ts src/app/shared/components/ui/system-hud/system-hud.spec.ts src/app/features/observability/widgets/system-status-widget/system-status-widget.spec.ts`: 14 passed;
  - `npm run lint`: passou;
  - `npx ng build --configuration development`: passou.
- Criterio de aceitacao atendido:
  - backend desconectado vira `warn`, nao `error`;
  - falha HTTP real continua sendo erro;
  - HUD e widget de Observability continuam consumindo o servico compartilhado;
  - build Angular continua valido.

### Riscos e limitacoes

- A deduplicacao e em memoria do servico Angular; reload da pagina reinicia o aviso.
- A validacao renderizada que originou o baseline foi feita antes da correcao; a pos-correcao foi validada por testes, lint e build, nao por nova captura de console em navegador.
- A mudanca reduz ruido de console, mas nao resolve a indisponibilidade do backend nem falhas ja existentes de `process is not defined` observadas anteriormente.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para classificacao de falha de conectividade no servico compartilhado; media para percepcao final ate nova verificacao visual com servidor dev refletindo o bundle atualizado.

## Ciclo 31 - Frontend de Health passou a normalizar payload malformado antes de atualizar o HUD

### Problema

- Categoria: robustez de contrato frontend, UX de Health e disponibilidade percebida.
- Fato observado: `SystemStatusService.getServicesHealth()` assumia que a resposta do backend sempre teria `services: ServiceHealthItem[]`.
- Fato observado: o codigo lia `response.services.length` e `response.services.every(...)` sem validar a forma do payload.
- Baseline reproduzida: payload `{ status: "ok" }` nao representava servicos e podia quebrar o fluxo do HUD ou cair em tratamento generico de erro.
- Baseline reproduzida: item com `status: "operational"` e campos nao-string nao era normalizado na borda e poderia chegar ao HUD como estado nao reconhecido.
- Fato observado adicional: no polling de `/system/status`, a correcao do Ciclo 30 ainda resetava a flag de warning apos emitir fallback, porque o `map` externo rodava tambem para a resposta sintetica de erro.
- Inferencia: o Health visto pelo usuario ainda dependia de um backend perfeito; em falha parcial de contrato, poderia gerar console ruidoso, estado visual inconsistente ou falso saudavel.

### Hipotese

Acredito que normalizar o contrato no `SystemStatusService`, antes de atualizar `isSystemHealthy$` ou entregar dados ao HUD, torna a interface resistente a payloads parciais e impede falso saudavel sem criar uma camada nova.

### Implementacao

- `frontend/src/app/core/services/system-status.service.ts`:
  - adicionou `normalizeServiceHealthResponse(response)`;
  - adicionou `normalizeServiceHealthItem(item, index)`;
  - adicionou `normalizeServiceStatus(rawStatus)`;
  - adicionou `readNonEmptyString(value)`;
  - lista `services` ausente ou nao-array vira `[]`;
  - item sem `key` recebe `service-{n}`;
  - item sem `name` recebe `Servico sem nome`;
  - status fora de `ok | degraded | error | unknown` vira `unknown`;
  - `metric_text` nao-string vira `undefined`;
  - `isSystemHealthy$` agora e calculado sobre a resposta normalizada;
  - reset da deduplicacao de conectividade de `/system/status` foi movido para resposta HTTP real, antes do `catchError`, evitando reset por fallback sintetico.
- `frontend/src/app/core/services/system-status.spec.ts`:
  - adicionou regressao para payload sem lista de servicos;
  - adicionou regressao para item malformado que deve virar `unknown`;
  - adicionou regressao para o fluxo real de `retry(1)` do status, exigindo apenas um warning para duas falhas consecutivas.

### Metricas

- Baseline antes da correcao:
  - payload sem `services` nao tinha normalizacao defensiva;
  - item com status desconhecido podia atravessar o servico sem classificacao segura;
  - fallback de `/system/status` limpava a flag de outage e permitia warning repetido em polls futuros.
- Depois da correcao:
  - `npm run test -- --run src/app/core/services/system-status.spec.ts`: 10 passed;
  - `npm run test -- --run src/app/core/services/system-status.spec.ts src/app/shared/components/ui/system-hud/system-hud.spec.ts src/app/features/observability/widgets/system-status-widget/system-status-widget.spec.ts`: 17 passed;
  - `npm run lint`: passou;
  - `npx ng build --configuration development`: passou.
- Criterio de aceitacao atendido:
  - payload sem `services` vira estado sem telemetria, nao excecao;
  - item malformado vira `unknown` e impede falso saudavel;
  - warning de conectividade do status e deduplicado no fluxo com retry;
  - HUD e widget de Observability continuam compativeis.

### Riscos e limitacoes

- A normalizacao frontend nao substitui contrato backend; payload malformado ainda deve ser investigado na origem se ocorrer em producao.
- Status alias como `operational` foi tratado como `unknown`, nao como `ok`, por decisao conservadora na UI.
- A validacao e por testes unitarios/build; nao foi repetida uma captura visual no Browser apos a alteracao.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para robustez do servico compartilhado de Health; media para cobertura de todos os formatos futuros de backend ate haver contrato schema compartilhado.

## Ciclo 32 - Telemetria de memoria nao finita deixou de derrubar `/system/health/services`

### Problema

- Categoria: disponibilidade do Health, robustez de telemetria e experiencia operacional.
- Fato observado: `backend/app/services/system_health_service.py` convertia `memory_usage_mb` com `float(...)` e depois montava `metric_text` com `int(round(mem_mb))`.
- Baseline reproduzida: quando `OptimizationService.analyze_system()` retornava `memory_usage_mb: "NaN"`, `/api/v1/system/health/services` respondia `400 Bad Request` com `cannot convert float NaN to integer`.
- Inferencia: uma leitura invalida de telemetria de memoria podia derrubar o endpoint agregado de Health inteiro, ocultando tambem Agent, Knowledge e LLM.
- Impacto antes: o HUD e a tela de Observability poderiam perder todo o inventario de Health por causa de um unico valor numerico nao finito.

### Hipotese

Acredito que aceitar apenas floats finitos para memoria e tratar `NaN`/`inf` como telemetria indisponivel preserva disponibilidade do endpoint e comunica incerteza sem inventar uso de memoria.

### Implementacao

- `backend/app/services/system_health_service.py`:
  - adicionou `math`;
  - adicionou `_finite_float_or_none(value)`;
  - leituras de `memory_usage_mb` vindas de `analyze_system()` e `get_metrics_history()` agora retornam `None` quando o valor nao e finito ou nao e conversivel;
  - `None` continua usando o contrato existente de `Memory Service` como `status: "unknown"` e `metric_text: "Uso: indisponivel"`.
- `qa/test_system_endpoints_contract.py`:
  - adicionou regressao para `memory_usage_mb: "NaN"`;
  - exige HTTP 200 e memoria `unknown`.

### Metricas

- Baseline antes da correcao:
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q qa/test_system_endpoints_contract.py::TestSystemEndpointsContract::test_get_services_health_reports_unknown_memory_for_non_finite_telemetry`: falhou com `assert 400 == 200`;
  - log da falha: `cannot convert float NaN to integer`.
- Depois da correcao:
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q qa/test_system_endpoints_contract.py::TestSystemEndpointsContract::test_get_services_health_reports_unknown_memory_for_non_finite_telemetry`: 1 passed;
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_health_monitor_critical_classification.py qa/test_health_endpoint_contract.py backend/tests/unit/test_auto_healer_idempotency.py qa/test_system_endpoints_contract.py qa/test_workers_status_contract.py qa/test_dx007_quick_diagnostics_cli.py`: 42 passed;
  - `backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/app/services/system_health_service.py qa/test_system_endpoints_contract.py`: passou;
  - `backend\.venv\Scripts\python.exe -m py_compile backend/app/services/system_health_service.py qa/test_system_endpoints_contract.py`: passou.
- Criterio de aceitacao atendido:
  - valor `NaN` nao derruba o endpoint;
  - memoria invalida vira `unknown`;
  - demais servicos continuam retornando no payload;
  - contratos ampliados de Health/System/Workers continuam passando.

### Riscos e limitacoes

- A correcao nao distingue a origem do valor nao finito; ela classifica como telemetria indisponivel.
- O teste cobre `NaN`; `inf` e valores nao numericos usam o mesmo helper, mas nao foram todos enumerados individualmente.
- Nao foi executado teste com telemetria real de processo retornando valor nao finito, apenas dublagem do `OptimizationService`.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para impedir queda do endpoint por `NaN`; media para cobertura de todas as fontes reais de telemetria ate validar com dados operacionais.

## Ciclo 33 - Health de memoria passou a usar historico valido quando snapshot atual nao e finito

### Problema

- Categoria: qualidade de telemetria, UX de Health e robustez de falha parcial.
- Fato observado: apos o Ciclo 32, `backend/app/services/system_health_service.py` rejeitava `memory_usage_mb` nao finito vindo de `OptimizationService.analyze_system()`, mas retornava `None` imediatamente.
- Fato observado: quando `analyze_system()` retornava `memory_usage_mb: "NaN"` e `get_metrics_history(limit=1)` tinha `memory_usage_mb = 2048.0`, `/api/v1/system/health/services` classificava memoria como `unknown`.
- Baseline reproduzida: o teste focado falhou com `assert 'unknown' == 'ok'`.
- Inferencia: o Health visto pelo usuario perdia uma medicao valida ja disponivel e comunicava incerteza maior do que a evidenciada pelos dados.

### Hipotese

Acredito que validar o snapshot atual e, quando ele nao for finito, consultar o ultimo historico finito melhora a fidelidade do Health sem esconder a falha do snapshot atual, porque o sistema ainda retorna `unknown` quando nao existe historico valido.

### Implementacao

- `backend/app/services/system_health_service.py`:
  - `_read_memory_usage_mb()` passou a tentar o historico quando o snapshot atual existe mas nao e finito;
  - `_read_memory_usage_mb_from_history()` centraliza a leitura do ultimo item historico;
  - o mesmo helper `_finite_float_or_none(value)` continua impedindo `NaN`, `inf` ou valores nao numericos de virarem metrica exibida.
- `qa/test_system_endpoints_contract.py`:
  - adicionou regressao para snapshot atual `NaN` com historico valido;
  - exige memoria `ok` e `metric_text: "Uso: 2048MB"`;
  - manteve a regressao do Ciclo 32 para o caso sem historico valido, que deve continuar `unknown`.

### Metricas

- Baseline antes da correcao:
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q qa/test_system_endpoints_contract.py::TestSystemEndpointsContract::test_get_services_health_falls_back_to_history_when_memory_snapshot_is_non_finite`: falhou com `assert 'unknown' == 'ok'`.
- Depois da correcao:
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q qa/test_system_endpoints_contract.py::TestSystemEndpointsContract::test_get_services_health_reports_unknown_memory_for_non_finite_telemetry qa/test_system_endpoints_contract.py::TestSystemEndpointsContract::test_get_services_health_falls_back_to_history_when_memory_snapshot_is_non_finite`: 2 passed;
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_health_monitor_critical_classification.py qa/test_health_endpoint_contract.py backend/tests/unit/test_auto_healer_idempotency.py qa/test_system_endpoints_contract.py qa/test_workers_status_contract.py qa/test_dx007_quick_diagnostics_cli.py`: 43 passed;
  - `backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/app/services/system_health_service.py qa/test_system_endpoints_contract.py`: passou;
  - `backend\.venv\Scripts\python.exe -m py_compile backend/app/services/system_health_service.py qa/test_system_endpoints_contract.py`: passou.
- Criterio de aceitacao atendido:
  - snapshot `NaN` nao derruba o endpoint;
  - snapshot `NaN` com historico valido usa o historico;
  - snapshot `NaN` sem historico valido continua `unknown`;
  - contratos ampliados de Health/System/Workers continuam passando.

### Riscos e limitacoes

- O valor historico pode estar ligeiramente defasado; esta e uma decisao de engenharia aceitavel para exibir a ultima evidencia valida, nao uma garantia de valor em tempo real.
- A correcao usa apenas o ultimo ponto de historico; nao tenta interpolar nem estimar memoria.
- Nao foi adicionada metrica explicita indicando que houve fallback de snapshot para historico; isso pode ser avaliado em ciclo futuro se a operacao precisar auditar essa frequencia.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para preservar disponibilidade e fidelidade basica do Health de memoria sob snapshot nao finito; media para frescor operacional do valor historico ate haver timestamp exposto no contrato.

## Ciclo 34 - `/system/overview` passou a degradar parcialmente quando o status do sistema falha

### Problema

- Categoria: disponibilidade do Health, UX operacional e tolerancia a falha parcial.
- Fato observado: `backend/app/api/v1/endpoints/system_overview.py` executava `system_status_service.get_system_status()` dentro de um `try` que englobava todo o endpoint.
- Fato observado: uma excecao local nessa coleta retornava `503 Service Unavailable` para `/api/v1/system/overview`, mesmo quando `services_status` e `workers_status` ainda poderiam ser montados.
- Baseline reproduzida: ao simular `system_status_service.get_system_status()` levantando `RuntimeError("system status unavailable")`, o teste focado recebeu `503`, nao payload parcial.
- Inferencia: a tela de Health podia perder a visao inteira por falha de uma subcoleta local, reduzindo a capacidade do usuario de diagnosticar o proprio problema.

### Hipotese

Acredito que isolar a falha de `system_status` e retornar um `SystemStatus` degradado com campos minimos preserva a experiencia central do Health, porque o usuario continua vendo servicos e workers enquanto a falha de status local fica explicita.

### Implementacao

- `backend/app/api/v1/endpoints/system_overview.py`:
  - adicionou `_build_system_status(now)`;
  - `system_status_service.get_system_status()` agora e protegido por fallback local;
  - em falha, o overview retorna `status: "DEGRADED"`, timestamp atual, identificadores de app/versao/ambiente e metricas de performance como `None`;
  - `services_status` e `workers_status` continuam sendo montados no mesmo request.
- `qa/test_system_endpoints_contract.py`:
  - adicionou regressao simulando falha de `system_status_service.get_system_status()`;
  - exige HTTP 200, `system_status.status == "DEGRADED"`, performance indisponivel e preservacao de `services_status`/`workers_status`.

### Metricas

- Baseline antes da correcao:
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q qa/test_system_endpoints_contract.py::TestSystemEndpointsContract::test_get_system_overview_degrades_when_system_status_fails`: falhou com `assert 503 == 200`.
- Depois da correcao:
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q qa/test_system_endpoints_contract.py::TestSystemEndpointsContract::test_get_system_overview_degrades_when_system_status_fails`: 1 passed;
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_health_monitor_critical_classification.py qa/test_health_endpoint_contract.py backend/tests/unit/test_auto_healer_idempotency.py qa/test_system_endpoints_contract.py qa/test_workers_status_contract.py qa/test_dx007_quick_diagnostics_cli.py`: 44 passed;
  - `backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/app/api/v1/endpoints/system_overview.py qa/test_system_endpoints_contract.py`: passou;
  - `backend\.venv\Scripts\python.exe -m py_compile backend/app/api/v1/endpoints/system_overview.py qa/test_system_endpoints_contract.py`: passou.
- Criterio de aceitacao atendido:
  - falha isolada em `system_status` nao derruba o overview;
  - falha fica visivel como `DEGRADED`;
  - servicos e workers continuam visiveis ao usuario;
  - contratos consolidados de Health/System/Workers continuam passando.

### Riscos e limitacoes

- O fallback nao inclui detalhes da excecao no payload por decisao de seguranca e estabilidade de contrato; a evidencia fica em log estruturado.
- `uptime_seconds`, `system`, `process` e `config` ficam indisponiveis quando a coleta local falha.
- O endpoint ainda pode retornar 503 se a montagem do payload inteiro falhar fora dos blocos tolerantes; ciclos futuros podem reduzir esse acoplamento por subsecao.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para falha isolada de `system_status`; media para resiliencia total do overview ate isolar tambem validacoes finais de modelo e outras fontes agregadas.

## Ciclo 35 - `/system/status` passou a responder degradado quando a coleta local falha

### Problema

- Categoria: disponibilidade do Health, experiencia central do usuario e robustez de contrato.
- Fato observado: `backend/app/api/v1/endpoints/system_status.py` chamava `system_status_service.get_system_status()` sem tratamento local de erro.
- Fato observado: se a coleta local de status levantasse excecao, a excecao atravessava a pilha ASGI e a requisicao de `/api/v1/system/status` falhava.
- Baseline reproduzida: ao simular `RuntimeError("system status unavailable")`, o teste focado falhou antes de receber resposta HTTP valida.
- Inferencia: o frontend que consome `/system/status` podia perceber o backend como offline por falha local de telemetria, mesmo com a API ainda capaz de responder.

### Hipotese

Acredito que retornar um `StatusResponse` degradado, com campos minimos e metricas indisponiveis, preserva a comunicacao de Health ao usuario sem mascarar a falha real de coleta.

### Implementacao

- `backend/app/api/v1/endpoints/system_status.py`:
  - adicionou `_degraded_status_response(now)`;
  - protegeu `system_status_service.get_system_status()` com `try/except`;
  - em falha, registra `system_status_collection_unavailable` e retorna `status: "DEGRADED"`;
  - mantem `app_name`, `version`, `environment`, `timestamp` e explicita `cpu_percent`/`memory_percent` como `None`.
- `qa/test_system_endpoints_contract.py`:
  - adicionou regressao para `/api/v1/system/status` quando a coleta local falha;
  - exige HTTP 200, `status: "DEGRADED"` e performance indisponivel.

### Metricas

- Baseline antes da correcao:
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q qa/test_system_endpoints_contract.py::TestSystemEndpointsContract::test_get_system_status_degrades_when_status_collection_fails`: falhou com excecao propagada por `RuntimeError("system status unavailable")`.
- Depois da correcao:
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q qa/test_system_endpoints_contract.py::TestSystemEndpointsContract::test_get_system_status_degrades_when_status_collection_fails`: 1 passed;
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_health_monitor_critical_classification.py qa/test_health_endpoint_contract.py backend/tests/unit/test_auto_healer_idempotency.py qa/test_system_endpoints_contract.py qa/test_workers_status_contract.py qa/test_dx007_quick_diagnostics_cli.py`: 45 passed;
  - `backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/app/api/v1/endpoints/system_status.py qa/test_system_endpoints_contract.py`: passou;
  - `backend\.venv\Scripts\python.exe -m py_compile backend/app/api/v1/endpoints/system_status.py qa/test_system_endpoints_contract.py`: passou.
- Criterio de aceitacao atendido:
  - falha local de coleta nao derruba `/system/status`;
  - o endpoint comunica estado degradado;
  - o contrato permanece serializavel e compativel com o frontend;
  - matriz consolidada de Health/System/Workers permanece verde.

### Riscos e limitacoes

- O payload degradado nao expoe a excecao ao cliente por decisao de seguranca; a investigacao depende de log estruturado.
- A solucao nao corrige a causa raiz da falha em `system_status_service`; ela impede que a falha destrua o contrato de Health.
- Ainda ha duplicacao conceitual entre fallback de `/system/status` e `/system/overview`; uma futura consolidacao pode reduzir esse custo, mas nao foi necessaria para a correcao atual.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para disponibilidade do endpoint direto de status sob falha local de coleta; media para todos os cenarios de telemetria malformada ate adicionar normalizacao numerica no proprio `SystemStatusService`.

## Ciclo 36 - HUD de Health deixou de exibir uptime falso quando a telemetria esta indisponivel

### Problema

- Categoria: UX operacional de Health, fidelidade de telemetria e contrato frontend/backend.
- Fato observado: os Ciclos 34 e 35 passaram a permitir `uptime_seconds: null` em respostas degradadas do backend.
- Fato observado: `frontend/src/app/core/services/system-status.service.ts` ainda tipava `uptime_seconds` como `number` e, no fallback offline do frontend, sintetizava `uptime_seconds: 0`.
- Baseline reproduzida em teste: com `uptime_seconds: null`, o HUD nao exibia `uptime indisponivel`; renderizava um sufixo incompleto como `s uptime`.
- Baseline visual no browser: com backend desconectado, o HUD mostrava `0s uptime`, comunicando falso tempo de atividade mesmo em modo offline.
- Inferencia: o usuario via um sinal operacional enganoso exatamente no estado em que o Health deveria comunicar incerteza.

### Hipotese

Acredito que tratar uptime ausente como `null` no contrato frontend e formatar explicitamente valores nulos/invalidos como indisponiveis melhora a confiabilidade percebida do Health sem criar novo endpoint ou nova camada.

### Implementacao

- `frontend/src/app/core/services/system-status.service.ts`:
  - `SystemStatusResponse.uptime_seconds` passou a aceitar `number | null`;
  - fallback offline de `/system/status` agora retorna `uptime_seconds: null`, nao `0`.
- `frontend/src/app/shared/components/ui/system-hud/system-hud.ts` e `.html`:
  - adicionou `formatUptime(seconds)`;
  - `null`, `undefined`, `NaN`, infinito e valores negativos viram `uptime indisponivel`;
  - valores numericos validos continuam aparecendo como `{n}s uptime`.
- `frontend/src/app/features/observability/widgets/system-status-widget/system-status-widget.ts`:
  - `formatUptime` passou a aceitar `null` sem quebrar o build Angular.
- Testes:
  - `system-status.spec.ts` exige `uptime_seconds: null` no fallback offline;
  - `system-hud.spec.ts` exige `uptime indisponivel` para status degradado sem uptime;
  - `system-status-widget.spec.ts` cobre uptime nulo e status degradado no widget.

### Metricas

- Baseline antes da correcao:
  - `npm run test -- --run src/app/shared/components/ui/system-hud/system-hud.spec.ts`: falhou com `expected ... to contain 'uptime indisponivel'`;
  - validacao visual no Browser mostrou `0s uptime` no HUD em backend offline.
- Depois da correcao:
  - `npm run test -- --run src/app/shared/components/ui/system-hud/system-hud.spec.ts`: 6 passed;
  - `npm run test -- --run src/app/core/services/system-status.spec.ts src/app/shared/components/ui/system-hud/system-hud.spec.ts src/app/features/observability/widgets/system-status-widget/system-status-widget.spec.ts`: 19 passed;
  - `npm run lint`: passou;
  - `npx ng build --configuration development`: passou;
  - Browser em `http://127.0.0.1:4200/`: HUD abriu com `uptime indisponivel` e sem overlay de framework.
- Criterio de aceitacao atendido:
  - fallback offline nao inventa uptime;
  - HUD nao mostra `0s uptime` quando o backend esta desconectado;
  - status degradado com uptime nulo nao quebra build nem testes;
  - widget de Observability continua compilando com o novo contrato.

### Riscos e limitacoes

- A validacao renderizada ocorreu com backend desconectado e modo visitante; nao cobre estado autenticado com backend real.
- O console do browser ainda continha erros/warnings antigos de backend offline e `process is not defined`; estes nao foram introduzidos por esta correcao e permanecem como candidatos a ciclos futuros.
- O texto do widget de Observability permanece `N/A`, enquanto o HUD usa `uptime indisponivel`; isso e aceitavel por densidade de UI, mas pode ser padronizado depois.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para o HUD em modo offline/degradado; media para todos os fluxos autenticados ate validar com backend real conectado.

## Ciclo 37 - Polling de Health deixou de duplicar erro global de HTTP no console

### Problema

- Categoria: usabilidade operacional, ruido de observabilidade frontend e experiencia de Health.
- Fato observado: `SystemStatusService` ja tratava falhas de conectividade de `/system/status` e `/system/health/services` como estado offline/degradado, com warning deduplicado.
- Fato observado: `errorLoggerInterceptor` ainda registrava todo `HttpErrorResponse` como `[HTTP ERROR]`, inclusive os erros esperados e controlados pelo polling de Health.
- Baseline reproduzida: uma requisicao com contexto de erro controlado ainda gerava `logger.warn('[HTTP ERROR]', ...)`.
- Evidencia visual anterior: o Browser exibia muitos `[HTTP ERROR]` junto do HUD offline, dificultando separar falha esperada de polling de falha real de aplicacao.
- Inferencia: a UI de Health podia estar correta, mas a experiencia de diagnostico seguia ruidosa e induzia a tratar backend offline esperado como erro global repetitivo.

### Hipotese

Acredito que permitir opt-out explicito do log global por `HttpContextToken`, aplicado somente aos polls de Health que ja tratam seus erros, reduz ruido sem esconder erros HTTP de outras areas.

### Implementacao

- `frontend/src/app/core/interceptors/error-logger.interceptor.ts`:
  - adicionou `SUPPRESS_HTTP_ERROR_LOG`;
  - o interceptor global preserva o comportamento padrao, mas nao emite `[HTTP ERROR]` quando o contexto da requisicao esta marcado.
- `frontend/src/app/core/services/system-status.service.ts`:
  - adicionou `healthPollingContext()`;
  - `getSystemStatus()` e `getServicesHealth()` passam `SUPPRESS_HTTP_ERROR_LOG: true`;
  - o tratamento local e deduplicado de Health continua responsavel por comunicar backend offline.
- `frontend/src/app/core/interceptors/error-logger.interceptor.spec.ts`:
  - adicionou regressao para erro HTTP padrao continuar logando;
  - adicionou regressao para erro controlado por contexto nao gerar log global.
- `frontend/src/app/core/services/system-status.spec.ts`:
  - passou a verificar que os requests de status e health carregam o contexto de supressao.

### Metricas

- Baseline antes da correcao:
  - `npm run test -- --run src/app/core/interceptors/error-logger.interceptor.spec.ts`: falhou com `expected "spy" to not be called`, pois `[HTTP ERROR]` ainda era emitido para requisicao marcada como controlada.
- Depois da correcao:
  - `npm run test -- --run src/app/core/interceptors/error-logger.interceptor.spec.ts src/app/core/services/system-status.spec.ts`: 12 passed;
  - `npm run test -- --run src/app/shared/components/ui/system-hud/system-hud.spec.ts src/app/features/observability/widgets/system-status-widget/system-status-widget.spec.ts`: 9 passed;
  - `npm run lint`: passou;
  - `npx ng build --configuration development`: passou;
  - Browser em `http://127.0.0.1:4200/`: HUD abriu, exibiu `uptime indisponivel` e nao apresentou overlay de framework.
- Criterio de aceitacao atendido:
  - erros HTTP comuns continuam registrados pelo interceptor global;
  - polling de Health pode controlar seu proprio erro sem duplicar `[HTTP ERROR]`;
  - estados offline/degradados continuam visiveis no HUD;
  - build e testes de Health permanecem verdes.

### Riscos e limitacoes

- A supressao e opt-in por request; se outro servico quiser comportamento semelhante, precisa marcar explicitamente o contexto.
- A validacao de console no Browser ficou limitada porque o runtime preserva logs antigos; as entradas listadas apos reload tinham timestamps antigos e nao serviram como contagem limpa de antes/depois.
- O erro `process is not defined` visto anteriormente nao foi tratado neste ciclo porque nao ha referencia direta a `process` no codigo de app auditado; permanece candidato separado.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para reducao de ruido nos polls de Health em testes unitarios e contrato de request; media para console real ate executar em sessao limpa de browser/dev server.

## Ciclo 38 - Status do sistema passou a ser normalizado antes de chegar ao HUD

### Problema

- Categoria: robustez de contrato frontend, UX de Health e fidelidade de telemetria.
- Fato observado: `SystemStatusService.getSystemStatus()` retornava o payload de `/api/v1/system/status` sem normalizacao.
- Fato observado: se o backend retornasse `app_name: ""`, `version: null`, `environment: 42`, `status: "operational"`, `uptime_seconds: "NaN"` e `performance: "invalid"`, esses valores atravessavam diretamente para HUD/widget.
- Baseline reproduzida: o teste focado recebeu o payload cru e falhou contra o contrato esperado normalizado.
- Inferencia: uma resposta parcial ou malformada de Health podia gerar texto ruim, status inconsistente ou metrica invalida na interface do usuario.

### Hipotese

Acredito que normalizar o status geral no mesmo servico que ja normaliza `services health` reduz falsos sinais visuais e protege HUD/widget contra payloads parciais sem alterar o contrato backend.

### Implementacao

- `frontend/src/app/core/services/system-status.service.ts`:
  - adicionou `normalizeSystemStatusResponse(response)`;
  - adicionou `normalizeSystemStatus(rawStatus)`;
  - adicionou `readFiniteNonNegativeNumber(value)`;
  - adicionou `readRecord(value)`;
  - `app_name`, `version` e `environment` agora usam fallback seguro quando ausentes ou nao-string;
  - status alias `operational | ok | healthy` vira `OPERATIONAL`;
  - status `degraded | warning | unknown` vira `DEGRADED`;
  - status `error | critical | unhealthy` vira `ERROR`;
  - uptime nao numerico, nao finito ou negativo vira `null`;
  - `system`, `process` e `performance` so passam quando sao objetos simples.
- `frontend/src/app/core/services/system-status.spec.ts`:
  - adicionou regressao para payload malformado de status do sistema;
  - exige valores seguros antes de o payload chegar aos componentes.

### Metricas

- Baseline antes da correcao:
  - `npm run test -- --run src/app/core/services/system-status.spec.ts`: falhou com payload recebido cru, incluindo `version: null`, `environment: 42`, `uptime_seconds: "NaN"` e `performance: "invalid"`.
- Depois da correcao:
  - `npm run test -- --run src/app/core/services/system-status.spec.ts`: 11 passed;
  - `npm run test -- --run src/app/core/interceptors/error-logger.interceptor.spec.ts src/app/shared/components/ui/system-hud/system-hud.spec.ts src/app/features/observability/widgets/system-status-widget/system-status-widget.spec.ts`: 11 passed;
  - `npm run lint`: passou;
  - `npx ng build --configuration development`: passou;
  - Browser em `http://127.0.0.1:4200/`: HUD abriu e continuou mostrando `uptime indisponivel` no modo offline, sem overlay de framework.
- Criterio de aceitacao atendido:
  - status geral malformado nao atravessa cru para a UI;
  - uptime invalido vira indisponivel;
  - status conhecido vira canonico;
  - HUD e widget seguem compilando e renderizando.

### Riscos e limitacoes

- A normalizacao e conservadora: status desconhecido vira `DEGRADED`, nao `OPERATIONAL`.
- Campos estruturados como `system`, `process` e `performance` sao descartados quando nao sao objetos; isso evita renderizacao invalida, mas perde dados malformados para a UI.
- A validacao visual ocorreu em modo offline/visitante; nao cobre resposta real malformada vinda de backend conectado.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para protecao frontend contra payload malformado de `/system/status`; media para todos os formatos futuros ate haver schema compartilhado frontend/backend.

## Ciclo 39 - Health passou a explicar capacidade afetada, impacto ao usuario e acao recomendada

### Problema

- Categoria: UX operacional de Health, confiabilidade IA/ML e autodiagnostico.
- Fato observado: `/api/v1/system/health/services` e `/api/v1/system/overview` expunham `key`, `name`, `status` e `metric_text`, mas nao explicavam qual capacidade do Janus ficava afetada.
- Fato observado: o HUD renderizava status tecnico generico, como `Degradado` ou `Sem telemetria`, sem traduzir o impacto em chat, memoria, RAG, LLM ou automacao.
- Baseline antes da correcao: 0 de 4 servicos reportavam `capability`, `user_impact` e `recommended_action`.
- Inferencia: mesmo quando o Health estava correto tecnicamente, o usuario ainda precisava interpretar sozinho se o Janus podia conversar, usar memoria, consultar RAG ou confiar no roteador LLM.

### Hipotese

Acredito que enriquecer o contrato existente com capacidade afetada, impacto ao usuario e acao recomendada melhora a utilidade operacional do Health sem criar endpoint paralelo, porque o mesmo payload passa a responder "o que isso muda para mim?".

### Implementacao

- `backend/app/services/system_health_service.py`:
  - adicionou uma matriz explicita de impacto por servico e status;
  - cada item de Health agora recebe `capability`, `user_impact` e `recommended_action`;
  - estados `ok`, `degraded`, `error` e `unknown` foram mapeados para agente, conhecimento/RAG, memoria e LLM.
- `backend/app/api/v1/endpoints/system_status.py` e `backend/app/api/v1/endpoints/system_overview.py`:
  - modelos `ServiceHealthItem` passaram a declarar os novos campos opcionais.
- `frontend/src/app/core/services/system-status.service.ts`:
  - normalizacao preserva `capability`, `user_impact` e `recommended_action` quando presentes;
  - payloads antigos continuam compativeis com campos indefinidos.
- `frontend/src/app/shared/components/ui/system-hud/*`:
  - HUD passou a mostrar capacidade afetada, impacto ao usuario e acao recomendada;
  - fallback visual continua usando descricao generica quando o backend antigo nao enviar os campos.

### Metricas

- Baseline antes da correcao:
  - contrato de servicos tinha 0/4 itens com capacidade e impacto operacional explicitos;
  - HUD nao conseguia mostrar acao recomendada por componente.
- Depois da correcao:
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q qa/test_system_endpoints_contract.py::TestSystemEndpointsContract::test_get_services_health qa/test_system_endpoints_contract.py::TestSystemEndpointsContract::test_get_services_health_explains_user_impact_for_ai_capabilities`: 2 passed;
  - `backend\.venv\Scripts\python.exe -m py_compile backend/app/services/system_health_service.py backend/app/api/v1/endpoints/system_status.py backend/app/api/v1/endpoints/system_overview.py qa/test_system_endpoints_contract.py`: passou;
  - `backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/app/services/system_health_service.py backend/app/api/v1/endpoints/system_status.py backend/app/api/v1/endpoints/system_overview.py qa/test_system_endpoints_contract.py`: passou;
  - `npm run test -- --run src/app/core/services/system-status.spec.ts src/app/shared/components/ui/system-hud/system-hud.spec.ts`: 19 passed.
- Resultado depois: 4/4 servicos de Health passam a expor capacidade afetada, impacto ao usuario e acao recomendada.

### Riscos e limitacoes

- A matriz de impacto e deterministica e conservadora; ela nao substitui diagnostico profundo de causa raiz.
- `workers` ainda aparecem em `/system/overview`, mas nao como item proprio em `/system/health/services`; um ciclo futuro pode consolidar readiness de workers como capacidade operacional separada.
- As acoes recomendadas sao orientativas; ainda nao disparam automedicacao automaticamente.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para melhoria de compreensibilidade do Health no contrato e no HUD; media para cobertura total de capacidades IA/ML ate criar uma visao consolidada de readiness para chat, memoria, RAG, LLM local/cloud e workers.

## Ciclo 40 - Workers entraram no contrato principal de Health consumido pelo HUD

### Problema

- Categoria: disponibilidade, UX operacional de Health e risco de degradacao silenciosa.
- Fato observado: `/api/v1/system/health/services`, endpoint consumido pelo HUD, expunha agente, conhecimento, memoria e LLM, mas nao expunha workers.
- Fato observado: `/api/v1/system/overview` possuia `workers_status`, mas o HUD principal nao consumia esse contrato.
- Baseline antes da correcao: 4 capacidades em `/system/health/services`; 0 item de Health para workers no contrato principal do usuario.
- Inferencia: uma falha em workers poderia afetar ingestao, consolidacao, automacoes e tarefas async sem aparecer no indicador principal de Health.

### Hipotese

Acredito que incluir workers como capacidade explicita em `/system/health/services` reduz degradacao silenciosa porque o mesmo contrato usado pelo HUD passa a mostrar se operacoes assincronas estao ativas, paradas, desabilitadas, em erro ou sem telemetria.

### Implementacao

- `backend/app/services/system_health_service.py`:
  - adicionou matriz de impacto para `workers`;
  - adicionou classificacao de tasks em `running`, `stopped`, `disabled`, `error` e `unknown`;
  - adicionou `build_workers_health_item(raw_workers)`;
  - passou a anexar `workers` ao contrato quando o endpoint fornece o registro de workers.
- `backend/app/api/v1/endpoints/system_status.py`:
  - `/api/v1/system/health/services` agora le `request.app.state.orchestrator_workers` e inclui workers no payload.
- `backend/app/api/v1/endpoints/system_overview.py`:
  - `services_status` tambem usa a mesma classificacao de workers, alem de manter `workers_status`.
- `frontend/src/app/core/services/system-status.service.ts`:
  - contrato existente ja aceitava o novo item sem schema paralelo.
- `frontend/src/app/shared/components/ui/system-hud/system-hud.ts`:
  - adicionou rotulo visual especifico `WRK` para workers.
- `qa/test_system_endpoints_contract.py` e specs frontend:
  - adicionaram regressao para workers saudaveis e worker parado degradando o Health principal.

### Metricas

- Baseline antes da correcao:
  - `/system/health/services`: 4 itens; `workers` ausente.
  - HUD nao tinha caminho direto para mostrar disponibilidade de workers.
- Depois da correcao:
  - `/system/health/services`: 5 itens esperados em contrato de teste, incluindo `workers`.
  - Worker parado gera `workers.status == "degraded"` e metric text com `parados: 1`.
  - HUD preserva e renderiza capacidade, impacto e acao recomendada de workers.

### Validacao

- `backend\.venv\Scripts\python.exe -m py_compile backend/app/services/system_health_service.py backend/app/api/v1/endpoints/system_status.py backend/app/api/v1/endpoints/system_overview.py qa/test_system_endpoints_contract.py`: passou.
- `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q qa/test_system_endpoints_contract.py`: 20 passed.
- `backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/app/services/system_health_service.py backend/app/api/v1/endpoints/system_status.py backend/app/api/v1/endpoints/system_overview.py qa/test_system_endpoints_contract.py`: passou.
- `npm run test -- --run src/app/core/services/system-status.spec.ts src/app/shared/components/ui/system-hud/system-hud.spec.ts`: 21 passed.
- `npm run lint`: passou.
- `npx ng build --configuration development`: passou.

### Riscos e limitacoes

- A classificacao usa o registro local `app.state.orchestrator_workers`; se um worker externo nao for registrado ali, ele continuara invisivel neste contrato.
- Ausencia de workers rastreados e classificada como `degraded`, nao `error`, porque pode ser configuracao deliberada em alguns ambientes.
- A mudanca nao consulta RabbitMQ diretamente; saude de filas/DLQ permanece responsabilidade dos endpoints e widgets especificos.

### Decisao

Recomendacao: manter a correcao. Confianca: alta para expor workers no Health principal e reduzir degradacao silenciosa no HUD; media para cobertura total de todos os workers ate consolidar registro runtime e telemetria de filas em um contrato unico.
