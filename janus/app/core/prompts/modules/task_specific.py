"""
Task-Specific Instructions Module - Intent-specific guidelines.
Provides clear, actionable instructions only for the current task type.
"""

from app.core.prompts.base import PromptModule
from app.core.prompts.context import ConversationContext
from app.core.prompts.types import IntentType


class TaskSpecificModule(PromptModule):
    """
    Provides focused instructions specific to the detected intent.
    Replaces verbose few-shot examples with concise, direct guidelines.
    """

    # Task-specific instruction templates
    TASK_INSTRUCTIONS = {
        IntentType.TOOL_CREATION: """
═══════════════════════════════════════════════════════════════════
                      TOOL CREATION PROTOCOL
═══════════════════════════════════════════════════════════════════

When user requests a **SYSTEM TOOL** (keywords: "tool", "ferramenta", "capability"):

✓ **Action**: Use `evolve_tool` with full capability description
✓ **Response**: "I'll create this as a registered system tool."
✓ **NEVER**: Use `write_file` for tool creation

The tool will be automatically registered and available for future use.
""",
        IntentType.SCRIPT_GENERATION: """
═══════════════════════════════════════════════════════════════════
                    SCRIPT GENERATION PROTOCOL
═══════════════════════════════════════════════════════════════════

When user requests a **STANDALONE SCRIPT** (keywords: "script", "file", "código"):

✓ **Action**: Use `write_file` to save to `/app/workspace/`
✓ **Process**: Generate code based on your training, then write file
✓ **Response**: Explain what the script does after writing it

No need to inspect existing code unless user explicitly asks for consistency.
""",
        IntentType.CODE_REVIEW: """
═══════════════════════════════════════════════════════════════════
                      CODE REVIEW PROTOCOL
═══════════════════════════════════════════════════════════════════

✓ **Read code**: Use `read_file` to get actual content
✓ **Analyze**: Check for bugs, style issues, best practices
✓ **Context**: Use `query_knowledge_graph` if you need project context
✓ **Report**: Provide specific, actionable feedback with line numbers
""",
        IntentType.DEBUGGING: """
═══════════════════════════════════════════════════════════════════
                       DEBUGGING PROTOCOL
═══════════════════════════════════════════════════════════════════

1. **Understand**: Ask clarifying questions if error is unclear
2. **Investigate**: Use `read_file` and `execute_shell` to gather data
3. **Hypothesize**: Form potential causes based on evidence
4. **Test**: Verify each hypothesis systematically
5. **Fix**: Propose specific code changes or configuration adjustments
""",
        IntentType.QUESTION: """
═══════════════════════════════════════════════════════════════════
                     QUESTION ANSWERING PROTOCOL
═══════════════════════════════════════════════════════════════════

✓ **Check knowledge**: Use `query_knowledge_graph` to ground your answer
✓ **Verify**: If unsure, read relevant files instead of guessing
✓ **Be honest**: If you need to check code, say so and use tools
✓ **Be clear**: Answer directly, avoid unnecessary preamble
""",
    }

    @property
    def name(self) -> str:
        return "task_specific"

    @property
    def priority(self) -> int:
        return 50  # Load last

    def is_applicable(self, intent: IntentType) -> bool:
        """Load instructions only for tasks with specific protocols."""
        return intent in self.TASK_INSTRUCTIONS

    async def render(self, intent: IntentType, context: ConversationContext) -> str:
        """Return task-specific instructions."""
        return self.TASK_INSTRUCTIONS.get(intent, "")
