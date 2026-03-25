---
tipo: dominio
dominio: backend
camada: inferencia
fonte-de-verdade: codigo
status: ativo
---

# LLM Routing e Prompts

## Objetivo
Descrever como o chat escolhe papel, provedor, prompt e caminho de execução.

## Responsabilidades
- Explicar `ModelRole`, `ModelPriority`, roteamento por intenção e fallback.
- Explicar quando o chat usa LLM direto e quando usa `ChatAgentLoop`.

## Entradas
- Prompt do usuário.
- `ModelRole` e `ModelPriority`.
- Política de tarefa inferida.
- Contexto recuperado por RAG e histórico recente.

## Saídas
- Invocação do provedor selecionado.
- Resposta com sinais de `routing`, `risk`, custo e resiliência.

## Dependências
- [[01 - Visão do Sistema/Dependências Externas]]
- [[02 - Backend/Como o Backend Pensa]]
- [[04 - Fluxos End-to-End/Conversa e Chat]]

## Roteamento por intenção
- `backend/app/services/intent_routing_service.py` classifica a mensagem em `code_generation`, `knowledge_query`, `security_audit`, `incident_response`, `deep_reasoning` ou `general`.
- A decisão contém `intent`, `risk_level`, `urgency_level`, `confidence`, `suggested_role`, `signals`, `guardrails` e alternativas.
- `resolve_role()` só muda o papel automaticamente quando:
  - `requested_role=auto`
  - ou o papel pedido é `orchestrator` e a confiança passa os thresholds configurados
  - ou há escalonamento por risco alto
- O frontend de conversa envia `selectedRole = 'orchestrator'` por padrão; logo o override depende dos thresholds de confiança, não do modo `auto`.
- Se `knowledge_space_id` ativo for resolvido, os endpoints de chat forçam `ModelRole.ORCHESTRATOR` e desabilitam a troca automática.

## Montagem de prompt
- `MessageOrchestrationService` e `StreamingService` usam `PromptBuilderService.build_prompt(persona, history, message, summary, relevant_memories)`.
- O histórico usado no REST vai até 60 mensagens recentes; no SSE, 20.
- `build_understanding_payload()` roda antes da inferência e gera o rascunho semântico que depois pode ser enriquecido por `routing`, `risk` e `confirmation`.

## Caminhos de execução
### REST (`POST /api/v1/chat/message`)
- Se a mensagem for curta, papel `orchestrator` e intenção simples, o serviço pode usar `invoke_llm()` direto no modo leve.
- Fora disso, o fluxo geral usa `ChatAgentLoop.run_loop()`.
- `ChatAgentLoop`:
  - invoca LLM com `FallbackChain`
  - procura envelope `tool_call_envelope`
  - executa tools com `ToolExecutorService`
  - aplica `PolicyEngine` para risco, quotas, confirmação e content safety
  - coleta `pending_action_id` a partir do resultado das tools

### SSE (`GET /api/v1/chat/stream/{conversation_id}`)
- O stream faz `llm.select_provider()` e `llm.invoke_llm()` diretamente no caminho geral.
- O SSE aplica circuit breaker, heartbeat, TTFT e streaming incremental, mas não entra no `ChatAgentLoop`.
- Resultado prático: stream e REST compartilham parte do grounding/prompting, porém divergem no suporte a tools e no acoplamento com RAG pós-resposta.

## Resiliência observada no código
- `LLMService` é usado com seleção de provedor, fallback e pricing.
- `StreamingService` mantém circuit breaker local por provedor e emite `CHAT_CIRCUIT_OPEN`.
- `ChatAgentLoop` possui fallback para modelo mais barato e para execução permissiva/minimal de tools.

## Provedores previstos
- OpenAI
- Gemini
- Ollama
- DeepSeek
- xAI
- OpenRouter

## Arquivos-fonte
- `backend/app/services/intent_routing_service.py`
- `backend/app/services/chat_agent_loop.py`
- `backend/app/services/chat/message_orchestration_service.py`
- `backend/app/services/chat/streaming_service.py`
- `backend/app/services/llm_service.py`
- `backend/app/repositories/llm_repository.py`
- `backend/app/core/llm/*`
- `backend/app/core/infrastructure/prompt_loader.py`
- `backend/app/core/infrastructure/advanced_prompts.py`
- `backend/app/core/infrastructure/janus_specialized_prompts.py`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Conversa e Chat]]
- [[04 - Fluxos End-to-End/Ferramentas e Sandbox]]

## Riscos/Lacunas
- O comportamento final depende de flags, thresholds e budgets espalhados entre endpoint, serviço de chat, `LLMService` e config.
- O papel efetivo no chat muda conforme confiança/risco, mas a UI padrão continua pedindo `orchestrator`; isso torna o roteamento menos visível para o operador.
- REST e SSE têm diferenças estruturais de execução, então a mesma pergunta pode produzir capacidades diferentes dependendo do transporte.
