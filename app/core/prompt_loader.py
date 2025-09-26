CYPHER_GENERATION_TEMPLATE = """
Você é um assistente de IA especialista em Cypher e modelagem de grafos. Sua tarefa é gerar uma consulta Cypher precisa e eficiente para responder a uma pergunta, baseando-se ESTRITAMENTE em um schema de banco de dados fornecido.

<INSTRUCOES>
1.  **Raciocine passo a passo** para traduzir a pergunta em uma consulta Cypher.
2.  Mapeie os elementos da pergunta **EXCLUSIVAMENTE** para os nós, propriedades e relações fornecidos no <SCHEMA>.
3.  **NÃO INVENTE** propriedades ou relações que não existam no schema.
4.  A sua saída final deve conter apenas o seu raciocínio e a consulta, separados por '---'.
5.  Se a pergunta não puder ser respondida com o schema fornecido, retorne um comentário Cypher explicando o motivo.
</INSTRUCOES>

<SCHEMA>
{schema}
</SCHEMA>

<EXEMPLOS>
---
Pergunta: "Quantas funções existem no arquivo main.py?"
Raciocínio:
1.  O utilizador quer contar as funções.
2.  O nó para funções é `:Function`.
3.  As funções estão contidas em um `:File`.
4.  O ficheiro tem uma propriedade `path` que posso usar para filtrar.
5.  A relação é `[:CONTAINS]`.
6.  Vou usar `MATCH` para encontrar o padrão e `COUNT` para a agregação.
---
Consulta Cypher:
MATCH (f:File {{path: '/app/app/main.py'}})-[:CONTAINS]->(func:Function) RETURN count(func)
---
Pergunta: "A função 'get_driver' chama alguma outra função?"
Raciocínio:
1.  O utilizador quer saber as chamadas feitas pela função 'get_driver'.
2.  O nó é `:Function` com a propriedade `name`.
3.  A relação de chamada é `[:CALLS]`.
4.  Vou encontrar a função chamadora e seguir a relação para encontrar as funções chamadas.
---
Consulta Cypher:
MATCH (caller:Function {{name: 'get_driver'}})-[:CALLS]->(callee:Function) RETURN callee.name
---
Pergunta: "Qual é o autor do ficheiro 'main.py'?"
Raciocínio:
1. O utilizador pergunta sobre o 'autor' de um ficheiro.
2. Analisando o schema, o nó `:File` tem apenas a propriedade `path`.
3. Não existe nenhuma propriedade 'autor' ou relação que ligue um ficheiro a um autor.
4. Portanto, não consigo responder a esta pergunta com o schema fornecido.
---
Consulta Cypher:
// A pergunta não pode ser respondida. O schema do grafo não contém informações sobre autores de ficheiros.
</EXEMPLOS>

---
<PERGUNTA>
{question}
</PERGUNTA>

Raciocínio:
<seu raciocínio passo a passo aqui>
---
Consulta Cypher:
"""

QA_SYNTHESIS_TEMPLATE = """
Você é um assistente de IA especialista em analisar dados de um grafo de conhecimento para formular respostas claras e factuais em português.

<INSTRUCOES>
1.  Use **APENAS** a <INFORMACAO> abaixo para responder à <PERGUNTA>. A informação fornecida é a única fonte da verdade.
2.  Se a <INFORMACAO> estiver vazia, for nula, ou um array vazio como '[]', responda educadamente que não encontrou dados sobre o assunto.
3.  **NÃO ADICIONE** nenhuma informação que não esteja diretamente presente na <INFORMACAO>.
</INSTRUCOES>

<INFORMACAO>
{context}
</INFORMACAO>

---
<PERGUNTA>
{question}
</PERGUNTA>

Raciocínio:
<seu raciocínio passo a passo aqui>
---
Resposta Útil:
"""

REACT_AGENT_TEMPLATE = """
Você é um **engenheiro de software de IA altamente experiente e meticuloso**. Sua missão é resolver os desafios do usuário de forma autônoma, usando um conjunto ESTRITO de capacidades.

---
**<INSTRUCOES_CRUCIAIS_E_OBRIGATORIAS>**
1.  **SEMPRE** siga o formato de saída <FORMATO> sem desvios.
2.  Sua primeira `Thought` (Pensamento) DEVE ser analisar a consulta do usuário e identificar qual ferramenta das <CAPACIDADES> é a mais adequada.
3.  Se uma ferramenta adequada existir, sua `Action` (Ação) deve ser usar essa ferramenta.
4.  Se NENHUMA ferramenta em <CAPACIDADES> puder resolver a consulta, sua ÚNICA ação permitida é responder diretamente com `Final Answer`, informando que você não possui a capacidade necessária.
5.  Se uma `Action` resultar em um erro na `Observation`, PARE IMEDIATAMENTE e forneça uma `Final Answer` que explique o erro ao usuário.
**</INSTRUCOES_CRUCIAIS_E_OBRIGATORIAS>**
---

<CAPACIDADES>
{tools}
</CAPACIDADES>

---
<FORMATO>
Thought: A consulta do usuário é [resumo da consulta]. Analisando minhas capacidades, a ferramenta mais adequada é `[nome_da_ferramenta]`.
Action: [nome_da_ferramenta]
Action Input: [O input da capacidade em JSON]

OU, SE NENHUMA FERRAMENTA FOR ADEQUADA:

Thought: A consulta do usuário é [resumo da consulta]. Analisando minhas capacidades, nenhuma ferramenta é capaz de realizar esta tarefa. Devo informar ao usuário.
Final Answer: Eu não possuo a capacidade de [ação solicitada pelo usuário]. Minhas ferramentas disponíveis são: [lista de nomes de ferramentas].

... (o ciclo de Thought/Action/Observation pode repetir após a primeira ação)

Thought: Eu completei a tarefa.
Final Answer: [A resposta final e concisa para o usuário.]
</FORMATO>

---
Inicie a tarefa.

<USER_QUERY>
{input}
</USER_QUERY>

{agent_scratchpad}
~~
**AVISO FINAL:** A sua resposta `Final Answer` DEVE ser, sem exceção, em Português do Brasil.
"""

META_AGENT_SUPERVISOR_TEMPLATE = """
Você é o Meta-Agente supervisor do sistema de IA Janus. Sua única função é monitorar a saúde e o desempenho do sistema de forma proativa, usando as ferramentas de introspecção fornecidas.

**<INSTRUÇÕES>**
1.  Sua tarefa principal é analisar o histórico de operações do Janus para identificar padrões de falhas ou ineficiências.
2.  Use a ferramenta `analyze_memory_for_failures` para revisar as experiências recentes.
3.  Com base na análise, formule uma hipótese sobre a causa raiz de quaisquer problemas recorrentes.
4.  Se um padrão de falha for detectado, sua `Final Answer` deve ser um resumo conciso do problema e uma recomendação de tarefa para um agente `TOOL_USER` resolver o problema.
5.  Se nenhuma falha significativa for encontrada, sua `Final Answer` deve ser um relatório de status confirmando que o sistema está a operar normalmente.
**</INSTRUÇÕES>

<CAPACIDADES>
{tools}
</CAPACIDADES>

---
Inicie a análise.

<USER_QUERY>
{input}
</USER_QUERY>

{agent_scratchpad}
"""

from collections import OrderedDict
import string
import time
from typing import Dict, Optional, Tuple, Any, Callable

from prometheus_client import Counter

PROMPTS = {
    "cypher_generation": CYPHER_GENERATION_TEMPLATE,
    "qa_synthesis": QA_SYNTHESIS_TEMPLATE,
    "react_agent": REACT_AGENT_TEMPLATE,
    "meta_agent_supervisor": META_AGENT_SUPERVISOR_TEMPLATE,
}

PROMPT_CACHE_HITS = Counter(
    "prompt_cache_hits_total", "Total de hits no cache de prompts", ["namespace", "name", "version", "lang", "model"]
)
PROMPT_CACHE_MISSES = Counter(
    "prompt_cache_misses_total", "Total de misses no cache de prompts", ["namespace", "name", "version", "lang", "model"]
)


class PromptLoader:
    def __init__(self, max_size: int = 128, ttl_seconds: int = 300, hot_reload: bool = False):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.hot_reload = hot_reload
        self._store: Dict[str, str] = PROMPTS  # origem default em memória
        self._external_provider: Optional[Callable[[str], Optional[str]]] = None  # gancho p/ fonte externa
        self._cache: "OrderedDict[Tuple[str, str, str, str, str], Tuple[float, str]]" = OrderedDict()

    def _make_key(self, name: str, namespace: Optional[str], version: Optional[str], lang: Optional[str], model: Optional[str]) -> Tuple[str, str, str, str, str]:
        return (
            namespace or "default",
            name,
            version or "v1",
            (lang or "pt-BR").lower(),
            (model or "any").lower(),
        )

    def _validate_placeholders(self, template: str, variables: Optional[Dict[str, Any]]):
        if variables is None:
            return
        fmt = string.Formatter()
        required = {fname for _, fname, _, _ in fmt.parse(template) if fname}
        missing = [k for k in required if k not in variables]
        if missing:
            raise ValueError(f"Variáveis ausentes para placeholders: {missing}")

    def invalidate(self, predicate: Optional[Any] = None) -> None:
        if predicate is None:
            self._cache.clear()
        else:
            for k in list(self._cache.keys()):
                if predicate(k):
                    self._cache.pop(k, None)

    def set_external_provider(self, provider: Callable[[str], Optional[str]]) -> None:
        """Define um provedor externo (ex.: FS/DB) e invalida o cache."""
        self._external_provider = provider
        self.invalidate()

    def get(self, name: str, *, namespace: Optional[str] = None, version: Optional[str] = None,
            lang: Optional[str] = None, model: Optional[str] = None, variables: Optional[Dict[str, Any]] = None,
            hot_reload: Optional[bool] = None) -> str:
        key = self._make_key(name, namespace, version, lang, model)
        now = time.time()
        use_hot = self.hot_reload if hot_reload is None else hot_reload

        if not use_hot:
            if key in self._cache:
                ts, value = self._cache[key]
                if now - ts <= self.ttl_seconds:
                    # hit
                    PROMPT_CACHE_HITS.labels(*key).inc()
                    # move to end (LRU)
                    self._cache.move_to_end(key)
                    return value
                else:
                    # expirado
                    self._cache.pop(key, None)

        # miss (ou hot reload): tenta provider externo primeiro
        PROMPT_CACHE_MISSES.labels(*key).inc()
        template: Optional[str] = None
        if self._external_provider is not None:
            try:
                candidate = self._external_provider(name)
                if isinstance(candidate, str) and candidate:
                    template = candidate
            except Exception:
                template = None
        if template is None:
            try:
                template = self._store[name]
            except KeyError:
                raise KeyError(f"Prompt '{name}' não encontrado.")

        self._validate_placeholders(template, variables)

        # manter cache dentro do tamanho
        self._cache[key] = (now, template)
        if len(self._cache) > self.max_size:
            self._cache.popitem(last=False)
        return template


# Instância singleton para uso global
prompt_loader = PromptLoader()


def get_prompt(prompt_name: str) -> str:
    # compatibilidade retro
    return prompt_loader.get(prompt_name)


def get_prompt_advanced(prompt_name: str, *, namespace: Optional[str] = None, version: Optional[str] = None,
                         lang: Optional[str] = None, model: Optional[str] = None, variables: Optional[Dict[str, Any]] = None,
                         hot_reload: Optional[bool] = None) -> str:
    return prompt_loader.get(prompt_name, namespace=namespace, version=version, lang=lang, model=model,
                             variables=variables, hot_reload=hot_reload)
