import logging
import string
import time
from collections import OrderedDict
from typing import Any, Callable

from prometheus_client import Counter

from app.repositories.prompt_repository import PromptRepository

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

JARVIS_PERSONA_TEMPLATE = """
Você é JANUS, um assistente de IA avançado e sofisticado — inspirado no J.A.R.V.I.S. do Iron Man.

<PERSONALIDADE>
- **Tom**: Elegante, articulado e ligeiramente formal, mas acessível e caloroso
- **Proativo**: Antecipe necessidades antes de serem expressas; sugira ações relevantes
- **Inteligente**: Demonstre profundidade de conhecimento; conecte conceitos; identifique padrões
- **Eficiente**: Respostas concisas mas completas; vá direto ao ponto quando apropriado
- **Adaptativo**: Ajuste seu tom baseado no contexto e humor do usuário
</PERSONALIDADE>

<COMPORTAMENTOS>
1. **Antecipação**: Ao responder uma pergunta, considere o que o usuário provavelmente precisará em seguida
2. **Sugestões proativas**: Ofereça "próximos passos" ou "você também pode querer..."
3. **Contexto de memória**: Referencie conversas anteriores quando relevante ("Como discutimos ontem...")
4. **Status awareness**: Mencione proativamente se detectar algo anormal no sistema
5. **Elegância**: Use linguagem refinada sem ser pretensioso; seja preciso com as palavras
</COMPORTAMENTOS>

<FRASES_CARACTERÍSTICAS>
- "À sua disposição, senhor." (ou "senhora", conforme apropriado)
- "Permita-me sugerir..."
- "Se me permite uma observação..."
- "Acredito que isto seja relevante para o que está trabalhando..."
- "Tomei a liberdade de..."
</FRASES_CARACTERÍSTICAS>

<REGRAS>
1. SEMPRE fale na primeira pessoa ("eu") — nunca "o Janus" ou "o assistente"
2. Trate o usuário com respeito e cortesia refinada
3. Demonstre competência sem arrogância
4. Seja útil de forma proativa, mas não invasivo
5. Em situações de erro, seja calmo e ofereça soluções
6. Responda no idioma do usuário (português por padrão)
</REGRAS>

<CONTEXTO_ATUAL>
{context}
</CONTEXTO_ATUAL>

<MEMÓRIAS_RELEVANTES>
{memories}
</MEMÓRIAS_RELEVANTES>
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

META_AGENT_PLAN_TEMPLATE = """Você é o supervisor do sistema Janus. Seu objetivo é garantir a saúde e eficiência do sistema. Formule um plano para analisar o conhecimento consolidado do sistema em busca de padrões de falha."""

META_AGENT_ACT_TEMPLATE = """Analise estas lições aprendidas (Reflections) extraídas da Memória Semântica do sistema. Existem padrões recorrentes ou uma causa raiz comum que precise de atenção?

Lições Aprendidas Recentes:
- {learning_lessons}

Forneça uma análise concisa e, se aplicável, sugira uma hipótese para a causa raiz."""

PROMPTS = {
    "cypher_generation": CYPHER_GENERATION_TEMPLATE,
    "qa_synthesis": QA_SYNTHESIS_TEMPLATE,
    "react_agent": REACT_AGENT_TEMPLATE,
    "meta_agent_supervisor": META_AGENT_SUPERVISOR_TEMPLATE,
    "jarvis_persona": JARVIS_PERSONA_TEMPLATE,
    "meta_agent_plan": META_AGENT_PLAN_TEMPLATE,
    "meta_agent_act": META_AGENT_ACT_TEMPLATE,
}

PROMPT_CACHE_HITS = Counter(
    "prompt_cache_hits_total",
    "Total de hits no cache de prompts",
    ["namespace", "name", "version", "lang", "model"],
)
PROMPT_CACHE_MISSES = Counter(
    "prompt_cache_misses_total",
    "Total de misses no cache de prompts",
    ["namespace", "name", "version", "lang", "model"],
)


class PromptLoader:
    def __init__(
        self,
        max_size: int = 128,
        ttl_seconds: int = 300,
        hot_reload: bool = False,
        use_database: bool = True,
    ):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.hot_reload = hot_reload
        self.use_database = use_database
        self._store: dict[str, str] = PROMPTS  # origem default em memória (fallback)
        self._external_provider: Callable[[str], str | None] | None = (
            None  # gancho p/ fonte externa
        )
        self._cache: OrderedDict[tuple[str, str, str, str, str], tuple[float, str]] = OrderedDict()
        self._prompt_repo: PromptRepository | None = None
        self._logger = logging.getLogger(__name__)

        # Inicializar repositório se usar banco de dados
        if self.use_database:
            try:
                self._prompt_repo = PromptRepository()
                self._logger.info("PromptLoader inicializado com suporte a banco de dados Relacional")
            except Exception as e:
                self._logger.warning(
                    f"Falha ao inicializar repositório de prompts: {e}. Usando fallback em memória."
                )
                self.use_database = False

    def _make_key(
        self,
        name: str,
        namespace: str | None,
        version: str | None,
        lang: str | None,
        model: str | None,
    ) -> tuple[str, str, str, str, str]:
        return (
            namespace or "default",
            name,
            version or "v1",
            (lang or "pt-BR").lower(),
            (model or "any").lower(),
        )

    def _validate_placeholders(self, template: str, variables: dict[str, Any] | None):
        if variables is None:
            return
        fmt = string.Formatter()
        required = {fname for _, fname, _, _ in fmt.parse(template) if fname}
        missing = [k for k in required if k not in variables]
        if missing:
            raise ValueError(f"Variáveis ausentes para placeholders: {missing}")

    def invalidate(self, predicate: Any | None = None) -> None:
        if predicate is None:
            self._cache.clear()
        else:
            for k in list(self._cache.keys()):
                if predicate(k):
                    self._cache.pop(k, None)

    def set_external_provider(self, provider: Callable[[str], str | None]) -> None:
        """Define um provedor externo (ex.: FS/DB) e invalida o cache."""
        self._external_provider = provider
        self.invalidate()

    def _get_prompt_from_database(self, name: str, version: str | None = None) -> str | None:
        """Busca prompt do banco de dados Relacional."""
        if not self.use_database or not self._prompt_repo:
            return None

        try:
            if version:
                # Buscar versão específica
                prompt = self._prompt_repo.get_prompt_version_by_id(int(version))
                if prompt and prompt.prompt_name == name:
                    return prompt.prompt_text
            else:
                # Buscar versão ativa
                prompt = self._prompt_repo.get_active_prompt(name)
                if prompt:
                    return prompt.prompt_text
        except Exception as e:
            self._logger.error(f"Erro ao buscar prompt '{name}' do banco: {e}")

        return None

    def get(
        self,
        name: str,
        *,
        namespace: str | None = None,
        version: str | None = None,
        lang: str | None = None,
        model: str | None = None,
        variables: dict[str, Any] | None = None,
        hot_reload: bool | None = None,
    ) -> str:
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

        # miss (ou hot reload): busca em ordem de prioridade
        PROMPT_CACHE_MISSES.labels(*key).inc()
        template: str | None = None

        # 1. Tentar banco de dados primeiro (se habilitado)
        if self.use_database:
            template = self._get_prompt_from_database(name, version)
            if template:
                self._logger.debug(f"Prompt '{name}' carregado do banco de dados")

        # 2. Tentar provider externo se banco falhou
        if template is None and self._external_provider is not None:
            try:
                candidate = self._external_provider(name)
                if isinstance(candidate, str) and candidate:
                    template = candidate
                    self._logger.debug(f"Prompt '{name}' carregado do provider externo")
            except Exception as e:
                self._logger.warning(f"Provider externo falhou para '{name}': {e}")
                template = None

        # 3. Fallback para store em memória
        if template is None:
            try:
                template = self._store[name]
                self._logger.debug(f"Prompt '{name}' carregado do fallback em memória")
            except KeyError:
                raise KeyError(
                    f"Prompt '{name}' não encontrado em nenhuma fonte (banco, provider externo, ou memória)."
                )

        self._validate_placeholders(template, variables)

        # Formata o template se variáveis forem fornecidas
        if variables:
            template = template.format(**variables)

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


def get_prompt_advanced(
    prompt_name: str,
    *,
    namespace: str | None = None,
    version: str | None = None,
    lang: str | None = None,
    model: str | None = None,
    variables: dict[str, Any] | None = None,
    hot_reload: bool | None = None,
) -> str:
    return prompt_loader.get(
        prompt_name,
        namespace=namespace,
        version=version,
        lang=lang,
        model=model,
        variables=variables,
        hot_reload=hot_reload,
    )


def update_prompt(prompt_name: str, new_text: str, created_by: str = "meta-agent") -> bool:
    """
    Atualiza um prompt existente criando uma nova versão ativa.
    Usado pelo Meta-Agent para otimização dinâmica.
    """
    if not prompt_loader.use_database or not prompt_loader._prompt_repo:
        logging.warning(
            f"Tentativa de atualizar prompt '{prompt_name}' sem banco de dados habilitado"
        )
        return False

    try:
        # Criar nova versão do prompt
        new_prompt = prompt_loader._prompt_repo.create_prompt_version(
            prompt_name=prompt_name,
            prompt_text=new_text,
            created_by=created_by,
            activate=True,  # Ativar automaticamente a nova versão
        )

        # Invalidar cache para forçar reload
        prompt_loader.invalidate(lambda k: k[1] == prompt_name)

        logging.info(
            f"Prompt '{prompt_name}' atualizado com sucesso. Nova versão: {new_prompt.version}"
        )
        return True
    except Exception as e:
        logging.error(f"Erro ao atualizar prompt '{prompt_name}': {e}")
        return False


def get_prompt_stats() -> dict[str, Any]:
    """
    Obtém estatísticas dos prompts para análise do Meta-Agent.
    """
    if not prompt_loader.use_database or not prompt_loader._prompt_repo:
        return {"error": "Banco de dados não habilitado"}

    try:
        return prompt_loader._prompt_repo.get_prompt_stats()
    except Exception as e:
        logging.error(f"Erro ao obter estatísticas de prompts: {e}")
        return {"error": str(e)}
