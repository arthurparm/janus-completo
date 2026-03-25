---
tipo: operacao
dominio: infra
camada: deploy
fonte-de-verdade: codigo
status: ativo
---

# PC1 PC2 e Docker

## Objetivo
Registrar a divisão física e lógica de deploy do Janus.

## Responsabilidades
- Explicar o que roda em cada máquina.
- Ligar compose a responsabilidades operacionais.

## Entradas
- `docker-compose.pc1.yml`
- `docker-compose.pc2.yml`

## Saídas
- Plano de entendimento de deploy.

## Dependências
- [[01 - Visão do Sistema/Topologia Runtime]]
- [[05 - Infra e Operação/Bancos Filas e Modelos]]

## PC1
- `janus-api`
- `janus-frontend`
- `postgres`
- `redis`
- `rabbitmq`

## PC2
- `neo4j`
- `qdrant`
- `ollama`
- `ollama-model-init`

## Leitura operacional
- PC1 carrega aplicação e persistência operacional.
- PC2 concentra recursos cognitivos de maior peso e memória.

## Arquivos-fonte
- `docker-compose.pc1.yml`
- `docker-compose.pc2.yml`

## Fluxos relacionados
- [[05 - Infra e Operação/Healthchecks e Contratos Operacionais]]
- [[07 - Glossário e Inventários/Inventário de Integrações Externas]]

## Riscos/Lacunas
- O deploy distribuído aumenta sensibilidade à conectividade entre hosts.
