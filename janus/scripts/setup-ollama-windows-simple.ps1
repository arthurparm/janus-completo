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

# Verificar GPU
try {
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>$null
    if ($?) {
        Write-Host "✅ GPU NVIDIA detectada" -ForegroundColor Green
    } else {
        Write-Host "⚠️  GPU NVIDIA não detectada. Usando CPU" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  nvidia-smi não encontrado. Usando CPU" -ForegroundColor Yellow
}

Write-Host "📦 Baixando modelos otimizados para 16GB VRAM..." -ForegroundColor Cyan

# Modelos otimizados para 16GB VRAM
$models = @(
    "llama3.1:8b-instruct-q5_K_M",
    "codellama:7b-instruct-q5_K_M",
    "phi3:14b-instruct-q4_K_M"
)

foreach ($model in $models) {
    Write-Host "⬇️  Baixando $model..." -ForegroundColor Yellow
    ollama pull $model
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ $model baixado com sucesso" -ForegroundColor Green
    } else {
        Write-Host "❌ Erro ao baixar $model" -ForegroundColor Red
    }
}

Write-Host "🔧 Configurando Ollama..." -ForegroundColor Cyan

# Criar diretório de configuração
$configDir = "$env:USERPROFILE\.ollama"
if (!(Test-Path $configDir)) {
    New-Item -ItemType Directory -Path $configDir -Force
}

# Configuração otimizada
$configContent = @"
{
    "num_ctx": 8192,
    "num_batch": 128,
    "num_gpu": 48,
    "num_thread": 32,
    "keep_alive": "120m"
}
"@

$configContent | Out-File -FilePath "$configDir\config.json" -Encoding UTF8
Write-Host "✅ Configuração salva" -ForegroundColor Green

Write-Host "🧪 Testando modelos..." -ForegroundColor Cyan
foreach ($model in $models) {
    Write-Host "📝 Testando $model..." -ForegroundColor Yellow
    $output = ollama run $model "Hello" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ $model funcionando" -ForegroundColor Green
    } else {
        Write-Host "⚠️  $model com problema" -ForegroundColor Red
    }
    Start-Sleep -Seconds 1
}

Write-Host ""
Write-Host "🎉 Setup concluído!" -ForegroundColor Green
Write-Host "📊 Modelos instalados: llama3.1:8b, codellama:7b, phi3:14b" -ForegroundColor Cyan
Write-Host "💡 Use: ollama run llama3.1:8b-instruct-q5_K_M" -ForegroundColor Yellow