# Plano de Melhoria de Funcionalidades Críticas

Com base na análise, priorizei as melhorias nos seguintes componentes para aumentar a robustez e a confiabilidade do sistema:

1.  **Orquestração de Agentes (Refatoração de Busca SQL):**
    *   **Problema:** Uso de SQL frágil com `LIKE` em colunas JSON (`janus/app/api/v1/endpoints/pending_actions.py`).
    *   **Solução:** Substituir por consultas estruturadas usando operadores JSON nativos do banco de dados (PostgreSQL/SQLite) ou lógica de filtro em memória robusta.
    *   **Benefício:** Evita quebras silenciosas se o formato de serialização do LangGraph mudar.

2.  **Rastreamento de Custos (Redis Usage Tracker):**
    *   **Problema:** Falha silenciosa em `janus/app/core/infrastructure/redis_usage_tracker.py` que retorna `0.0` em erros de incremento.
    *   **Solução:** Implementar tratamento de erro adequado. Se o incremento falhar, lançar uma exceção ou registrar em um log de auditoria secundário (fallback) para reconciliação posterior, garantindo que nenhum custo seja perdido.
    *   **Benefício:** Garante a integridade financeira do sistema e evita uso "gratuito" acidental.

3.  **Execução de Ferramentas (Sandbox Não-Bloqueante):**
    *   **Problema:** Execução síncrona/bloqueante de containers Docker em `janus/app/core/tools/sandbox_executor.py`.
    *   **Solução:** Refatorar para usar `detach=True` e `container.wait()`, permitindo timeouts reais e liberando a thread do worker.
    *   **Benefício:** Previne travamento de workers por código malicioso ou loops infinitos de usuários.

4.  **Guardião do Grafo (Persistência de Quarentena):**
    *   **Problema:** Itens rejeitados são apenas logados e perdidos (`janus/app/core/memory/graph_guardian.py`).
    *   **Solução:** Implementar persistência real em uma tabela ou coleção de "Quarentena" (via `postgres_db` ou arquivo de log estruturado dedicado) para permitir revisão e reprocessamento.
    *   **Benefício:** Permite auditoria de qualidade de dados e recuperação de informações válidas rejeitadas erroneamente.

## Ordem de Execução
1.  **Sandbox Executor:** Crítico para estabilidade.
2.  **Redis Usage Tracker:** Crítico para integridade de dados/custo.
3.  **Graph Guardian:** Importante para qualidade de dados.
4.  **Pending Actions SQL:** Importante para manutenibilidade.

Vou começar aplicando as correções no **Sandbox Executor** e **Redis Usage Tracker** imediatamente, pois têm impacto direto na estabilidade e segurança.
