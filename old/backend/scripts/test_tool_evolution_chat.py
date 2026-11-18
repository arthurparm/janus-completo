import time

import requests

BASE_URL = "http://localhost:8000"
CHAT_URL = f"{BASE_URL}/api/v1/chat"
TOOLS_URL = f"{BASE_URL}/api/v1/tools"


def list_tools_names():
    try:
        resp = requests.get(f"{TOOLS_URL}/")
        resp.raise_for_status()
        data = resp.json()
        names = {t["name"] for t in data.get("tools", [])}
        return names, data
    except Exception as e:
        print("Erro ao listar ferramentas:", e)
        return set(), None


def start_conversation(title):
    payload = {
        "persona": "architect",
        "user_id": "tool_test_user",
        "project_id": "janus_core",
        "title": title,
    }
    resp = requests.post(f"{CHAT_URL}/start", json=payload)
    resp.raise_for_status()
    cid = resp.json()["conversation_id"]
    print("Conversa iniciada:", cid)
    return cid


def send_message(conversation_id, message, role="orchestrator", priority="high_quality"):
    payload = {
        "conversation_id": conversation_id,
        "message": message,
        "role": role,
        "priority": priority,
        "user_id": "tool_test_user",
        "project_id": "janus_core",
    }
    print("--- Enviando mensagem:", message)
    start = time.time()
    resp = requests.post(f"{CHAT_URL}/message", json=payload)
    duration = time.time() - start
    print("Status:", resp.status_code, "Tempo:", round(duration, 2), "s")
    resp.raise_for_status()
    data = resp.json()
    print("Resposta:", data.get("response"))
    return data


def test_tool_creation_cep_basic():
    print("==== Teste 1: criação ferramenta CEP básica ====")
    before_names, _ = list_tools_names()
    print("Total de ferramentas antes:", len(before_names))

    cid = start_conversation("Criação ferramenta CEP básica")

    full_spec_message = (
        "Quero criar uma única ferramenta interna de sistema, usando o mecanismo de auto-evolução, "
        "para consulta de CEP brasileiro via ViaCEP. Por favor leia toda a especificação abaixo e, "
        "se já existir alguma ferramenta de CEP nesta conversa (como 'consultar_cep', "
        "'consultar_endereco_por_cep' ou 'fetch_brazilian_address_by_cep'), NÃO crie uma nova: "
        "aprimorar/refinar a existente e manter apenas uma ferramenta final com o nome pedido.\n\n"
        "Especificação desejada:\n"
        "- Nome interno exato da tool: cep_lookup_e2e_test_1\n"
        "- Tipo: ferramenta de sistema que o próprio Janus chama como tool (não é script solto).\n"
        "- Fonte de dados: API pública ViaCEP, endpoint HTTPS no formato "
        "https://viacep.com.br/ws/{cep}/json/ (sem parênteses e sem caracteres extras na URL).\n"
        "- Entrada: um único parâmetro 'cep' como texto, aceitando CEP com ou sem hífen ou espaços "
        "(ex: '01001-000', '01001000', '01001 000').\n"
        "- Normalização: remover tudo que não for dígito e exigir exatamente 8 dígitos; se não "
        "tiver 8 dígitos após normalizar, retornar erro.\n"
        "- Comportamento:\n"
        "  1) Normalizar o CEP.\n"
        "  2) Validar formato (8 dígitos).\n"
        "  3) Chamar ViaCEP com HTTPS, timeout razoável e tratamento de exceções.\n"
        "  4) Interpretar a resposta JSON e montar um retorno estruturado.\n"
        "- Formato de retorno (sempre um dict):\n"
        "  {\n"
        "    'success': bool,\n"
        "    'data': {\n"
        "      'cep_normalizado': str | None,\n"
        "      'logradouro': str | None,\n"
        "      'bairro': str | None,\n"
        "      'cidade': str | None,\n"
        "      'estado': str | None,\n"
        "      'raw_response': dict | None\n"
        "    } | None,\n"
        "    'error': str | None\n"
        "  }\n"
        "- Casos de erro que devem ser tratados explicitamente, sempre com success=False:\n"
        "  * CEP com formato inválido (menos ou mais de 8 dígitos após normalizar).\n"
        "  * CEP não encontrado pela API (incluindo respostas de erro/404 do ViaCEP).\n"
        "  * Problemas de rede, DNS, timeout ou resposta JSON inválida.\n"
        "- Mensagens de erro devem ser claras (por exemplo: 'CEP inválido', "
        "'CEP não encontrado', 'Erro ao acessar ViaCEP: ...').\n"
        "- Nível de permissão: 'safe'.\n"
        "- Categoria: 'custom'.\n\n"
        "Tarefa: usando o mecanismo de auto-evolução, crie ou atualize uma ÚNICA ferramenta com "
        "essas características, garantindo que o nome interno final seja exatamente "
        "'cep_lookup_e2e_test_1'. Se já existir alguma ferramenta de CEP criada anteriormente, "
        "reaproveite-a e refine o código em vez de registrar uma quarta ferramenta. No final, "
        "me responda confirmando o nome exato da ferramenta registrada, a categoria, o nível de "
        "permissão e um exemplo de chamada usando o CEP 01001000."
    )

    send_message(cid, full_spec_message)

    after_names, _ = list_tools_names()
    print("Total de ferramentas depois:", len(after_names))
    new_tools = after_names - before_names
    print("Ferramentas novas após Teste 1:", new_tools)

    if "cep_lookup_e2e_test_1" in after_names:
        resp = requests.get(f"{TOOLS_URL}/cep_lookup_e2e_test_1")
        print("Detalhes da ferramenta cep_lookup_e2e_test_1:", resp.status_code, resp.json())
    else:
        print("Ferramenta cep_lookup_e2e_test_1 não encontrada após criação.")

    print("==== Exercitando ferramenta cep_lookup_e2e_test_1 ====")
    send_message(
        cid,
        "Agora use a ferramenta cep_lookup_e2e_test_1 para consultar o CEP 01001000. Me responda claramente com logradouro, bairro, cidade e estado retornados pela API oficial de CEP.",
    )


def test_tool_creation_cep_refined():
    print("==== Teste 2: criação ferramenta CEP refinada ====")
    before_names, _ = list_tools_names()
    print("Total de ferramentas antes:", len(before_names))

    cid = start_conversation("Refinamento ferramenta CEP existente")

    refinement_message = (
        "Agora quero REFINAR a ferramenta de CEP existente em vez de criar outra nova. "
        "Considere que já existe uma ferramenta de CEP criada na conversa anterior "
        "(idealmente 'cep_lookup_e2e_test_1' ou alguma equivalente). A tarefa agora é: "
        "aprimorar essa mesma ferramenta, sem registrar outra ferramenta adicional.\n\n"
        "Refinamento desejado:\n"
        "- Manter todo o comportamento atual de consulta ViaCEP, normalização e tratamento de erros.\n"
        "- Estender o campo de dados retornados para incluir dois novos itens em data:\n"
        "  * 'tipo_logradouro': string opcional com o tipo do logradouro (ex.: 'Praça', 'Rua', 'Avenida'), "
        "extraído do início do campo logradouro quando fizer sentido.\n"
        "  * 'eh_capital': booleano indicando se a cidade retornada é capital do estado.\n"
        "- Essa lógica deve ser implementada dentro da MESMA ferramenta já criada (não crie "
        "uma nova como 'consultar_cep', 'consultar_endereco_por_cep' ou outro nome diferente).\n\n"
        "Tarefa: use o mecanismo de auto-evolução para atualizar/refinar o código da ferramenta "
        "de CEP existente, preservando o nome interno já registrado. No final, explique rapidamente "
        "quais mudanças foram feitas no contrato de saída e mostre um exemplo de resposta completa "
        "para o CEP 01001000, incluindo tipo_logradouro e eh_capital."
    )

    send_message(cid, refinement_message)

    after_names, _ = list_tools_names()
    print("Total de ferramentas depois:", len(after_names))
    new_tools = after_names - before_names
    print("Ferramentas novas após Teste 2:", new_tools)

    if "cep_lookup_e2e_test_2" in after_names:
        resp = requests.get(f"{TOOLS_URL}/cep_lookup_e2e_test_2")
        print("Detalhes da ferramenta cep_lookup_e2e_test_2:", resp.status_code, resp.json())
    else:
        print("Ferramenta cep_lookup_e2e_test_2 não encontrada após criação.")

    print("==== Exercitando ferramenta cep_lookup_e2e_test_2 ====")
    send_message(
        cid,
        "Agora use a ferramenta cep_lookup_e2e_test_2 para consultar o CEP 01001000. Me responda listando todos os campos que ela retorna.",
    )


if __name__ == "__main__":
    test_tool_creation_cep_basic()
    print()
    test_tool_creation_cep_refined()
