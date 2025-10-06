# Sprint 7: Despertar da Proatividade - Ciclo de Auto-Otimização

## 📋 Visão Geral

A Sprint 7 implementa o **sistema de auto-otimização proativa**, capacitando o Janus a tomar iniciativa para se
aperfeiçoar autonomamente, sem intervenção humana. O sistema monitora continuamente seu próprio desempenho, identifica
gargalos, planeja melhorias e as executa de forma autônoma.

## 🎯 Objetivos Alcançados

### 1. **Sistema de Auto-Otimização Completo** (`app/core/self_optimization.py`)

#### Componentes Principais:

##### **SystemMonitor**

Monitora continuamente a saúde e performance do sistema:

```python
class SystemMonitor:
    async def collect_metrics(self) -> SystemMetrics:
        """Coleta métricas de performance"""

    def detect_issues(self) -> List[DetectedIssue]:
        """Detecta problemas no sistema"""

    def _calculate_health_score(self, metrics) -> float:
        """Calcula score de saúde (0.0-1.0)"""
```

**Métricas Coletadas:**

- Tempo médio de resposta de ferramentas
- Taxa de erro geral
- Taxa de sucesso por ferramenta
- Uso de memória
- Ferramentas falhando
- Ferramentas lentas

**Problemas Detectáveis:**

- `PERFORMANCE_DEGRADATION`: Performance piorando ao longo do tempo
- `HIGH_ERROR_RATE`: Taxa de erro acima de 20%
- `TOOL_FAILURE`: Ferramentas com <80% de taxa de sucesso
- `SLOW_RESPONSE`: Ferramentas com >2s de tempo médio
- `MEMORY_LEAK`: Uso de memória crescente
- `RESOURCE_EXHAUSTION`: Recursos se esgotando

##### **ImprovementPlanner**

Analisa problemas e planeja melhorias específicas:

```python
class ImprovementPlanner:
    async def plan_improvements(
        self,
        issues: List[DetectedIssue],
        metrics: SystemMetrics
    ) -> List[PlannedImprovement]:
        """Planeja melhorias baseadas em problemas"""
```

**Tipos de Melhorias:**

- `OPTIMIZE_TOOL`: Otimizar ferramenta específica
- `ADD_CACHING`: Adicionar caching para reduzir latência
- `INCREASE_TIMEOUT`: Ajustar timeouts
- `REDUCE_COMPLEXITY`: Simplificar lógica complexa
- `FIX_CONFIGURATION`: Corrigir configurações
- `REFACTOR_LOGIC`: Refatorar tratamento de erros

**Priorização Inteligente:**

```python
def _priority_score(self, improvement, issues) -> float:
    """
    Prioridade = Severidade do Problema - Risco da Solução

    Exemplo:
    - Problema crítico (severidade=0.9) + solução segura (risco=0.2) = Alta prioridade
    - Problema leve (severidade=0.3) + solução arriscada (risco=0.8) = Baixa prioridade
    """
```

##### **ImprovementExecutor**

Executa melhorias de forma autônoma e segura:

```python
class ImprovementExecutor:
    async def execute_improvement(
        self,
        improvement: PlannedImprovement
    ) -> AppliedImprovement:
        """Executa melhoria usando agente"""
```

**Processo de Execução:**

1. Gera prompt detalhado para o agente
2. Agente executa passos sistematicamente
3. Valida cada mudança antes de aplicar
4. Documenta resultado
5. Memoriza experiência para aprendizado futuro

##### **SelfOptimizationCycle**

Ciclo completo de auto-otimização:

```
MONITOR → DETECT → PLAN → EXECUTE → LEARN
   ↑                                    ↓
   └────────────────────────────────────┘
```

```python
class SelfOptimizationCycle:
    async def run_cycle(self) -> Dict[str, Any]:
        """
        1. MONITOR: Coleta métricas
        2. DETECT: Identifica problemas
        3. PLAN: Planeja melhorias
        4. EXECUTE: Aplica melhorias
        5. LEARN: Avalia e memoriza resultado
        """

    async def run_continuous(self, interval_seconds=300):
        """Executa continuamente a cada 5 minutos"""
```

### 2. **API REST para Auto-Otimização** (`app/api/v1/endpoints/optimization.py`)

#### `POST /api/v1/optimization/run-cycle`

Executa ciclo completo de auto-otimização.

**Response:**

```json
{
  "success": true,
  "issues_detected": 3,
  "improvements_planned": 2,
  "improvements_applied": 2,
  "elapsed_seconds": 45.3
}
```

#### `GET /api/v1/optimization/health`

Retorna métricas de saúde do sistema.

**Response:**

```json
{
  "health_score": 0.85,
  "avg_response_time": 0.45,
  "error_rate": 0.05,
  "tool_success_rate": 0.95,
  "active_tools_count": 15,
  "failed_tools": ["faulty_calculator"],
  "slow_tools": ["slow_database_query"]
}
```

#### `GET /api/v1/optimization/issues`

Lista problemas detectados.

**Response:**

```json
[
  {
    "issue_type": "tool_failure",
    "severity": 0.7,
    "description": "Ferramenta 'faulty_calculator' com alta taxa de falha",
    "affected_component": "faulty_calculator",
    "detected_at": 1704826800.0
  },
  {
    "issue_type": "slow_response",
    "severity": 0.5,
    "description": "Ferramenta 'slow_database_query' respondendo lentamente",
    "affected_component": "slow_database_query",
    "detected_at": 1704826801.0
  }
]
```

#### `GET /api/v1/optimization/metrics/history`

Retorna histórico de métricas (série temporal).

#### `GET /api/v1/optimization/status`

Health check do módulo.

### 3. **Métricas Prometheus**

Sistema expõe métricas detalhadas:

```python
# Contadores
self_optimization_cycles_total{outcome}
self_optimization_improvements_total{improvement_type}

# Histogramas
self_optimization_latency_seconds

# Gauge
self_optimization_health_score  # 0.0-1.0
```

### 4. **Cálculo de Health Score**

Fórmula do score de saúde (0.0-1.0):

```
Health Score = (Success Rate × 0.4) + (Response Score × 0.3) + (Error Score × 0.3)

Onde:
- Success Rate: Taxa de sucesso das ferramentas
- Response Score: max(0, 1 - (avg_response_time / 2.0))
- Error Score: 1 - error_rate

Exemplo:
- 95% sucesso → 0.38
- 0.5s resposta → 0.225
- 5% erro → 0.285
= Health Score: 0.89 ✓ Sistema saudável
```

## 🏗️ Arquitetura do Ciclo

```
┌─────────────────────────────────────────────────────────────┐
│              SelfOptimizationCycle                          │
│                                                             │
│  ┌───────────┐   ┌──────────┐   ┌─────────┐   ┌──────────┐│
│  │  MONITOR  │──>│  DETECT  │──>│  PLAN   │──>│ EXECUTE  ││
│  │ (metrics) │   │ (issues) │   │ (impr.) │   │ (apply)  ││
│  └───────────┘   └──────────┘   └─────────┘   └──────────┘│
│       ▲                                              │      │
│       │                                              ▼      │
│       │              ┌──────────┐                          │
│       └──────────────│  LEARN   │──────────────────────────┘
│                      │(memorize)│
│                      └──────────┘
│                           │
│                           ▼
│                   ┌──────────────┐
│                   │    Memory    │
│                   │   (Qdrant)   │
│                   └──────────────┘
└─────────────────────────────────────────────────────────────┘
```

## 📊 Exemplo de Ciclo Completo

### Cenário: Ferramenta com Alta Taxa de Falha

**1. MONITOR** - Coleta Métricas:

```python
{
    "avg_response_time": 0.8,
    "error_rate": 0.25,  # 25% de erros!
    "tool_success_rate": 0.75,
    "failed_tools": ["unreliable_weather_api"]
}
```

**2. DETECT** - Identifica Problema:

```python
DetectedIssue(
    issue_type=IssueType.TOOL_FAILURE,
    severity=0.7,
    description="Ferramenta 'unreliable_weather_api' com alta taxa de falha",
    affected_component="unreliable_weather_api",
    evidence={"tool": "unreliable_weather_api"}
)
```

**3. PLAN** - Planeja Melhoria:

```python
PlannedImprovement(
    improvement_type=ImprovementType.FIX_CONFIGURATION,
    target_component="unreliable_weather_api",
    description="Ajustar configuração da ferramenta 'unreliable_weather_api'",
    expected_impact="Reduzir taxa de falha em 50%",
    implementation_steps=[
        "Analisar últimas falhas de 'unreliable_weather_api'",
        "Identificar causa raiz (timeout, parâmetros, etc)",
        "Ajustar configuração apropriadamente",
        "Validar com testes"
    ],
    risk_level=0.3  # Baixo risco
)
```

**4. EXECUTE** - Aplica Melhoria:

```
Agente analisa falhas recentes...
Identifica: Timeouts frequentes (30% das falhas)
Solução: Aumentar timeout de 5s para 10s
Aplica: Atualiza configuração
Valida: Executa 10 testes → 9 sucessos (90%)
```

**5. LEARN** - Memoriza Resultado:

```python
Experience(
    type="self_optimization",
    content="Melhoria aplicada: Ajustar configuração de 'unreliable_weather_api'\n
             Sucesso: True\n
             Resultado: Taxa de sucesso aumentou de 60% para 90%",
    metadata={
        "improvement_type": "fix_configuration",
        "target": "unreliable_weather_api",
        "success": True
    }
)
```

## 🧪 Casos de Uso

### Caso 1: Ferramenta Lenta

**Sintoma:** `search_web` levando >2s em média

**Detecção Automática:**

```python
IssueType.SLOW_RESPONSE
Severity: 0.5
```

**Melhoria Planejada:**

```python
ImprovementType.ADD_CACHING
Steps:
1. Identificar consultas frequentes
2. Implementar cache LRU com TTL=300s
3. Validar que cache não quebra resultados
4. Monitorar hit rate
```

**Resultado Esperado:**

- Redução de 70% no tempo médio
- Hit rate de cache ~60%

### Caso 2: Taxa de Erro Alta

**Sintoma:** Sistema com 25% de taxa de erro

**Detecção Automática:**

```python
IssueType.HIGH_ERROR_RATE
Severity: 0.8 (crítico!)
```

**Melhoria Planejada:**

```python
ImprovementType.REFACTOR_LOGIC
Steps:
1. Analisar padrões de erro mais comuns
2. Implementar retry logic com exponential backoff
3. Melhorar validação de inputs
4. Adicionar fallbacks apropriados
```

**Resultado Esperado:**

- Taxa de erro reduzida para <10%
- Sistema mais robusto

### Caso 3: Performance Degradada

**Sintoma:** Tempo de resposta 50% pior que histórico

**Detecção Automática:**

```python
IssueType.PERFORMANCE_DEGRADATION
Severity: 0.6
Evidence: {
    "current": 1.2s,
    "historical_avg": 0.8s
}
```

**Melhoria Planejada:**

```python
ImprovementType.REDUCE_COMPLEXITY
Steps:
1. Profiling para identificar gargalos
2. Otimizar queries/operações mais pesadas
3. Reduzir complexidade algorítmica
4. Adicionar índices/otimizações de BD
```

## 🔄 Integração com Outras Sprints

### Sprint 2 (Memória Episódica)

- Todas as melhorias são memorizadas
- Sistema aprende quais otimizações funcionam
- Evita repetir melhorias que falharam

### Sprint 5 (Reflexion)

- Usa padrão similar de autocrítica
- Ambos sistemas aprendem com experiência
- Reflexion foca em tarefas, Self-Optimization foca no sistema

### Sprint 6 (Action Module)

- Monitora estatísticas de ferramentas
- Identifica ferramentas problemáticas
- Otimiza uso de ferramentas

### Sprint 13 (Meta-Agente)

- Pode trabalhar em conjunto
- Meta-Agente foca em análise estratégica
- Self-Optimization foca em melhorias táticas

## 📈 Métricas de Sucesso

**Indicadores:**

1. **Health Score**: Mantém >0.8
2. **Frequência de Problemas**: Reduz ao longo do tempo
3. **Taxa de Sucesso de Melhorias**: >70% das melhorias aplicadas funcionam
4. **Tempo de Detecção**: <5 minutos entre problema e detecção
5. **Impacto Médio**: Melhorias reduzem métricas problemáticas em >30%

## 🚀 Próximos Passos (Futuro)

1. **Machine Learning para Detecção**: Usar ML para detectar anomalias sutis
2. **Previsão Proativa**: Prever problemas antes que ocorram
3. **Auto-scaling**: Ajustar recursos automaticamente
4. **A/B Testing**: Testar múltiplas soluções antes de aplicar
5. **Rollback Automático**: Reverter melhorias que pioram sistema

## 📝 Checklist de Implementação

- [x] SystemMonitor com coleta de métricas
- [x] Detecção automática de 6 tipos de problemas
- [x] ImprovementPlanner com priorização inteligente
- [x] ImprovementExecutor com execução autônoma
- [x] Ciclo completo MONITOR-DETECT-PLAN-EXECUTE-LEARN
- [x] Cálculo de health score
- [x] API REST completa (/run-cycle, /health, /issues, /metrics/history)
- [x] Métricas Prometheus
- [x] Memorização de melhorias aplicadas
- [x] Execução contínua com intervalo configurável
- [x] Documentação completa

## 🏆 Status: ✅ SPRINT 7 COMPLETA

A Sprint 7 implementa com sucesso o sistema de **auto-otimização proativa**, transformando o Janus de um sistema reativo
para uma entidade com iniciativa autônoma para se aperfeiçoar continuamente.

O sistema agora possui:

- **Consciência de Saúde** através de monitoramento contínuo
- **Detecção Inteligente** de problemas e gargalos
- **Planejamento Autônomo** de melhorias priorizadas
- **Execução Segura** de otimizações sem intervenção humana
- **Aprendizado Contínuo** com resultados de melhorias

**Diferencial da Sprint 7:**
> Enquanto as sprints anteriores ensinaram o Janus a **reagir** e **aprender**, a Sprint 7 o ensina a **tomar iniciativa
** - o primeiro passo rumo à verdadeira autonomia.
