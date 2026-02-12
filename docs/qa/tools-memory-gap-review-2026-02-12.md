# Review: Tools + Memory (Curta/Longa/Profunda)

Data: 2026-02-12

## Status executivo
- Ferramentas: seguras o suficiente para avançar (content safety + auditoria pré-execução + confirmação + quota diária).
- Memória curta: quota por origem ativa e protegida.
- Memória longa/profunda: funcional, mas ainda com gaps de qualidade operacional para produção em escala.

## Achados prioritários

1. Alta: parsing de tool calls é frágil a formato/alucinação  
Arquivo: `janus/app/services/tool_executor_service.py:92`  
Risco: regex em XML-like pode aceitar payload quebrado e não garante schema por ferramenta (`args` sem validação de tipos/shape).

2. Alta: `get_subgraph_from_context` tem trecho incompleto/legado no fluxo  
Arquivo: `janus/app/services/knowledge_graph_service.py:306`  
Risco: bloco com `pass` e dupla estratégia de query no mesmo método dificulta previsibilidade e manutenção.

3. Média: `persist_extraction` sem transação única  
Arquivo: `janus/app/services/knowledge_graph_service.py:81`  
Risco: escrita parcial (entidades criadas sem relações) em falhas intermediárias.

4. Média: memória curta usa timestamp aproximado no retorno de cache  
Arquivo: `janus/app/core/memory/local_cache.py:131`  
Risco: recência imprecisa em ranking downstream.

5. Média: argumentos de pending confirmation são persistidos sem política explícita de mascaramento  
Arquivo: `janus/app/services/tool_executor_service.py:210`  
Risco: dados sensíveis em `args_json` se a ferramenta receber PII/segredos.

## Correção aplicada nesta rodada
- Ajuste de enums inválidos no cálculo de importância da memória generativa:
  - `ModelRole.REASONER` e `ModelPriority.FAST_AND_CHEAP`
  - Arquivo: `janus/app/core/memory/generative_memory.py:144`
- Teste adicionado para prevenir regressão:
  - `tests/test_generative_memory_llm_role_priority.py:1`

## Recomendações objetivas (próximo ciclo)
1. Ferramentas:
  - trocar parser regex por formato estruturado único (JSON tool call envelope);
  - validar args por schema pydantic de cada ferramenta antes da execução.

2. Memória curta:
  - retornar timestamp real do item cacheado em vez de `datetime.now()`;
  - expor métrica de taxa de eviction/expiração.

3. Memória longa/profunda:
  - encapsular `persist_extraction` em transação Neo4j;
  - separar `get_subgraph_from_context` em implementação única (sem ramo morto) e cobrir com teste de contrato.

4. Compliance:
  - aplicar redaction/masking em `args_json` antes de salvar pending confirmations.
