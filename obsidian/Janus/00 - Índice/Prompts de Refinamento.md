---
tipo: indice
dominio: vault
camada: navegacao
fonte-de-verdade: codigo
status: ativo
---

# Prompts de Refinamento

## Objetivo
Estes prompts existem para aprofundar a documentação do vault sem causar regressão editorial.

## Regra-mãe
Use sempre este bloco no início de qualquer prompt de refinamento:

```text
Modo de trabalho: refinamento incremental, nunca reescrita total.

Regras obrigatórias:
1. Use apenas a lógica do código como fonte de verdade.
2. Ignore a documentação existente do repositório como base de conteúdo.
3. Preserve o que já estiver correto no vault; não reescreva a nota inteira só porque você leu um novo trecho do código.
4. Atualize apenas as notas e seções realmente afetadas pelo escopo desta revisão.
5. Não remova conteúdo já documentado, a menos que o código contradiga explicitamente esse conteúdo.
6. Quando houver contradição com o código, corrija apenas o trecho incorreto e mantenha o restante da nota intacto.
7. Não encurte, não simplifique e não “normalize” outras seções da nota sem necessidade.
8. Mantenha frontmatter, links wiki, estrutura do vault e navegação existentes.
9. Preserve links válidos já existentes e apenas adicione links novos quando forem realmente úteis.
10. Expanda a documentação em profundidade local: mais precisão, mais evidência, mais contexto técnico, sem apagar trabalho anterior.

Antes de editar:
- Liste quais notas serão atualizadas.
- Liste quais seções de cada nota serão alteradas.
- Diga explicitamente o que será preservado sem mudança.

Durante a edição:
- Trabalhe em modo patch, não em modo rewrite.
- Prefira adicionar detalhes, corrigir frases específicas e introduzir subtópicos locais.
- Em "Arquivos-fonte", acrescente novas referências relevantes sem remover as já úteis.
- Em "Riscos/Lacunas", apenas complemente ou ajuste o que mudou.

Saída esperada:
- Atualizar somente as notas afetadas.
- Não tocar em notas fora do escopo.
- Produzir documentação cumulativa, estável e progressivamente mais precisa.
```

## Prompt-base

```text
Refine incrementalmente a documentação do vault Obsidian do projeto Janus para a área abaixo, usando somente a lógica do código como fonte de verdade.

[COLE AQUI O BLOCO "Modo de trabalho: refinamento incremental, nunca reescrita total."]

Tarefa:
- Ler apenas o escopo de código informado.
- Identificar quais notas do vault são realmente afetadas.
- Atualizar só os trechos necessários dessas notas.
- Tornar a documentação mais precisa e mais profunda, sem apagar conteúdo válido já consolidado.
- Se o código confirmar o que já está escrito, preserve.
- Se o código ampliar o entendimento, complemente.
- Se o código contradizer algo, corrija pontualmente o trecho contradito e registre a correção com base no código.

Formato da atualização:
- objetivo
- responsabilidades
- entradas
- saídas
- dependências
- arquivos-fonte
- fluxos relacionados
- riscos/lacunas

Restrições:
- Não reescrever a nota inteira.
- Não mexer em notas fora do escopo.
- Não usar a documentação existente do repositório como base de conteúdo.
- Não inventar comportamento que o código não prove.
```

## Backend

### Kernel

```text
Refine incrementalmente a documentação da área "Kernel e Startup" do projeto Janus.

[COLE AQUI O BLOCO "Modo de trabalho: refinamento incremental, nunca reescrita total."]

Escopo de código:
- backend/app/main.py
- backend/app/core/kernel.py
- backend/app/config.py

Foco:
- ordem de boot
- startup e shutdown
- app.state
- dependency graph
- background processes
- pontos críticos e degradação parcial

Notas-alvo prováveis:
- 02 - Backend/Kernel e Startup
- 01 - Visão do Sistema/Sequência de Boot
- 01 - Visão do Sistema/Arquitetura Geral

Instrução crítica:
- Não reescreva as notas por completo.
- Atualize só os trechos ligados a boot, wiring e lifecycle.
```

### Chat

```text
Refine incrementalmente a documentação da área "Chat" do projeto Janus.

[COLE AQUI O BLOCO "Modo de trabalho: refinamento incremental, nunca reescrita total."]

Escopo de código:
- backend/app/api/v1/endpoints/chat/*
- backend/app/services/chat_service.py
- backend/app/services/chat/*
- backend/app/services/chat_agent_loop.py
- backend/app/services/intent_routing_service.py

Foco:
- start conversation
- send message
- SSE
- role routing
- confirmation
- pending actions
- citations
- integração com memória, RAG e tools

Notas-alvo prováveis:
- 04 - Fluxos End-to-End/Conversa e Chat
- 02 - Backend/API por Bounded Context
- 02 - Backend/Como o Backend Pensa
- 02 - Backend/LLM Routing e Prompts

Instrução crítica:
- Preserve a estrutura já existente do fluxo.
- Aprofunde somente os trechos do pipeline de chat realmente suportados pelo código.
```

### Autonomia

```text
Refine incrementalmente a documentação da área "Autonomia" do projeto Janus.

[COLE AQUI O BLOCO "Modo de trabalho: refinamento incremental, nunca reescrita total."]

Escopo de código:
- backend/app/api/v1/endpoints/autonomy.py
- backend/app/services/autonomy_service.py
- backend/app/services/autonomy_admin_service.py
- backend/app/core/autonomy/*
- backend/app/core/workers/orchestrator.py

Foco:
- start/stop/status
- plan update
- policy update
- goals
- validation de passos
- runtime lock
- relação com workers e scheduler

Notas-alvo prováveis:
- 02 - Backend/Autonomia e Workers
- 04 - Fluxos End-to-End/Autonomia
- 07 - Glossário e Inventários/Inventário de Workers

Instrução crítica:
- Não apague o que já estiver correto sobre workers.
- Corrija localmente apenas onde o código mostrar nuance adicional ou contradição.
```

### Memória e RAG

```text
Refine incrementalmente a documentação da área "Memória, Conhecimento e RAG" do projeto Janus.

[COLE AQUI O BLOCO "Modo de trabalho: refinamento incremental, nunca reescrita total."]

Escopo de código:
- backend/app/services/knowledge_service.py
- backend/app/services/memory_service.py
- backend/app/services/rag_service.py
- backend/app/core/memory/*
- backend/app/db/graph.py
- backend/app/db/vector_store.py

Foco:
- papéis de Neo4j e Qdrant
- indexação
- recuperação
- consolidação
- self-memory
- codebase indexing
- uso em chat

Notas-alvo prováveis:
- 02 - Backend/Memória Conhecimento e RAG
- 04 - Fluxos End-to-End/Documentos Conhecimento e Memória
- 05 - Infra e Operação/Bancos Filas e Modelos

Instrução crítica:
- Preserve a explicação sistêmica já existente.
- Acrescente precisão sobre implementação e fluxos de dados sem recomeçar a nota do zero.
```

### Observabilidade

```text
Refine incrementalmente a documentação da área "Observabilidade" do projeto Janus.

[COLE AQUI O BLOCO "Modo de trabalho: refinamento incremental, nunca reescrita total."]

Escopo de código:
- backend/app/api/v1/endpoints/observability.py
- backend/app/services/observability_service.py
- backend/app/core/monitoring/*
- endpoints de workers/system status quando necessário

Foco:
- health agregado
- métricas
- poison pills
- SLO por domínio
- graph audit
- status de workers

Notas-alvo prováveis:
- 04 - Fluxos End-to-End/Observabilidade
- 05 - Infra e Operação/Healthchecks e Contratos Operacionais
- 06 - Qualidade e Testes/Contratos Cobertos

Instrução crítica:
- Não resuma demais a observabilidade.
- Expanda apenas os trechos onde o código revelar semântica adicional.
```

## Frontend

### Conversations

```text
Refine incrementalmente a documentação da área "Frontend Conversations" do projeto Janus.

[COLE AQUI O BLOCO "Modo de trabalho: refinamento incremental, nunca reescrita total."]

Escopo de código:
- frontend/src/app/features/conversations/conversations.ts
- serviços frontend usados por essa feature
- componentes compartilhados relevantes

Foco:
- responsabilidades reais da tela
- subfluxos embutidos
- integração com chat, docs, memória, RAG, autonomia e feedback
- estado local e concentração de complexidade

Notas-alvo prováveis:
- 03 - Frontend/Features e Experiência
- 04 - Fluxos End-to-End/Conversa e Chat
- 04 - Fluxos End-to-End/Documentos Conhecimento e Memória

Instrução crítica:
- Não substitua a descrição já existente da feature.
- Enriqueça-a com a decomposição real da tela.
```

### Auth

```text
Refine incrementalmente a documentação da área "Frontend Auth" do projeto Janus.

[COLE AQUI O BLOCO "Modo de trabalho: refinamento incremental, nunca reescrita total."]

Escopo de código:
- frontend/src/app/core/auth/auth.service.ts
- frontend/src/app/core/guards/auth.guard.ts
- frontend/src/app/features/auth/*
- interceptors relacionados quando impactarem o fluxo

Foco:
- inicialização da sessão
- armazenamento do token
- current user
- guards
- redirecionamento
- roles

Notas-alvo prováveis:
- 03 - Frontend/Guards Interceptors e Estado
- 04 - Fluxos End-to-End/Login e Identidade
- 03 - Frontend/Shell e Navegação

Instrução crítica:
- Preserve o fluxo já descrito.
- Corrija localmente apenas o que o código mostrar com mais exatidão.
```

### Frontend Observability

```text
Refine incrementalmente a documentação da área "Frontend Observability" do projeto Janus.

[COLE AQUI O BLOCO "Modo de trabalho: refinamento incremental, nunca reescrita total."]

Escopo de código:
- frontend/src/app/features/observability/observability.ts
- widgets da feature
- serviços frontend usados por essa tela

Foco:
- auto-refresh
- workers
- queues
- operator view
- limites da tela em relação à API

Notas-alvo prováveis:
- 03 - Frontend/Features e Experiência
- 04 - Fluxos End-to-End/Observabilidade

Instrução crítica:
- Não reestruture a nota inteira da feature.
- Aprofunde somente a parte observability da UI.
```

### Tools

```text
Refine incrementalmente a documentação da área "Tools" do projeto Janus.

[COLE AQUI O BLOCO "Modo de trabalho: refinamento incremental, nunca reescrita total."]

Escopo de código:
- frontend/src/app/features/tools/tools.ts
- frontend services relacionados
- backend/app/api/v1/endpoints/tools.py
- backend/app/services/tool_service.py
- backend/app/services/tool_executor_service.py
- backend/app/core/tools/*

Foco:
- catálogo
- categorias
- permissões
- criação dinâmica
- execução
- governança
- fronteira entre UI e backend executor

Notas-alvo prováveis:
- 04 - Fluxos End-to-End/Ferramentas e Sandbox
- 02 - Backend/API por Bounded Context
- 02 - Backend/Segurança e Infra

Instrução crítica:
- Preserve a documentação atual da governança.
- Só adicione o que o código provar.
```

## Infra

### PC1 / PC2

```text
Refine incrementalmente a documentação da área "PC1 / PC2" do projeto Janus.

[COLE AQUI O BLOCO "Modo de trabalho: refinamento incremental, nunca reescrita total."]

Escopo de código:
- docker-compose.pc1.yml
- docker-compose.pc2.yml
- backend/app/config.py

Foco:
- o que roda em cada host
- dependências entre hosts
- impacto operacional da divisão

Notas-alvo prováveis:
- 05 - Infra e Operação/PC1 PC2 e Docker
- 01 - Visão do Sistema/Topologia Runtime

Instrução crítica:
- Não reescreva as notas de operação por inteiro.
- Corrija e aprofunde somente a topologia e dependências reais.
```

### Bancos

```text
Refine incrementalmente a documentação da área "Bancos e persistência" do projeto Janus.

[COLE AQUI O BLOCO "Modo de trabalho: refinamento incremental, nunca reescrita total."]

Escopo de código:
- docker-compose.pc1.yml
- docker-compose.pc2.yml
- backend/app/db/*
- backend/app/repositories/*
- serviços dependentes de Postgres, Redis, Neo4j e Qdrant

Foco:
- papel de cada banco
- dependência por domínio
- impacto de indisponibilidade

Notas-alvo prováveis:
- 05 - Infra e Operação/Bancos Filas e Modelos
- 02 - Backend/Repositórios e Modelos
- 02 - Backend/Memória Conhecimento e RAG

Instrução crítica:
- Preserve o mapa existente.
- Apenas torne a relação banco -> domínio mais precisa.
```

### Workers

```text
Refine incrementalmente a documentação da área "Workers" do projeto Janus.

[COLE AQUI O BLOCO "Modo de trabalho: refinamento incremental, nunca reescrita total."]

Escopo de código:
- backend/app/core/workers/*
- backend/app/core/kernel.py
- backend/app/api/v1/endpoints/workers.py
- contrato de runtime de workers quando visível

Foco:
- workers por arquivo
- workers/tarefas observadas em runtime
- boot, scheduler e orquestração
- diferenças entre nome de módulo e nome reportado

Notas-alvo prováveis:
- 02 - Backend/Autonomia e Workers
- 07 - Glossário e Inventários/Inventário de Workers
- 05 - Infra e Operação/Healthchecks e Contratos Operacionais

Instrução crítica:
- Não apagar o inventário atual.
- Complemente-o com a distinção entre código e runtime.
```

### Deploy

```text
Refine incrementalmente a documentação da área "Deploy e operação" do projeto Janus.

[COLE AQUI O BLOCO "Modo de trabalho: refinamento incremental, nunca reescrita total."]

Escopo de código:
- docker-compose.pc1.yml
- docker-compose.pc2.yml
- backend/app/main.py
- endpoints de health/system/workers

Foco:
- readiness
- healthchecks
- restart policies
- variáveis críticas
- critérios mínimos de operação

Notas-alvo prováveis:
- 05 - Infra e Operação/Healthchecks e Contratos Operacionais
- 05 - Infra e Operação/PC1 PC2 e Docker
- 06 - Qualidade e Testes/Checklist de Validação

Instrução crítica:
- Não substitua o checklist atual.
- Apenas refine o contrato operacional real.
```

## Fluxos

### Login

```text
Refine incrementalmente a documentação do fluxo "Login e Identidade" do projeto Janus.

[COLE AQUI O BLOCO "Modo de trabalho: refinamento incremental, nunca reescrita total."]

Escopo de código:
- frontend auth
- frontend guards
- backend auth endpoints
- criação/validação de token

Foco:
- emissão de token
- persistência de sessão
- carregamento do usuário
- proteção de rotas

Nota-alvo principal:
- 04 - Fluxos End-to-End/Login e Identidade

Notas secundárias possíveis:
- 03 - Frontend/Guards Interceptors e Estado
- 02 - Backend/Segurança e Infra

Instrução crítica:
- Atualize o fluxo existente; não reescreva a narrativa inteira.
```

### Chat

```text
Refine incrementalmente a documentação do fluxo "Conversa e Chat" do projeto Janus.

[COLE AQUI O BLOCO "Modo de trabalho: refinamento incremental, nunca reescrita total."]

Escopo de código:
- frontend conversations
- services frontend de chat
- endpoints backend de chat
- chat service, streaming, routing, citation e pending actions

Foco:
- caminho ponta a ponta
- fronteiras entre UI, API e serviços
- falhas e confirmações

Nota-alvo principal:
- 04 - Fluxos End-to-End/Conversa e Chat

Notas secundárias possíveis:
- 03 - Frontend/Serviços de Integração
- 02 - Backend/LLM Routing e Prompts

Instrução crítica:
- Preserve o fluxo já escrito.
- Só aumente precisão e profundidade local.
```

### Autonomia

```text
Refine incrementalmente a documentação do fluxo "Autonomia" do projeto Janus.

[COLE AQUI O BLOCO "Modo de trabalho: refinamento incremental, nunca reescrita total."]

Escopo de código:
- frontend de autonomia
- endpoints/serviços de autonomia
- goal manager
- workers/scheduler ligados ao fluxo

Foco:
- metas
- plano
- políticas
- locks
- execução contínua

Nota-alvo principal:
- 04 - Fluxos End-to-End/Autonomia

Notas secundárias possíveis:
- 02 - Backend/Autonomia e Workers
- 07 - Glossário e Inventários/Inventário de Workers

Instrução crítica:
- Não troque a estrutura da nota.
- Corrija e aprofunde só os trechos afetados pela leitura do código.
```

### Docs / Memória

```text
Refine incrementalmente a documentação do fluxo "Documentos, Conhecimento e Memória" do projeto Janus.

[COLE AQUI O BLOCO "Modo de trabalho: refinamento incremental, nunca reescrita total."]

Escopo de código:
- frontend conversations nos trechos de docs/memory/rag
- endpoints documents, memory e rag
- services de ingestão, knowledge, memory e rag

Foco:
- upload e link
- indexação
- enriquecimento
- busca
- uso em resposta

Nota-alvo principal:
- 04 - Fluxos End-to-End/Documentos Conhecimento e Memória

Notas secundárias possíveis:
- 02 - Backend/Memória Conhecimento e RAG
- 05 - Infra e Operação/Bancos Filas e Modelos

Instrução crítica:
- Preserve o mapa atual.
- Amplie só o fluxo que o código realmente demonstrar.
```

### Ferramentas

```text
Refine incrementalmente a documentação do fluxo "Ferramentas e Sandbox" do projeto Janus.

[COLE AQUI O BLOCO "Modo de trabalho: refinamento incremental, nunca reescrita total."]

Escopo de código:
- feature tools no frontend
- endpoints tools/sandbox
- tool_service
- tool_executor_service
- core/tools

Foco:
- catálogo
- governança
- execução
- confirmação
- sandbox

Nota-alvo principal:
- 04 - Fluxos End-to-End/Ferramentas e Sandbox

Notas secundárias possíveis:
- 02 - Backend/Segurança e Infra
- 02 - Backend/API por Bounded Context

Instrução crítica:
- Não simplifique demais a governança.
- Faça refinamento cumulativo, não reescrita.
```
