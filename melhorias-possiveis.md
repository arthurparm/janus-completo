# Melhorias Possíveis e Análise Crítica do Janus

Este documento compila uma análise técnica detalhada do estado atual do projeto Janus, identificando áreas de melhoria, código obsoleto, funcionalidades incipientes e dívidas técnicas.

**Data da Análise:** 11/02/2026
**Autor:** Agente de Planejamento (Jules)

---

## 1. Melhorias Críticas de Arquitetura (Backend)

### 1.1. Refatoração do `config.py`
**Problema:** O arquivo `janus/app/config.py` é um monolito de configuração. Ele mistura:
*   Credenciais de infraestrutura (DB, RabbitMQ).
*   Configurações de negócio (Custos de LLM, Pesos de RAG).
*   Definições de roles de agentes.
*   Lógica complexa de validação (parsers JSON manuais em validadores Pydantic).

**Impacto:** Dificuldade de manutenção, risco de quebra ao alterar uma config simples, acoplamento forte entre infra e regras de negócio.

**Sugestão:** Quebrar em múltiplos arquivos:
*   `config/infrastructure.py`: Apenas conexões.
*   `config/business.py`: Regras de negócio, custos, pesos.
*   `config/agents.py`: Definições de roles e modelos.

### 1.2. Duplicidade e Confusão em Workers
**Problema:** Existem workers com propósitos sobrepostos ou nomes confusos:
*   `codex_worker.py` vs `code_agent_worker.py`: O primeiro parece focar em execução de ferramentas CLI, o segundo em geração via LLM. A fronteira não é clara.
*   `knowledge_consolidator_worker.py` vs `async_consolidation_worker.py`: Um contém a classe de lógica, o outro o loop do consumidor. A nomenclatura sugere dois workers distintos, o que confunde.

**Sugestão:** Unificar a nomenclatura (ex: `CodeGenerationWorker` e `ToolExecutionWorker`) e consolidar arquivos de lógica e consumo onde fizer sentido, ou adotar um padrão claro (ex: `Service` + `WorkerAdapter`).

### 1.3. Hardcoded Prompts e Roles
**Problema:** Definições de modelos candidatos (`LLM_CLOUD_MODEL_CANDIDATES`) e expectativas de tokens (`LLM_EXPECTED_KTOKENS_BY_ROLE`) estão "cravadas" no código/config.

**Sugestão:** Mover essas definições para o banco de dados (tabela `AgentProfiles` ou `ModelConfig`) para permitir ajuste dinâmico sem deploy.

---

## 2. Melhorias Críticas de Frontend (Angular)

### 2.1. "God Component" (`ConversationsComponent`)
**Problema:** O arquivo `front/src/app/features/conversations/conversations.ts` possui mais de 800 linhas e acumula responsabilidades de:
*   Listagem de conversas.
*   Janela de chat e renderização de mensagens.
*   Gerenciamento de stream SSE.
*   Exibição de documentos e traces.
*   Painel de Autonomia.

**Impacto:** Testabilidade baixa, legibilidade ruim, dificuldade de reutilização.

**Sugestão:** Refatorar em sub-componentes:
*   `ConversationListComponent`
*   `ChatWindowComponent`
*   `MessageItemComponent`
*   `AutonomyPanelComponent`
*   `TraceViewerComponent`

### 2.2. Tratamento de Erros Genérico
**Problema:** O método `extractErrorMessage` no frontend faz uma tentativa genérica de pegar mensagens de erro, mas a tipagem é fraca (`any` / `unknown` com casts manuais).

**Sugestão:** Implementar um interceptor de erro global mais robusto que padronize as respostas de erro da API (ex: `ProblemDetails` RFC 7807) e tipar corretamente no front.

---

## 3. Funcionalidades Incipientes ou MVP

### 3.1. `neural_training_worker.py`
**Estado:** Parece ser uma implementação esquelética ("MVP"). Ele recebe tarefas mas delega para um `LearningRepository` que não foi auditado profundamente, mas a complexidade de um "treinamento neural" real geralmente exige pipelines dedicados (MLFlow, Kubeflow), não apenas um worker Python simples.

**Sugestão:** Avaliar se essa funcionalidade é real ou apenas um placeholder. Se for real, documentar a infraestrutura de treino (onde roda? GPU?).

### 3.2. Testes E2E e Integração
**Estado:** Embora existam pastas de testes, a cobertura de cenários complexos (ex: RAG Híbrido com falha parcial de um DB) pode ser melhorada.

**Sugestão:** Adicionar testes de caos (Chaos Engineering) para simular queda do RabbitMQ ou Neo4j durante um fluxo de conversa.

---

## 4. Documentação e Processos

### 4.1. Documentação Automática (BMAD)
**Problema:** Os arquivos gerados pelo BMAD (`docs/project-overview.md`, etc.) são úteis como snapshot, mas tendem a ficar obsoletos rapidamente se não forem regerados no CI/CD. Além disso, misturam inglês e português ou estruturas genéricas.

**Sugestão:** Manter a documentação manual (`docs/MANUAL_*.md`) como fonte da verdade para humanos e usar o BMAD apenas para análise estática automatizada.

### 4.2. Tradução
**Problema:** O projeto mistura termos em inglês e português na documentação e no código (comentários).

**Sugestão:** Padronizar a documentação oficial (Manuais) em Português (conforme feito nesta atualização) e manter o código/comentários internos preferencialmente em Inglês para padrão internacional, ou assumir Português em tudo. A mistura atual gera atrito.

---

## 5. Segurança

### 5.1. Segredos no Frontend
**Problema:** O frontend Angular consome APIs (como Firebase) diretamente. Embora padrão, expor chaves de API no código cliente (`environment.ts`) requer regras de segurança (Security Rules) muito bem configuradas no backend do Firebase.

**Sugestão:** Garantir que nenhuma chave de serviço backend (OpenAI, AWS, etc.) vaze para o frontend. O Janus já faz isso proxying via backend Python, o que é ótimo. Manter esse padrão rigorosamente.

### 5.2. Rate Limiting
**Observação:** O sistema possui Rate Limiting, mas a configuração parece global ou por IP.

**Sugestão:** Implementar Rate Limiting por Tenant/Usuário logado para evitar que um usuário consuma toda a quota da API de LLM.
