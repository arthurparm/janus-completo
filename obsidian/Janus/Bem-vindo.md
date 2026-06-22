---
tipo: indice
dominio: vault
camada: navegacao
fonte-de-verdade: codigo
status: ativo
---

# Bem-vindo

## Em uma frase
Este vault existe para qualquer pessoa entender o que o Janus faz, como ele roda e como ele falha.

## O que é o Janus
- Um sistema de chat e automação (“agentic”) usado internamente.
- Ele tem:
  - Frontend Angular (interface do operador)
  - Backend FastAPI (API e motor de execução)
  - Workers assíncronos (tarefas em filas e loops)
  - Infra distribuída (PC1/PC2): Postgres/Redis/RabbitMQ/Neo4j/Qdrant/Ollama

## Onde começar
- Ponto de entrada: [[00 - Índice/Home]]
- Mapa único do sistema: [[00 - Índice/Mapa Mestre do Sistema]]

## Referências de código (onde a verdade está)
- `backend/app/main.py`
- `backend/app/core/kernel.py`
- `frontend/src/app/app.routes.ts`
- `docker-compose.pc1.yml`
- `docker-compose.pc2.yml`

## Riscos/Lacunas
- O vault depende de manutenção conforme o código evolui.
