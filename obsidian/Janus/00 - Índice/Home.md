---
tipo: indice
dominio: sistema
camada: navegacao
fonte-de-verdade: codigo
status: ativo
---

# Home

## Objetivo
Ser a porta de entrada para entender o Janus a partir da implementação real.

## Responsabilidades
- Apontar para a espinha dorsal do sistema.
- Organizar a leitura por domínio, fluxo e operação.
- Explicitar onde a verdade está no código.

## Entradas
- Estrutura do monorepo.
- Entry points do backend, frontend e compose.

## Saídas
- Navegação inicial do vault.
- Roteiro de leitura por profundidade.

## Dependências
- [[00 - Índice/Mapa Mestre do Sistema]]
- [[00 - Índice/Mapa por Domínio]]
- [[00 - Índice/Mapa por Fluxos Críticos]]

## Arquivos-fonte
- `backend/app/main.py`
- `backend/app/core/kernel.py`
- `backend/app/api/v1/router.py`
- `frontend/src/app/app.routes.ts`
- `frontend/src/app/services/backend-api.service.ts`
- `docker-compose.pc1.yml`
- `docker-compose.pc2.yml`

## Leituras principais
- Visão sistêmica: [[01 - Visão do Sistema/Arquitetura Geral]]
- Boot e runtime: [[01 - Visão do Sistema/Sequência de Boot]], [[01 - Visão do Sistema/Topologia Runtime]]
- Backend: [[02 - Backend/Como o Backend Pensa]]
- Frontend: [[03 - Frontend/Shell e Navegação]]
- Fluxos críticos: [[04 - Fluxos End-to-End/Conversa e Chat]], [[04 - Fluxos End-to-End/Autonomia]]
- Operação: [[05 - Infra e Operação/PC1 PC2 e Docker]]
- Qualidade: [[06 - Qualidade e Testes/Mapa de Testes]]

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Login e Identidade]]
- [[04 - Fluxos End-to-End/Observabilidade]]

## Riscos/Lacunas
- O sistema é maior que a superfície usada pelo frontend atual.
- Alguns módulos existem como capacidade de plataforma, mas não estão expostos igualmente na UI.
