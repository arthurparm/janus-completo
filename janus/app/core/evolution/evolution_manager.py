import ast
import json
import logging
from typing import Any

from app.core.evolution.prompts import TOOL_GENERATION_PROMPT, TOOL_SPECIFICATION_PROMPT
from app.core.llm import ModelPriority, ModelRole
from app.services.llm_service import LLMService
from app.services.tool_service import ToolService

logger = logging.getLogger(__name__)


class EvolutionManager:
    """
    Gerencia o ciclo de auto-evolução do Janus.
    Responsável por coordenar a especificação, criação, validação e registro de novas ferramentas.
    """

    BACKLOG_FILE = "data/evolution_backlog.json"

    def __init__(self, llm_service: LLMService, tool_service: ToolService):
        self.llm_service = llm_service
        self.tool_service = tool_service
        self._ensure_backlog_exists()

    def result_callback(self, result: dict[str, Any]):
        """Callback placeholder for future implementation."""
        pass

    def queue_request(self, capability_request: str) -> str:
        """
        Adiciona uma solicitação à fila de evolução para processamento posterior (quando ocioso).
        Returns:
            ID da solicitação.
        """
        import time
        import uuid

        req_id = str(uuid.uuid4())
        item = {
            "id": req_id,
            "request": capability_request,
            "status": "pending",
            "created_at": time.time(),
        }

        backlog = self._load_backlog()
        backlog.append(item)
        self._save_backlog(backlog)

        logger.info(f"[Evolution] Solicitação agendada: {capability_request} (ID: {req_id})")
        return req_id

    async def process_next_pending(self) -> dict[str, Any] | None:
        """
        Processa o próximo item pendente da fila, se houver.
        Deve ser chamado quando o sistema estiver ocioso.
        """
        backlog = self._load_backlog()
        pending = [i for i in backlog if i["status"] == "pending"]

        if not pending:
            return None

        # FIFO strategy
        item = pending[0]
        item_id = item["id"]
        request = item["request"]

        logger.info(f"[Evolution] Processando item pendente: {request} (ID: {item_id})")

        try:
            # Mark as processing
            self._update_status(item_id, "processing", backlog)

            result = await self.evolve_tool(request)

            # Mark as completed
            self._update_status(item_id, "completed", backlog, result=result)
            return result

        except Exception as e:
            logger.error(f"[Evolution] Erro ao processar item {item_id}: {e}")
            self._update_status(item_id, "failed", backlog, error=str(e))
            raise

    def get_backlog_status(self) -> dict[str, int]:
        """Retorna contagem de itens por status."""
        backlog = self._load_backlog()
        stats = {"pending": 0, "processing": 0, "completed": 0, "failed": 0}
        for item in backlog:
            s = item.get("status", "unknown")
            stats[s] = stats.get(s, 0) + 1
        return stats

    def _ensure_backlog_exists(self):
        import os

        if not os.path.exists(self.BACKLOG_FILE):
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.BACKLOG_FILE), exist_ok=True)
            with open(self.BACKLOG_FILE, "w") as f:
                json.dump([], f)

    def _load_backlog(self) -> list:
        try:
            with open(self.BACKLOG_FILE) as f:
                return json.load(f)
        except Exception:
            return []

    def _save_backlog(self, data: list):
        try:
            with open(self.BACKLOG_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"[Evolution] Falha ao salvar backlog: {e}")

    def _update_status(
        self, item_id: str, status: str, backlog: list, result: Any = None, error: str = None
    ):
        for item in backlog:
            if item["id"] == item_id:
                item["status"] = status
                if result:
                    item["result"] = str(result)  # Simplify storage
                if error:
                    item["error"] = error
                break
        self._save_backlog(backlog)

    async def evolve_tool(self, capability_request: str) -> dict[str, Any]:
        """
        Inicia o processo de criação de uma nova ferramenta baseada em uma necessidade.

        Args:
            capability_request: Descrição da capacidade ausente (ex: "Listar filas do RabbitMQ")

        Returns:
            Metadata da ferramenta criada ou erro.
        """
        logger.info(f"[Evolution] Iniciando evolução para: {capability_request}")

        try:
            # 1. Especificação
            spec = await self._specify_tool(capability_request)
            if not spec:
                raise ValueError("Falha na especificação da ferramenta.")

            logger.info(f"[Evolution] Especificação gerada: {spec.get('tool_name')}")

            # 2. Geração de Código
            code = await self._generate_code(spec)
            if not code:
                raise ValueError("Falha na geração de código.")

            # 3. Validação Estática (Safety Check)
            if not self._validate_safety(code):
                raise ValueError("Código gerado violou verificações de segurança.")

            # 4. Registro
            tool_meta = self._register_tool(spec, code)

            logger.info(f"[Evolution] Ferramenta '{tool_meta.name}' registrada com sucesso.")
            from dataclasses import asdict

            return asdict(tool_meta)

        except Exception as e:
            logger.error(f"[Evolution] Falha no processo de evolução: {e}", exc_info=True)
            raise

    async def _specify_tool(self, request: str) -> dict[str, Any] | None:
        """Usa LLM para criar a especificação técnica da ferramenta."""
        import asyncio

        prompt = TOOL_SPECIFICATION_PROMPT.format(request=request)

        # Executar síncrono em thread pool
        response = await asyncio.to_thread(
            self.llm_service.invoke_llm,
            prompt=prompt,
            role=ModelRole.ORCHESTRATOR,
            priority=ModelPriority.HIGH_QUALITY,
            timeout_seconds=60,
        )

        text = response.get("response", "")
        # Tentar extrair JSON
        try:
            # Limpeza básica de markdown code blocks
            text = text.replace("```json", "").replace("```", "").strip()
            # Se houver texto antes ou depois do JSON, tentar achar { ... }
            if "{" in text and "}" in text:
                start = text.find("{")
                end = text.rfind("}") + 1
                text = text[start:end]

            spec = json.loads(text)
            return spec
        except json.JSONDecodeError:
            logger.error(f"[Evolution] Falha ao decodificar JSON da especificação: {text}")
            return None

    async def _generate_code(self, spec: dict[str, Any]) -> str | None:
        """Usa LLM para gerar o código Python."""
        import asyncio

        spec_str = json.dumps(spec, indent=2)
        prompt = TOOL_GENERATION_PROMPT.format(specification=spec_str)

        response = await asyncio.to_thread(
            self.llm_service.invoke_llm,
            prompt=prompt,
            role=ModelRole.CODE_GENERATOR,
            priority=ModelPriority.HIGH_QUALITY,
            timeout_seconds=120,
        )

        code = response.get("response", "")
        # Limpeza de markdown
        cleaned_code = code.replace("```python", "").replace("```", "").strip()
        return cleaned_code

    def _validate_safety(self, code: str) -> bool:
        """
        Verificação de segurança estática (AST).
        Impede imports perigosos óbvios.
        """
        forbidden_imports = {"subprocess", "os.system", "os.popen", "shutil.rmtree"}
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in forbidden_imports:
                            logger.warning(f"[Evolution] Import proibido detectado: {alias.name}")
                            return False
                elif isinstance(node, ast.ImportFrom):
                    if node.module in forbidden_imports:
                        logger.warning(f"[Evolution] ImportFrom proibido detectado: {node.module}")
                        return False
                    # Check os.system usage specifically usually complicated via AST without deep analysis
                    # This is a basic filter.
            return True
        except SyntaxError:
            logger.error("[Evolution] Erro de sintaxe no código gerado.")
            return False

    def _register_tool(self, spec: dict[str, Any], code: str):
        """Registra a ferramenta no ToolService."""
        request_data = {
            "name": spec.get("tool_name"),
            "description": spec.get("description"),
            "code": code,
            "function_name": spec.get("tool_name"),  # Assumindo que a função tem o mesmo nome
            "category": "dynamic",  # Nova categoria para ferramentas evoluídas
            "permission_level": spec.get("safety_level", "safe"),
            "tags": ["evolved", "auto-generated"],
        }

        return self.tool_service.create_tool_from_function(request_data)
