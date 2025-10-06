import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, Optional, Any, List

from prometheus_client import Counter, Histogram

from app.config import settings
from app.core.llm_manager import get_llm_client, ModelRole
from app.core.memory_core import memory_core
from app.models.schemas import Experience

logger = logging.getLogger(__name__)


class Step(Enum):
    PLAN = "plan"
    CRITIQUE = "critique"
    SOLVE = "solve"
    VERIFY = "verify"


# Metrics
_REASONING_EVENTS = Counter(
    "reasoning_events_total",
    "Eventos do núcleo de raciocínio por etapa",
    ["step", "outcome"],
)
_REASONING_LAT = Histogram(
    "reasoning_latency_seconds",
    "Latência por etapa do núcleo de raciocínio",
    ["step", "outcome"],
)
_REASONING_TOKENS = Counter(
    "reasoning_tokens_total",
    "Contagem aproximada de tokens por direção e etapa",
    ["direction", "step"],  # direction: in|out
)


@dataclass
class ReasoningLimits:
    max_iterations: int
    max_seconds: int
    max_tokens: int  # estimativa aproximada

    @staticmethod
    def from_settings() -> "ReasoningLimits":
        return ReasoningLimits(
            max_iterations=getattr(settings, "REASONING_MAX_ITERATIONS", 3),
            max_seconds=getattr(settings, "REASONING_MAX_SECONDS", 60),
            max_tokens=getattr(settings, "REASONING_MAX_TOKENS", 8000),
        )


def _approx_tokens(text: str) -> int:
    try:
        return max(1, len(text) // 4)
    except Exception:
        return max(1, len(str(text)))


class ReasoningSession:
    """Executa um fluxo explícito de raciocínio: plan -> critique -> solve -> verify.

    - Limites de iteração/tempo/tokens
    - Telemetria por etapa
    - Memorização das etapas (memória episódica)
    - Verificador automático pluggable (callable)
    """

    def __init__(self, question: str, verifier: Optional[Callable[[str, Dict[str, Any]], Dict[str, Any]]] = None,
                 limits: Optional[ReasoningLimits] = None,
                 role: ModelRole = ModelRole.ORCHESTRATOR):
        self.question = question.strip()
        self.verifier = verifier
        self.limits = limits or ReasoningLimits.from_settings()
        self.role = role
        self._llm = get_llm_client(role=self.role)
        self._start_time = time.perf_counter()
        self._tokens_used = 0
        self.steps: List[Dict[str, Any]] = []

    def _time_left(self) -> float:
        return max(0.0, self.limits.max_seconds - (time.perf_counter() - self._start_time))

    def _record_step(self, step: Step, prompt: str, output: str, ok: bool,
                     extra: Optional[Dict[str, Any]] = None) -> None:
        try:
            self.steps.append({
                "step": step.value,
                "prompt": prompt,
                "output": output,
                "ok": ok,
                "extra": extra or {},
            })
            # Memória do raciocínio (curto prazo)
            memory_core.memorize(Experience(
                type=f"reasoning_{step.value}",
                content=f"Q: {self.question}\n[{step.value.upper()}]\n{output}",
                metadata={"origin": "reasoning_core"}
            ))
        except Exception:
            # Evita falhar por causa da memória
            pass

    def _run_llm(self, step: Step, prompt: str) -> str:
        t0 = time.perf_counter()
        try:
            _REASONING_TOKENS.labels("in", step.value).inc(_approx_tokens(prompt))
            out = self._llm.send(prompt, timeout_s=min(30, int(self._time_left()) or 5))
            _REASONING_TOKENS.labels("out", step.value).inc(_approx_tokens(out))
            self._tokens_used += _approx_tokens(prompt) + _approx_tokens(out)
            _REASONING_EVENTS.labels(step.value, "success").inc()
            _REASONING_LAT.labels(step.value, "success").observe(time.perf_counter() - t0)
            return out
        except Exception as e:
            _REASONING_EVENTS.labels(step.value, "error").inc()
            _REASONING_LAT.labels(step.value, "error").observe(time.perf_counter() - t0)
            logger.error({"event": "reasoning_step_error", "step": step.value, "error": str(e)}, exc_info=True)
            raise

    def _check_limits(self) -> None:
        if self._time_left() <= 0:
            raise TimeoutError("Limite de tempo do raciocínio atingido")
        if self._tokens_used >= self.limits.max_tokens:
            raise RuntimeError("Limite de tokens do raciocínio atingido")

    def run(self) -> Dict[str, Any]:
        iteration = 0
        final_answer = ""
        verify_report: Dict[str, Any] = {}

        while iteration < self.limits.max_iterations:
            iteration += 1
            self._check_limits()

            # PLAN
            plan_prompt = (
                    "Você é um engenheiro de software meticuloso. Crie um plano objetivo, com 3-6 passos, para resolver: "
                    f"\n" + self.question + "\nRegras: seja específico, cite verificações e critérios de sucesso ao final."
            )
            plan = self._run_llm(Step.PLAN, plan_prompt)
            self._record_step(Step.PLAN, plan_prompt, plan, ok=True)
            self._check_limits()

            # CRITIQUE
            critique_prompt = (
                    "Analise criticamente o plano abaixo, procurando riscos, ambiguidade e passos faltantes. "
                    "Sugira correções e melhore os critérios de sucesso.\n---\nPlano:\n" + plan
            )
            critique = self._run_llm(Step.CRITIQUE, critique_prompt)
            self._record_step(Step.CRITIQUE, critique_prompt, critique, ok=True)
            self._check_limits()

            # SOLVE
            solve_prompt = (
                    "Execute o plano revisado de forma objetiva. Forneça a solução final no final sob o marcador 'FINAL'. "
                    "Inclua, se aplicável, snippets de código formatados e explicações sucintas.\n---\nPlano revisado:\n" + critique
            )
            solution = self._run_llm(Step.SOLVE, solve_prompt)
            self._record_step(Step.SOLVE, solve_prompt, solution, ok=True)
            self._check_limits()

            # VERIFY
            verify_prompt = (
                    "Verifique automaticamente a solução a seguir.\n"
                    "- Valide consistência com os critérios do plano.\n"
                    "- Se JSON, valide sintaxe. Se Python, valide sintaxe AST.\n"
                    "- Liste evidências/checagens realizadas.\n"
                    "- Responda com um veredito: PASS ou FAIL, e correções se necessárias.\n---\nSolução:\n" + solution
            )
            verify_text = self._run_llm(Step.VERIFY, verify_prompt)
            verify_report = self._run_verify_hooks(solution, plan=plan, critique=critique, llm_verification=verify_text)
            ok = bool(verify_report.get("pass", False))
            self._record_step(Step.VERIFY, verify_prompt, verify_text, ok=ok, extra=verify_report)

            # Tentativa de extrair resposta final
            final_answer = self._extract_final_answer(solution) or solution

            if ok:
                break

        return {
            "ok": bool(verify_report.get("pass", False)),
            "answer": final_answer,
            "verification": verify_report,
            "steps": self.steps,
            "tokens_used": self._tokens_used,
            "elapsed_s": round(time.perf_counter() - self._start_time, 3),
            "iterations": iteration,
        }

    @staticmethod
    def _extract_final_answer(text: str) -> str:
        marker = "FINAL"
        try:
            if marker in text:
                part = text.split(marker, 1)[1]
                return part.strip("\n :#\t")
        except Exception:
            pass
        return text.strip()

    def _run_verify_hooks(self, solution: str, **ctx) -> Dict[str, Any]:
        report: Dict[str, Any] = {"pass": False, "checks": []}
        # 1) Sintaxe JSON
        try:
            import json
            if solution.strip().startswith("{") or solution.strip().startswith("["):
                json.loads(solution)
                report["checks"].append("json_syntax_ok")
        except Exception as e:
            report["checks"].append(f"json_syntax_fail:{e}")
        # 2) Sintaxe Python
        try:
            if "```" in solution and "python" in solution.lower():
                code = self._extract_code_block(solution)
                import ast as _ast
                _ast.parse(code)
                report["checks"].append("python_ast_ok")
        except Exception as e:
            report["checks"].append(f"python_ast_fail:{e}")
        # 3) Verificador customizado
        if self.verifier:
            try:
                custom = self.verifier(solution, ctx)
                if isinstance(custom, dict):
                    report.update({k: v for k, v in custom.items() if k not in ("checks",)})
                    if "checks" in custom and isinstance(custom["checks"], list):
                        report["checks"].extend(custom["checks"])
            except Exception as e:
                report["checks"].append(f"custom_verifier_error:{e}")
        # PASS se não houver falhas nos checks sintáticos básicos e sem indicadores de FAIL no texto do veredito LLM
        llm_verdict = (ctx.get("llm_verification") or "").lower()
        syntactic_ok = all(
            not str(c).startswith(("json_syntax_fail", "python_ast_fail", "custom_verifier_error")) for c in
            report["checks"])  # noqa: E501
        llm_ok = ("pass" in llm_verdict) and ("fail" not in llm_verdict)
        report["pass"] = bool(syntactic_ok and llm_ok) or report.get("pass", False)
        return report

    @staticmethod
    def _extract_code_block(text: str) -> str:
        """Extrai o primeiro bloco de código markdown encontrado."""
        try:
            import re
            m = re.search(r"```[a-zA-Z0-9_+-]*\n(.*?)\n```", text, flags=re.DOTALL)
            if m:
                return m.group(1)
        except Exception:
            pass
        return text


def solve_question(question: str, verifier: Optional[Callable[[str, Dict[str, Any]], Dict[str, Any]]] = None,
                   limits: Optional[ReasoningLimits] = None) -> Dict[str, Any]:
    """API simples: executa um fluxo de raciocínio completo e retorna resposta + telemetria."""
    session = ReasoningSession(question=question, verifier=verifier, limits=limits)
    return session.run()
