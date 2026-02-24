import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.exc import IntegrityError

BACKEND_ROOT = Path(__file__).resolve().parents[1]
backend_root_str = str(BACKEND_ROOT)
if backend_root_str not in sys.path:
    sys.path.append(backend_root_str)

from app.db import db
from app.models.config_models import Prompt

PROMPTS_TO_UPDATE = [
    "meta_agent",
    "meta_agent_diagnosis",
    "meta_agent_planning",
    "meta_agent_reflection",
    "meta_agent_act_template",
    "meta_agent_plan_template",
]


def load_prompt_content(prompt_name: str) -> Optional[str]:
    candidates = [
        BACKEND_ROOT / "app" / "prompts" / f"{prompt_name}.txt",
        Path("/app/app/prompts") / f"{prompt_name}.txt",
    ]
    for file_path in candidates:
        if file_path.exists():
            return file_path.read_text(encoding="utf-8")
    print(f"  [WARN] File not found in candidates: {[str(path) for path in candidates]}")
    return None


def update_prompts():
    session = db.get_session_direct()
    print("Starting Meta Agent prompt update (Full Production Refactoring)...")

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
                existing.prompt_version = "3.0-refactored"
                existing.is_active = True
                existing.updated_at = datetime.utcnow()
                action = "UPDATED"
            else:
                # Create if doesn't exist
                new_prompt = Prompt(
                    prompt_name=prompt_name,
                    prompt_version="3.0-refactored",
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
