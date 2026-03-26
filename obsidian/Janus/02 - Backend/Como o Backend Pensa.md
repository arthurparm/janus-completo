---
tipo: dominio
dominio: backend
camada: logica
fonte-de-verdade: codigo
status: ativo
---

# Como o Backend Pensa

## Objetivo
Explicar o modelo mental do backend além da lista de módulos.

## Responsabilidades
- Mostrar o caminho request -> serviço -> repositório -> runtime.
- Destacar onde o sistema toma decisões.

## Entradas
- `ChatService`, `LLMService`, `KnowledgeService`, `AutonomyService`.
- Repositórios e workers.

## Saídas
- Mapa decisório do backend.

## Dependências
- [[02 - Backend/Kernel e Startup]]
- [[02 - Backend/LLM Routing e Prompts]]
- [[02 - Backend/Memória Conhecimento e RAG]]
- [[02 - Backend/Autonomia e Workers]]

## Modelo mental
- A API é fina: endpoints delegam quase tudo aos serviços.
- Os serviços concentram política, orquestração e integração entre subsistemas.
- Repositórios encapsulam persistência e gateways para bancos e infraestrutura.
- Workers executam rotinas contínuas e assíncronas fora do caminho síncrono da request.
- O kernel é o centro de composição e o `app.state` é o barramento de entrega para os endpoints.

## Exemplo concreto: chat
- O endpoint decide o mínimo necessário de borda:
  - resolver identidade
  - validar acesso/tamanho/origem
  - resolver papel efetivo inicial
  - traduzir exceções para contrato HTTP/SSE
- `ChatService` funciona como fachada estável e distribui responsabilidade para três serviços internos:
  - `ConversationService`: ciclo de vida da conversa, histórico e reconciliação de pending actions já resolvidas
  - `MessageOrchestrationService`: ramo REST, ordem de decisão, RAG/memória, grounding documental e pós-processamento
  - `StreamingService`: ramo SSE, handshake incremental, heartbeats, circuito e persistência final do stream
- A política real do chat não fica num ponto único:
  - heurística semântica nasce em `message_helpers.py`
  - routing por intenção nasce no endpoint via `IntentRoutingService`
  - confirmação/pending action nasce na combinação endpoint + `chat_contracts.py`
  - tool loop e content safety ficam em `ChatAgentLoop`
- O backend pensa em degradação por transporte:
  - REST prioriza capacidade completa, incluindo `ChatAgentLoop`, indexação RAG do turno e sumarização
  - SSE prioriza entrega incremental e observabilidade, mas o caminho geral não usa `ChatAgentLoop`

## Padrões recorrentes
- DTOs Pydantic nos endpoints.
- Serviços como fachadas estáveis.
- Feature flags e políticas vindas de `settings`.
- Degradação parcial em vez de abortar sempre que possível.

## Arquivos-fonte
- `backend/app/services/chat_service.py`
- `backend/app/services/knowledge_service.py`
- `backend/app/services/llm_service.py`
- `backend/app/core/kernel.py`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Conversa e Chat]]
- [[04 - Fluxos End-to-End/Documentos Conhecimento e Memória]]

## Riscos/Lacunas
- A largura funcional do backend dificulta separar domínio de plataforma.
- Há sinais de monólito modular: bom para velocidade, custoso para isolamento.
