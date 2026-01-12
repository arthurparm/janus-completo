"""
Semantic Commit Message Service.

Analyzes git diffs and generates semantic commit messages using LLM.
Follows Conventional Commits specification: type(scope): description
"""
import subprocess
from typing import Any

import structlog

from app.core.llm.router import ModelPriority, ModelRole, get_llm_async

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

SEMANTIC_COMMIT_PROMPT = """Analyze the following git diff and generate a semantic commit message.

Follow the Conventional Commits specification:
- Format: type(scope): description
- Types: feat, fix, docs, style, refactor, perf, test, chore, ci, revert
- Scope: optional, describes the area of the codebase affected
- Description: concise, imperative mood, no period at end

Rules:
1. Be specific about WHAT changed
2. Use imperative mood ("add" not "added")
3. Keep under 72 characters
4. If multiple unrelated changes, list the most significant one

Git Diff:
```
{diff}
```

Respond with ONLY the commit message, nothing else.
Example: feat(auth): add JWT token refresh endpoint
"""


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

        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            logger.warning("Git diff failed", stderr=result.stderr)
            return ""

        return result.stdout.strip()
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

        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            return []

        return [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
    except Exception as e:
        logger.error("Failed to get changed files", error=str(e))
        return []


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

    if not diff:
        return {
            "success": False,
            "error": "No changes detected" if staged_only else "No diff found",
            "commit_message": None,
            "files_changed": [],
        }

    # Get changed files
    files = await get_changed_files(repo_path, staged_only)

    # Truncate diff if too long
    truncated = False
    if len(diff) > max_diff_chars:
        diff = diff[:max_diff_chars] + "\n... (truncated)"
        truncated = True

    # Generate commit message using LLM
    prompt = SEMANTIC_COMMIT_PROMPT.format(diff=diff)

    try:
        llm = await get_llm_async(
            role=ModelRole.ORCHESTRATOR,
            priority=ModelPriority.FAST_AND_CHEAP,
            cache_key="semantic_commit",
        )

        # LLM invoke is sync, use thread pool
        import asyncio
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, llm.invoke, prompt)
        commit_message = response.content.strip()

        # Clean up response (remove quotes, markdown, etc.)
        commit_message = commit_message.strip('"\'`')
        if commit_message.startswith("```"):
            commit_message = commit_message.split("\n")[1] if "\n" in commit_message else commit_message

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
        logger.error("Failed to generate commit message", error=str(e))
        return {
            "success": False,
            "error": str(e),
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

    # Simple heuristics based on file paths
    for f in files:
        f_lower = f.lower()
        if "test" in f_lower:
            return "test"
        if "readme" in f_lower or "docs/" in f_lower or ".md" in f_lower:
            return "docs"
        if "ci/" in f_lower or ".github" in f_lower or "dockerfile" in f_lower:
            return "ci"
        if "requirements" in f_lower or "package.json" in f_lower or "pyproject" in f_lower:
            return "chore"

    return "feat"  # Default to feature
