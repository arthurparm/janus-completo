import os
import sys
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

# Mocking settings if needed, but easier to just use env vars
XAI_API_KEY = "xai-0bVs7JZBDG2En88eMr0GBkEJhTYFJVgUjdvtw2og2Eic0lwwoE8cP5LSNWoKBye2jepq08Te8n28MsE9"
XAI_BASE_URL = "https://api.x.ai/v1"
MODEL_CANDIDATES = ["grok-beta", "grok-2", "grok-4", "grok-3", "grok-4.1-fast"]

for MODEL_NAME in MODEL_CANDIDATES:
    print(f"\n--- Testing Grok with model: {MODEL_NAME} ---")
    try:
        llm = ChatOpenAI(
            model=MODEL_NAME,
            temperature=0,
            api_key=XAI_API_KEY,
            base_url=XAI_BASE_URL,
            max_tokens=100,
        )
        response = llm.invoke("Say 'Grok is alive'")
        print(f"SUCCESS with {MODEL_NAME}!")
        print(f"Response: {response.content}")
        break
    except Exception as e:
        print(f"FAILED with {MODEL_NAME}: {e}")
        import traceback

        traceback.print_exc()
