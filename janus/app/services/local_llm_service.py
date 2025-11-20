"""
Serviço de LLM Local otimizado para RTX 4060 Ti
Gerencia modelos locais e roteamento inteligente
"""
import os
import psutil
import logging
import requests
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SystemResources:
    cpu_percent: float
    memory_percent: float
    gpu_memory_used: int  # MB
    gpu_memory_total: int  # MB
    can_run_local: bool

class LocalLLMService:
    """Serviço de LLM local com otimização de recursos"""
    
    def __init__(self):
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.max_gpu_memory_percent = 85  # Não usar mais que 85% da VRAM
        self.max_cpu_percent = 80        # Não usar mais que 80% da CPU
        self.max_memory_percent = 85     # Não usar mais que 85% da RAM
        
        # Modelos otimizados para RTX 4060 Ti (16GB VRAM)
        self.local_models = {
            "codellama:7b": {
                "name": "CodeLlama 7B",
                "vram_mb": 4000,
                "ram_mb": 2000,
                "description": "Modelo de código otimizado"
            },
            "mistral:7b": {
                "name": "Mistral 7B", 
                "vram_mb": 3800,
                "ram_mb": 1800,
                "description": "Modelo geral de alta qualidade"
            },
            "llama2:7b": {
                "name": "Llama 2 7B",
                "vram_mb": 4200,
                "ram_mb": 2100,
                "description": "Modelo geral versátil"
            }
        }
    
    def get_system_resources(self) -> SystemResources:
        """Obtém recursos do sistema"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent
            
            # GPU info (simplificado - você pode usar nvidia-ml-py)
            gpu_memory_used = self._get_gpu_memory_used()
            gpu_memory_total = 16384  # RTX 4060 Ti tem 16GB
            
            # Decide se pode rodar local
            can_run_local = (
                cpu_percent < self.max_cpu_percent and
                memory_percent < self.max_memory_percent and
                (gpu_memory_used / gpu_memory_total) < (self.max_gpu_memory_percent / 100)
            )
            
            return SystemResources(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                gpu_memory_used=gpu_memory_used,
                gpu_memory_total=gpu_memory_total,
                can_run_local=can_run_local
            )
            
        except Exception as e:
            logger.error(f"Erro ao obter recursos do sistema: {e}")
            return SystemResources(0, 0, 0, 16384, False)
    
    def _get_gpu_memory_used(self) -> int:
        """Obtém memória GPU usada (simplificado)"""
        try:
            # Você pode usar nvidia-ml-py para obter dados reais
            # Por enquanto, estimamos baseado em processos Ollama
            for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
                if 'ollama' in proc.info['name'].lower():
                    return proc.info['memory_info'].rss // (1024 * 1024)  # Convert to MB
        except:
            pass
        return 0
    
    def is_model_available(self, model_name: str) -> bool:
        """Verifica se modelo está disponível localmente"""
        try:
            response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                return any(model.get('name', '').startswith(model_name) for model in models)
        except Exception as e:
            logger.error(f"Erro ao verificar modelos: {e}")
        return False
    
    def generate_text(self, model_name: str, prompt: str, **kwargs) -> Dict[str, Any]:
        """Gera texto usando modelo local"""
        try:
            resources = self.get_system_resources()
            
            if not resources.can_run_local:
                return {
                    "error": "Sistema sobrecarregado. Use API externa.",
                    "resources": resources.__dict__,
                    "suggestion": "Reduza a carga ou use OpenAI/Anthropic"
                }
            
            if not self.is_model_available(model_name):
                return {
                    "error": f"Modelo {model_name} não disponível",
                    "available_models": list(self.local_models.keys())
                }
            
            # Chama Ollama
            payload = {
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": kwargs.get('temperature', 0.7),
                    "top_p": kwargs.get('top_p', 0.9),
                    "max_tokens": kwargs.get('max_tokens', 1000)
                }
            }
            
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "text": result.get('response', ''),
                    "model": model_name,
                    "resources_used": resources.__dict__,
                    "local": True
                }
            else:
                return {
                    "error": f"Erro Ollama: {response.status_code}",
                    "details": response.text
                }
                
        except requests.exceptions.Timeout:
            return {
                "error": "Timeout ao gerar texto",
                "suggestion": "Tente um modelo menor ou reduza o prompt"
            }
        except Exception as e:
            logger.error(f"Erro na geração: {e}")
            return {
                "error": str(e),
                "suggestion": "Verifique se Ollama está rodando"
            }
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Obtém informações sobre um modelo"""
        return self.local_models.get(model_name, {
            "error": "Modelo não encontrado",
            "available": list(self.local_models.keys())
        })
    
    def get_available_models(self) -> list:
        """Lista modelos disponíveis localmente"""
        try:
            response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                return [model.get('name', '') for model in models]
        except:
            pass
        return []

# Singleton instance
local_llm_service = LocalLLMService()