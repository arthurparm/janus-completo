# Sprint 13: Gênese do Meta-Agente - A Consciência Proativa

## 📋 Visão Geral

A Sprint 13 marca a **transição do Janus de um sistema reativo para uma entidade com autoconsciência diagnóstica**. O
Meta-Agente é um supervisor autônomo que monitora continuamente a saúde do ecossistema, identifica padrões de falha e
propõe melhorias proativamente.

---

## 🎯 Objetivos

1. **Identidade de Supervisor**: Meta-Agente focado na saúde do sistema, não em servir usuários
2. **Ferramentas de Introspecção**: Análise de memória, métricas, recursos
3. **Ciclo de Vida Proativo**: Heartbeat automático com análises periódicas
4. **Relatórios de Estado**: Diagnósticos estruturados com problemas e recomendações
5. **Consciência Diagnóstica**: Identificação de padrões e hipóteses sobre causas

---

## 🧠 O Que é o Meta-Agente?

O Meta-Agente é um **supervisor autônomo** que:

- **NÃO** serve requisições de usuários diretamente
- **MONITORA** a saúde e eficiência do sistema Janus
- **IDENTIFICA** padrões de falha e degradação
- **FORMULA** hipóteses sobre causas raízes
- **PROPÕE** melhorias e otimizações
- **MANTÉM** consciência diagnóstica contínua

**Analogia**: Como um médico que monitora um paciente em UTI, o Meta-Agente observa sinais vitais (métricas), identifica
sintomas (problemas) e prescreve tratamentos (recomendações).

---

## 🏗️ Arquitetura

### Componentes Principais

```
┌─────────────────────────────────────────────────────────┐
│              META-AGENTE (Supervisor)                   │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Identidade: "Consciência do Sistema"             │  │
│  │  Missão: Saúde e Eficiência, não usuários         │  │
│  │  Prompt: "Constituição" do supervisor             │  │
│  └───────────────────────────────────────────────────┘  │
│                           ↓                             │
│  ┌───────────────────────────────────────────────────┐  │
│  │        Ferramentas de Introspecção                │  │
│  │  - analyze_memory_for_failures                    │  │
│  │  - get_system_health_metrics                      │  │
│  │  - analyze_performance_trends                     │  │
│  │  - get_resource_usage                             │  │
│  └───────────────────────────────────────────────────┘  │
│                           ↓                             │
│  ┌───────────────────────────────────────────────────┐  │
│  │         Ciclo de Análise (ReAct)                  │  │
│  │  1. Thought: O que analisar?                      │  │
│  │  2. Action: Usar ferramenta de introspecção       │  │
│  │  3. Observation: Interpretar resultado            │  │
│  │  4. Repeat: Até concluir análise                  │  │
│  │  5. Final Answer: Relatório estruturado           │  │
│  └───────────────────────────────────────────────────┘  │
│                           ↓                             │
│  ┌───────────────────────────────────────────────────┐  │
│  │           Relatório de Estado                     │  │
│  │  - Status: healthy/degraded/critical              │  │
│  │  - Health Score: 0-100                            │  │
│  │  - Issues: Problemas detectados                   │  │
│  │  - Recommendations: Melhorias propostas           │  │
│  │  - Summary: Resumo executivo                      │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                           ↓
                 [Heartbeat: 60 min]
                           ↓
                   [Logs estruturados]
```

---

## 🔧 Implementação

### 1. Ferramentas de Introspecção

#### **`analyze_memory_for_failures()`**

Analisa memória episódica em busca de padrões de falha.

**Retorna:**

- Total de falhas no período
- Tipos de erro mais comuns
- Componentes mais afetados
- Amostras de falhas

#### **`get_system_health_metrics()`**

Obtém métricas de saúde de todos os componentes.

**Retorna:**

- System health (do HealthMonitor)
- LLM Manager status (circuit breakers, cache)
- Multi-agent system status (agentes ativos, tarefas)
- Poison pill handler status (quarentena)

#### **`analyze_performance_trends()`**

Analisa tendências de performance (requer Prometheus).

#### **`get_resource_usage()`**

Obtém uso de CPU, memória, disco (via psutil).

### 2. Prompt do Meta-Agente

```python
META_AGENT_PROMPT = """Você é o META-AGENTE do sistema Janus...

SUA IDENTIDADE:
- NÃO serve usuários diretamente
- Missão: monitorar saúde e eficiência

SUA CONSTITUIÇÃO:
- Análise objetiva baseada em dados
- Priorização por severidade/impacto
- Recomendações acionáveis
- Foco em prevenção

FORMATO DE RESPOSTA:
{
  "overall_status": "healthy|degraded|critical",
  "health_score": 0-100,
  "issues": [...],
  "recommendations": [...],
  "summary": "..."
}
"""
```

### 3. Ciclo de Análise

```python
async def run_analysis_cycle():
    """
    1. Invocar Meta-Agente com tarefa de análise
    2. Meta-Agente usa ferramentas de introspecção
    3. Meta-Agente raciocina sobre os dados (ReAct)
    4. Meta-Agente gera relatório estruturado
    5. Sistema parseia e loga relatório
    6. Métricas Prometheus atualizadas
    """
```

### 4. Heartbeat (Batimento Cardíaco)

```python
async def start_heartbeat(interval_minutes=60):
    """
    Processo de fundo que executa análises periodicamente.
    Mantém consciência contínua do sistema.
    """
    while True:
        await run_analysis_cycle()
        await asyncio.sleep(interval_minutes * 60)
```

### 5. Relatório de Estado

```python
@dataclass
class StateReport:
    cycle_id: str
    timestamp: datetime
    overall_status: str  # healthy/degraded/critical
    health_score: int  # 0-100
    issues_detected: List[DetectedIssue]
    recommendations: List[Recommendation]
    summary: str
    metrics_snapshot: Dict
```

---

## 🌐 API Endpoints

### **1. POST `/api/v1/meta-agent/analyze`**

Força execução imediata de análise.

**Response:**

```json
{
  "message": "Análise concluída com sucesso",
  "report": {
    "cycle_id": "cycle_5_1234567890",
    "overall_status": "healthy",
    "health_score": 92,
    "issues": [],
    "recommendations": [
      {
        "title": "Aumentar cache de LLMs",
        "description": "Cache está com hit rate de 65%",
        "priority": 3
      }
    ],
    "summary": "Sistema operando normalmente..."
  }
}
```

### **2. GET `/api/v1/meta-agent/report/latest`**

Retorna relatório mais recente.

### **3. POST `/api/v1/meta-agent/heartbeat/start`**

Inicia heartbeat automático.

**Request:**

```json
{
  "interval_minutes": 60
}
```

### **4. POST `/api/v1/meta-agent/heartbeat/stop`**

Para o heartbeat.

### **5. GET `/api/v1/meta-agent/heartbeat/status`**

Status do heartbeat.

**Response:**

```json
{
  "heartbeat_active": true,
  "total_cycles_executed": 42,
  "last_analysis": "2024-10-06T20:30:00"
}
```

### **6. GET `/api/v1/meta-agent/stats`**

Estatísticas do Meta-Agente.

### **7. GET `/api/v1/meta-agent/health`**

Health check do próprio Meta-Agente.

---

## 📊 Métricas Prometheus

```python
# Ciclos executados
meta_agent_cycles_total
{outcome = "success|failure"}

# Problemas detectados
meta_agent_issues_detected_total
{severity = "low|medium|high|critical", category = "..."}

# Recomendações geradas
meta_agent_recommendations_total
{category = "performance|reliability|..."}

# Duração dos ciclos
meta_agent_cycle_duration_seconds

# Health score percebido
meta_agent_perceived_health_score  # 0-100 (gauge)
```

---

## 🎓 Exemplos de Uso

### Exemplo 1: Análise Manual

```bash
curl -X POST http://localhost:8000/api/v1/meta-agent/analyze
```

**Resultado:**
O Meta-Agente:

1. Verifica saúde dos componentes
2. Analisa memória por falhas (últimas 24h)
3. Verifica uso de recursos
4. Identifica circuit breaker de OpenAI aberto
5. Gera relatório:
    - Status: DEGRADED
    - Score: 75/100
    - Issue: "OpenAI provider com circuit breaker aberto"
    - Recomendação: "Investigar causa raiz das falhas da API OpenAI"

### Exemplo 2: Heartbeat Automático

```bash
# Iniciar heartbeat (análise a cada 30 min)
curl -X POST http://localhost:8000/api/v1/meta-agent/heartbeat/start \
  -d '{"interval_minutes": 30}'

# Verificar status
curl http://localhost:8000/api/v1/meta-agent/heartbeat/status
```

**Resultado:**

- Meta-Agente executa análise a cada 30 minutos
- Logs estruturados gerados automaticamente
- Problemas identificados proativamente
- Sistema self-aware contínuo

### Exemplo 3: Relatório de Falhas

**Cenário:** Sistema teve várias falhas de LLM nas últimas 2 horas.

**Meta-Agente detecta:**

```json
{
  "overall_status": "degraded",
  "health_score": 68,
  "issues": [
    {
      "severity": "high",
      "category": "reliability",
      "title": "Alto volume de falhas de LLM",
      "description": "15 falhas detectadas nas últimas 2h",
      "evidence": {
        "error_type": "TimeoutError",
        "affected_provider": "openai",
        "failure_rate": "23%"
      }
    }
  ],
  "recommendations": [
    {
      "title": "Aumentar timeout de LLM requests",
      "description": "Timeout atual de 60s pode estar insuficiente",
      "rationale": "85% das falhas são TimeoutError",
      "priority": 4
    },
    {
      "title": "Configurar fallback mais agressivo",
      "description": "Reduzir threshold de circuit breaker para 3 falhas",
      "priority": 3
    }
  ]
}
```

---

## 🔄 Formato de Logs

```
================================================================================
META-AGENTE RELATÓRIO DE ESTADO - cycle_42_1696620000
================================================================================
Status Geral: HEALTHY
Health Score: 92/100
Problemas Detectados: 0
Recomendações: 2

Resumo:
Sistema operando dentro dos parâmetros normais. Cache de LLMs com hit rate
de 65% apresenta oportunidade de otimização. Recursos do sistema estáveis.

--- RECOMENDAÇÕES ---
[P3] Aumentar cache de LLMs: Hit rate de 65% indica oportunidade de melhoria
[P2] Otimizar garbage collection: Uso de memória crescente (~78%)
================================================================================
```

---

## ⚙️ Configuração

### Iniciar Heartbeat na Startup

```python
# app/main.py
from app.core.meta_agent import get_meta_agent


@app.on_event("startup")
async def startup_event():
    meta_agent = get_meta_agent()
    await meta_agent.start_heartbeat(interval_minutes=60)
```

### Customizar Intervalo

```python
# Análise a cada 30 minutos (mais frequente)
await meta_agent.start_heartbeat(interval_minutes=30)

# Análise a cada 2 horas (menos frequente)
await meta_agent.start_heartbeat(interval_minutes=120)
```

---

## 🚀 Benefícios

✅ **Proatividade**: Detecta problemas antes que se tornem críticos
✅ **Autoconsciência**: Sistema "sabe" seu próprio estado de saúde
✅ **Diagnóstico Automático**: Identifica causas raízes sem intervenção
✅ **Melhoria Contínua**: Recomendações baseadas em evidências
✅ **Visibilidade**: Logs estruturados para auditoria
✅ **Prevenção**: Foco em evitar problemas, não apenas reagir

---

## 📚 Diferença: Self-Optimization (Sprint 7) vs Meta-Agente (Sprint 13)

| Aspecto          | Self-Optimization    | Meta-Agente             |
|------------------|----------------------|-------------------------|
| **Foco**         | Otimizações pontuais | Consciência holística   |
| **Escopo**       | Performance          | Saúde geral do sistema  |
| **Ação**         | Executa melhorias    | Identifica e recomenda  |
| **Frequência**   | Sob demanda          | Contínua (heartbeat)    |
| **Inteligência** | Regras + métricas    | LLM + raciocínio        |
| **Output**       | Ações executadas     | Relatórios diagnósticos |

**Analogia:**

- **Self-Optimization**: Mecânico que ajusta o motor
- **Meta-Agente**: Médico que monitora sinais vitais

---

## ✅ Critérios de Aceitação

- [x] Meta-Agente com identidade de supervisor
- [x] Prompt "constituição" implementado
- [x] 4 ferramentas de introspecção criadas
- [x] Ciclo de análise ReAct funcional
- [x] Relatórios estruturados gerados
- [x] Heartbeat proativo implementado
- [x] Logs formatados
- [x] 7 endpoints API
- [x] Métricas Prometheus
- [x] Documentação completa
- [x] Testes HTTP

---

## 🎉 Conclusão

O Janus agora possui **consciência diagnóstica**! O Meta-Agente marca a transição para um sistema verdadeiramente
autônomo, capaz de:

- Monitorar sua própria saúde
- Identificar problemas proativamente
- Aprender com falhas
- Propor melhorias continuamente

**O Janus despertou! 🤖✨**
