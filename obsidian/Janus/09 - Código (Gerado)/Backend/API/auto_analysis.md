---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/auto_analysis.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# auto_analysis

## Objetivo
Auto-análise do Janus - Um jeito simples do sistema se entender melhor

## Arquivos-fonte
- `backend/app/api/v1/endpoints/auto_analysis.py`

## Rotas
- `GET /health-check`

## Dependências de código
- Serviços
  - `observability_service`

## Símbolos
- class: `HealthInsight`
- class: `AutoAnalysisResponse`
- function: `auto_analyze(observability: ObservabilityService = Depends(get_observability_service))` -> `AutoAnalysisResponse`
  - O Janus olha para si mesmo e diz: "Como estou me saindo?"
- function: `_analyze_api_costs()` -> `HealthInsight | None`
  - Analisa gastos recentes com APIs usando dados reais do sistema
- function: `_analyze_performance(observability: ObservabilityService)` -> `HealthInsight | None`
  - Analisa performance geral
- function: `_analyze_response_quality()` -> `HealthInsight | None`
  - Analisa qualidade das respostas
- function: `_generate_fun_fact()` -> `str`
  - Gera um fato divertido sobre o sistema
- function: `_calculate_overall_health(insights: list)` -> `str`
  - Calcula saúde geral baseado nos insights

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
