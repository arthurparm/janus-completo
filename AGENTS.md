# Guia Definitivo da Arquitetura de Agentes do Projeto Janus

## 1. Filosofia: Especialização e Resiliência

A arquitetura de agentes do Janus é construída sobre dois pilares fundamentais:

1.  **Especialização e Princípio do Menor Privilégio**: Em vez de um único agente monolítico, o Janus emprega um elenco de agentes especializados, cada um com um papel (`AgentType`) e um conjunto de ferramentas (`tools`) estritamente definidos. Isso garante que um agente tenha apenas as permissões necessárias para cumprir sua função, aumentando a segurança e a previsibilidade do sistema.

2.  **Resiliência Nativa**: A execução de cada agente é uma operação crítica. Por isso, o `AgentManager` envolve cada chamada em múltiplas camadas de proteção, incluindo **Circuit Breakers**, **retentativas com backoff exponencial** e **timeouts**. Isso garante que o sistema possa lidar com falhas transitórias (ex: instabilidade da API do LLM) e falhas persistentes sem comprometer sua estabilidade geral.

## 2. O Elenco de Agentes: Papéis e Responsabilidades

O `AgentType` (definido em `app/core/agent_manager.py`) classifica os diferentes papéis cognitivos no sistema.

### 2.1. `AgentType.TOOL_USER`

*   **Descrição**: O agente de linha de frente, o "operário" do sistema. É responsável por executar a maioria das tarefas que exigem interação com o ambiente, como ler e escrever arquivos, buscar informações na web ou consultar a memória.
*   **Prompt Principal**: `react_agent` (de `app/core/prompt_loader.py`).
*   **Ferramentas**: Acesso ao `unified_tools`, o conjunto mais amplo de ferramentas, incluindo `write_file`, `read_file`, `list_directory`, `recall_experiences`, etc.
*   **Exemplo de Tarefa**: "Crie um arquivo chamado `plano.md` com o plano de desenvolvimento para o próximo sprint."

### 2.2. `AgentType.ORCHESTRATOR`

*   **Descrição**: Um planejador tático. Embora atualmente compartilhe o mesmo prompt e ferramentas do `TOOL_USER`, seu papel é semanticamente distinto. É invocado para tarefas que exigem um planejamento inicial ou a decomposição de um problema antes da execução.
*   **Prompt Principal**: `react_agent`.
*   **Ferramentas**: `unified_tools`.
*   **Exemplo de Tarefa**: "Analise a solicitação do usuário e crie um plano passo a passo para implementar a nova funcionalidade."

### 2.3. `AgentType.META_AGENT`

*   **Descrição**: O "supervisor" do sistema, responsável pela autoanálise e otimização. Ele opera em um ciclo de vida próprio (`meta_agent_cycle.py`) para monitorar a saúde do Janus.
*   **Prompt Principal**: `meta_agent_supervisor`.
*   **Ferramentas**: Um conjunto restrito e poderoso de ferramentas de introspecção, como `analyze_memory_for_failures` e `recall_experiences`.
*   **Exemplo de Tarefa (invocada pelo sistema)**: "Analise as últimas 20 experiências e identifique padrões de falha recorrentes."

## 3. O Ciclo de Vida de Execução de um Agente

Toda a lógica de execução é orquestrada pelo `AgentManager` (`app/core/agent_manager.py`). Quando uma tarefa é delegada a um agente, o seguinte fluxo ocorre:

1.  **Requisição**: Um endpoint (ex: `app/api/v1/endpoints/agent.py`) recebe uma `question` e um `agent_type`.

2.  **Execução Assíncrona**: A chamada é encaminhada para `agent_manager.run_agent_async`, que é totalmente assíncrona e não bloqueia o servidor.

3.  **Seleção de Configuração**: O `_get_agent_config` seleciona o template de prompt e o conjunto de ferramentas corretos para o `agent_type` solicitado.

4.  **Criação do Executor**: Um `AgentExecutor` da LangChain é instanciado, combinando o LLM, as ferramentas e o prompt. Este é o motor que executa o ciclo **ReAct (Reason-and-Act)**.

5.  **Execução Resiliente (O Coração da Robustez)**:
    *   **Circuit Breaker**: Antes de qualquer tentativa, o `CircuitBreaker` específico do agente é verificado. Se estiver "aberto" (devido a falhas anteriores), a chamada é bloqueada imediatamente, prevenindo sobrecarga.
    *   **Timeout**: Cada tentativa de execução tem um timeout estrito (`OP_TIMEOUT`).
    *   **Retentativas com Backoff**: Se a execução falhar (ex: erro de rede, LLM indisponível), o sistema não desiste. Ele espera por um período de tempo (backoff exponencial com jitter) e tenta novamente, até `MAX_ATTEMPTS`.

6.  **Memorização**: Se a execução for bem-sucedida e uma ferramenta for utilizada, a função `_handle_successful_run` memoriza a experiência (`action_success`) no `memory_core`. Isso permite que o sistema aprenda com suas ações.

7.  **Resposta**: O resultado final (`Final Answer` do agente) ou um erro estruturado é retornado.

## 4. Ferramentas: As Capacidades dos Agentes

As ferramentas (`app/core/agent_tools.py`) são as "mãos" dos agentes. A função `get_tools_for_agent` atua como um "gatekeeper", garantindo que cada agente receba apenas as ferramentas que seu papel permite.

### Ferramentas Principais:

*   `write_file`: Escreve arquivos no disco, mas com **validações de segurança críticas**:
    *   Restringe a escrita ao diretório `/app/workspace`.
    *   Valida extensões de arquivo permitidas (`.txt`, `.py`, etc.).
    *   Impede path traversal (`..`).
*   `read_file`: Lê arquivos do projeto.
*   `list_directory`: Lista o conteúdo do workspace.
*   `recall_experiences`: Permite ao agente consultar sua própria memória sobre ações passadas.
*   `analyze_memory_for_failures`: **Ferramenta exclusiva do Meta-Agente** para diagnósticos de saúde.

## 5. Engenharia de Prompts: Guiando o Raciocínio

Os prompts em `app/core/prompt_loader.py` são o "DNA" do comportamento do agente.

*   **`REACT_AGENT_TEMPLATE`**: É o prompt mais importante. Ele instrui o agente a seguir o padrão `Thought -> Action -> Action Input -> Observation`. As `INSTRUCOES_CRUCIAIS_E_OBRIGATORIAS` forçam o agente a ser metódico, a usar apenas as ferramentas disponíveis e a lidar com erros de forma previsível.

*   **`META_AGENT_SUPERVISOR_TEMPLATE`**: Um prompt mais focado, que instrui o Meta-Agente a usar suas ferramentas de diagnóstico para encontrar problemas e propor soluções.

## 6. Como Estender o Sistema

A arquitetura foi projetada para ser extensível.

### Adicionando uma Nova Ferramenta

1.  **Crie a Função**: Em `app/core/agent_tools.py`, defina sua função Python.
2.  **Decore com `@tool`**: Adicione o decorador `@tool` da LangChain.
3.  **Defina os Argumentos**: Crie uma classe Pydantic (ex: `MyToolInput(BaseModel)`) para definir os argumentos da sua ferramenta. Isso garante validação automática.
4.  **Adicione à Lista**: Adicione sua nova ferramenta à lista apropriada (`unified_tools`, `meta_agent_tools`, etc.). O `AgentManager` a disponibilizará automaticamente para os agentes corretos.

**Exemplo de Esqueleto de Ferramenta:**

```python
# Em app/core/agent_tools.py

class MyToolInput(BaseModel):
    param1: str = Field(description="Descrição do primeiro parâmetro.")

@tool(args_schema=MyToolInput)
def my_new_tool(param1: str) -> str:
    """Descrição clara do que esta ferramenta faz, para o LLM entender."""
    # Sua lógica aqui
    return f"A ferramenta foi executada com '{param1}'."

# Adicione `my_new_tool` à lista `unified_tools`
```

### Adicionando um Novo Tipo de Agente

1.  **Enum**: Adicione um novo valor ao `AgentType` em `app/core/agent_manager.py`.
2.  **Configuração**: Atualize a função `_get_agent_config` no `AgentManager` para retornar o prompt e as ferramentas para seu novo agente.
3.  **Circuit Breaker**: Um novo `CircuitBreaker` será criado automaticamente para o seu novo tipo de agente.
4.  **Prompt (Opcional)**: Se necessário, crie um novo template de prompt em `app/core/prompt_loader.py`.

## 7. Debugging e Observabilidade

*   **Logs Correlacionados**: Cada requisição recebe um `trace_id` (`X-Request-ID`). Todos os logs gerados durante a execução de um agente, incluindo pensamentos, ações e erros, conterão este ID. Use-o para filtrar os logs e rastrear o fluxo completo de uma tarefa.
*   **Métricas Prometheus**: O `AgentManager` (via `resilience.py`) expõe métricas detalhadas sobre a execução de cada agente, visíveis no dashboard Grafana:
    *   `janus_resilience_attempt_latency_seconds`: Latência de cada tentativa.
    *   `janus_resilience_retries_total`: Número de retentativas.
    *   `janus_resilience_circuit_state`: Estado do Circuit Breaker (0=CLOSED, 1=OPEN).
*   **Modo `verbose=True`**: O `AgentExecutor` é configurado com `verbose=True`, o que significa que o ciclo completo de `Thought/Action/Observation` é impresso nos logs do console, fornecendo uma visão clara do "raciocínio" do agente.