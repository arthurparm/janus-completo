import time
from dataclasses import dataclass, field

import structlog

from app.core.tools.action_module import PermissionLevel, ToolMetadata, action_registry

logger = structlog.get_logger(__name__)


class RiskProfile(str):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


@dataclass
class PolicyConfig:
    risk_profile: str = RiskProfile.BALANCED
    auto_confirm: bool = True
    allowlist: set[str] = field(default_factory=set)
    blocklist: set[str] = field(default_factory=set)
    max_actions_per_cycle: int = 20
    max_seconds_per_cycle: int = 60


@dataclass
class PolicyDecision:
    allowed: bool
    require_confirmation: bool = False
    reason: str | None = None


class PolicyEngine:
    """Validações mínimas antes de executar ferramentas.

    - Verifica nível de permissão vs. perfil de risco
    - Aplica listas de bloqueio/permitidos
    - Respeita rate limits do ActionRegistry
    - Exige confirmação quando aplicável
    """

    def __init__(self, config: PolicyConfig | None = None):
        self.config = config or PolicyConfig()
        self._cycle_started_at: float = time.time()
        self._actions_in_cycle: int = 0

    def reset_cycle_quota(self):
        self._cycle_started_at = time.time()
        self._actions_in_cycle = 0

    def can_continue_cycle(self) -> bool:
        elapsed = time.time() - self._cycle_started_at
        if self.config.max_seconds_per_cycle and elapsed > self.config.max_seconds_per_cycle:
            return False
        if (
            self.config.max_actions_per_cycle
            and self._actions_in_cycle >= self.config.max_actions_per_cycle
        ):
            return False
        return True

    def _check_permission_vs_risk(self, meta: ToolMetadata) -> PolicyDecision:
        rp = (self.config.risk_profile or RiskProfile.BALANCED).lower()
        pl = meta.permission_level

        # Conservative: somente READ_ONLY e SAFE; WRITE requer confirmação; DANGEROUS bloqueado
        if rp == RiskProfile.CONSERVATIVE:
            if pl in [PermissionLevel.READ_ONLY, PermissionLevel.SAFE]:
                return PolicyDecision(allowed=True)
            if pl == PermissionLevel.WRITE:
                return PolicyDecision(
                    allowed=self.config.auto_confirm,
                    require_confirmation=not self.config.auto_confirm,
                    reason="WRITE requer confirmação em modo conservador",
                )
            return PolicyDecision(
                allowed=False, reason="Ferramenta perigosa bloqueada em modo conservador"
            )

        # Balanced: SAFE e WRITE permitidos; DANGEROUS somente se na allowlist
        if rp == RiskProfile.BALANCED:
            if pl in [PermissionLevel.READ_ONLY, PermissionLevel.SAFE, PermissionLevel.WRITE]:
                return PolicyDecision(allowed=True)
            # DANGEROUS
            return PolicyDecision(
                allowed=meta.name in self.config.allowlist,
                reason="Ferramenta perigosa fora da allowlist em modo balanceado",
            )

        # Aggressive: permite tudo exceto DANGEROUS fora da allowlist; sempre auto-confirma
        if rp == RiskProfile.AGGRESSIVE:
            if pl == PermissionLevel.DANGEROUS:
                return PolicyDecision(
                    allowed=meta.name in self.config.allowlist,
                    reason="Ferramenta perigosa fora da allowlist em modo agressivo",
                )
            return PolicyDecision(allowed=True)

        # Fallback
        return PolicyDecision(allowed=True)

    def validate_tool_call(self, tool_name: str, input_args: dict | None = None) -> PolicyDecision:
        # Blocklist global
        if tool_name in self.config.blocklist:
            return PolicyDecision(allowed=False, reason="Ferramenta na blocklist")

        tool = action_registry.get_tool(tool_name)
        meta = action_registry.get_metadata(tool_name) if tool else None
        if not tool or not meta:
            return PolicyDecision(allowed=False, reason="Ferramenta não registrada")

        # Rate limit
        if not action_registry.check_rate_limit(tool_name):
            return PolicyDecision(allowed=False, reason="Rate limit atingido")

        # Permissões vs risco
        decision = self._check_permission_vs_risk(meta)
        if not decision.allowed:
            return decision

        # Confirmação obrigatória
        if meta.requires_confirmation and not self.config.auto_confirm:
            return PolicyDecision(
                allowed=False, require_confirmation=True, reason="Requer confirmação manual"
            )

        self._actions_in_cycle += 1
        return PolicyDecision(allowed=True)
