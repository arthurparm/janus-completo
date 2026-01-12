import asyncio
import sys
import os

# Ajusta path para o diretório 'janus'
current_dir = os.path.dirname(os.path.abspath(__file__))
janus_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.insert(0, janus_root)

from app.core.infrastructure.prompt_fallback import get_formatted_prompt


async def verify_prompts():
    print("=== Iniciando Verificação de Prompts Janus ===")

    prompts_to_test = [
        "semantic_commit",
        "hyde_generation",
        "rerank",
        "knowledge_extraction",
        "meta_agent",
        "cypher_generation",
        "qa_synthesis",
        "reflexion_evaluate",
        "reflexion_refine",
        "task_decomposition",
        "autonomy_plan_draft",
        "autonomy_plan_critique",
        "autonomy_plan_refine",
        "tool_specification",
        "tool_generation",
        "tool_validation",
    ]

    success_count = 0

    for name in prompts_to_test:
        print(f"\nTestando prompt: {name}...")
        try:
            # Tenta carregar sem variáveis primeiro para ver se existe
            content = get_formatted_prompt(name)
            if content and len(content) > 100:
                print(f"  [OK] Prompt '{name}' carregado com sucesso ({len(content)} caracteres).")
                success_count += 1
            else:
                print(f"  [AVISO] Prompt '{name}' carregado mas parece curto ou vazio.")
        except Exception as e:
            print(f"  [ERRO] Falha ao carregar prompt '{name}': {e}")

    print(f"\n=== Resultado Final: {success_count}/{len(prompts_to_test)} prompts validados ===")


if __name__ == "__main__":
    asyncio.run(verify_prompts())
