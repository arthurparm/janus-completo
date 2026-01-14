# Plano de Melhoria de Infraestrutura e Segurança

Este plano aborda a migração do pool de conexões para `asyncpg` e a implementação de segurança robusta na execução de ferramentas via Sandbox.

## 1. Gestão de Conexões de Banco (Pool)

### 1.1 Migração para Asyncpg
- **Refatorar `PostgresDatabase`**:
  - Modificar `janus/app/db/postgres_config.py` para usar `create_async_engine` (SQLAlchemy 2.0+).
  - Substituir o driver `psycopg2` por `asyncpg`.
  - Implementar métodos assíncronos `get_session_async` e `create_tables_async`.

### 1.2 Integração com LangGraph
- **Atualizar `graph_orchestrator.py`**:
  - Remover a criação manual de conexão no `get_graph`.
  - Instanciar `AsyncPostgresSaver` (ou `PostgresSaver` com conexão assíncrona, dependendo da versão da lib) utilizando o pool global do `postgres_db`.
  - Garantir que o ciclo de vida da conexão (acquire/release) seja gerenciado pelo contexto do grafo.

## 2. Segurança na Execução de Ferramentas (Sandbox)

### 2.1 Refatoração do `LeafWorker`
- **Isolamento**: Modificar `janus/app/core/agents/leaf_worker.py` para interceptar chamadas de ferramentas marcadas como perigosas.
- **Integração com Docker**:
  - Utilizar a lógica já existente em `sandbox_agent_worker.py` como base.
  - Criar um wrapper `SandboxExecutor` que encapsula a lógica de `docker run`.

### 2.2 Implementação do SandboxExecutor
- **Novo Arquivo**: `janus/app/core/tools/sandbox_executor.py`.
- **Funcionalidades**:
  - Execução de código Python em container isolado (`python:3.11-slim`).
  - Limites rígidos: `network_mode="none"`, `mem_limit="256m"`, `cpu_quota`.
  - Timeout obrigatório (ex: 10s).
  - Captura segura de `stdout` e `stderr`.

### 2.3 Registro de Ferramentas Seguras
- **Atualização**: Marcar ferramentas de sistema (ex: `RunCommand`, `WriteFile`) como `unsafe=True`.
- **Middleware**: O `LeafWorker` verificará essa flag e delegará para o `SandboxExecutor` em vez de executar localmente.

## 3. Testes e Validação

### 3.1 Testes de Integração (Banco)
- Verificar se o pool assíncrono está reciclando conexões corretamente.
- Testar persistência de estado do LangGraph com o novo engine.

### 3.2 Testes de Segurança (Sandbox)
- Tentar executar comandos maliciosos (`rm -rf`, acesso à rede) via worker e validar bloqueio.
- Garantir que ferramentas seguras (ex: `date`) continuem rápidas.

## Cronograma
1. Configuração do Async Engine (Postgres).
2. Integração LangGraph + Pool.
3. Implementação do SandboxExecutor.
4. Refatoração do LeafWorker para usar Sandbox.
5. Testes finais.
