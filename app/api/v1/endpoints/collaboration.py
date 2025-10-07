"""
API endpoints para o Sistema de Colaboração Multi-Agente (Sprint 11).
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.agents import AgentRole, get_multi_agent_system
from app.core.agents.multi_agent_system import TaskStatus, TaskPriority, Task

router = APIRouter()
logger = logging.getLogger(__name__)


# --- Schemas ---

class CreateAgentRequest(BaseModel):
    """Request para criar um agente."""
    role: str = Field(...,
                      description="Papel do agente: project_manager, researcher, coder, tester, documenter, optimizer")


class CreateAgentResponse(BaseModel):
    """Response da criação de agente."""
    agent_id: str
    role: str
    message: str


class CreateTaskRequest(BaseModel):
    """Request para criar uma tarefa."""
    description: str = Field(..., description="Descrição da tarefa")
    assigned_to: Optional[str] = Field(None, description="ID do agente responsável")
    priority: str = Field(default="medium", description="Prioridade: low, medium, high, critical")
    dependencies: List[str] = Field(default_factory=list, description="IDs de tarefas dependentes")


class ExecuteTaskRequest(BaseModel):
    """Request para executar uma tarefa."""
    task_id: str = Field(..., description="ID da tarefa a executar")
    agent_id: str = Field(..., description="ID do agente executor")


class ExecuteProjectRequest(BaseModel):
    """Request para executar um projeto completo."""
    description: str = Field(..., description="Descrição do projeto")


class SendMessageRequest(BaseModel):
    """Request para enviar mensagem entre agentes."""
    from_agent: str = Field(..., description="ID do agente remetente")
    to_agent: str = Field(..., description="ID do agente destinatário")
    content: str = Field(..., description="Conteúdo da mensagem")


class AddArtifactRequest(BaseModel):
    """Request para adicionar artefato ao workspace."""
    key: str = Field(..., description="Chave do artefato")
    value: str = Field(..., description="Valor/conteúdo do artefato")
    author: str = Field(..., description="ID do agente autor")


# --- Endpoints ---

@router.post("/agents/create", response_model=CreateAgentResponse)
async def create_agent(request: CreateAgentRequest):
    """
    Cria um novo agente especializado no sistema.

    Papéis disponíveis:
    - project_manager: Coordenador geral
    - researcher: Pesquisa e análise
    - coder: Geração de código
    - tester: Testes e validação
    - documenter: Documentação
    - optimizer: Otimização e refatoração
    """
    try:
        # Validar papel
        try:
            role = AgentRole(request.role)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Papel inválido: {request.role}. Opções: project_manager, researcher, coder, tester, documenter, optimizer"
            )

        system = get_multi_agent_system()
        agent = system.create_agent(role)

        return CreateAgentResponse(
            agent_id=agent.agent_id,
            role=agent.role.value,
            message=f"Agente {role.value} criado com sucesso"
        )

    except Exception as e:
        logger.error(f"Erro ao criar agente: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents")
async def list_agents():
    """
    Lista todos os agentes ativos no sistema.

    Retorna informações sobre papel, ID e tarefas atribuídas.
    """
    try:
        system = get_multi_agent_system()
        agents = system.list_agents()

        return {
            "total_agents": len(agents),
            "agents": agents
        }

    except Exception as e:
        logger.error(f"Erro ao listar agentes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_id}")
async def get_agent_details(agent_id: str):
    """
    Obtém detalhes de um agente específico.
    """
    try:
        system = get_multi_agent_system()
        agent = system.get_agent(agent_id)

        if not agent:
            raise HTTPException(status_code=404, detail=f"Agente {agent_id} não encontrado")

        tasks = system.workspace.get_tasks_by_agent(agent_id)

        return {
            "agent_id": agent.agent_id,
            "role": agent.role.value,
            "total_tasks": len(tasks),
            "tasks_by_status": {
                "pending": len([t for t in tasks if t.status == TaskStatus.PENDING]),
                "in_progress": len([t for t in tasks if t.status == TaskStatus.IN_PROGRESS]),
                "completed": len([t for t in tasks if t.status == TaskStatus.COMPLETED]),
                "failed": len([t for t in tasks if t.status == TaskStatus.FAILED]),
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter detalhes do agente: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/create")
async def create_task(request: CreateTaskRequest):
    """
    Cria uma nova tarefa no workspace compartilhado.
    """
    try:
        # Validar prioridade
        try:
            priority = TaskPriority[request.priority.upper()]
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=f"Prioridade inválida: {request.priority}. Opções: low, medium, high, critical"
            )

        system = get_multi_agent_system()

        task = Task(
            description=request.description,
            assigned_to=request.assigned_to,
            priority=priority,
            dependencies=request.dependencies
        )

        system.workspace.add_task(task)

        return {
            "task_id": task.id,
            "description": task.description,
            "status": task.status.value,
            "priority": task.priority.value,
            "message": "Tarefa criada com sucesso"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao criar tarefa: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/execute")
async def execute_task(request: ExecuteTaskRequest):
    """
    Executa uma tarefa específica usando um agente.
    """
    try:
        system = get_multi_agent_system()

        # Validar agente
        agent = system.get_agent(request.agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agente {request.agent_id} não encontrado")

        # Validar tarefa
        task = system.workspace.get_task(request.task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Tarefa {request.task_id} não encontrada")

        # Executar tarefa
        result = await agent.execute_task(task)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao executar tarefa: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks")
async def list_tasks(status: Optional[str] = None):
    """
    Lista todas as tarefas do workspace.

    Query params:
    - status: Filtrar por status (pending, in_progress, completed, failed, blocked)
    """
    try:
        system = get_multi_agent_system()

        if status:
            try:
                task_status = TaskStatus(status)
                tasks = system.workspace.get_tasks_by_status(task_status)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Status inválido: {status}"
                )
        else:
            tasks = list(system.workspace.tasks.values())

        return {
            "total_tasks": len(tasks),
            "tasks": [task.to_dict() for task in tasks]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao listar tarefas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}")
async def get_task_details(task_id: str):
    """
    Obtém detalhes de uma tarefa específica.
    """
    try:
        system = get_multi_agent_system()
        task = system.workspace.get_task(task_id)

        if not task:
            raise HTTPException(status_code=404, detail=f"Tarefa {task_id} não encontrada")

        return task.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter detalhes da tarefa: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/execute")
async def execute_project(request: ExecuteProjectRequest):
    """
    Executa um projeto completo usando coordenação multi-agente.

    O Gestor de Projetos analisa o requisito, divide em tarefas,
    atribui aos agentes especializados e coordena a execução.
    """
    try:
        system = get_multi_agent_system()
        result = await system.execute_project(request.description)

        return result

    except Exception as e:
        logger.error(f"Erro ao executar projeto: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workspace/messages/send")
async def send_message(request: SendMessageRequest):
    """
    Envia uma mensagem entre agentes no workspace compartilhado.
    """
    try:
        system = get_multi_agent_system()

        # Validar agentes
        from_agent = system.get_agent(request.from_agent)
        to_agent = system.get_agent(request.to_agent)

        if not from_agent:
            raise HTTPException(status_code=404, detail=f"Agente remetente {request.from_agent} não encontrado")
        if not to_agent:
            raise HTTPException(status_code=404, detail=f"Agente destinatário {request.to_agent} não encontrado")

        system.workspace.send_message(request.from_agent, request.to_agent, request.content)

        return {
            "message": "Mensagem enviada com sucesso",
            "from": request.from_agent,
            "to": request.to_agent
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspace/messages/{agent_id}")
async def get_agent_messages(agent_id: str):
    """
    Recupera mensagens destinadas a um agente específico.
    """
    try:
        system = get_multi_agent_system()

        agent = system.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agente {agent_id} não encontrado")

        messages = agent.get_messages()

        return {
            "agent_id": agent_id,
            "total_messages": len(messages),
            "messages": messages
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao recuperar mensagens: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workspace/artifacts/add")
async def add_artifact(request: AddArtifactRequest):
    """
    Adiciona um artefato ao workspace compartilhado.

    Artefatos podem ser arquivos, dados, resultados intermediários, etc.
    """
    try:
        system = get_multi_agent_system()

        agent = system.get_agent(request.author)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agente {request.author} não encontrado")

        system.workspace.add_artifact(request.key, request.value, request.author)

        return {
            "message": "Artefato adicionado com sucesso",
            "key": request.key,
            "author": request.author
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao adicionar artefato: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspace/artifacts/{key}")
async def get_artifact(key: str):
    """
    Recupera um artefato do workspace.
    """
    try:
        system = get_multi_agent_system()
        artifact_data = system.workspace.artifacts.get(key)

        if not artifact_data:
            raise HTTPException(status_code=404, detail=f"Artefato '{key}' não encontrado")

        return {
            "key": key,
            "value": artifact_data["value"],
            "author": artifact_data["author"],
            "timestamp": artifact_data["timestamp"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao recuperar artefato: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspace/status")
async def get_workspace_status():
    """
    Retorna o status geral do workspace compartilhado.

    Inclui contadores de artefatos, mensagens e tarefas.
    """
    try:
        system = get_multi_agent_system()
        status = system.get_workspace_status()

        return status

    except Exception as e:
        logger.error(f"Erro ao obter status do workspace: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/system/shutdown")
async def shutdown_system():
    """
    Desliga todos os agentes do sistema.

    Use com cuidado! Isto remove todos os agentes ativos.
    """
    try:
        system = get_multi_agent_system()
        system.shutdown_all()

        return {
            "message": "Sistema multi-agente desligado com sucesso",
            "agents_shutdown": len(system.agents)
        }

    except Exception as e:
        logger.error(f"Erro ao desligar sistema: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """
    Health check do sistema de colaboração multi-agente.
    """
    try:
        system = get_multi_agent_system()

        return {
            "status": "healthy",
            "total_agents": len(system.agents),
            "project_manager_active": system.project_manager is not None,
            "workspace_status": system.get_workspace_status()
        }

    except Exception as e:
        logger.error(f"Erro no health check: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
