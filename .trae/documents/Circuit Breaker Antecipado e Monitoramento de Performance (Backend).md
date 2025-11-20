## Objetivo
Aplicar bloqueio antecipado com Circuit Breaker antes da invocação do LLM e implementar logging estruturado completo de performance, mantendo compatibilidade e baixo overhead, com testes e visibilidade.

## Contexto no Código
- Chat: `janus/app/services/chat_service.py` (método `stream_message` e orquestração).
- LLM: `janus/app/services/llm_service.py` + `janus/app/repositories/llm_repository.py` + `janus/app/core/llm/llm_manager.py` (seleção e cliente de provedor).
- Observabilidade: `prometheus_fastapi_instrumentator` já ativo em `janus/app/main.py:220`.

## 1) Bloqueio Antecipado via LLMService
- Nova API em `LLMService`:
  - `select_provider(role: ModelRole, priority: ModelPriority, user_id?: str, project_id?: str) -> Dict{ provider, model }`
  - Implementar chamando `get_llm_client(...)` de `llm_manager` e retornando os metadados sem invocar o LLM.
- Circuit Breaker (CB) na camada de serviço:
  - `LLMService.is_provider_open(provider: str) -> bool` e `get_circuit_breaker_statuses()` já existem; usar como fonte autoritativa.
  - Em `ChatService.stream_message(...)`: antes da invocação, obter `{provider, model}` via `select_provider(...)`; se `is_provider_open(provider)` indicar "open", emitir `event: error { code: "CircuitOpen" }` imediatamente e abortar, sem custo computacional.
  - Em caso de sucesso, prosseguir para invocação (`invoke_llm`); em falha, atualizar CB e aplicar failover como hoje no `LLMRepository`.
- Métricas atualizadas como base de decisão: usar os CBs mantidos pelo `llm_manager`/`llm_repository` (estado e cooldown) e sinalizar transições no log.

## 2) Logging Estruturado Completo
- Em `ChatService.stream_message(...)`:
  - `trace_id`: gerar `uuid4()` no início da interação e propagar em todos os logs.
  - `ttft_ms`: medir do `start` ao primeiro `token`.
  - `latency_ms`: medir do `start` ao `done/error`.
  - `provider/model`: provenientes de `select_provider`/`invoke_llm`.
  - `retries`: contar tentativas de failover e reenvios internos (0 se nenhum).
  - Códigos de erro: `MessageTooLarge`, `TTFTTimeout`, `TotalTimeout`, `CircuitOpen`, `InvocationError`.
- Formato de log: JSON estruturado via `structlog` (já configurado) com `logger.info/warning/error` incluindo campos acima.
- Centralização: logs ficam indexáveis via stack existente; manter nível e chaves consistentes.

## 3) Testes
- Unidade (novo arquivo): `janus/tests/unit/test_llm_select_and_cb.py`
  - `LLMService.select_provider` retorna `{provider, model}` corretamente para diferentes `role/priority`.
  - CB antecipado: simular provider aberto e verificar que `ChatService.stream_message` retorna `event: error { CircuitOpen }` sem invocar o LLM.
  - Logs: validar presença de campos essenciais no logger (mock de `structlog`).
- Integração: ampliar `janus/tests/integration/test_chat_sse.py`
  - Fluxo com CB aberto (via env/estado) deve encerrar com `event: error` imediato.
  - Fluxo normal mede `protocol/ack/token/done` e `ttft/latency` presentes nos logs.

## 4) Dashboards
- Prometheus: manter métricas existentes e adicionar contadores:
  - `CHAT_CB_STATE_CHANGES{provider,state}`
  - `CHAT_TTFT_MS` (summary/histogram), `CHAT_LATENCY_MS` (summary/histogram)
  - `CHAT_ERRORS_TOTAL{code}`
- Painel simples (se necessário): página no front lê métricas agregadas dos endpoints de observabilidade já disponíveis; complementar com tabela de interações recentes (trace_id, tempos, CB hits).

## Compatibilidade e Overhead
- Compatível: sem mudança de endpoint/contrato; CB apenas antecipa decisão antes de custo da invocação.
- Baixo overhead: seleção de provider é leve; medições de tempo e logs são simples.
- Documentação: adicionar seção em Swagger/OpenAPI descrevendo campos de log e códigos de erro; documentar protocolo SSE (versão e transição `partial`→`token`).

## Passos de Implementação
1. Adicionar `select_provider` e `is_provider_open` em `LLMService`, utilizando `llm_manager.get_llm_client` sem invocar o modelo.
2. Atualizar `ChatService.stream_message` para bloquear antecipadamente com CB usando `select_provider`, gerar `trace_id`, medir `ttft/latency` e logar JSON estruturado.
3. Estender Prometheus com novas métricas de TTFT/latência/CB/erros.
4. Escrever testes unitários e ampliar integração conforme itens acima.
5. Atualizar documentação e, opcionalmente, adicionar uma visão no dashboard de UX com as novas métricas backend.

## Referências de Código
- `janus/app/services/chat_service.py` — fluxo de stream e logging.
- `janus/app/services/llm_service.py` — adicionar seleção antecipada e estado de CB.
- `janus/app/core/llm/llm_manager.py` — `get_llm_client` (seleção de provider/modelo).
- `janus/app/repositories/llm_repository.py` — failover e estado de circuitos.
