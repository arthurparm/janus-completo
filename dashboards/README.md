# Dashboard de Resiliência de Componentes do Janus

Este documento detalha o dashboard Grafana `Janus - Component Resilience`, projetado para monitorar a saúde e a resiliência dos componentes da aplicação Janus. O dashboard utiliza métricas expostas pelo Prometheus para visualizar a latência, a taxa de erros e o estado dos Circuit Breakers.

## Visão Geral

O dashboard está organizado em duas seções principais:

1.  **Latency (Latência)**: Mede o tempo de resposta das operações nos componentes.
2.  **Reliability (Confiabilidade)**: Acompanha a taxa de sucesso das operações e o comportamento dos Circuit Breakers.

### Filtros

O dashboard permite a filtragem por `Component/Operation`, possibilitando a análise de um componente específico ou de todos eles.

## Paineis do Dashboard

### Latency

-   **p95 Latency (s)**: Exibe o 95º percentil da latência das operações. Isso significa que 95% das requisições são mais rápidas que o valor mostrado. É uma métrica importante para entender o desempenho da "maioria" dos usuários.
-   **p99 Latency (s)**: Mostra o 99º percentil da latência. Este valor representa o pior desempenho que um pequeno percentual de usuários experimenta e é crucial para identificar outliers e problemas de cauda longa.

### Reliability

-   **Error Rate (%)**: Calcula a porcentagem de operações que resultaram em falha. É um indicador direto da saúde do componente.
-   **Current CB OPEN (0/1)**: Monitora o estado dos Circuit Breakers. O valor `1` (vermelho) indica que o Circuit Breaker está no estado "Aberto", o que significa que as chamadas para o componente foram interrompidas devido a falhas excessivas. O valor `0` (verde) indica que o circuito está "Fechado" ou "Meio-Aberto".
-   **CB Open Duration (s)**: Mede por quanto tempo um Circuit Breaker permaneceu no estado "Aberto". Períodos prolongados podem indicar problemas graves e persistentes no componente.

## Métricas Utilizadas

O dashboard é alimentado pelas seguintes métricas do Prometheus:

-   `janus_resilience_attempt_latency_seconds_bucket`: Histograma da latência das tentativas de operação, usado para calcular os percentis p95 e p99.
-   `janus_resilience_attempt_latency_seconds_count`: Contador do número total de tentativas de operação, com labels para `operation` e `outcome` (sucesso/falha).
-   `janus_resilience_circuit_state`: O estado atual do Circuit Breaker (`OPEN`, `CLOSED`, `HALF_OPEN`).
-   `janus_resilience_open_time_seconds`: O tempo que o Circuit Breaker passou no estado `OPEN`.
