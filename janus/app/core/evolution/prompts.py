import logging
from pathlib import Path
from app.core.infrastructure.prompt_loader import prompt_loader

logger = logging.getLogger(__name__)

def _filesystem_prompt_provider(name: str) -> str | None:
    """
    Loads prompts from the filesystem (janus/app/prompts/).
    This allows prompts to be edited in external markdown files.
    """
    try:
        # Calculate prompts directory path
        # Current file: app/core/evolution/prompts.py
        # Target: app/prompts
        current_file = Path(__file__)
        prompts_dir = current_file.parent.parent.parent / "prompts"
        
        # Check specific file
        file_path = prompts_dir / f"{name}.md"
        
        if file_path.exists():
            return file_path.read_text(encoding="utf-8")
            
        # If not found, try to look in project root relative path (fallback)
        # This handles cases where execution context might be different
        project_root_prompts = Path("janus/app/prompts")
        file_path_fallback = project_root_prompts / f"{name}.md"
        
        if file_path_fallback.exists():
            return file_path_fallback.read_text(encoding="utf-8")
            
    except Exception as e:
        logger.error(f"Error reading prompt file for '{name}': {e}")
        return None
        
    return None

# Register the filesystem provider to PromptLoader
# This enables loading prompts from files if they are not found in the database
prompt_loader.set_external_provider(_filesystem_prompt_provider)

# Load the prompts via PromptLoader
# This ensures we get the latest version (from DB if active, or file if not)
# and leverages caching.

try:
    TOOL_SPECIFICATION_PROMPT = prompt_loader.get("tool_specification")
except Exception as e:
    logger.error(f"Failed to load TOOL_SPECIFICATION_PROMPT: {e}")
    TOOL_SPECIFICATION_PROMPT = "ERROR: Could not load prompt tool_specification"

try:
    TOOL_GENERATION_PROMPT = prompt_loader.get("tool_generation")
except Exception as e:
    logger.error(f"Failed to load TOOL_GENERATION_PROMPT: {e}")
    TOOL_GENERATION_PROMPT = "ERROR: Could not load prompt tool_generation"

try:
    # Variable name preserved as lowercase to match original usage
    tool_validation_prompt = prompt_loader.get("tool_validation")
except Exception as e:
    logger.error(f"Failed to load tool_validation_prompt: {e}")
    tool_validation_prompt = "ERROR: Could not load prompt tool_validation"
