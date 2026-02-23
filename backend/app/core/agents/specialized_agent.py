import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any

from langchain_core.prompts import PromptTemplate

from app.core.llm.router import get_llm
from app.core.llm.types import ModelPriority, ModelRole
from app.core.tools import get_all_tools
from app.core.tools.action_module import PermissionLevel, action_registry
from app.repositories.agent_config_repository import AgentConfigRepository

from app.core.agents.structures import AgentRole, Task, TaskStatus
from app.core.agents.workspace import SharedWorkspace
from app.core.agents.metrics import (
    AGENT_TASKS_COUNTER,
    AGENT_TASK_DURATION,
    ACTIVE_AGENTS_GAUGE,
)
from app.core.agents.utils import (
    _create_tool_wrapper,
    _clean_json_output,
    AgentEventCallbackHandler,
)
from app.core.infrastructure.prompt_fallback import get_prompt_with_fallback

logger = logging.getLogger(__name__)


class SpecializedAgentError(Exception):
    """Erro genérico para o agente especializado."""

    pass


class SpecializedAgent:
    """Agente especializado com papel específico."""

    def __init__(self, role: AgentRole, workspace: SharedWorkspace, agent_id: str | None = None):
        self.role = role
        self.agent_id = agent_id or f"{role.value}_{uuid.uuid4().hex[:8]}"
        self.workspace = workspace
        self.executor: Any | None = None
        self.config_repo = AgentConfigRepository()
        self.event_callback = None

        # self._initialize_agent() chamada lazily no execute_task
        ACTIVE_AGENTS_GAUGE.inc()
        logger.info(f"Agente '{self.agent_id}' ({role.value}) instanciado")

    def set_event_callback(self, callback):
        """Define callback assíncrono para eventos de progresso."""
        self.event_callback = callback

    async def _get_prompt_for_role(self, config) -> str:
        """Obtém o prompt para o papel do agente (do banco ou fallback)."""
        # config pode ser None ou um objeto AgentConfiguration
        if config and hasattr(config, "prompt_template") and config.prompt_template:
            return config.prompt_template

        prompt_name = f"agent_{self.role.value}"
        try:
            prompt_text = await get_prompt_with_fallback(prompt_name)
            if prompt_text:
                return prompt_text
        except Exception as e:
            logger.error(f"Erro ao buscar prompt para {self.role.value}: {e}")

        raise ValueError(f"Prompt não encontrado para {prompt_name}")

    def _get_llm_config_for_role(self, config):
        """Obtém configuração do LLM para o papel do agente (do banco ou fallback)."""
        if config and config.llm_config:
            llm_role_str = config.llm_config.get("role", "ORCHESTRATOR")
            llm_priority_str = config.llm_config.get("priority", "HIGH_QUALITY")

            # Converter strings para enums
            try:
                llm_role = ModelRole[llm_role_str]
                llm_priority = ModelPriority[llm_priority_str]
                return llm_role, llm_priority
            except KeyError as e:
                logger.warning(f"Configuração LLM inválida no banco: {e}. Usando fallback.")

        # Fallback para mapeamento padrão
        llm_mapping = {
            AgentRole.PROJECT_MANAGER: (ModelRole.ORCHESTRATOR, ModelPriority.HIGH_QUALITY),
            AgentRole.CODER: (ModelRole.CODE_GENERATOR, ModelPriority.HIGH_QUALITY),
            AgentRole.RESEARCHER: (ModelRole.ORCHESTRATOR, ModelPriority.FAST_AND_CHEAP),
            AgentRole.TESTER: (ModelRole.CODE_GENERATOR, ModelPriority.FAST_AND_CHEAP),
            AgentRole.DOCUMENTER: (ModelRole.KNOWLEDGE_CURATOR, ModelPriority.FAST_AND_CHEAP),
            AgentRole.OPTIMIZER: (ModelRole.CODE_GENERATOR, ModelPriority.HIGH_QUALITY),
            AgentRole.SYSADMIN: (ModelRole.CODE_GENERATOR, ModelPriority.HIGH_QUALITY),
        }

        return llm_mapping.get(self.role, (ModelRole.ORCHESTRATOR, ModelPriority.LOCAL_ONLY))

    async def _initialize_agent(self):
        """Inicializa o executor do agente com prompt especializado."""
        # Tentar carregar configuração do banco de dados
        config = None
        try:
            # FIX: Await necessário pois o repositório agora é async
            config = await self.config_repo.get_active_config(
                agent_name=self.agent_id, agent_role=self.role.value
            )
            if config:
                logger.info(
                    f"Configuração dinâmica carregada para {self.role.value} ({self.agent_id})"
                )
        except Exception as e:
            logger.warning(f"Falha ao carregar configuração dinâmica para {self.role.value}: {e}")

        # Carregar prompt (do banco ou fallback)
        prompt_text = await self._get_prompt_for_role(config)
        prompt = PromptTemplate.from_template(prompt_text)

        # Selecionar LLM (do banco ou fallback)
        llm_role, llm_priority = self._get_llm_config_for_role(config)
        llm = await get_llm(role=llm_role, priority=llm_priority)

        # Selecionar ferramentas baseado no papel
        tools = self._get_tools_for_role()
        wrapped_tools = [_create_tool_wrapper(tool) for tool in tools]

        # Tenta importar create_react_agent (novo) ou cria fallback
        try:
            from langchain.agents import AgentExecutor, create_react_agent

            agent = create_react_agent(llm, wrapped_tools, prompt)
            agent_executor = AgentExecutor(
                agent=agent,
                tools=wrapped_tools,
                verbose=True,
                handle_parsing_errors=True,
                max_iterations=15,
                max_execution_time=180,
            )
            self.executor = agent_executor
        except ImportError:
            # Fallback para versões antigas ou diferentes
            from langchain.agents import AgentType, initialize_agent

            agent = initialize_agent(
                wrapped_tools,
                llm,
                agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
                verbose=True,
                # max_execution_time não suportado em initialize_agent diretamente as vezes
            )
            self.executor = agent

        logger.info(f"Agente '{self.agent_id}' inicializado com sucesso.")

    async def execute_task(self, task: Task, max_retries: int = 2) -> dict[str, Any]:
        """
        Executa uma tarefa atribuída ao agente com retry automático.

        Args:
            task: Tarefa a ser executada
            max_retries: Número máximo de tentativas (padrão: 2)

        Returns:
            Dicionário com resultado da execução
        """
        if not self.executor:
            await self._initialize_agent()

        if task.status != TaskStatus.PENDING:
            raise ValueError(f"Tarefa {task.id} não está em estado PENDING")

        task.status = TaskStatus.IN_PROGRESS
        task.started_at = datetime.now()
        task.assigned_to = self.agent_id

        logger.info(f"Agente {self.agent_id} iniciando tarefa: {task.description}")

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    logger.warning(
                        f"Tentativa {attempt + 1}/{max_retries + 1} para tarefa {task.id}"
                    )
                    await asyncio.sleep(2**attempt)  # Backoff exponencial

                # Prepare callbacks
                run_callbacks = []
                if self.event_callback:
                    run_callbacks.append(AgentEventCallbackHandler(self.event_callback))

                # Executar a tarefa
                start_time = asyncio.get_event_loop().time()

                # Langchain invoke suporta callbacks em config
                if hasattr(self.executor, "ainvoke"):
                    result = await self.executor.ainvoke(
                        {"input": task.description}, {"callbacks": run_callbacks}
                    )
                else:
                    # Fallback for older langchain versions or different executor types
                    result = await asyncio.to_thread(
                        self.executor.invoke,
                        {"input": task.description},
                        {"callbacks": run_callbacks},
                    )
                duration = asyncio.get_event_loop().time() - start_time

                # Limpar output (remover markdown se presente)
                output = result.get("output", "")
                cleaned_output = _clean_json_output(output)

                # Validar que o resultado não está vazio
                if not cleaned_output or cleaned_output.strip() == "":
                    raise ValueError("Agente retornou output vazio")

                # Atualizar task
                task.status = TaskStatus.COMPLETED
                task.result = cleaned_output
                task.completed_at = datetime.now()

                # Métricas
                AGENT_TASKS_COUNTER.labels(agent_role=self.role.value, status="completed").inc()
                AGENT_TASK_DURATION.labels(agent_role=self.role.value).observe(duration)

                logger.info(f"Tarefa {task.id} concluída com sucesso (tentativa {attempt + 1})")

                return {
                    "task_id": task.id,
                    "status": "completed",
                    "result": task.result,
                    "duration_seconds": duration,
                    "attempts": attempt + 1,
                }

            except TimeoutError as e:
                last_error = f"Timeout ao executar tarefa: {e}"
                logger.warning(f"Timeout na tentativa {attempt + 1} para tarefa {task.id}")
                if attempt == max_retries:
                    break
                continue

            except ValueError as e:
                # Erros de validação (parsing, output vazio, etc)
                last_error = f"Erro de validação: {e}"
                logger.warning(
                    f"Erro de validação na tentativa {attempt + 1} para tarefa {task.id}: {e}"
                )
                if attempt == max_retries:
                    break
                continue

            except Exception as e:
                last_error = str(e)
                logger.error(
                    f"Erro na tentativa {attempt + 1} para tarefa {task.id}: {e}", exc_info=True
                )
                if attempt == max_retries:
                    break
                continue

        # Se chegou aqui, todas as tentativas falharam
        logger.error(f"Tarefa {task.id} falhou após {max_retries + 1} tentativas: {last_error}")
        task.status = TaskStatus.FAILED
        task.error = last_error
        task.completed_at = datetime.now()
        AGENT_TASKS_COUNTER.labels(agent_role=self.role.value, status="failed").inc()

        return {
            "task_id": task.id,
            "status": "failed",
            "error": last_error,
            "attempts": max_retries + 1,
        }

    def communicate(self, to_agent_id: str, message: str):
        """Envia uma mensagem para outro agente."""
        self.workspace.send_message(self.agent_id, to_agent_id, message)

    def get_messages(self) -> list[dict[str, Any]]:
        """Recupera mensagens destinadas a este agente."""
        return self.workspace.get_messages_for(self.agent_id)

    def _get_tools_for_role(self):
        """Filtra ferramentas baseadas no papel do agente."""
        if self.role == AgentRole.SYSADMIN:
            # SysAdmin tem acesso a tudo, incluindo ferramentas perigosas
            return get_all_tools()

        # Outros agentes recebem apenas ferramentas seguras/padrao
        # Filtra ferramentas DANGEROUS
        all_tools = get_all_tools()
        safe_tools = []
        for tool in all_tools:
            meta = action_registry.get_metadata(tool.name)
            if meta and meta.permission_level == PermissionLevel.DANGEROUS:
                continue
            safe_tools.append(tool)
        return safe_tools

    async def update_config(self, config):
        """Atualiza a configuração do agente dinamicamente."""
        try:
            logger.info(f"Atualizando configuração do agente {self.agent_id}")
            # FIX: método correto é _initialize_agent (que é async)
            await self._initialize_agent()
            logger.info(f"Configuração do agente {self.agent_id} atualizada com sucesso")
        except Exception as e:
            logger.error(f"Erro ao atualizar configuração do agente {self.agent_id}: {e}")
            raise SpecializedAgentError(f"Falha na atualização de config: {e}") from e

    def shutdown(self):
        """Desliga o agente."""
        ACTIVE_AGENTS_GAUGE.dec()
        logger.info(f"Agente {self.agent_id} desligado")
