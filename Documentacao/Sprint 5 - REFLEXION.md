# Sprint 5: Auto-otimização e Aprendizado com Erros (Reflexion)

## 📋 Visão Geral

A Sprint 5 implementa o **padrão Reflexion**, capacitando o Janus a aprender com suas próprias falhas e otimizar seu
desempenho de forma autônoma através de ciclos iterativos de ação, avaliação, reflexão e refinamento.

## 🎯 Objetivos Alcançados

### 1. **Sistema Reflexion Completo** (`app/core/reflexion_core.py`)

Implementa o ciclo completo de auto-otimização:

```
ACT → EVALUATE → REFLECT → RETRY → LEARN
```

#### Componentes:

- **ReflexionSession**: Gerencia ciclo completo de tentativas com autocrítica
- **ReflexionConfig**: Configurações ajustáveis (iterações, tempo, threshold)
- **Avaliador LLM**: Crítica inteligente dos resultados usando o modelo de linguagem
- **Extrator de Lições**: Analisa todas as tentativas e extrai insights gerais

#### Fluxo de Execução:

1. **ACT**: Executa a tarefa usando o agente com ferramentas disponíveis
2. **EVALUATE**: Avalia criticamente o resultado (score 0.0-1.0)
3. **REFLECT**: Identifica o que deu errado e como melhorar
4. **RETRY**: Tenta novamente incorporando os aprendizados anteriores
5. **LEARN**: Ao final, extrai lições gerais que são memorizadas

#### Exemplo de Uso:

```python
from app.core.reflexion_core import run_with_reflexion

result = run_with_reflexion(
    task="Calcule a média de [10, 20, 30, 40] e explique o método",
    config=ReflexionConfig(
        max_iterations=3,
        max_time_seconds=180,
        success_threshold=0.8
    )
)

print(f"Sucesso: {result['success']}")
print(f"Melhor resultado: {result['best_result']}")
print(f"Lições aprendidas: {result['lessons_learned']}")
```

### 2. **Ferramentas Defeituosas para Treinamento** (`app/core/faulty_tools.py`)

Conjunto de 6 ferramentas intencionalmente defeituosas para treinar o sistema a detectar e corrigir erros:

#### Ferramentas Implementadas:

1. **`faulty_calculator`**
    - 30% de chance de falha
    - Tipos: resultado incorreto, exceção, formato inválido, timeout
    - Objetivo: Treinar validação de cálculos

2. **`unreliable_weather_api`**
    - 40% dados incompletos, 20% JSON quebrado, 10% erro de conexão
    - Objetivo: Treinar tratamento de APIs não confiáveis

3. **`slow_database_query`**
    - 50% normal, 30% lento, 20% timeout
    - Objetivo: Treinar detecção de problemas de performance

4. **`inconsistent_file_reader`**
    - 25% truncado, 15% encoding incorreto, 10% não encontrado, 5% embaralhado
    - Objetivo: Treinar robustez na leitura de arquivos

5. **`flaky_api_call`**
    - Simula erros HTTP: 500, 503, 429, 400, dados inválidos
    - Objetivo: Treinar retry logic e tratamento de erros HTTP

6. **`memory_leaking_processor`**
    - Consome mais memória a cada chamada até falhar
    - Objetivo: Treinar detecção de memory leaks

#### Ferramentas de Diagnóstico:

- **`validate_tool_output`**: Valida formato e integridade de saídas
- **`reset_faulty_tools`**: Reseta estado para novos testes

### 3. **Novo Tipo de Agente: REFLEXION_AGENT**

Agente especializado com acesso a todas as ferramentas, incluindo as defeituosas:

```python
# app/core/enums.py
class AgentType(Enum):
    ORCHESTRATOR = "orchestrator"
    TOOL_USER = "tool_user"
    META_AGENT = "meta_agent"
    REFLEXION_AGENT = "reflexion_agent"  # Sprint 5
```

### 4. **API REST para Reflexion** (`app/api/v1/endpoints/reflexion.py`)

Endpoints expostos:

#### `POST /api/v1/reflexion/execute`

Executa uma tarefa com ciclo completo de Reflexion.

**Request:**

```json
{
  "task": "Calcule o fatorial de 5 e valide o resultado",
  "max_iterations": 3,
  "max_time_seconds": 180,
  "success_threshold": 0.8
}
```

**Response:**

```json
{
  "success": true,
  "best_result": "O fatorial de 5 é 120...",
  "best_score": 0.95,
  "iterations": 2,
  "lessons_learned": [
    "Sempre validar cálculos com método alternativo",
    "Incluir explicação passo-a-passo aumenta confiabilidade"
  ],
  "elapsed_seconds": 45.2,
  "steps": [
    ...
  ]
}
```

#### `GET /api/v1/reflexion/config`

Retorna configuração atual do sistema.

#### `GET /api/v1/reflexion/health`

Health check do módulo Reflexion.

### 5. **Configurações no `app/config.py`**

```python
# Sprint 5: Reflexion
REFLEXION_MAX_ITERATIONS: int = 3
REFLEXION_MAX_TIME_SECONDS: int = 180
REFLEXION_SUCCESS_THRESHOLD: float = 0.8
```

### 6. **Métricas Prometheus**

O sistema expõe métricas detalhadas:

- `reflexion_cycles_total{outcome}`: Total de ciclos executados (success/partial_success)
- `reflexion_iterations`: Distribuição do número de iterações por ciclo
- `reflexion_latency_seconds`: Tempo de execução de ciclos

## 🔧 Arquitetura

```
┌─────────────────────────────────────────────────────────┐
│                   Reflexion System                       │
│                                                          │
│  ┌────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │    ACT     │───>│   EVALUATE  │───>│   REFLECT   │  │
│  │  (Agent)   │    │    (LLM)    │    │    (LLM)    │  │
│  └────────────┘    └─────────────┘    └─────────────┘  │
│        ▲                                       │         │
│        │                                       ▼         │
│        │                              ┌─────────────┐   │
│        └──────────────────────────────│    RETRY    │   │
│                                       └─────────────┘   │
│                                                          │
│                         │                                │
│                         ▼                                │
│                  ┌─────────────┐                        │
│                  │    LEARN    │                        │
│                  │  (Lessons)  │                        │
│                  └─────────────┘                        │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
                 ┌──────────────┐
                 │    Memory    │
                 │   (Qdrant)   │
                 └──────────────┘
```

## 📊 Benefícios Implementados

### 1. **Aprendizado Autônomo**

- Sistema aprende com próprias falhas sem intervenção humana
- Lições são memorizadas e reutilizadas em tarefas futuras

### 2. **Detecção Inteligente de Erros**

- Identifica problemas em resultados aparentemente corretos
- Detecta inconsistências, dados incompletos, formatos inválidos

### 3. **Melhoria Iterativa**

- Cada tentativa incorpora aprendizados das anteriores
- Score crescente ao longo das iterações

### 4. **Treinamento Controlado**

- Ferramentas defeituosas permitem treinar sem riscos
- Ambiente seguro para praticar recuperação de erros

### 5. **Observabilidade Completa**

- Histórico detalhado de todas as tentativas
- Métricas Prometheus para monitoramento
- Lições aprendidas estruturadas e consultáveis

## 🧪 Exemplo de Uso Completo

### Cenário: Cálculo com validação

```python
# 1. Configurar Reflexion
from app.core.reflexion_core import run_with_reflexion, ReflexionConfig

config = ReflexionConfig(
    max_iterations=4,
    success_threshold=0.85
)

# 2. Executar tarefa complexa
result = run_with_reflexion(
    task="""
    Calcule a raiz quadrada de 144 usando a ferramenta faulty_calculator.
    Valide o resultado e se houver erro, tente alternativas.
    Explique o método usado.
    """,
    config=config
)

# 3. Analisar resultado
print(f"✓ Sucesso após {result['iterations']} tentativas")
print(f"✓ Score final: {result['best_score']:.2f}")
print(f"✓ Resultado: {result['best_result']}")
print(f"\n📚 Lições aprendidas:")
for lesson in result['lessons_learned']:
    print(f"  - {lesson}")
```

### Saída Esperada:

```
✓ Sucesso após 2 tentativas
✓ Score final: 0.92
✓ Resultado: A raiz quadrada de 144 é 12. Validado usando método alternativo (12 * 12 = 144).

📚 Lições aprendidas:
  - Sempre validar resultados de calculadoras com método reverso
  - Incluir múltiplas formas de validação aumenta confiabilidade
  - Documentar o raciocínio melhora a avaliação
```

## 🎓 Casos de Uso

### 1. **Depuração Autônoma**

```python
run_with_reflexion(
    task="Identifique e corrija o erro no código que calcula fibonacci(10)"
)
```

### 2. **Validação de APIs**

```python
run_with_reflexion(
    task="Obtenha clima de São Paulo e valide completude dos dados"
)
```

### 3. **Otimização de Performance**

```python
run_with_reflexion(
    task="Execute query no banco e detecte se há problema de performance"
)
```

### 4. **Tratamento de Erros HTTP**

```python
run_with_reflexion(
    task="Chame API /users/123 e implemente retry logic adequado"
)
```

## 🔄 Integração com Outros Componentes

### Memória Episódica (Sprint 2)

- Todas as reflexões são memorizadas no Qdrant
- Lições aprendidas podem ser consultadas em tarefas futuras
- Tipo de experiência: `reflexion_iteration`, `lessons_learned`

### Meta-Agente (Sprint 13)

- Meta-agente pode usar Reflexion para auto-otimização
- Analisa falhas do sistema e aprende padrões de correção

### Sandbox Python (Sprint 4)

- Ferramentas defeituosas executam em ambiente seguro
- Nenhum risco ao sistema mesmo com erros

## 📈 Métricas de Sucesso

**Indicadores implementados:**

1. **Taxa de Sucesso**: % de tarefas que atingem threshold
2. **Iterações Médias**: Quantas tentativas até sucesso
3. **Tempo Médio**: Duração típica de ciclo Reflexion
4. **Lições por Ciclo**: Quantas lições são extraídas
5. **Melhoria por Iteração**: ΔScore entre tentativas

## 🚀 Próximos Passos (Futuro)

1. **Avaliadores Especializados**: Criar avaliadores para domínios específicos (código, matemática, texto)
2. **Banco de Lições**: Interface para consultar e editar lições aprendidas
3. **Reflexion Colaborativa**: Múltiplos agentes refletindo juntos
4. **Auto-tuning**: Sistema ajusta próprios parâmetros baseado em histórico

## 📝 Checklist de Implementação

- [x] Sistema Reflexion completo com ciclo ACT-EVALUATE-REFLECT-RETRY-LEARN
- [x] 6 ferramentas defeituosas para treinamento de detecção de erros
- [x] Novo tipo de agente REFLEXION_AGENT
- [x] API REST com endpoints /execute, /config, /health
- [x] Configurações em settings
- [x] Métricas Prometheus
- [x] Integração com memória episódica
- [x] Documentação completa

## 🏆 Status: ✅ SPRINT 5 COMPLETA

A Sprint 5 implementa com sucesso o padrão Reflexion, capacitando o Janus a aprender autonomamente com seus erros
através de autocrítica iterativa e extração de lições aprendidas.
