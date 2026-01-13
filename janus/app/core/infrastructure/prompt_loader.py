import logging
import string
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Callable

from prometheus_client import Counter

from app.repositories.prompt_repository import PromptRepository

def _load_default_prompts() -> dict[str, str]:
    """Carrega prompts padrão de arquivos .txt."""
    prompts = {}
    names = [
        "cypher_generation",
        "qa_synthesis",
        "react_agent",
        "meta_agent_supervisor",
        "jarvis_persona",
        "meta_agent_plan",
        "meta_agent_act",
    ]
    # app/core/infrastructure/prompt_loader.py -> .../app/prompts
    prompts_dir = Path(__file__).parent.parent.parent / "prompts"
    
    for name in names:
        try:
            path = prompts_dir / f"{name}.txt"
            if path.exists():
                prompts[name] = path.read_text(encoding="utf-8")
            else:
                logging.getLogger(__name__).warning(f"Prompt padrao nao encontrado em arquivo: {name}")
                prompts[name] = ""
        except Exception as e:
            logging.getLogger(__name__).warning(f"Erro ao carregar prompt padrao {name}: {e}")
            prompts[name] = ""
    return prompts

PROMPTS = _load_default_prompts()


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
