import asyncio
import os
import sys
import time

# Adiciona o diretório pai ao path para importar app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings
from app.core.llm.client import get_llm_client
from app.core.llm.types import ModelPriority, ModelRole


async def test_deepseek():
    print("\n🔵 TESTANDO DEEPSEEK (CLOUD)...")
    try:
        # Força o uso do DeepSeek via config temporária ou direta
        # Como o .env já tem a chave, vamos tentar instanciar direto
        if not settings.DEEPSEEK_API_KEY:
            print("❌ DEEPSEEK_API_KEY não encontrada no .env")
            return

        client = get_llm_client(role=ModelRole.ORCHESTRATOR, priority=ModelPriority.HIGH_QUALITY)
        # Hack para forçar DeepSeek se o Router não o escolher por padrão
        client.provider = "deepseek"
        client.model = settings.DEEPSEEK_MODEL_NAME

        # Precisamos re-instanciar o adapter/base se mudarmos na marra, mas o get_llm_client
        # usa o Router. Vamos confiar que se configuramos candidato ele vai.
        # Melhor: Vamos instanciar um client específico manual para teste
        from langchain_openai import ChatOpenAI

        from app.core.llm.client import LLMClient

        base_llm = ChatOpenAI(
            model=settings.DEEPSEEK_MODEL_NAME,
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            temperature=0
        )

        janus_client = LLMClient(
            base=base_llm,
            provider="deepseek",
            model=settings.DEEPSEEK_MODEL_NAME,
            role=ModelRole.ORCHESTRATOR,
            cache_key="test_deepseek"
        )

        start = time.perf_counter()
        print("   Enviando prompt: 'Quanto é 25 * 4? Responda curto.'")
        resp = await janus_client.asend("Quanto é 25 * 4? Responda curto.")
        dur = time.perf_counter() - start

        print(f"✅ RESPOSTA: {resp}")
        print(f"   Tempo: {dur:.2f}s")
        print("   Cost Tracking: Verifique os logs do Janus para 'Cost USD'")

    except Exception as e:
        print(f"❌ ERRO DEEPSEEK: {e}")

async def test_local_ollama():
    print("\n🟢 TESTANDO OLLAMA (LOCAL) - VIA JANUS (OTIMIZADO)...")
    try:
        print(f"   Configuração carregada: LAYERS={settings.OLLAMA_GPU_LAYERS}, CTX={settings.OLLAMA_NUM_CTX}")

        # Usa o factory oficial que aplica as otimizações
        client = get_llm_client(role=ModelRole.CODE_GENERATOR, priority=ModelPriority.LOCAL_ONLY)

        # Verifica se pegou o modelo certo
        print(f"   Modelo Selecionado: {client.model} ({client.provider})")

        prompt = "Escreva uma função python de fibonacci recursiva."

        start = time.perf_counter()
        print("   Gerando código...")
        resp = await client.asend(prompt)
        dur = time.perf_counter() - start

        # Estimativa grosseira de tokens
        tokens = len(resp) / 4
        tps = tokens / dur

        print(f"✅ CONCLUÍDO em {dur:.2f}s")
        print(f"   Speed Estimado: ~{tps:.1f} tokens/s (Janus Optimized)")

        if tps > 10:
            print("🚀 RESULTADO: Aceleração confirmada! (Terminal estava ~6 t/s)")
        else:
            print("⚠️ RESULTADO: Ainda lento. O modelo pode estar recarregando ou layers insuficientes.")

    except Exception as e:
        print(f"❌ ERRO OLLAMA: {e}")

async def main():
    print("=== JANUS HYBRID VERIFICATION ===")
    await test_deepseek()
    await test_local_ollama()

if __name__ == "__main__":
    if sys.platform.startswith("win") and sys.version_info >= (3, 8):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
