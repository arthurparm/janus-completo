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
