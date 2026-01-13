import sys
import os
import glob
from pathlib import Path
from sqlalchemy import text

# Add parent directory to path to allow imports
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.db.postgres_config import postgres_db
from app.models.config_models import Prompt

def get_namespace(filename):
    if filename.startswith("agent_"):
        return "agents"
    if filename.startswith("tool_") or filename.startswith("evolution_"):
        return "evolution"
    if filename.startswith("autonomy_"):
        return "autonomy"
    if filename.startswith("capability_"):
        return "capabilities"
    if filename.startswith("reflexion_"):
        return "reflexion"
    if filename.startswith("specialized_"):
        return "specialized"
    if filename == "cypher_generation":
        return "graph"
    if filename == "knowledge_extraction":
        return "knowledge"
    if filename == "rerank":
        return "rag"
    if filename == "meta_agent":
        return "orchestrator"
    return "default"

def migrate_prompts():
    prompts_dir = Path(os.path.dirname(__file__)) / "../app/prompts"
    prompts_dir = prompts_dir.resolve()
    
    print(f"📂 Scanning for prompts in {prompts_dir}...")
    
    if not prompts_dir.exists():
        print(f"❌ Directory not found: {prompts_dir}")
        return

    files = glob.glob(str(prompts_dir / "*.txt"))
    
    if not files:
        print("❌ No prompt files found!")
        return

    session = postgres_db.get_session_direct()
    
    count = 0
    updated_count = 0
    created_count = 0
    
    try:
        for file_path in files:
            path = Path(file_path)
            prompt_name = path.stem
            content = path.read_text(encoding="utf-8")
            
            namespace = get_namespace(prompt_name)
            
            # Check if exists active
            # We filter by name and namespace. We ignore language/model for matching purposes
            # to avoid creating duplicates if language changed.
            existing = session.query(Prompt).filter_by(
                prompt_name=prompt_name, 
                namespace=namespace,
                is_active=True
            ).first()
            
            if existing:
                print(f"🔄 Updating {prompt_name} (Namespace: {namespace})...")
                existing.prompt_text = content
                existing.updated_at = text("NOW()")
                if existing.prompt_version == "1.0":
                     existing.prompt_version = "2.0"
                updated_count += 1
            else:
                print(f"➕ Creating {prompt_name} (Namespace: {namespace})...")
                new_prompt = Prompt(
                    prompt_name=prompt_name,
                    prompt_text=content,
                    is_active=True,
                    namespace=namespace,
                    prompt_version="2.0",
                    language="mixed",
                    model_target="general"
                )
                session.add(new_prompt)
                created_count += 1
            
            # Flush to check for errors immediately
            session.flush()
            count += 1
            
        session.commit()
        print(f"✅ Successfully processed {count} prompts.")
        print(f"   - Created: {created_count}")
        print(f"   - Updated: {updated_count}")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error migrating prompts: {e}")
        # import traceback
        # traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    migrate_prompts()
