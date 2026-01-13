"""
Benchmark script to compare token consumption: old vs new prompt system.
Run with: python scripts/benchmark_prompt_tokens.py --samples 100
"""

import argparse
import asyncio
import statistics
from typing import Any

# Sample test messages covering different intent types
SAMPLE_MESSAGES = [
    # Tool creation
    "Crie uma ferramenta para buscar informações de CEP",
    "Create a tool to validate email addresses",
    "Preciso de uma ferramenta que consulte APIs REST",
    # Script generation
    "Escreva um script Python que calcule fibonacci",
    "Write a shell script to backup my database",
    "Generate code to parse JSON files",
    # Questions
    "Como funciona o sistema de memória de longo prazo?",
    "What tools are available?",
    "Explain the architecture of Janus",
    # Code review
    "Revise este código Python: def foo(): pass",
    "Review my implementation of QuickSort",
    # Debugging
    "Meu código está dando erro 'undefined'",
    "The API returns 500 error",
    # Casual
    "Olá, tudo bem?",
    "Hello, how are you?",
]


async def benchmark_old_system(prompt_builder, sample_msg: str) -> dict[str, Any]:
    """Benchmark old prompt_builder_service."""
    history = [
        {"role": "user", "text": "Previous message 1"},
        {"role": "assistant", "text": "Response 1"},
    ]

    prompt = await prompt_builder._build_prompt_legacy(
        persona="assistant",
        history=history,
        new_user_message=sample_msg,
        summary="Previous conversation context",
        relevant_memories=None,
    )

    tokens = len(prompt) // 4  # Estimate

    return {"prompt": prompt, "tokens": tokens, "length": len(prompt)}


async def benchmark_new_system(prompt_builder, sample_msg: str) -> dict[str, Any]:
    """Benchmark new PromptComposer system."""
    from app.core.prompts.context import ConversationContext, Message

    history = [
        Message(role="user", text="Previous message 1"),
        Message(role="assistant", text="Response 1"),
    ]

    context = ConversationContext(
        history=history,
        current_message=sample_msg,
        summary="Previous conversation context",
    )

    # Use new system
    from app.services.prompt_composer_service import get_prompt_composer

    composer = get_prompt_composer()

    from app.core.prompts.intent_classifier import IntentClassifier

    classifier = IntentClassifier()
    intent = classifier.classify(sample_msg)

    compiled = await composer.compose(intent, context)

    return {
        "prompt": compiled.text,
        "tokens": compiled.token_count,
        "length": len(compiled.text),
        "intent": intent.value,
        "modules": compiled.modules_used,
    }


async def run_benchmark(samples: int = 100):
    """Run benchmark comparing both systems."""
    from app.services.prompt_builder_service import PromptBuilderService

    builder = PromptBuilderService()

    print("=" * 70)
    print("PROMPT SYSTEM BENCHMARK")
    print("=" * 70)
    print(f"Samples: {samples}")
    print()

    old_tokens = []
    new_tokens = []

    # Run comparisons
    for i in range(samples):
        msg = SAMPLE_MESSAGES[i % len(SAMPLE_MESSAGES)]

        try:
            old_result = await benchmark_old_system(builder, msg)
            new_result = await benchmark_new_system(builder, msg)

            old_tokens.append(old_result["tokens"])
            new_tokens.append(new_result["tokens"])

            if i < 5:  # Show first 5 in detail
                print(f"\nSample {i+1}: {msg[:50]}...")
                print(f"  OLD: {old_result['tokens']} tokens")
                print(f"  NEW: {new_result['tokens']} tokens (intent={new_result['intent']})")
                print(f"  Modules: {', '.join(new_result['modules'])}")
                reduction = (
                    (old_result["tokens"] - new_result["tokens"]) / old_result["tokens"]
                ) * 100
                print(f"  Reduction: {reduction:.1f}%")

        except Exception as e:
            print(f"Error on sample {i}: {e}")
            continue

    # Summary statistics
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    old_avg = statistics.mean(old_tokens)
    new_avg = statistics.mean(new_tokens)
    reduction = ((old_avg - new_avg) / old_avg) * 100

    print(f"Old System:")
    print(f"  Average: {old_avg:.0f} tokens")
    print(f"  Min: {min(old_tokens)} tokens")
    print(f"  Max: {max(old_tokens)} tokens")
    print()
    print(f"New System:")
    print(f"  Average: {new_avg:.0f} tokens")
    print(f"  Min: {min(new_tokens)} tokens")
    print(f"  Max: {max(new_tokens)} tokens")
    print()
    print(f"Token Reduction: {reduction:.1f}%")
    print()

    # Verdict
    if reduction >= 50:
        print("✅ PASSED: Token reduction ≥ 50% target achieved!")
    elif reduction >= 30:
        print("⚠️  PARTIAL: {reduction:.1f}% reduction (target: 50%+)")
    else:
        print("❌ FAILED: Token reduction below target")

    return {"old_avg": old_avg, "new_avg": new_avg, "reduction": reduction}


def main():
    parser = argparse.ArgumentParser(description="Benchmark prompt token consumption")
    parser.add_argument("--samples", type=int, default=100, help="Number of samples to test")
    args = parser.parse_args()

    asyncio.run(run_benchmark(args.samples))


if __name__ == "__main__":
    main()
