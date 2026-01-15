# Plano de Implementação: Estratégia de Fusão "Strict Mode + Regex Fallback"

Este plano visa unificar o tratamento de respostas JSON, priorizando o **Strict Mode** nativo dos LLMs (Plan A) e mantendo uma limpeza leve via Regex como segurança (Plan B), descartando qualquer tentativa de "reparo" via LLM secundário.

## 1. Atualizar Adaptadores LLM (Plan A: Strict Mode)
**Objetivo:** Garantir que os provedores (OpenAI, DeepSeek) recebam e respeitem o parâmetro `response_format` ou `strict: true`.

*   **Arquivo:** `janus/app/core/llm/adapters.py` (e `factory.py` se necessário)
*   **Ações:**
    *   Atualizar `OpenAIAdapter` (usado também pelo DeepSeek) para aceitar e injetar `response_format={"type": "json_object"}` ou schemas Pydantic quando solicitado.
    *   Garantir que o parâmetro `strict=True` seja passado para modelos que o suportam (ex: GPT-4o, DeepSeek V3 via API compatível).

## 2. Unificar Lógica de Parsing (Plan B: Regex Fallback)
**Objetivo:** Criar um utilitário único que implementa a estratégia de fusão: Tenta parse nativo -> Falha -> Tenta limpeza Regex -> Falha -> Erro.

*   **Arquivo:** `janus/app/core/agents/utils.py`
*   **Ações:**
    *   Refatorar/Criar função `parse_json_strict(content: str) -> dict`.
    *   **Lógica:**
        1.  `try: return json.loads(content)` (Sucesso imediato do Strict Mode).
        2.  `except`: Executar `_clean_json_output` (Regex para remover markdown/sujeira).
        3.  `try: return json.loads(cleaned)`.
        4.  `except`: Raise `JSONDecodeError` (Sem retry via LLM).

## 3. Refatorar Consumidores para Usar o Novo Padrão
**Objetivo:** Remover implementações redundantes de regex espalhadas pelo código e usar o novo utilitário centralizado.

*   **Arquivos Alvo:**
    *   `janus/app/core/agents/utils.py` (`_create_tool_wrapper` / `async_wrapper`): Simplificar para usar `parse_json_strict`.
    *   `janus/app/core/optimization/reflexion_core.py` (`_extract_json`): Substituir pela chamada centralizada.
    *   `janus/app/core/workers/professor_agent_worker.py` (`_parse_review_json`): Substituir pela chamada centralizada.
    *   `janus/app/core/autonomy/planner.py` (`_extract_json_array`): Substituir ou adaptar para usar a lógica centralizada.

## 4. Limpeza (Discard Stage 2)
**Objetivo:** Garantir que não existam "Fixers" complexos.

*   **Ação:** Verificar e remover qualquer lógica que capture `JSONDecodeError` e tente fazer uma nova chamada de LLM para "consertar" o JSON (se existir). O fallback de *rede/erro* do `client.py` será mantido, mas não haverá fallback de *conteúdo*.

## Verificação
*   Criar um teste unitário simples em `tests/core/test_json_parsing.py` (ou similar) cobrindo:
    *   JSON Perfeito (Strict Mode simulado).
    *   JSON com Markdown (Cenário Regex).
    *   JSON Irrecuperável (Erro imediato).
