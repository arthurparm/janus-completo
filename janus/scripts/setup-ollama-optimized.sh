#!/bin/bash
# Script de setup Ollama otimizado para RTX 4060 Ti 16GB
# Execute: bash setup-ollama-optimized.sh

echo "🚀 Configurando Ollama otimizado para RTX 4060 Ti 16GB..."

# Verificar se Ollama está instalado
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama não encontrado. Instale primeiro: https://ollama.ai"
    exit 1
fi

# Verificar se GPU está disponível
if nvidia-smi &> /dev/null; then
    echo "✅ GPU NVIDIA detectada:"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
else
    echo "⚠️  GPU NVIDIA não detectada. Usando CPU (performance reduzida)"
fi

echo "📦 Baixando modelos otimizados para 16GB VRAM..."

# Modelos otimizados para 16GB VRAM
MODELS=(
    "llama3.1:8b-instruct-q5_K_M"      # ~6GB VRAM - Principal
    "codellama:7b-instruct-q5_K_M"     # ~5GB VRAM - Código
    "phi3:14b-instruct-q4_K_M"         # ~8GB VRAM - Grande contexto
    "mistral:7b-instruct-q5_K_M"       # ~5GB VRAM - Alternativa
    "neural-chat:7b-v3.3-q5_K_M"      # ~5GB VRAM - Chat otimizado
)

for model in "${MODELS[@]}"; do
    echo "⬇️  Baixando $model..."
    ollama pull "$model"
    if [ $? -eq 0 ]; then
        echo "✅ $model baixado com sucesso"
    else
        echo "❌ Erro ao baixar $model"
    fi
done

echo "🔧 Configurando Ollama com parâmetros otimizados..."

# Criar arquivo de configuração Ollama
cat > ~/.ollama/config.json << 'EOF'
{
    "num_ctx": 8192,
    "num_batch": 128,
    "num_gpu": 48,
    "num_thread": 32,
    "keep_alive": "120m",
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 40,
    "repeat_penalty": 1.1
}
EOF

echo "🧪 Testando modelos..."
for model in "${MODELS[@]}"; do
    echo "📝 Testando $model..."
    ollama run "$model" "Hello, how are you?" --keepalive 120m
    if [ $? -eq 0 ]; then
        echo "✅ $model funcionando"
    else
        echo "❌ $model com problema"
    fi
    sleep 2
done

echo ""
echo "🎉 Setup Ollama otimizado concluído!"
echo ""
echo "📊 Resumo dos modelos instalados:"
echo "  • llama3.1:8b-instruct-q5_K_M - Principal (recomendado)"
echo "  • codellama:7b-instruct-q5_K_M - Código"
echo "  • phi3:14b-instruct-q4_K_M - Grande contexto"
echo "  • mistral:7b-instruct-q5_K_M - Alternativa"
echo "  • neural-chat:7b-v3.3-q5_K_M - Chat"
echo ""
echo "💡 Dicas de uso:"
echo "  • Use llama3.1:8b para tarefas gerais"
echo "  • Use codellama:7b para código"
echo "  • Use phi3:14b para contextos longos"
echo "  • Monitore VRAM com: nvidia-smi"
echo ""
echo "🚀 Pronto para usar com Janus!"