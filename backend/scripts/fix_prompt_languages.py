import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.db import db
from app.models.config_models import Prompt

PROMPTS_TO_UPDATE = [
    "knowledge_extraction",
    "meta_agent",
    "meta_agent_act_template",
    "meta_agent_diagnosis",
    "meta_agent_planning",
    "meta_agent_plan_template",
    "meta_agent_reflection",
    "reflexion_refine",
    "knowledge_extraction_system",
    "reflexion_evaluate",
    "graph_query_planning",
    "knowledge_wisdom_extraction",
    "memory_integration",
    "security_red_team_audit",
    "context_compression",
    "error_recovery",
    "multi_agent_decomposition",
    "reflexion_execution",
    "task_decomposition",
    "janus_identity_jarvis",
]


def load_prompt_content(prompt_name: str) -> Optional[str]:
    prompts_dir = Path(__file__).resolve().parents[1] / "app" / "prompts"
    # Try flat path first (backwards compatibility)
    flat = prompts_dir / f"{prompt_name}.txt"
    if flat.exists():
        return flat.read_text(encoding="utf-8")
    # Fall back to recursive search in subdirectories
    if prompts_dir.exists():
        matches = list(prompts_dir.rglob(f"{prompt_name}.txt"))
        if matches:
            return matches[0].read_text(encoding="utf-8")
    print(f"  [WARN] File not found for prompt: {prompt_name}")
    return None


def update_prompts():
    session = db.get_session_direct()
    print("Starting prompt language update (Update In-Place)...")

    updated_count = 0
    errors = []

    for prompt_name in PROMPTS_TO_UPDATE:
        print(f"Processing {prompt_name}...", end="")

        content = load_prompt_content(prompt_name)
        if not content:
            print(" SKIPPED (No content)")
            errors.append(f"{prompt_name}: No content")
            continue

        try:
            # Update In-Place Strategy
            # Find ANY existing prompt with this name
            existing = session.query(Prompt).filter(Prompt.prompt_name == prompt_name).first()

            if existing:
                # Update existing record
                existing.prompt_text = content
                existing.language = "en"
                existing.prompt_version = "2.1-en-fix"
                existing.is_active = True
                existing.updated_at = datetime.utcnow()
                action = "UPDATED"
            else:
                # Create if doesn't exist
                new_prompt = Prompt(
                    prompt_name=prompt_name,
                    prompt_version="2.1-en-fix",
                    prompt_text=content,
                    is_active=True,
                    namespace="default",
                    language="en",
                    model_target="general",
                    created_by="migration_script",
                )
                session.add(new_prompt)
                action = "CREATED"

            session.commit()
            print(f" {action} OK")
            updated_count += 1

        except IntegrityError as ie:
            session.rollback()
            print(f" FAILED (IntegrityError)")
            print(f"    Details: {ie}")
            errors.append(f"{prompt_name}: IntegrityError")
        except Exception as e:
            session.rollback()
            print(f" FAILED ({type(e).__name__})")
            print(f"    Details: {e}")
            errors.append(f"{prompt_name}: {e}")

    session.close()

    print("\n" + "=" * 50)
    print(f"Migration Complete. Updated: {updated_count}, Errors: {len(errors)}")
    print("=" * 50)


if __name__ == "__main__":
    update_prompts()
