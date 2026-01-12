import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(os.path.join(os.getcwd(), "janus"))

import traceback

try:
    from app.core.evolution.prompts import TOOL_SPECIFICATION_PROMPT, TOOL_GENERATION_PROMPT, tool_validation_prompt
    
    print(f"TOOL_SPECIFICATION_PROMPT length: {len(TOOL_SPECIFICATION_PROMPT)}")
    # ...
    
except Exception:
    traceback.print_exc()
