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
