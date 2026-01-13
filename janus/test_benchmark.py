#!/usr/bin/env python3
"""
Quick benchmark comparing OLD vs NEW prompt systems.
Run inside Docker: docker exec janus_api python /app/test_benchmark.py
"""
import asyncio
import sys

sys.path.insert(0, "/app")

from app.services.prompt_builder_service import PromptBuilderService
from app.core.prompts.context import ConversationContext, Message
from app.core.prompts.intent_classifier import IntentClassifier
from app.services.prompt_composer_service import get_prompt_composer

# Sample messages
SAMPLES = [
    "What can you do?",
    "Crie uma ferramenta para buscar CEP",
    "Escreva um script Python",
    "Como funciona o sistema?",
    "Review this code: def foo(): pass",
]


async def main():
    builder = PromptBuilderService()
    classifier = IntentClassifier()
    composer = get_prompt_composer()

    print("=" * 70)
    print("PROMPT SYSTEM COMPARISON")
    print("=" * 70)

    old_tokens = []
    new_tokens = []

    for msg in SAMPLES:
        # OLD SYSTEM
        history = [{"role": "user", "text": "previous"}]
        old_prompt = await builder._build_prompt_legacy("assistant", history, msg, None)
        old_tok = len(old_prompt) // 4
        old_tokens.append(old_tok)

        # NEW SYSTEM
        ctx = ConversationContext(
            history=[Message(role="user", text="previous")], current_message=msg
        )
        intent = classifier.classify(msg)
        compiled = await composer.compose(intent, ctx)
        new_tok = compiled.token_count
        new_tokens.append(new_tok)

        reduction = ((old_tok - new_tok) / old_tok) * 100
        print(f"\n'{msg[:40]}...'")
        print(f"  OLD: {old_tok:4d} tokens")
        print(f"  NEW: {new_tok:4d} tokens (intent={intent.value})")
        print(f"  Reduction: {reduction:.1f}%")

    # Summary
    old_avg = sum(old_tokens) / len(old_tokens)
    new_avg = sum(new_tokens) / len(new_tokens)
    reduction = ((old_avg - new_avg) / old_avg) * 100

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"OLD Average: {old_avg:.0f} tokens")
    print(f"NEW Average: {new_avg:.0f} tokens")
    print(f"Reduction: {reduction:.1f}%")
    print()

    if reduction >= 50:
        print("✅ PASSED: Token reduction ≥ 50% target!")
    elif reduction >= 30:
        print(f"⚠️  PARTIAL: {reduction:.1f}% reduction (target: 50%+)")
    else:
        print("❌ FAILED: Below target")


if __name__ == "__main__":
    asyncio.run(main())
