#!/usr/bin/env python
from app.repositories.prompt_repository import PromptRepository

repo = PromptRepository()
p = repo.get_active_prompt_sync("meta_agent_planning")

if p:
    print(f"Version: {p.prompt_version}")
    print(f"Language: {p.language}")
    print(f"Active: {p.is_active}")
    print(f"First 300 chars of text:")
    print(p.prompt_text[:300])
    print("\n---")
    print("Checking for unescaped braces in JSON schema section...")
    if '{\n  "recommendations"' in p.prompt_text:
        print("ERROR: Found UNESCAPED braces in database!")
    elif '{{\n  "recommendations"' in p.prompt_text:
        print("OK: Braces are properly escaped.")
    else:
        print("WARNING: Could not find JSON schema section.")
else:
    print("ERROR: Prompt not found in database!")
