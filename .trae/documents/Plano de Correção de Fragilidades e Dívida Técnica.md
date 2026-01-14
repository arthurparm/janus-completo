Vou realizar as correções nos 4 pontos identificados para resolver as fragilidades do sistema.

### 1. Corrigir Fragilidade no `pending_actions.py` (SQL Injection/Parsing)
**Problema:** O código atual usa `LIKE` em uma coluna serializada (blob/json), o que é frágil e pode quebrar se o formato mudar.
**Solução:**
- Alterar a query SQL para buscar apenas os blobs brutos (`checkpoint`, `metadata`) do registro mais recente.
- Mover a lógica de filtragem para o Python, onde podemos deserializar o conteúdo de forma segura.
- Adicionar tratamento de erro na deserialização para evitar que falhas em um registro bloqueiem a listagem inteira.

### 2. Corrigir Falha Silenciosa no `redis_usage_tracker.py` (Risco Financeiro)
**Problema:** O sistema engole exceções do Redis e retorna custo `0.0`, permitindo uso gratuito ilimitado se o banco de cache falhar.
**Solução:**
- Adicionar logging de erro (`logger.error` com stack trace) para visibilidade imediata de falhas.
- Manter o comportamento "fail-open" (retornar 0.0) para não parar a produção, mas garantindo que o erro seja registrado nos logs de observabilidade.

### 3. Resolver Lógica "Hardcoded" e Duplicada (`factory.py` e `router.py`)
**Problema:** A criação de instâncias do Ollama e a lógica de fallback estão duplicadas e marcadas como "simplificadas/hardcoded".
**Solução:**
- Criar uma função factory centralizada `create_ollama_llm` em `factory.py` que encapsula toda a configuração (timeouts, headers, kwargs).
- Refatorar `router.py` e `factory.py` para usar essa função única, eliminando a duplicação e garantindo consistência nas configurações.

### 4. Implementar Verificação de Segurança (`knowledge_graph_service.py`)
**Problema:** Existe um `# TODO` crítico indicando que a verificação de política de segurança (`check_policy`) não está implementada.
**Solução:**
- Implementar o método `check_policy` na classe `GraphGuardian` em `graph_guardian.py`.
- Adicionar validação básica (ex: impedir tipos de relação inválidos ou nulos).
- Descomentar e ativar a chamada no `knowledge_graph_service.py` para garantir que nenhuma inserção no grafo ocorra sem validação.
