---
tipo: visao
dominio: sistema
camada: integracoes
fonte-de-verdade: codigo
status: ativo
---

# Dependências Externas

## Objetivo
Consolidar os sistemas externos que o Janus precisa para operar.

## Responsabilidades
- Separar dependências obrigatórias de opcionais.
- Ligar cada recurso ao domínio que ele sustenta.

## Entradas
- Compose.
- Configuração pydantic.
- Serviços centrais.

## Saídas
- Mapa de integração externa.

## Dependências
- [[05 - Infra e Operação/Bancos Filas e Modelos]]
- [[07 - Glossário e Inventários/Inventário de Integrações Externas]]

## Dependências obrigatórias
- Postgres: dados operacionais, contratos SQL, chat repository SQL.
- Redis: suporte infra, rate/control/cache managers.
- RabbitMQ: filas e execução assíncrona.
- Neo4j: grafo de conhecimento.
- Qdrant: memória vetorial e recuperação semântica.

## Dependências contextuais
- Ollama: modelos locais.
- OpenAI, Gemini, DeepSeek, xAI, OpenRouter: inferência cloud.
- Firebase: opcional, ativado por flag.
- LangSmith: tracing, se configurado.

## Arquivos-fonte
- `backend/app/config.py`
- `backend/app/core/kernel.py`
- `backend/app/services/knowledge_service.py`
- `backend/app/services/llm_service.py`
- `docker-compose.pc1.yml`
- `docker-compose.pc2.yml`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Conversa e Chat]]
- [[04 - Fluxos End-to-End/Documentos Conhecimento e Memória]]
- [[04 - Fluxos End-to-End/Observabilidade]]

## Riscos/Lacunas
- O sistema mistura provedores locais e cloud, então custo, latência e disponibilidade variam por política.
