# Plano de Implementação de Versionamento e Observabilidade

Este plano visa resolver os problemas de corrupção de estado do LangGraph (Schema Migration) e melhorar a observabilidade (LangSmith).

## 1. Versionamento de Grafos e Schema Migration

### 1.1 Controle de Versão
- **Modificar `AgentState`**: Adicionar campo opcional `schema_version: int` no TypedDict em `graph_orchestrator.py`.
- **Configuração**: Definir `GRAPH_SCHEMA_VERSION = 1` em `config.py` ou constante no orquestrador.

### 1.2 Mecanismo de Validação e Limpeza
- **Hook de Inicialização**: Ao instanciar o grafo (`get_graph`), adicionar uma verificação prévia (via SQL cru, similar ao `pending_actions.py`) para inspecionar threads ativas.
- **Estratégia "Lazy Migration"**:
  - O LangGraph não suporta migração "in-place" fácil de blobs binários.
  - **Abordagem Segura**: Criar um endpoint/script de manutenção `POST /admin/graph/purge_incompatible` que:
    1.  Varre a tabela `checkpoints`.
    2.  Verifica se o snapshot contém campos incompatíveis ou falta de campos obrigatórios novos.
    3.  Arquiva a thread antiga (move para tabela `archived_threads`) e deleta da `checkpoints`, forçando o usuário a iniciar uma nova conversa limpa.
  - **Justificativa**: Tentar converter estado binário complexo é propenso a erros. Arquivar é mais seguro para auditoria.

### 1.3 Logs de Migração
- Adicionar logs estruturados (via `structlog`) sempre que uma thread for arquivada por incompatibilidade.

## 2. Observabilidade e Tracing (LangSmith)

### 2.1 Configuração Robusta
- **Verificação no Startup**:
  - No `main.py` (startup event), validar se `LANGCHAIN_API_KEY` está presente se `LANGCHAIN_TRACING_V2=true`.
  - Emitir warning claro se o tracing estiver ativado mas sem chave.

### 2.2 Instrumentação Detalhada
- **Decoradores**: Aplicar `@traceable` do `langsmith` em funções críticas fora do grafo:
  - `LeafWorker.run`
  - `NativeGraphRAG.query`
  - `SandboxExecutor.run_code`
- **Metadata**: Injetar metadados de projeto/ambiente (`ENVIRONMENT`, `APP_VERSION`) no tracer global.

### 2.3 Detecção de Loops
- **Configuração LangGraph**:
  - Definir `recursion_limit` explicitamente no `workflow.compile(...)`.
  - O padrão é 25, vamos ajustar para configurável via `config.REASONING_MAX_ITERATIONS`.

## Cronograma de Execução
1. Atualizar `AgentState` com campo de versão.
2. Implementar script de limpeza de threads incompatíveis.
3. Adicionar validação de credenciais LangSmith no startup.
4. Instrumentar componentes chave com `@traceable`.
