---
tipo: inventario
dominio: infra
camada: referencia
fonte-de-verdade: codigo
status: ativo
---

# Inventário de Integrações Externas

## Objetivo
Consolidar os endpoints e recursos externos usados pelo sistema.

## Responsabilidades
- Relacionar integração a função operacional.

## Entradas
- Configuração e compose.

## Saídas
- Índice de integrações.

## Dependências
- [[01 - Visão do Sistema/Dependências Externas]]
- [[05 - Infra e Operação/Bancos Filas e Modelos]]

## Integrações
- Postgres
  - host principal no deploy: PC1
  - papel: fonte transacional de identidade, chat, autonomia, manifests, knowledge spaces, outbox e prompts
- Redis
  - host principal no deploy: PC1
  - papel: rate limit, Pub/Sub de config e spend/quota temporária
- RabbitMQ
  - host principal no deploy: PC1
  - papel: broker assíncrono para workers
- Neo4j
  - host principal no deploy: PC2
  - papel: conhecimento estruturado, code graph, self-memory e estrutura de knowledge spaces
- Qdrant
  - host principal no deploy: PC2
  - papel: memória vetorial, documentos, preferências, regras, segredos e fila implícita da consolidação
- Ollama
  - host principal no deploy: PC2
  - papel: inferência local
- OpenAI
  - papel: provider contextual de LLM/embeddings conforme roteamento
- Gemini
  - papel: provider contextual de LLM conforme roteamento
- DeepSeek
  - papel: provider contextual de LLM conforme roteamento
- xAI
  - papel: provider contextual de LLM conforme roteamento
- OpenRouter
  - papel: provider contextual de LLM/embeddings conforme roteamento
- Firebase
  - papel: integração opcional por feature flag
- LangSmith
  - papel: tracing opcional

## Arquivos-fonte
- `backend/app/config.py`
- `docker-compose.pc1.yml`
- `docker-compose.pc2.yml`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Conversa e Chat]]
- [[04 - Fluxos End-to-End/Documentos Conhecimento e Memória]]
- [[04 - Fluxos End-to-End/Observabilidade]]

## Riscos/Lacunas
- Parte das integrações é opcional por ambiente, mas o código já prevê sua presença.
- A documentação operacional precisa distinguir integração de plano transacional, coordenação, vetor, grafo e inferência; apenas listar nomes não explica o impacto de falha.
