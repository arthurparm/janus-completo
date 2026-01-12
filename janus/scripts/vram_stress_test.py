import subprocess
import time
import requests
import json
import logging

# Config
OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:32b"  # O modelo que queremos testar
MAX_VRAM_MB = 15800  # 16GB com uma margem de segurança
START_LAYERS = 30
MAX_LAYERS = 70
STEP_LAYERS = 5

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

def get_gpu_memory_used():
    """Retorna o uso de memória da GPU em MB via nvidia-smi."""
    try:
        result = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,nounits,noheader"],
            encoding="utf-8",
        )
        return int(result.strip())
    except Exception as e:
        logger.error(f"Erro ao ler nvidia-smi: {e}")
        return 0

def set_ollama_layers(layers):
    """
    Nota: O Ollama não permite mudar layers via API dinamicamente de forma fácil sem reiniciar ou recarregar.
    Este script simula o teste tentando carregar o modelo e medindo o VRAM.
    A melhor forma de 'forçar' o reload com novas camadas via API é passar 'num_gpu' (ou num_gpu_layers) nas options.
    """
    logger.info(f"Testando com {layers} camadas...")
    
    payload = {
        "model": MODEL_NAME,
        "prompt": "Testando alocação de memória. Responda apenas 'OK'.",
        "stream": False,
        "options": {
            "num_gpu": layers,  # Parâmetro para camadas na GPU
            "num_ctx": 4096     # Contexto fixo para o teste
        }
    }
    
    try:
        start_mem = get_gpu_memory_used()
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=30)
        response.raise_for_status()
        time.sleep(2)  # Dar tempo para alocar
        end_mem = get_gpu_memory_used()
        
        logger.info(f"Memória Inicial: {start_mem}MB -> Final: {end_mem}MB (Delta: {end_mem - start_mem}MB)")
        return end_mem
    except Exception as e:
        logger.error(f"Falha ao rodar com {layers} camadas: {e}")
        return -1

def main():
    logger.info("=== INICIANDO STRESS TEST DE VRAM (Ollama) ===")
    logger.info(f"Modelo Alvo: {MODEL_NAME}")
    
    # Check if model exists
    try:
        check = requests.post("http://localhost:11434/api/show", json={"name": MODEL_NAME})
        if check.status_code != 200:
            logger.error(f"Modelo {MODEL_NAME} não encontrado! Rode 'ollama pull {MODEL_NAME}' primeiro.")
            return
    except:
        logger.error("Ollama não parece estar rodando em localhost:11434")
        return

    optimal_layers = 0
    
    # Scan simplificado: Testa 30, 40, 50, 60...
    for layers in range(START_LAYERS, MAX_LAYERS, STEP_LAYERS):
        mem_used = set_ollama_layers(layers)
        
        if mem_used > MAX_VRAM_MB:
            logger.warning(f"⚠️ {layers} camadas ESTOUROU a VRAM ({mem_used}MB > {MAX_VRAM_MB}MB).")
            break
        elif mem_used == -1:
             logger.warning("Erro na execução (provável crash ou timeout). Parando.")
             break
        else:
            logger.info(f"✅ {layers} camadas: OK ({mem_used}MB usados).")
            optimal_layers = layers
            
            # Se a memória parou de subir significativamente, talvez o modelo já esteja "todo" na GPU
            # Mas como o modelo é 32B, é improvável caber tudo em 16GB.
            
    
    logger.info("="*40)
    logger.info(f"RESULTADO: Recomendamos configurar OLLAMA_GPU_LAYERS={optimal_layers}")
    logger.info("="*40)

if __name__ == "__main__":
    main()
