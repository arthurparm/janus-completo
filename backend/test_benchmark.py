#!/usr/bin/env python3
"""
Quick benchmark for the current modular prompt system.
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
    print("PROMPT SYSTEM BENCHMARK")
    print("=" * 70)

    prompt_tokens = []
    composer_tokens = []

    for msg in SAMPLES:
        # PromptBuilder API
        history = [{"role": "user", "text": "previous"}]
        prompt_text = await builder.build_prompt("assistant", history, msg, None)
        prompt_tok = len(prompt_text) // 4
        prompt_tokens.append(prompt_tok)

        # PromptComposer API (lower level)
        ctx = ConversationContext(
            history=[Message(role="user", text="previous")], current_message=msg
        )
        intent = classifier.classify(msg)
        compiled = await composer.compose(intent, ctx)
        composed_tok = compiled.token_count
        composer_tokens.append(composed_tok)

        delta = ((prompt_tok - composed_tok) / max(prompt_tok, 1)) * 100
        print(f"\n'{msg[:40]}...'")
        print(f"  Builder:  {prompt_tok:4d} tokens")
        print(f"  Composer: {composed_tok:4d} tokens (intent={intent.value})")
        print(f"  Delta: {delta:.1f}%")

    # Summary
    builder_avg = sum(prompt_tokens) / len(prompt_tokens)
    composer_avg = sum(composer_tokens) / len(composer_tokens)
    delta = ((builder_avg - composer_avg) / max(builder_avg, 1)) * 100

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Builder Average:  {builder_avg:.0f} tokens")
    print(f"Composer Average: {composer_avg:.0f} tokens")
    print(f"Delta: {delta:.1f}%")
    print()

    print("Benchmark completed.")


if __name__ == "__main__":
    asyncio.run(main())
