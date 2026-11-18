import os
import sys

sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.config import settings
from app.core.autonomy.policy_engine import RiskProfile
from app.services.chat_agent_loop import ChatAgentLoop


class DummyToolExecutor:
    def parse_tool_calls(self, _text: str):
        return []


def test_chat_agent_loop_build_policy_reads_settings_singleton():
    loop = ChatAgentLoop(llm_service=None, tool_executor=DummyToolExecutor())
    original = {
        "CHAT_TOOL_RISK_PROFILE": settings.CHAT_TOOL_RISK_PROFILE,
        "CHAT_TOOL_AUTO_CONFIRM": settings.CHAT_TOOL_AUTO_CONFIRM,
        "CHAT_TOOL_ALLOWLIST": list(settings.CHAT_TOOL_ALLOWLIST),
        "CHAT_TOOL_BLOCKLIST": list(settings.CHAT_TOOL_BLOCKLIST),
        "CHAT_TOOL_MAX_ACTIONS": settings.CHAT_TOOL_MAX_ACTIONS,
        "CHAT_TOOL_MAX_SECONDS": settings.CHAT_TOOL_MAX_SECONDS,
    }

    try:
        settings.update(
            {
                "CHAT_TOOL_RISK_PROFILE": RiskProfile.CONSERVATIVE,
                "CHAT_TOOL_AUTO_CONFIRM": True,
                "CHAT_TOOL_ALLOWLIST": ["Execute_Shell", "list_files"],
                "CHAT_TOOL_BLOCKLIST": ["delete_file"],
                "CHAT_TOOL_MAX_ACTIONS": 7,
                "CHAT_TOOL_MAX_SECONDS": 21,
            }
        )
        policy = loop._build_policy()

        assert policy.config.risk_profile == RiskProfile.CONSERVATIVE
        assert policy.config.auto_confirm is True
        assert policy.config.allowlist == {"execute_shell", "list_files"}
        assert policy.config.blocklist == {"delete_file"}
        assert policy.config.max_actions_per_cycle == 7
        assert policy.config.max_seconds_per_cycle == 21
    finally:
        settings.update(original)
