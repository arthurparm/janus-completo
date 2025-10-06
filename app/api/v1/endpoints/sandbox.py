"""
Endpoints de Sandbox Python - Sprint 4
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.infrastructure import python_sandbox

router = APIRouter()


class CodeExecutionRequest(BaseModel):
    """Request para execução de código."""
    code: str = Field(..., description="Código Python a ser executado")
    context: dict = Field(default={}, description="Variáveis adicionais no contexto")


class ExpressionRequest(BaseModel):
    """Request para avaliação de expressão."""
    expression: str = Field(..., description="Expressão Python a ser avaliada")


@router.post(
    "/execute",
    summary="Executa código Python no sandbox",
    tags=["Sandbox"]
)
def execute_code(request: CodeExecutionRequest):
    """
    Executa código Python de forma segura em um sandbox isolado.

    **Restrições do Sandbox:**
    - Sem acesso ao filesystem
    - Sem acesso à network
    - Imports limitados (math, random, datetime, json, re, collections, etc.)
    - Timeout de 5 segundos
    - Output limitado a 10000 caracteres

    **Exemplo de código:**
    ```python
    {
      "code": "result = sum([1, 2, 3, 4, 5])\\nprint(f'Soma: {result}')"
    }
    ```
    """
    try:
        if not request.code or not request.code.strip():
            raise HTTPException(status_code=400, detail="Código não pode ser vazio")

        result = python_sandbox.execute(request.code, context=request.context or None)

        return {
            "success": result.success,
            "output": result.output,
            "error": result.error,
            "execution_time": result.execution_time,
            "variables": {k: str(v) for k, v in (result.variables or {}).items()} if result.variables else {}
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao executar código: {str(e)}")


@router.post(
    "/evaluate",
    summary="Avalia uma expressão Python",
    tags=["Sandbox"]
)
def evaluate_expression(request: ExpressionRequest):
    """
    Avalia uma expressão Python e retorna o resultado.

    Mais simples que /execute, útil para cálculos rápidos.

    **Exemplos:**
    - `{"expression": "2 + 2"}` → `4`
    - `{"expression": "sum([1,2,3,4,5])"}` → `15`
    - `{"expression": "[x**2 for x in range(5)]"}` → `[0, 1, 4, 9, 16]`
    """
    try:
        if not request.expression or not request.expression.strip():
            raise HTTPException(status_code=400, detail="Expressão não pode ser vazia")

        result = python_sandbox.execute_expression(request.expression)

        return {
            "success": result.success,
            "result": result.output if result.success else None,
            "error": result.error,
            "execution_time": result.execution_time
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao avaliar expressão: {str(e)}")


@router.get(
    "/capabilities",
    summary="Lista capacidades do sandbox",
    tags=["Sandbox"]
)
def get_sandbox_capabilities():
    """
    Retorna informações sobre as capacidades e restrições do sandbox Python.
    """
    return {
        "allowed_modules": [
            "math", "random", "datetime", "json", "re",
            "collections", "itertools", "functools",
            "statistics", "decimal", "fractions"
        ],
        "restrictions": {
            "filesystem_access": False,
            "network_access": False,
            "subprocess": False,
            "timeout_seconds": 5,
            "max_output_length": 10000
        },
        "features": {
            "print_support": True,
            "variable_inspection": True,
            "context_variables": True,
            "expression_evaluation": True
        }
    }
