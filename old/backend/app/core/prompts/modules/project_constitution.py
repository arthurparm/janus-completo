"""Always-on prompt module for the Janus founding law."""

from app.core.project_constitution import get_project_constitution
from app.core.prompts.base import PromptModule
from app.core.prompts.context import ConversationContext
from app.core.prompts.types import IntentType


class ProjectConstitutionModule(PromptModule):
    """Apply the immutable project mission before dynamically managed prompts."""

    @property
    def name(self) -> str:
        return "project_constitution"

    @property
    def priority(self) -> int:
        return 5

    async def render(self, intent: IntentType, context: ConversationContext) -> str:
        """Render the founding law for every intent and persona."""

        return get_project_constitution()
