---
tipo: fluxo
dominio: observabilidade
camada: end-to-end
fonte-de-verdade: codigo
status: ativo
---

# Observabilidade

## Objetivo
Mapear a visão operacional de saúde, filas e anomalias.

## Responsabilidades
- Cobrir dashboard frontend e endpoints backend.
- Ligar saúde lógica a dependências infra.

## Entradas
- Health checks.
- Status de workers.
- Métricas e poison pills.

## Saídas
- Visão de operador.
- Alertas e relatórios de SLO.

## Dependências
- [[02 - Backend/Segurança e Infra]]
- [[05 - Infra e Operação/Healthchecks e Contratos Operacionais]]

## Sequência
1. Tela `observability` abre e inicia refresh periódico.
2. Frontend consulta workers e filas.
3. Backend expõe health agregado, componentes, poison pills, SLO por domínio e auditoria de grafo.
4. ObservabilityService consolida estado do sistema.

## Arquivos-fonte
- `frontend/src/app/features/observability/observability.ts`
- `backend/app/api/v1/endpoints/observability.py`
- `backend/app/services/observability_service.py`
- `backend/app/core/monitoring/*`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Conversa e Chat]]
- [[04 - Fluxos End-to-End/Documentos Conhecimento e Memória]]

## Riscos/Lacunas
- A UI mostra parte da observabilidade; a API oferece mais profundidade que a tela atual.
