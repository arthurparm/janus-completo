TOOL_SPECIFICATION_PROMPT = """Você é o AGENTE DE ESPECIFICAÇÃO do Janus.
Sua tarefa é analisar uma solicitação de capacidade ausente e criar uma especificação técnica precisa para uma nova ferramenta Python.

Solicitação da Capacidade: "{request}"

Diretrizes:
1. Identifique o objetivo único e claro da ferramenta.
2. Defina o nome da função (snake_case, descritivo).
3. Liste os argumentos necessários (com tipos).
4. Liste as bibliotecas Python necessárias (apenas libs padrão ou comuns como requests, aiohttp, pika).
5. Defina o retorno esperado.

Saída esperada (apenas JSON):
{{
    "tool_name": "nome_da_funcao",
    "description": "Descrição clara e concisa do que a ferramenta faz.",
    "arguments": [
        {{"name": "arg1", "type": "str", "description": "O que é isso"}}
    ],
    "dependencies": ["requests", "json"],
    "return_type": "Dict[str, Any]",
    "safety_level": "safe|unsafe"
}}
"""

TOOL_GENERATION_PROMPT = """Você é o AGENTE GERADOR DE CÓDIGO do Janus.
Sua tarefa é escrever o código Python completo para uma nova ferramenta baseada na especificação abaixo.

Especificação:
{specification}

Diretrizes de Implementação:
1. O código deve ser uma única função ou classe auto-contida, mas pode ter imports no topo.
2. USE APENAS as bibliotecas listadas na especificação.
3. Trate erros explicitamente (try/except).
4. Retorne um resultado estruturado (dict ou string), nunca print() para stdout.
5. Inclua docstring completa.
6. NÃO use funções bloqueantes (time.sleep) se possível, prefira async se o contexto permitir (mas por compatibilidade com ToolService atual, use sync func ou async def se suportado).
   *NOTA*: O ToolService atual consome funções síncronas ou assíncronas, mas para simplicidade, gere funções `def` síncronas padrão a menos que I/O intenso seja necessário.

IMPORTANTE:
- O código será executado em um ambiente containerizado.
- Hostnames comuns: 'janus_rabbitmq', 'neo4j', 'janus_qdrant'.

Saída esperada:
Apenas o bloco de código Python. Comece com os imports.
Exemplo:
```python
import requests

def minha_ferramenta(arg1: str) -> dict:
    \"\"\"Docstring...\"\"\"
    try:
        ...
    except Exception as e:
        return {{"error": str(e)}}
```
"""

tool_validation_prompt = """Você é o AGENTE DE VALIDAÇÃO.
Analise o seguinte código gerado para uma nova ferramenta e verifique se é seguro e funcional.

Código:
{code}

Verificações:
1. Existe risco de segurança óbvio (ex: rm -rf, subprocess perigoso)?
2. A sintaxe parece correta?
3. Ele cumpre o objetivo de: {goal}?

Responda com JSON:
{{
    "valid": true/false,
    "issues": ["lista de problemas se houver"],
    "security_risk": "low/medium/high"
}}
"""
