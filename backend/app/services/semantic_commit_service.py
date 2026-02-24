"""
Semantic Commit Message Service.

Analyzes git diffs and generates semantic commit messages using LLM.
Follows Conventional Commits specification: type(scope): description
"""

import asyncio
import re
import subprocess
from typing import Any

import structlog

from app.core.llm.router import ModelPriority, ModelRole, get_llm
from app.core.infrastructure.prompt_loader import get_formatted_prompt

logger = structlog.get_logger(__name__)

# Conventional Commits types
COMMIT_TYPES = {
    "feat": "A new feature",
    "fix": "A bug fix",
    "docs": "Documentation only changes",
    "style": "Code style changes (formatting, missing semi colons, etc)",
    "refactor": "Code refactoring without changing functionality",
    "perf": "Performance improvements",
    "test": "Adding or updating tests",
    "chore": "Maintenance tasks, dependencies, build changes",
    "ci": "CI/CD configuration changes",
    "revert": "Reverting a previous commit",
}

# SEMANTIC_COMMIT_PROMPT is now loaded dynamically from DB or fallback files


async def get_git_diff(repo_path: str = ".", staged_only: bool = True) -> str:
    """
    Get git diff for the repository.

    Args:
        repo_path: Path to the git repository.
        staged_only: If True, only show staged changes (git diff --cached).

    Returns:
        Git diff output as string.
    """
    try:
        cmd = ["git", "diff"]
        if staged_only:
            cmd.append("--cached")
        cmd.extend(["--no-color", "--unified=3"])

        # Run in executor to avoid blocking event loop
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=30,
            ),
        )

        if result.returncode != 0:
            logger.warning("Git diff failed", stderr=result.stderr)
            return ""

        diff_content = result.stdout.strip()
        # Fallback: if staged usage returns empty, maybe check if there are unstaged changes
        # to warn the user, but for now we strictly respect staged_only=True logic.
        return diff_content

    except subprocess.TimeoutExpired:
        logger.error("Git diff timed out")
        return ""
    except Exception as e:
        logger.error("Git diff error", error=str(e))
        return ""


async def get_changed_files(repo_path: str = ".", staged_only: bool = True) -> list[str]:
    """Get list of changed files."""
    try:
        cmd = ["git", "diff", "--name-only"]
        if staged_only:
            cmd.append("--cached")

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10,
            ),
        )

        if result.returncode != 0:
            return []

        return [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
    except Exception as e:
        logger.error("Failed to get changed files", error=str(e))
        return []


def _clean_commit_message(response_content: str) -> str:
    """Robust method to clean LLM response and extract commit message."""
    content = response_content.strip()

    # 1. Try to find content inside markdown code blocks
    code_block_pattern = re.compile(r"```(?:text|markdown)?\s*(.*?)\s*```", re.DOTALL)
    match = code_block_pattern.search(content)
    if match:
        content = match.group(1).strip()

    # 2. Remove quotes if present
    content = content.strip("\"'`")

    # 3. Use regex to ensure it looks like a semantic commit (type(scope): or type:)
    # This acts as a validator and cleaner
    semantic_pattern = re.compile(r"^([a-z]+)(?:\([a-z0-9_\-\./]+\))?: .+$", re.IGNORECASE)

    # If content has multiple lines, take the first one that matches
    lines = content.split("\n")
    for line in lines:
        line = line.strip()
        if semantic_pattern.match(line):
            return line

    # Fallback: just return the first non-empty line
    return lines[0].strip() if lines else content


async def generate_semantic_commit(
    repo_path: str = ".",
    staged_only: bool = True,
    max_diff_chars: int = 8000,
) -> dict[str, Any]:
    """
    Generate a semantic commit message based on git diff.

    Args:
        repo_path: Path to the git repository.
        staged_only: If True, analyze only staged changes.
        max_diff_chars: Maximum characters of diff to send to LLM.

    Returns:
        Dict with commit_message, files_changed, and metadata.
    """
    # Get diff
    diff = await get_git_diff(repo_path, staged_only)

    # Get changed files - independent of diff success to provide context
    files = await get_changed_files(repo_path, staged_only)

    if not diff:
        return {
            "success": False,
            "error": "No changes detected" if staged_only else "No diff found",
            "commit_message": None,
            "files_changed": files,
        }

    # Truncate diff if too long
    truncated = False
    if len(diff) > max_diff_chars:
        diff = diff[:max_diff_chars] + "\n... (truncated)"
        truncated = True

    # Generate commit message using LLM
    try:
        # Prepare context from changed files
        context_str = f"Files changed:\n{chr(10).join(['- ' + f for f in files[:20]])}"
        if len(files) > 20:
            context_str += f"\n...and {len(files) - 20} more files"

        try:
            prompt = await get_formatted_prompt("semantic_commit", diff=diff, context=context_str)
        except Exception as e:
            logger.error("Failed to load semantic commit prompt", error=str(e))
            return {
                "success": False,
                "error": f"Prompt error: {e}",
                "commit_message": None,
                "files_changed": files,
            }

        try:
            llm = await get_llm(
                role=ModelRole.ORCHESTRATOR,
                priority=ModelPriority.FAST_AND_CHEAP,
                cache_key="semantic_commit",
            )

            # Retry logic for fragility
            retries = 2
            last_error = None

            for attempt in range(retries):
                try:
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(None, llm.invoke, prompt)
                    raw_content = response.content.strip()

                    commit_message = _clean_commit_message(raw_content)

                    logger.info(
                        "Semantic commit generated",
                        commit_message=commit_message,
                        files=len(files),
                    )

                    return {
                        "success": True,
                        "commit_message": commit_message,
                        "files_changed": files,
                        "truncated": truncated,
                        "diff_chars": len(diff),
                    }
                except Exception as e:
                    logger.warning(f"Attempt {attempt + 1} failed for semantic commit: {e}")
                    last_error = e
                    await asyncio.sleep(1)  # exponential backoff if needed

            raise last_error or Exception("Failed after retries")

        except Exception as e:
            logger.error("Failed to generate commit message", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "commit_message": None,
                "files_changed": files,
            }

    except Exception as e:
        logger.error("Unexpected error in generate_semantic_commit", error=str(e))
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "commit_message": None,
            "files_changed": files,
        }


async def suggest_commit_type(files: list[str]) -> str:
    """
    Suggest a commit type based on file paths (heuristic).

    Args:
        files: List of changed file paths.

    Returns:
        Suggested commit type.
    """
    if not files:
        return "chore"

    # Enhanced heuristics based on file paths
    # Priority ordered

    for f in files:
        f_lower = f.lower()
        if "test" in f_lower or "spec" in f_lower:
            return "test"
        if any(x in f_lower for x in ["readme", "documentation/", ".md", "license", "changelog"]):
            return "docs"
        if any(x in f_lower for x in ["ci/", ".github", "dockerfile", "docker-compose", ".gitlab"]):
            return "ci"
        if any(
            x in f_lower
            for x in ["requirements", "package.json", "pyproject.toml", "poetry.lock", ".gitignore"]
        ):
            return "chore"
        if "migration" in f_lower or "alembic" in f_lower:
            return "chore"

    return "feat"  # Default to feature
