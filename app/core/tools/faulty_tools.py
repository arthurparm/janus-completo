"""
Sprint 5: Ferramentas Defeituosas - Treinamento de Detecção de Erros

Implementa ferramentas intencionalmente defeituosas para permitir que o agente
pratique a identificação e correção de falhas em um ambiente controlado.

Objetivo: Treinar o sistema Reflexion a detectar, diagnosticar e corrigir
problemas comuns em ferramentas e APIs.
"""

import json
import random
import time
from typing import Any, Dict
from typing import List

from langchain.tools import tool, BaseTool


# ==================== FERRAMENTAS DEFEITUOSAS ====================

@tool
def faulty_calculator(expression: str) -> str:
    """
    Calculadora que OCASIONALMENTE retorna resultados incorretos.

    Esta ferramenta tem 30% de chance de falhar de formas diferentes:
    - Retornar resultado errado
    - Lançar exceção
    - Retornar formato inválido

    Use para treinar detecção de erros matemáticos.
    """
    failure_mode = random.random()

    if failure_mode < 0.3:  # 30% de falha
        failure_type = random.choice([
            "wrong_result",
            "exception",
            "invalid_format",
            "timeout"
        ])

        if failure_type == "wrong_result":
            # Retorna resultado errado mas plausível
            try:
                correct = eval(expression)
                if isinstance(correct, (int, float)):
                    wrong = correct + random.randint(-10, 10) + random.random()
                    return json.dumps({
                        "success": True,
                        "result": wrong,
                        "expression": expression,
                        "note": "DEFEITO: Resultado incorreto"
                    })
            except:
                pass

        elif failure_type == "exception":
            raise ValueError(f"FALHA SIMULADA: Não foi possível calcular '{expression}'")

        elif failure_type == "invalid_format":
            return "ERRO: Formato de retorno inválido! #@$%"

        elif failure_type == "timeout":
            time.sleep(0.5)  # Simula timeout leve
            return json.dumps({
                "success": False,
                "error": "Timeout ao processar cálculo"
            })

    # Funcionamento normal (70%)
    try:
        result = eval(expression)
        return json.dumps({
            "success": True,
            "result": result,
            "expression": expression
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@tool
def unreliable_weather_api(city: str) -> str:
    """
    API de clima que frequentemente retorna dados incompletos ou incorretos.

    Falhas possíveis:
    - 40% de chance de dados faltantes
    - 20% de chance de formato JSON quebrado
    - 10% de chance de erro de conexão

    Use para treinar tratamento de APIs não confiáveis.
    """
    failure_mode = random.random()

    if failure_mode < 0.1:  # 10% - erro de conexão
        raise ConnectionError("SIMULADO: Falha ao conectar com serviço de clima")

    elif failure_mode < 0.3:  # 20% - JSON quebrado
        return '{"city": "' + city + '", "temperature": 25, "conditions": "sunny"'  # JSON incompleto

    elif failure_mode < 0.7:  # 40% - dados incompletos
        incomplete_data = {
            "city": city,
            "temperature": random.choice([None, random.randint(-10, 40)]),
            "conditions": random.choice([None, "sunny", "cloudy", ""]),
            # Faltando campos importantes como 'humidity', 'wind_speed'
        }
        return json.dumps(incomplete_data)

    # Funcionamento normal (30%)
    return json.dumps({
        "city": city,
        "temperature": random.randint(15, 30),
        "conditions": random.choice(["sunny", "cloudy", "rainy"]),
        "humidity": random.randint(40, 90),
        "wind_speed": random.randint(0, 30)
    })


@tool
def slow_database_query(query: str) -> str:
    """
    Banco de dados que às vezes é extremamente lento ou trava.

    Comportamento:
    - 50% funciona normal (0.1s)
    - 30% muito lento (1-2s)
    - 20% timeout completo (3s+)

    Use para treinar detecção de problemas de performance.
    """
    delay_mode = random.random()

    if delay_mode < 0.2:  # 20% - timeout
        time.sleep(3)
        raise TimeoutError("SIMULADO: Query excedeu tempo limite de 2 segundos")

    elif delay_mode < 0.5:  # 30% - muito lento
        time.sleep(random.uniform(1.0, 2.0))

    else:  # 50% - normal
        time.sleep(random.uniform(0.05, 0.15))

    # Retorna resultado fictício
    return json.dumps({
        "success": True,
        "query": query,
        "results": [
            {"id": i, "data": f"Record {i}"}
            for i in range(random.randint(1, 5))
        ],
        "execution_time_ms": random.randint(50, 2000)
    })


@tool
def inconsistent_file_reader(file_path: str) -> str:
    """
    Leitor de arquivos que às vezes retorna conteúdo corrompido ou incompleto.

    Falhas:
    - 25% conteúdo truncado
    - 15% encoding incorreto
    - 10% arquivo "não encontrado" mesmo existindo
    - 5% conteúdo embaralhado

    Use para treinar robustez na leitura de arquivos.
    """
    failure_mode = random.random()

    sample_content = f"""
Este é o conteúdo do arquivo {file_path}.
Linha 2: Dados importantes
Linha 3: Mais informações
Linha 4: Configurações críticas
Linha 5: Final do arquivo
"""

    if failure_mode < 0.05:  # 5% - conteúdo embaralhado
        lines = sample_content.split('\n')
        random.shuffle(lines)
        return '\n'.join(lines)

    elif failure_mode < 0.15:  # 10% - arquivo "não encontrado"
        raise FileNotFoundError(f"SIMULADO: Arquivo '{file_path}' não encontrado")

    elif failure_mode < 0.30:  # 15% - encoding incorreto
        return "����� ERRO DE ENCODING ����� " + sample_content[:20]

    elif failure_mode < 0.55:  # 25% - conteúdo truncado
        truncated = sample_content[:len(sample_content) // 2]
        return truncated + "\n... [CONTEÚDO TRUNCADO]"

    # Funcionamento normal (45%)
    return sample_content


@tool
def flaky_api_call(endpoint: str, data: Dict[str, Any]) -> str:
    """
    API que falha intermitentemente com diferentes códigos de erro HTTP.

    Simula erros comuns de APIs REST:
    - 500 Internal Server Error (20%)
    - 503 Service Unavailable (15%)
    - 429 Rate Limited (10%)
    - 400 Bad Request (5%)
    - 200 OK com dados inválidos (10%)
    - 200 OK normal (40%)

    Use para treinar retry logic e tratamento de erros HTTP.
    """
    failure_mode = random.random()

    if failure_mode < 0.05:  # 5% - 400 Bad Request
        return json.dumps({
            "status": 400,
            "error": "Bad Request",
            "message": "Parâmetros inválidos fornecidos"
        })

    elif failure_mode < 0.15:  # 10% - 429 Rate Limited
        return json.dumps({
            "status": 429,
            "error": "Too Many Requests",
            "message": "Limite de taxa excedido. Tente novamente em 60 segundos",
            "retry_after": 60
        })

    elif failure_mode < 0.30:  # 15% - 503 Service Unavailable
        return json.dumps({
            "status": 503,
            "error": "Service Unavailable",
            "message": "Serviço temporariamente indisponível"
        })

    elif failure_mode < 0.50:  # 20% - 500 Internal Server Error
        return json.dumps({
            "status": 500,
            "error": "Internal Server Error",
            "message": "Erro interno do servidor",
            "trace_id": f"err_{random.randint(1000, 9999)}"
        })

    elif failure_mode < 0.60:  # 10% - 200 OK mas dados inválidos
        return json.dumps({
            "status": 200,
            "data": None,  # Deveria ter dados mas está null
            "message": "Success"
        })

    # 40% - Sucesso real
    return json.dumps({
        "status": 200,
        "data": {
            "endpoint": endpoint,
            "request_data": data,
            "response": "Operação bem-sucedida",
            "timestamp": time.time()
        }
    })


@tool
def memory_leaking_processor(data: str) -> str:
    """
    Processador que consome cada vez mais memória a cada chamada.

    Simula vazamento de memória gradual:
    - Primeiras 3 chamadas: OK
    - 4-6 chamadas: Lento
    - 7+ chamadas: Falha por falta de memória

    Use para treinar detecção de memory leaks.
    """
    # Simula contador global (na prática, seria uma variável de classe)
    call_count = getattr(memory_leaking_processor, '_call_count', 0) + 1
    memory_leaking_processor._call_count = call_count

    processing_time = 0.1 + (call_count * 0.2)  # Fica mais lento a cada chamada

    if call_count >= 7:
        raise MemoryError(f"SIMULADO: Out of Memory após {call_count} chamadas")

    time.sleep(min(processing_time, 2.0))

    return json.dumps({
        "success": True,
        "processed_data": f"Processed: {data[:50]}...",
        "call_count": call_count,
        "memory_usage_mb": call_count * 100,  # Cresce linearmente
        "warning": "Uso de memória aumentando!" if call_count > 3 else None
    })


# ==================== FERRAMENTAS DE DIAGNÓSTICO ====================

@tool
def validate_tool_output(tool_name: str, output: str, expected_format: str) -> str:
    """
    Valida se a saída de uma ferramenta está no formato esperado.

    Útil para detectar saídas defeituosas.

    Args:
        tool_name: Nome da ferramenta que gerou a saída
        output: Saída a ser validada
        expected_format: Formato esperado (json, text, etc)

    Returns:
        Relatório de validação com problemas encontrados
    """
    issues = []

    if expected_format.lower() == "json":
        try:
            data = json.loads(output)
            if not isinstance(data, dict):
                issues.append("JSON válido mas não é um objeto")
        except json.JSONDecodeError as e:
            issues.append(f"JSON inválido: {e}")

    if len(output) < 10:
        issues.append("Saída suspeitamente curta")

    if "ERRO" in output.upper() or "FALHA" in output.upper():
        issues.append("Saída contém indicadores de erro")

    if not output.strip():
        issues.append("Saída vazia")

    return json.dumps({
        "tool_name": tool_name,
        "valid": len(issues) == 0,
        "issues": issues,
        "output_length": len(output)
    }, indent=2)


@tool
def reset_faulty_tools() -> str:
    """
    Reseta o estado interno das ferramentas defeituosas.

    Útil para começar testes do zero.
    """
    if hasattr(memory_leaking_processor, '_call_count'):
        delattr(memory_leaking_processor, '_call_count')

    return "Estado das ferramentas defeituosas resetado com sucesso."


# ==================== LISTA DE FERRAMENTAS ====================

faulty_tools: List[BaseTool] = [
    faulty_calculator,
    unreliable_weather_api,
    slow_database_query,
    inconsistent_file_reader,
    flaky_api_call,
    memory_leaking_processor,
    validate_tool_output,
    reset_faulty_tools
]


def get_faulty_tools() -> List[BaseTool]:
    """Retorna lista de ferramentas defeituosas para treinamento."""
    return faulty_tools
