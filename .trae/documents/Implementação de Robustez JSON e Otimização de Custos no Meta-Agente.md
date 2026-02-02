# Plano de Implementação: Robustez JSON e Otimização de Custos (Meta-Agente)

## 1. Objetivo

Permitir o uso de modelos mais baratos e inteligentes (DeepSeek, Grok) no Meta-Agente, contornando suas limitações de formatação JSON através de uma camada de tratamento ("JSONifier") e mantendo a resiliência do sistema (retries).

## 2. Arquitetura Proposta

### A. Camada de Parseamento ("JSONifier")

Criar um componente dedicado (`json_parser.py`) responsável por extrair JSON válido de respostas textuais "sujas".

* **Estágio 1 (Rápido)**: Extração via Regex/Heurística (remove markdown, comentários).

* **Estágio 2 (Inteligente)**: Se o parse falhar, utiliza um modelo Local (Ollama) ou barato para corrigir a sintaxe do JSON.

* **Validação**: Confirmação final via Pydantic.

### B. Ajuste do Meta-Agente

* **Prioridade de Modelo**: Alterar de `HIGH_QUALITY` para `FAST_AND_CHEAP`. Isso ativa o uso preferencial do DeepSeek/Grok e respeita os guardrails de orçamento.

* **Método de Chamada**: Substituir `with_structured_output` (rígido e dependente de provider) por chamadas padrão `invoke` + `json_parser`.

### C. Protocolo "JsonModule" (Conceitual)

Tratar as saídas como módulos tipados para facilitar o parseamento futuro e versionamento, similar à ideia de UiGenerative.

## 3. Passos de Execução

1. **Criar** **`janus/app/core/llm/json_parser.py`**

   * Implementar `extract_and_validate_json(text, schema)`.

   * Implementar fallback para modelo local em caso de erro de sintaxe.

2. **Atualizar** **`janus/app/core/agents/meta_agent.py`**

   * Modificar `_initialize_agent` para usar prioridade `FAST_AND_CHEAP`.

   * Atualizar nós (`diagnosis`, `plan`, `reflect`) para usar o novo parser em vez de `with_structured_output`.

3. **Verificação**

   * Rodar um ciclo de teste do Meta-Agente.

   * Confirmar que o modelo utilizado foi DeepSeek (ou o definido como Fast).

   * Confirmar que o JSON foi parseado corretamente mesmo se o modelo incluir "textos extras".
