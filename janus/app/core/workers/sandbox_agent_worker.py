"""
Sandbox Agent Worker

Consome a fila JANUS.tasks.agent.sandbox e orquestra a execução de código
em um contentor Docker extremamente restrito ("jaula"), capturando stdout/stderr
sem rede, sem volumes e com limites de CPU/memória.
"""

import base64
import logging
from datetime import datetime

from app.core.infrastructure.message_broker import get_broker
from app.core.monitoring.poison_pill_handler import protect_against_poison_pills
from app.models.schemas import QueueName, TaskMessage, TaskState
from app.repositories.collaboration_repository import CollaborationRepository
from app.services.collaboration_service import CollaborationService

logger = logging.getLogger(__name__)


def _build_command_for_code(code: str) -> list:
    """Monta comando `python -c` que decodifica o código via base64 e executa.
    Evita problemas de quoting/escape e mantém a jaula sem volumes/FS.
    """
    encoded = base64.b64encode(code.encode("utf-8")).decode("ascii")
    py = (
        "import base64,sys;"
        "code = base64.b64decode('" + encoded + "').decode('utf-8');"
        "globals_dict={'__name__':'__main__'};"
        "exec(code, globals_dict)"
    )
    return ["python", "-c", py]


def _run_in_docker(code: str) -> tuple[str, str]:
    """Executa o código em um contentor Docker altamente restrito.
    Retorna (stdout, stderr). Em caso de falha estrutural, stderr conterá a causa.
    """
    try:
        from docker.errors import APIError, ContainerError, ImageNotFound

        import docker

        client = docker.from_env()
        image = "python:3.11-slim"
        cmd = _build_command_for_code(code)

        try:
            # Tenta executar diretamente; se a imagem não existir, fará pull.
            logs = client.containers.run(
                image=image,
                command=cmd,
                remove=True,  # auto_remove=True
                network_mode="none",  # sem rede (jaula estéril)
                mem_limit="256m",  # limite de memória
                nano_cpus=1_000_000_000,  # ~1 CPU
                stderr=True,
                stdout=True,
                detach=False,
            )
            # Sucesso: logs combinados são stdout
            stdout = (
                logs.decode("utf-8", errors="replace")
                if isinstance(logs, (bytes, bytearray))
                else str(logs)
            )
            return stdout, ""
        except ImageNotFound:
            client.images.pull(image)
            logs = client.containers.run(
                image=image,
                command=cmd,
                remove=True,
                network_mode="none",
                mem_limit="256m",
                nano_cpus=1_000_000_000,
                stderr=True,
                stdout=True,
                detach=False,
            )
            stdout = (
                logs.decode("utf-8", errors="replace")
                if isinstance(logs, (bytes, bytearray))
                else str(logs)
            )
            return stdout, ""
        except ContainerError as e:
            # Erro de execução dentro do container: tratar como stderr
            err = None
            try:
                err = (
                    e.stderr.decode("utf-8", errors="replace")
                    if getattr(e, "stderr", None)
                    else str(e)
                )
            except Exception:
                err = str(e)
            return "", err
        except APIError as e:
            return "", f"Docker API error: {e.explanation if hasattr(e, 'explanation') else str(e)}"
        except Exception as e:
            return "", f"Docker run error: {e!s}"
    except Exception as e:
        # docker SDK ausente ou ambiente sem permissão/acesso ao daemon
        return "", f"Sandbox unavailable: {e!s}"


@protect_against_poison_pills(
    queue_name=QueueName.TASKS_AGENT_SANDBOX.value,
    extract_message_id=lambda task: task.task_id,
)
async def process_sandbox_task(task: TaskMessage) -> None:
    try:
        raw_state = (task.payload or {}).get("task_state", {})
        state = TaskState(**raw_state)
        state.current_agent_role = "sandbox"

        code = state.data_payload.script_code
        if not code or not code.strip():
            state.data_payload.sandbox_output = ""
            state.data_payload.sandbox_error = "No code provided to sandbox."
            state.history.append(
                {
                    "agent_role": "sandbox",
                    "action": "sandbox_skipped",
                    "notes": "empty_code",
                    "timestamp": datetime.utcnow().timestamp(),
                }
            )
            state.next_agent_role = "coder"
            service = CollaborationService(CollaborationRepository())
            await service.pass_task(state)
            return

        stdout, stderr = _run_in_docker(code)
        state.data_payload.sandbox_output = stdout
        state.data_payload.sandbox_error = stderr
        state.history.append(
            {
                "agent_role": "sandbox",
                "action": "code_executed",
                "notes": f"ok={'no' if bool(stderr) else 'yes'}",
                "timestamp": datetime.utcnow().timestamp(),
            }
        )

        # Decisão: dor -> volta para coder; sucesso -> router
        if stderr:
            state.next_agent_role = "coder"
        else:
            state.next_agent_role = "router"

        service = CollaborationService(CollaborationRepository())
        await service.pass_task(state)
        logger.info(
            "SandboxAgent executou e encaminhou",
            extra={"task_id": state.task_id, "next": state.next_agent_role},
        )
    except Exception as e:
        logger.error(f"SandboxAgent falhou: {e}", exc_info=True)
        raise


async def start_sandbox_agent_worker():
    logger.info("Iniciando Sandbox Agent Worker...")
    broker = await get_broker()
    consumer_task = broker.start_consumer(
        queue_name=QueueName.TASKS_AGENT_SANDBOX.value,
        callback=process_sandbox_task,
        prefetch_count=3,
    )
    logger.info("✓ Sandbox Agent Worker iniciado.")
    return consumer_task
