# Script de setup Ollama otimizado para Windows + RTX 4060 Ti 16GB
# Execute: PowerShell -ExecutionPolicy Bypass -File setup-ollama-optimized-windows.ps1

Write-Host "🚀 Configurando Ollama otimizado para RTX 4060 Ti 16GB..." -ForegroundColor Green

# Verificar se Ollama está instalado
try {
    $ollamaVersion = ollama --version
    Write-Host "✅ Ollama encontrado: $ollamaVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Ollama não encontrado. Instale primeiro: https://ollama.ai" -ForegroundColor Red
    exit 1
}

# Verificar se GPU está disponível
try {
    $gpuInfo = nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>$null
    if ($gpuInfo) {
        Write-Host "✅ GPU NVIDIA detectada: $gpuInfo" -ForegroundColor Green
    } else {
        Write-Host "⚠️  GPU NVIDIA não detectada. Usando CPU (performance reduzida)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  nvidia-smi não encontrado. Usando CPU (performance reduzida)" -ForegroundColor Yellow
}

Write-Host "📦 Baixando modelos otimizados para 16GB VRAM..." -ForegroundColor Cyan

# Modelos otimizados para 16GB VRAM
$models = @(
    "llama3.1:8b-instruct-q5_K_M",      # ~6GB VRAM - Principal
    "codellama:7b-instruct-q5_K_M",     # ~5GB VRAM - Código  
    "phi3:14b-instruct-q4_K_M",         # ~8GB VRAM - Grande contexto
    "mistral:7b-instruct-q5_K_M",       # ~5GB VRAM - Alternativa
    "neural-chat:7b-v3.3-q5_K_M"       # ~5GB VRAM - Chat otimizado
)

foreach ($model in $models) {
    Write-Host "⬇️  Baixando $model..." -ForegroundColor Yellow
    try {
        ollama pull $model
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ $model baixado com sucesso" -ForegroundColor Green
        } else {
            Write-Host "❌ Erro ao baixar $model" -ForegroundColor Red
        }
    } catch {
        Write-Host "❌ Erro ao baixar $model: $_" -ForegroundColor Red
    }
}

Write-Host "🔧 Configurando Ollama com parâmetros otimizados..." -ForegroundColor Cyan

# Criar arquivo de configuração Ollama no Windows
$configDir = "$env:USERPROFILE\.ollama"
if (!(Test-Path $configDir)) {
    New-Item -ItemType Directory -Path $configDir -Force
}

$configContent = @"
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
"@

$configContent | Out-File -FilePath "$configDir\config.json" -Encoding UTF8
Write-Host "✅ Configuração salva em: $configDir\config.json" -ForegroundColor Green

Write-Host "🧪 Testando modelos..." -ForegroundColor Cyan
foreach ($model in $models) {
    Write-Host "📝 Testando $model..." -ForegroundColor Yellow
    try {
        $output = ollama run $model "Hello, how are you?" --keepalive 120m 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ $model funcionando" -ForegroundColor Green
        } else {
            Write-Host "⚠️  $model com problema: $output" -ForegroundColor Red
        }
    } catch {
        Write-Host "⚠️  $model com problema: $_" -ForegroundColor Red
    }
    Start-Sleep -Seconds 2
}

Write-Host ""
Write-Host "🎉 Setup Ollama otimizado concluído!" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Resumo dos modelos instalados:" -ForegroundColor Cyan
Write-Host "  • llama3.1:8b-instruct-q5_K_M - Principal (recomendado)" -ForegroundColor White
Write-Host "  • codellama:7b-instruct-q5_K_M - Código" -ForegroundColor White
Write-Host "  • phi3:14b-instruct-q4_K_M - Grande contexto" -ForegroundColor White
Write-Host "  • mistral:7b-instruct-q5_K_M - Alternativa" -ForegroundColor White
Write-Host "  • neural-chat:7b-v3.3-q5_K_M - Chat" -ForegroundColor White
Write-Host ""
Write-Host "💡 Dicas de uso:" -ForegroundColor Yellow
Write-Host "  • Use llama3.1:8b para tarefas gerais" -ForegroundColor White
Write-Host "  • Use codellama:7b para código" -ForegroundColor White
Write-Host "  • Use phi3:14b para contextos longos" -ForegroundColor White
Write-Host "  • Monitore VRAM com: nvidia-smi" -ForegroundColor White
Write-Host ""
Write-Host "🚀 Pronto para usar com Janus!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Próximos passos:" -ForegroundColor Cyan
Write-Host "  1. Reinicie o backend: docker-compose restart janus-api"
Write-Host "  2. Teste no frontend: http://localhost:4201"
Write-Host "  3. Monitore performance: nvidia-smi"