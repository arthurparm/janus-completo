---
tipo: qualidade
dominio: testes
camada: riscos
fonte-de-verdade: codigo
status: ativo
---

# Lacunas e Riscos

## Objetivo
Registrar as fragilidades percebidas a partir do código e da cobertura.

## Responsabilidades
- Sinalizar acoplamentos altos.
- Sinalizar zonas de baixa visibilidade.

## Entradas
- Leitura estrutural do backend/frontend.
- Inventário de testes.

## Saídas
- Backlog técnico de risco arquitetural.

## Dependências
- [[06 - Qualidade e Testes/Mapa de Testes]]
- [[02 - Backend/Como o Backend Pensa]]

## Riscos principais
- `BackendApiService` concentra contratos demais.
- `ConversationsComponent` concentra subfluxos demais.
- O kernel compõe quase tudo manualmente.
- O deploy distribuído PC1/PC2 aumenta superfície de falha.
- Capacidades internas do backend são maiores que a UX operacional atual.

## Lacunas percebidas
- Pouca evidência de E2E de UX completa.
- Diferença potencial entre saúde de container e saúde lógica.
- Parte das integrações de LLM/local runtime depende fortemente de configuração.

## Arquivos-fonte
- `backend/app/core/kernel.py`
- `frontend/src/app/features/conversations/conversations.ts`
- `frontend/src/app/services/backend-api.service.ts`
- `qa/*.py`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Conversa e Chat]]
- [[05 - Infra e Operação/Healthchecks e Contratos Operacionais]]

## Riscos/Lacunas
- Esta nota é deliberadamente viva e deve crescer conforme incidentes reais forem mapeados.
