---
tipo: dominio
dominio: backend
camada: inferencia
fonte-de-verdade: codigo
status: ativo
---

# LLM Routing e Prompts

## Objetivo
Descrever como o Janus escolhe modelos e monta contexto de inferência.

## Responsabilidades
- Explicar papel, prioridade, política e prompt loading.
- Ligar provedores locais e cloud.

## Entradas
- Prompt do usuário.
- `ModelRole` e `ModelPriority`.
- Política de tarefa inferida.

## Saídas
- Invocação do provedor selecionado.
- Resposta com sinais de roteamento, custo e resiliência.

## Dependências
- [[01 - Visão do Sistema/Dependências Externas]]
- [[02 - Backend/Como o Backend Pensa]]
- [[04 - Fluxos End-to-End/Conversa e Chat]]

## Leitura operacional
- `LLMService.invoke_llm()` infere perfil da tarefa e aplica overrides de política.
- O serviço injeta cabeçalho de identidade quando a proteção de identidade está habilitada.
- Há cache, circuit breaker, seleção de provedor, warm-up e rate limits.
- O chat também faz roteamento de intenção antes de escolher o papel efetivo.

## Provedores previstos
- OpenAI
- Gemini
- Ollama
- DeepSeek
- xAI
- OpenRouter

## Arquivos-fonte
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
- A governança de custo e timeout é sofisticada, mas distribuída entre config, core e repo.
- O comportamento final depende fortemente de flags e budgets.
