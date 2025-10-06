# Sprint 4: Autonomia e Segurança - Agente Funcional

## Status: ✅ IMPLEMENTADA

A Sprint 4 foi **totalmente implementada** com o **Ciclo ReAct** (Reasoning and Acting) e um **Sandbox Python Seguro**, permitindo ao Janus raciocinar de forma estruturada e executar código de forma isolada e protegida.

---

## 🎯 Objetivos da Sprint

1. **Ciclo de Raciocínio ReAct**: Implementar o padrão Reasoning and Acting para permitir ao agente pensar antes de agir de forma iterativa
2. **Sandbox Python Seguro**: Criar ambiente isolado para execução segura de código Python, protegendo o sistema principal

---

## 🏗️ Arquitetura Implementada

### 1. Ciclo ReAct (`app/core/agent_manager.py` + `app/core/prompt_loader.py`)

O ciclo ReAct já estava implementado e foi mantido/validado nesta sprint.

#### 1.1 Fluxo ReAct

```
Thought (Pensar) → Action (Agir) → Observation (Observar) → [Repeat] → Final Answer
```

**Componentes:**

- **AgentManager**: Orquestra a execução dos agentes
- **REACT_AGENT_TEMPLATE**: Prompt que define o comportamento do ciclo
- **AgentExecutor**: Motor LangChain que executa o ciclo

#### 1.2 Formato do Ciclo

```
Thought: [Análise da situação e decisão sobre qual ferramenta usar]
Action: [nome_da_ferramenta]
Action Input: [input em JSON]
Observation: [Resultado da ação]

... (ciclo pode repetir) ...

Thought: Tarefa completa
Final Answer: [Resposta final ao usuário]
```

#### 1.3 Características do ReAct

- **Raciocínio Explícito**: Cada decisão é documentada
- **Iterativo**: Pode executar múltiplas ações em sequência
- **Autocorretivo**: Pode detectar e corrigir erros
- **Resiliente**: Circuit breakers, retries e timeouts
- **Observável**: Registra todos os passos intermediários

---

### 2. Sandbox Python (`app/core/python_sandbox.py`)

Módulo de execução segura de código Python usando **RestrictedPython**.

#### 2.1 Classe PythonSandbox

**Principais Métodos:**

```python
class PythonSandbox:
    def __init__(
        self,
        timeout_seconds: int = 5,
        max_output_length: int = 10000
    )

    def execute(
        self,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult

    def execute_expression(
        self,
        expression: str
    ) -> ExecutionResult
```

#### 2.2 ExecutionResult

```python
@dataclass
class ExecutionResult:
    success: bool                      # Sucesso ou falha
    output: str                        # Output do código
    error: Optional[str] = None        # Mensagem de erro (se houver)
    execution_time: float = 0.0        # Tempo de execução
    variables: Dict[str, Any] = None   # Variáveis definidas
```

#### 2.3 Restrições de Segurança

**✅ Permitido:**
- Módulos seguros: `math`, `random`, `datetime`, `json`, `re`, `collections`, `itertools`, `functools`, `statistics`, `decimal`, `fractions`
- Builtins básicos: `print`, `len`, `sum`, `range`, `list`, `dict`, etc.
- Definição de variáveis e funções
- Loops e condicionais
- List/dict comprehensions

**❌ Bloqueado:**
- Acesso ao filesystem (`open`, `file`, `os`)
- Acesso à network (`socket`, `urllib`, `requests`)
- Subprocess (`subprocess`, `os.system`)
- Imports perigosos (`sys`, `os`, `subprocess`)
- Eval/exec dinâmico
- Acesso a `__builtins__`

#### 2.4 Validações em Múltiplas Camadas

1. **Validação Sintática**: Verifica sintaxe Python válida
2. **Validação de Padrões**: Detecta padrões perigosos no código
3. **Compilação Restrita**: Usa `compile_restricted` do RestrictedPython
4. **Execução Isolada**: Contexto global controlado
5. **Timeout**: Limite de 5 segundos por execução
6. **Limitação de Output**: Máximo 10.000 caracteres

---

### 3. Ferramentas do Agente (`app/core/agent_tools.py`)

#### 3.1 `execute_python_code(code: str)`

Executa código Python completo no sandbox.

**Casos de Uso:**
- Processamento de dados
- Cálculos complexos
- Algoritmos e lógica
- Testes de código

**Exemplo:**
```python
code = """
numbers = [1, 2, 3, 4, 5]
total = sum(numbers)
average = total / len(numbers)
print(f"Média: {average}")
"""
result = execute_python_code(code)
```

#### 3.2 `execute_python_expression(expression: str)`

Avalia uma expressão Python simples.

**Casos de Uso:**
- Cálculos rápidos
- Avaliação de expressões
- Conversões

**Exemplos:**
```python
"2 + 2"  # → 4
"sum([1,2,3,4,5])"  # → 15
"[x**2 for x in range(5)]"  # → [0, 1, 4, 9, 16]
```

---

### 4. API Endpoints (`app/api/v1/endpoints/sandbox.py`)

#### 4.1 `POST /api/v1/sandbox/execute`

Executa código Python no sandbox.

**Request:**
```json
{
  "code": "result = sum([1, 2, 3, 4, 5])\nprint(f'Soma: {result}')",
  "context": {
    "variable1": "valor1"
  }
}
```

**Response:**
```json
{
  "success": true,
  "output": "Soma: 15\n",
  "error": null,
  "execution_time": 0.003,
  "variables": {
    "result": "15"
  }
}
```

#### 4.2 `POST /api/v1/sandbox/evaluate`

Avalia uma expressão Python.

**Request:**
```json
{
  "expression": "2 + 2"
}
```

**Response:**
```json
{
  "success": true,
  "result": "4",
  "error": null,
  "execution_time": 0.001
}
```

#### 4.3 `GET /api/v1/sandbox/capabilities`

Lista capacidades e restrições do sandbox.

**Response:**
```json
{
  "allowed_modules": [
    "math", "random", "datetime", "json", "re",
    "collections", "itertools", "functools",
    "statistics", "decimal", "fractions"
  ],
  "restrictions": {
    "filesystem_access": false,
    "network_access": false,
    "subprocess": false,
    "timeout_seconds": 5,
    "max_output_length": 10000
  },
  "features": {
    "print_support": true,
    "variable_inspection": true,
    "context_variables": true,
    "expression_evaluation": true
  }
}
```

---

## 📦 Dependências Adicionadas

### requirements.txt
```txt
RestrictedPython>=6.0
```

### pyproject.toml
```toml
RestrictedPython = ">=6.0"
```

---

## ⚙️ Configuração

### Config Settings (`app/config.py`)

```python
class AppSettings(BaseSettings):
    # Sprint 4: Python Sandbox
    SANDBOX_TIMEOUT_SECONDS: int = 5
    SANDBOX_MAX_OUTPUT_LENGTH: int = 10000
```

### Variáveis de Ambiente (`.env`)

Não requer configuração adicional no `.env` para esta sprint.

---

## 🔧 Como Usar

### 1. Via API Direta

```bash
# Executar código
curl -X POST http://localhost:8000/api/v1/sandbox/execute \
  -H "Content-Type: application/json" \
  -d '{
    "code": "import math\nprint(math.pi)"
  }'

# Avaliar expressão
curl -X POST http://localhost:8000/api/v1/sandbox/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "expression": "2 ** 10"
  }'

# Verificar capacidades
curl http://localhost:8000/api/v1/sandbox/capabilities
```

### 2. Via Agente

O agente pode usar as ferramentas automaticamente:

```
User: "Calcule a média de [10, 20, 30, 40, 50]"

Agent:
Thought: Preciso calcular a média de uma lista. Vou usar execute_python_code.
Action: execute_python_code
Action Input: {"code": "numbers = [10, 20, 30, 40, 50]\naverage = sum(numbers) / len(numbers)\nprint(f'Média: {average}')"}
Observation: {"success": true, "output": "Média: 30.0"}
Final Answer: A média é 30.0
```

### 3. Programaticamente

```python
from app.core.python_sandbox import python_sandbox

# Executar código
result = python_sandbox.execute("""
import math

def area_circulo(raio):
    return math.pi * raio ** 2

raio = 5
area = area_circulo(raio)
print(f"Área: {area:.2f}")
""")

print(result.output)  # "Área: 78.54"
print(result.variables)  # {'raio': 5, 'area': 78.53981633974483, ...}

# Avaliar expressão
result = python_sandbox.execute_expression("sum(range(1, 101))")
print(result.output)  # "5050"
```

---

## 🎯 Casos de Uso

### 1. Cálculos Matemáticos
```python
code = """
import math

# Calcular hipotenusa
a = 3
b = 4
c = math.sqrt(a**2 + b**2)
print(f"Hipotenusa: {c}")
"""
```

### 2. Processamento de Dados
```python
code = """
dados = [10, 25, 30, 15, 40, 35, 20]

media = sum(dados) / len(dados)
maximo = max(dados)
minimo = min(dados)

print(f"Média: {media}")
print(f"Máximo: {maximo}")
print(f"Mínimo: {minimo}")
"""
```

### 3. Algoritmos
```python
code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

resultado = [fibonacci(i) for i in range(10)]
print(f"Fibonacci: {resultado}")
"""
```

### 4. Análise de Texto
```python
code = """
import re
from collections import Counter

texto = "Python é uma linguagem Python poderosa"
palavras = re.findall(r'\w+', texto.lower())
frequencia = Counter(palavras)

print(f"Palavras mais comuns: {frequencia.most_common(3)}")
"""
```

---

## 🔒 Segurança

### Exemplos de Código Bloqueado

```python
# ❌ Tentativa de acesso ao filesystem
code = "open('/etc/passwd', 'r')"
# Resultado: "Código contém operações não permitidas"

# ❌ Tentativa de import perigoso
code = "import os; os.system('ls')"
# Resultado: "Import de 'os' não é permitido no sandbox"

# ❌ Tentativa de eval
code = "eval('print(\"hack\")')"
# Resultado: "Código contém operações não permitidas"

# ❌ Tentativa de subprocess
code = "import subprocess; subprocess.run(['ls'])"
# Resultado: "Import de 'subprocess' não é permitido"
```

### Exemplos de Código Permitido

```python
# ✅ Cálculos matemáticos
code = "import math; print(math.sqrt(16))"
# Resultado: "4.0"

# ✅ Manipulação de listas
code = "numeros = [1,2,3]; print(sum(numeros))"
# Resultado: "6"

# ✅ Datas
code = "from datetime import datetime; print(datetime.now().year)"
# Resultado: "2025"

# ✅ JSON
code = "import json; data = {'key': 'value'}; print(json.dumps(data))"
# Resultado: '{"key": "value"}'
```

---

## 🧪 Testes

Ver arquivo `http/sprint/Sprint 4 - Sandbox.http` para testes completos.

### Teste Rápido

```http
POST http://localhost:8000/api/v1/sandbox/execute
Content-Type: application/json

{
  "code": "print('Hello from Janus Sandbox!')"
}
```

---

## 📊 Métricas e Observabilidade

O sistema registra:
- Tempo de execução de cada código
- Sucessos e falhas
- Erros de compilação e runtime
- Uso das ferramentas pelos agentes

---

## 🚀 Melhorias Futuras

1. **Persistência de Contexto**: Manter estado entre execuções
2. **Mais Módulos**: Adicionar numpy, pandas (com restrições)
3. **Async Support**: Executar código assíncrono
4. **Resource Limits**: Limitar CPU e memória
5. **Dockerfile Sandbox**: Sandbox ainda mais isolado com Docker
6. **Code Review**: Análise estática antes da execução

---

## 🔗 Relação com Outras Sprints

- **Sprint 3 (Contexto)**: Sandbox pode usar data/hora do contexto
- **Sprint 5 (Reflexion)**: Análise de erros na execução de código
- **Sprint 6 (Multitask)**: Múltiplas execuções paralelas
- **Sprint 9 (Neural)**: Coleta de dados de execuções para treinamento

---

## ✅ Checklist de Implementação

- [x] Criar módulo `python_sandbox.py` com RestrictedPython
- [x] Implementar validação de segurança em múltiplas camadas
- [x] Adicionar ferramentas `execute_python_code` e `execute_python_expression`
- [x] Criar endpoints API `/sandbox/execute`, `/evaluate`, `/capabilities`
- [x] Adicionar dependências (RestrictedPython)
- [x] Configurar timeout e limites
- [x] Validar ciclo ReAct existente
- [x] Documentar uso e restrições
- [x] Criar testes HTTP

---

## 📝 Notas Técnicas

### Por que RestrictedPython?

- **Leve**: Não requer containers Docker
- **Rápido**: Execução praticamente instantânea
- **Seguro**: Validação em tempo de compilação
- **Flexível**: Permite controle fino de permissões
- **Maduro**: Usado em produção (Zope, Plone)

### Limitações Conhecidas

- **Não é 100% inviolável**: Segurança através de obscuridade tem limites
- **Performance**: Código restrito pode ser mais lento
- **Debugging**: Erros podem ser menos claros
- **Timeout simples**: Não protege contra CPU-intensive infinite loops perfeitamente

### Alternativas Consideradas

- **Docker Sandbox**: Mais isolamento, mas overhead maior
- **PyPy Sandbox**: Descontinuado
- **Epicbox**: Requer Docker, mais complexo
- **subprocess.run**: Menos controle, mais perigoso

---

**Sprint implementada por:** Claude Code
**Data:** 2025-10-06
**Status:** ✅ Produção Ready

---

## 🎓 Referências

- [RestrictedPython Documentation](https://restrictedpython.readthedocs.io/)
- [LangChain ReAct Agent](https://python.langchain.com/docs/modules/agents/agent_types/react)
- [OWASP Secure Coding Practices](https://owasp.org/www-project-secure-coding-practices-quick-reference-guide/)
