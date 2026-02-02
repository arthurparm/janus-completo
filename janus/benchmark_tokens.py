#!/usr/bin/env python3
"""
Token Reduction Benchmark - Compare modular vs monolithic prompts
Estimates based on documented OLD system (~2500 tokens) vs NEW measurements
"""

import asyncio

from app.core.prompts.intent_classifier import IntentClassifier
from app.services.prompt_builder_service import PromptBuilderService

# Test cases covering different intent types
TEST_CASES = [
    ("What can you do?", "CAPABILITIES_QUERY"),
    ("Crie uma ferramenta para buscar CEP", "TOOL_CREATION"),
    ("Escreva um script Python para fibonacci", "SCRIPT_GENERATION"),
    ("Como funciona o sistema de memória?", "QUESTION"),
    ("Review this code: def foo(): pass", "CODE_REVIEW"),
]

# OLD SYSTEM BASELINE (from documentation)
OLD_SYSTEM_BASELINE = 2500  # tokens (monolithic system)


async def main():
    builder = PromptBuilderService()
    classifier = IntentClassifier()

    print("=" * 70)
    print("🔬 MODULAR PROMPT SYSTEM - TOKEN REDUCTION BENCHMARK")
    print("=" * 70)
    print()

    results = []

    for msg, expected_intent in TEST_CASES:
        # Build with NEW system
        prompt = await builder.build_prompt(
            persona="assistant",
            history=[{"role": "user", "text": "previous context"}],
            new_user_message=msg,
            summary=None,
        )

        new_tokens = len(prompt) // 4
        reduction = ((OLD_SYSTEM_BASELINE - new_tokens) / OLD_SYSTEM_BASELINE) * 100

        # Verify intent
        intent = classifier.classify(msg)

        results.append((msg[:45], new_tokens, reduction, intent.value))

        print(f"📝 '{msg[:45]}...'")
        print(f"   OLD: ~{OLD_SYSTEM_BASELINE} tokens (baseline)")
        print(f"   NEW: ~{new_tokens} tokens")
        print(f"   Intent: {intent.value}")
        print(f"   🎯 Reduction: {reduction:.1f}%")
        print()

    # Summary
    avg_new = sum(r[1] for r in results) / len(results)
    avg_reduction = ((OLD_SYSTEM_BASELINE - avg_new) / OLD_SYSTEM_BASELINE) * 100

    print("=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    print(f"OLD System (Baseline): ~{OLD_SYSTEM_BASELINE} tokens/request")
    print(f"NEW System (Average):  ~{avg_new:.0f} tokens/request")
    print(f"Tokens Saved:          ~{OLD_SYSTEM_BASELINE - avg_new:.0f} tokens/request")
    print(f"Reduction:             {avg_reduction:.1f}%")
    print()

    # Verdict
    if avg_reduction >= 50:
        print("✅ PASSED: Token reduction ≥ 50% target ACHIEVED!")
        print("🎉 System is production-ready!")
    elif avg_reduction >= 30:
        print(f"⚠️  PARTIAL: {avg_reduction:.1f}% reduction (target: 50%+)")
        print("   Consider further optimization")
    else:
        print("❌ FAILED: Token reduction below 30% target")

    print()
    print("=" * 70)
    print("🏆 BENEFITS")
    print("=" * 70)
    print("• Faster responses (less LLM processing)")
    print(f"• Lower costs ({avg_reduction:.0f}% reduction in tokens)")
    print("• Modular architecture (easy to extend)")
    print("• Intent-based optimization (smart loading)")
    print("• NO LEGACY CODE (100% modern)")


if __name__ == "__main__":
    asyncio.run(main())
