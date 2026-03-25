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
- Redis
- RabbitMQ
- Neo4j
- Qdrant
- Ollama
- OpenAI
- Gemini
- DeepSeek
- xAI
- OpenRouter
- Firebase
- LangSmith

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
