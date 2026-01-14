# Implementação do Sistema de Debate Multi-Agente (Liang et al., 2023)

Este plano detalha a implementação do sistema de debate Proponente-Crítico dentro da arquitetura do Janus, utilizando o padrão Orchestrator-Worker e LangGraph.

## 1. Definição de Prompts Especializados
Criação de um novo módulo de prompts para definir as personas e diretrizes estritas do debate.
- **Arquivo**: `janus/app/core/prompts/modules/debate.py`
- **Conteúdo**:
    - `PROPONENT_PROMPT`: Focado em geração de código robusto, seguindo SOLID/DRY, e instruções para incorporar feedback.
    - `CRITIC_PROMPT`: Focado em análise estática, detecção de alucinações, segurança e performance. Deve retornar saída estruturada (JSON/XML) para facilitar o parsing.

## 2. Implementação dos Workers
Criação de dois novos workers especializados que consumirão filas dedicadas do RabbitMQ.

### 2.1 Debate Proponent Worker
- **Arquivo**: `janus/app/core/workers/debate_proponent_worker.py`
- **Base**: Similar ao `CodeAgentWorker`, mas configurado para o fluxo de debate.
- **Fila**: `JANUS.tasks.agent.debate.proponent`
- **Responsabilidade**: Gerar a solução inicial ou refinar a solução existente com base no `review_notes` do Crítico.

### 2.2 Debate Critic Worker
- **Arquivo**: `janus/app/core/workers/debate_critic_worker.py`
- **Base**: `LeafWorker` ou novo worker especializado.
- **Fila**: `JANUS.tasks.agent.debate.critic`
- **Responsabilidade**: Analisar o código recebido no payload e gerar um relatório de crítica (Aprovado/Reprovado + Lista de Issues).

## 3. Orquestração do Debate (LangGraph)
Implementação do fluxo de controle que gerencia o ciclo de debate.
- **Arquivo**: `janus/app/core/agents/debate_orchestrator.py`
- **Estrutura do Grafo**:
    1.  **Node `propose`**: Envia tarefa para o `DebateProponentWorker`.
    2.  **Node `critique`**: Envia o código gerado para o `DebateCriticWorker`.
    3.  **Node `decide`**: Avalia a resposta do Crítico.
        - Se `APROVADO` ou `MAX_ITERACOES` atingido -> Fim.
        - Se `REPROVADO` -> Volta para `propose` com as notas da crítica.
- **Estado**: Manterá o histórico das iterações, código atual e críticas.

## 4. Integração e Configuração
Atualização dos modelos e configurações do sistema para suportar os novos componentes.
- **`janus/app/models/schemas.py`**: Adicionar novas `QueueName` (`TASKS_AGENT_DEBATE_PROPONENT`, `TASKS_AGENT_DEBATE_CRITIC`).
- **`janus/app/core/workers/orchestrator.py`**: Registrar e iniciar os novos workers no startup do sistema.

## 5. Validação
- Criação de um script de teste `scripts/test_debate_system.py` para simular uma requisição de codificação e verificar se o ciclo de debate ocorre (logs de iteração, feedback gerado e refinamento).
