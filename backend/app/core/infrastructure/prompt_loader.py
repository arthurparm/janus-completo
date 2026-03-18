import string
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Callable

import structlog
from prometheus_client import Counter

from app.repositories.prompt_repository import PromptRepository

PROMPTS = {}
_file_prompts_cache: dict[str, str] = {}


def _path_exists_safely(path: Path) -> bool:
    try:
        return path.exists()
    except OSError:
        return False


PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"
if not _path_exists_safely(PROMPTS_DIR):
    container_prompts_dir = Path("/app/app/prompts")
    if _path_exists_safely(container_prompts_dir):
        PROMPTS_DIR = container_prompts_dir


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
logger = structlog.get_logger(__name__)


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
        self._logger = logger

        # Inicializar repositório se usar banco de dados
        if self.use_database:
            try:
                self._prompt_repo = PromptRepository()
                self._logger.info(
                    "PromptLoader inicializado com suporte a banco de dados Relacional"
                )
            except Exception as e:
                self._logger.warning(
                    "log_warning",
                    message=f"Falha ao inicializar repositório de prompts: {e}. Usando fallback em memória.",
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
            (lang or "en").lower(),
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

    async def _get_prompt_from_database(
        self,
        name: str,
        version: str | None = None,
        namespace: str | None = None,
        lang: str | None = None,
        model: str | None = None,
    ) -> str | None:
        """Busca prompt do banco de dados Relacional (Async)."""
        if not self.use_database or not self._prompt_repo:
            return None

        try:
            from app.db import get_db_session

            # Usar gerenciador de sessão para injetar sessão no repositório
            async for session in get_db_session():
                # Injetar sessão temporariamente
                self._prompt_repo._async_session = session
                try:
                    if version:
                        # Buscar versão específica (ainda não implementado async no repo, mas placeholder)
                        # prompt = await self._prompt_repo.get_prompt_version_by_id(int(version))
                        pass
                    else:
                        # Buscar versão ativa
                        prompt = await self._prompt_repo.get_active_prompt(
                            prompt_name=name,
                            namespace=namespace or "default",
                            language=lang or "en",
                            model_target=model or "general",
                        )
                        if prompt:
                            return prompt.prompt_text
                finally:
                    self._prompt_repo._async_session = None
                break  # Apenas uma sessão necessária

        except Exception as e:
            self._logger.error("log_error", message=f"Erro ao buscar prompt '{name}' do banco: {e}")

        return None

    def _get_prompt_from_file(self, name: str) -> str | None:
        if not PROMPTS_DIR.exists():
            return None

        # Buscar primeiro no diretório raiz (compatibilidade), depois em subdiretórios
        file_path = PROMPTS_DIR / f"{name}.txt"
        if not file_path.exists():
            # Busca recursiva em subdiretórios organizados por subsistema
            matches = list(PROMPTS_DIR.rglob(f"{name}.txt"))
            if not matches:
                return None
            file_path = matches[0]

        try:
            if name in _file_prompts_cache:
                return _file_prompts_cache[name]

            content = file_path.read_text(encoding="utf-8")
            _file_prompts_cache[name] = content
            self._logger.debug(
                "log_debug", message=f"Prompt '{name}' carregado de arquivo local: {file_path}"
            )
            return content
        except Exception as e:
            self._logger.warning(
                "log_warning", message=f"Erro ao ler arquivo de prompt '{name}': {e}"
            )
            return None

    async def get(
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
            template = await self._get_prompt_from_database(
                name, version=version, namespace=namespace, lang=lang, model=model
            )
            if template:
                self._logger.debug(
                    "log_debug", message=f"Prompt '{name}' carregado do banco de dados"
                )

        # 2. Tentar provider externo se banco falhou
        if template is None and self._external_provider is not None:
            try:
                # Nota: Providers externos ainda podem ser síncronos se não atualizados
                candidate = self._external_provider(name)
                if isinstance(candidate, str) and candidate:
                    template = candidate
                    self._logger.debug(
                        "log_debug", message=f"Prompt '{name}' carregado do provider externo"
                    )
            except Exception as e:
                self._logger.warning(
                    "log_warning", message=f"Provider externo falhou para '{name}': {e}"
                )
                template = None

        # 3. Fallback para arquivo local
        if template is None:
            template = self._get_prompt_from_file(name)

        # 4. Fallback para store em memória
        if template is None:
            try:
                template = self._store[name]
                self._logger.debug(
                    "log_debug", message=f"Prompt '{name}' carregado do fallback em memória"
                )
            except KeyError:
                raise KeyError(
                    f"Prompt '{name}' não encontrado em nenhuma fonte (banco, provider externo, arquivo)."
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


async def get_prompt(
    prompt_name: str,
    *,
    namespace: str | None = None,
    version: str | None = None,
    lang: str | None = None,
    model: str | None = None,
    hot_reload: bool | None = None,
) -> str | None:
    """Retorna o prompt bruto (sem formatação) usando a hierarquia canônica de fontes."""
    try:
        return await prompt_loader.get(
            prompt_name,
            namespace=namespace,
            version=version,
            lang=lang,
            model=model,
            hot_reload=hot_reload,
        )
    except KeyError:
        return None


async def get_formatted_prompt(prompt_name: str, **format_kwargs) -> str:
    """
    Carrega um prompt pela hierarquia canônica e aplica formatação.

    Se faltar placeholder, registra erro e retorna o template bruto (comportamento tolerante).
    """
    prompt = await get_prompt(prompt_name)
    if not prompt:
        raise ValueError(f"Prompt '{prompt_name}' não encontrado no banco de dados.")

    if format_kwargs:
        try:
            return prompt.format(**format_kwargs)
        except KeyError as e:
            logger.error(
                "prompt_format_variable_missing",
                prompt_name=prompt_name,
                error=str(e),
            )
            return prompt

    return prompt


def update_prompt(prompt_name: str, new_text: str, created_by: str = "meta-agent") -> bool:
    """
    Atualiza um prompt existente criando uma nova versão ativa.
    Usado pelo Meta-Agent para otimização dinâmica.
    """
    if not prompt_loader.use_database or not prompt_loader._prompt_repo:
        logger.warning(
            "prompt_update_database_disabled",
            prompt_name=prompt_name,
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

        logger.info(
            "prompt_updated",
            prompt_name=prompt_name,
            version=getattr(new_prompt, "version", None),
        )
        return True
    except Exception as e:
        logger.error(
            "prompt_update_failed",
            prompt_name=prompt_name,
            error=str(e),
        )
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
        logger.error("prompt_stats_failed", error=str(e))
        return {"error": str(e)}
