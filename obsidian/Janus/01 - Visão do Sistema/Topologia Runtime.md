---
tipo: visao
dominio: sistema
camada: runtime
fonte-de-verdade: codigo
status: ativo
---

# Topologia Runtime

## Objetivo
Descrever a topologia real do runtime distribuído e separar dependências locais de PC1 das dependências remotas apontadas para PC2.

## Responsabilidades
- Separar PC1 e PC2.
- Mostrar dependências duras e opcionais.

## Entradas
- `docker-compose.pc1.yml`
- `docker-compose.pc2.yml`

## Saídas
- Modelo operacional do runtime distribuído.
- Grafo de dependências entre hosts.

## Dependências
- [[05 - Infra e Operação/PC1 PC2 e Docker]]
- [[05 - Infra e Operação/Bancos Filas e Modelos]]

## Topologia
- PC1:
  - expõe a aplicação (`janus-api`, `janus-frontend`)
  - concentra estado transacional e coordenação local (`postgres`, `redis`, `rabbitmq`)
  - monta volumes de dados e workspace consumidos pela API
- PC2:
  - concentra persistência cognitiva e capacidade de IA (`neo4j`, `qdrant`, `ollama`)
  - executa `ollama-model-init` apenas como inicialização de modelos

## Grafo de dependências
- `janus-frontend` -> `janus-api`
- `janus-api` -> `postgres`
- `janus-api` -> `redis`
- `janus-api` -> `rabbitmq`
- `janus-api` -> `neo4j` no PC2 via `NEO4J_URI`
- `janus-api` -> `qdrant` no PC2 via `QDRANT_HOST` e `QDRANT_API_KEY`
- `janus-api` -> `ollama` no PC2 via `OLLAMA_HOST`
- `ollama-model-init` -> `ollama`

## Dependências por domínio
- Chat e identidade:
  - Postgres como persistência primária
  - Qdrant como contexto vetorial complementar
- Autonomia:
  - Postgres para runs, steps, goals, self-study state e leases
  - Qdrant para memória episódica/self-study
  - Neo4j para self-memory e conhecimento estrutural derivado
- Documentos e knowledge spaces:
  - Postgres para manifesto e estado do knowledge space
  - Qdrant para chunks e seções canônicas indexadas
  - Neo4j para projeção estrutural do knowledge space consolidado
- Governança operacional:
  - Redis para rate limit, Pub/Sub e spend/quota temporária
  - Postgres para quotas diárias de tools, outbox e pending actions

## Defaults locais vs deploy distribuído
- O `config.py` parte de defaults de descoberta local por nome de serviço:
  - `bolt://neo4j:7687`
  - `qdrant:6333`
  - `http://ollama:11434`
- O `docker-compose.pc1.yml` substitui esse cenário por endereçamento remoto obrigatório para PC2.
- Na prática, o runtime distribuído não nasce do código sozinho; ele nasce da combinação entre defaults do `AppSettings` e overrides obrigatórios do compose de PC1.

## Leitura operacional
- O backend só tem bloqueio de boot explícito para `postgres`, `redis` e `rabbitmq`.
- Neo4j, Qdrant e Ollama são dependências remotas mandatórias de configuração, mas não entram em `depends_on` porque vivem fora do host PC1.
- O frontend tem dependência estrita do healthcheck do `janus-api`.
- O deploy resultante é assimétrico: disponibilidade transacional do produto depende de PC1; persistência cognitiva e recursos de memória dependem de PC2.

## Efeito de falha resumido
- Falha em Postgres: quebra fonte de verdade transacional e parte do estado do orquestrador.
- Falha em Redis: degrada coordenação e proteção, mas não remove a persistência canônica.
- Falha em Qdrant: remove recuperação vetorial e pipelines de memória/documento.
- Falha em Neo4j: remove recuperação estrutural, code graph e self-memory.

## Arquivos-fonte
- `docker-compose.pc1.yml`
- `docker-compose.pc2.yml`
- `backend/app/config.py`

## Fluxos relacionados
- [[01 - Visão do Sistema/Dependências Externas]]
- [[05 - Infra e Operação/Healthchecks e Contratos Operacionais]]

## Riscos/Lacunas
- O sistema depende de rede estável entre PC1 e PC2 para todas as funções de grafo, vetor e inferência local.
- Como o Compose de PC1 não observa a saúde de PC2, falhas remotas podem aparecer apenas como erro funcional em runtime.
- A diferença entre defaults do `config.py` e overrides obrigatórios do compose torna perigoso assumir topologia single-host a partir do código isolado.
