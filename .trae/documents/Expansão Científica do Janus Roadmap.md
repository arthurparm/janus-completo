# Plano de Expansão Científica do Janus (V1+ Evolution)

Para elevar o Janus ao estado da arte (SOTA 2025/2026), propomos a implementação de novos conceitos identificados na literatura recente de agentes autônomos.

## 1. 🧠 Dynamic Cognitive Architecture (Flow Engineering)
*   **Gap Identificado**: O planejamento atual do `AutonomyWorker` é linear. O estado da arte usa grafos dinâmicos.
*   **Solução Científica**: Implementar **Language Agent Tree Search (LATS)**.
    *   **Conceito**: Usar Monte Carlo Tree Search (MCTS) para que o agente simule múltiplos futuros ("E se eu fizer isso?") antes de agir.
    *   **Ação**: Criar um nó `Planner` que gera uma árvore de decisões e avalia cada ramo usando um modelo "World Model" leve.

## 2. 🧩 Self-Evolving Toolset (Agent-0 Style)
*   **Gap Identificado**: Janus usa ferramentas fixas. O SOTA (Agent-0, Voyager) cria suas próprias ferramentas.
*   **Solução Científica**: **Autonomous Tool Synthesis**.
    *   **Conceito**: Quando o agente percebe que uma tarefa repetitiva não tem ferramenta, ele escreve um script Python, testa no Sandbox, e se funcionar, salva no banco de dados como uma nova `Tool` disponível para todos os agentes.
    *   **Ação**: Implementar o `ToolSynthesizerAgent` que monitora padrões de execução manual e propõe automação persistente.

## 3. 💾 Active Memory Management (MemGPT)
*   **Gap Identificado**: A gestão de contexto é passiva (RAG). O SOTA usa gestão ativa (OS Paging).
*   **Solução Científica**: **Active Context Paging**.
    *   **Conceito**: O agente recebe um token especial `<memory_warning>` quando o contexto enche e deve decidir explicitamente o que mover para a memória de longo prazo (Neo4j) ou descartar.
    *   **Ação**: Adicionar um wrapper no `LeafWorker` que intercepta o uso de tokens e força um ciclo de "Memory Cleanup" antes de continuar.

## 4. 🐝 Swarm Intelligence (Descentralização)
*   **Gap Identificado**: Orquestração hierárquica pode ser um gargalo.
*   **Solução Científica**: **Dynamic Handoffs**.
    *   **Conceito**: Permitir que um agente transfira a execução diretamente para outro especialista sem voltar ao Supervisor, reduzindo latência e custo.
    *   **Ação**: Implementar a tool `transfer_to_agent(agent_name, context)` disponível para todos os workers.

## Ação Imediata
Atualizar o `Melhorias possiveis.md` com uma nova seção **"🧪 Scientific Frontier (Post-V1)"** detalhando esses 4 pilares, além de reforçar a seção de **V1 Critical Path** com os itens de segurança já mapeados.
