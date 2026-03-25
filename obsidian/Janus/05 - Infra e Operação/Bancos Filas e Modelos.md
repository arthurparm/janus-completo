---
tipo: operacao
dominio: infra
camada: dependencias
fonte-de-verdade: codigo
status: ativo
---

# Bancos Filas e Modelos

## Objetivo
Mapear cada recurso infra ao papel sistêmico que ele cumpre.

## Responsabilidades
- Dizer “quem serve a quem”.
- Explicar impacto de indisponibilidade.

## Entradas
- Compose.
- `AppSettings`.
- Serviços centrais.

## Saídas
- Matriz componente -> recurso -> impacto.

## Dependências
- [[01 - Visão do Sistema/Dependências Externas]]
- [[05 - Infra e Operação/PC1 PC2 e Docker]]

## Matriz
- Postgres:
  - serve chat SQL, config/data, contratos persistidos
  - impacto: perda de operações transacionais e parte da API
- Redis:
  - serve rate control, caches e suporte infra
  - impacto: degradação de performance e controle
- RabbitMQ:
  - serve workers e filas
  - impacto: perda de processamento assíncrono
- Neo4j:
  - serve grafo de conhecimento
  - impacto: perda de parte da busca estrutural e auditoria do grafo
- Qdrant:
  - serve memória vetorial
  - impacto: degradação de RAG/memória semântica
- Ollama:
  - serve inferência local
  - impacto: perda de modo local_only e fallback local

## Arquivos-fonte
- `backend/app/config.py`
- `backend/app/core/kernel.py`
- `backend/app/services/knowledge_service.py`
- `docker-compose.pc1.yml`
- `docker-compose.pc2.yml`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Conversa e Chat]]
- [[04 - Fluxos End-to-End/Autonomia]]

## Riscos/Lacunas
- O sistema depende de múltiplas tecnologias de persistência; diagnósticos exigem leitura cruzada.
