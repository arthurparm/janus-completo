import sys
import os
from pathlib import Path
import structlog
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from app.repositories.prompt_repository import PromptRepository

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)
logger = structlog.get_logger()

PROMPTS_DIR = Path(__file__).parent.parent / "app" / "prompts"

def sync_prompts():
    """
    Reads all .txt files from janus/app/prompts/ and updates the database.
    Creates new versions if content differs.
    """
    logger.info("Starting Prompt Synchronization", directory=str(PROMPTS_DIR))
    
    if not PROMPTS_DIR.exists():
        logger.error("Prompts directory not found", path=str(PROMPTS_DIR))
        return

    # Engine is initialized on repository creation; ensure tables exist if needed.
    repo = PromptRepository()
    
    files = list(PROMPTS_DIR.glob("*.txt"))
    logger.info(f"Found {len(files)} prompt files")

    updated_count = 0
    skipped_count = 0
    error_count = 0

    for file_path in files:
        prompt_name = file_path.stem
        try:
            content = file_path.read_text(encoding="utf-8").strip()
            if not content:
                logger.warning("Empty prompt file skipped", file=file_path.name)
                continue

            # Check existing
            existing = repo.get_active_prompt_sync(prompt_name)
            
            if existing and existing.prompt_text.strip() == content:
                logger.debug("Prompt up to date", name=prompt_name)
                skipped_count += 1
                continue

            # Create new version
            logger.info("Updating prompt", name=prompt_name)
            version = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            repo.create_prompt_version(
                prompt_name=prompt_name,
                prompt_text=content,
                version=version,
                created_by="sync_script",
                activate=True
            )
            updated_count += 1

        except Exception as e:
            logger.error("Failed to sync prompt", name=prompt_name, error=str(e))
            error_count += 1

    logger.info(
        "Sync Completed", 
        updated=updated_count, 
        skipped=skipped_count, 
        errors=error_count
    )

if __name__ == "__main__":
    sync_prompts()
