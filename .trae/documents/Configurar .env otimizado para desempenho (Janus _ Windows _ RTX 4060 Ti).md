# Visão Geral
- O backend Python carrega `janus/app/.env` automaticamente via Pydantic (`janus/app/config.py:10`). O frontend Angular/Vite lê `import.meta.env` de `.env` no build.
- Vamos fornecer um `.env` completo com valores seguros e ajustados ao i9‑13900F (24C/32T), 64GB DDR5 5600MHz e RTX 4060 Ti, priorizando chaves realmente usadas pelo Janus e incluindo variáveis extras (CUDA/Windows) com comentários sobre efeitos e limitações.
- Onde cada variável impacta:
  - Threads/pools: `LLM_EXECUTOR_MAX_WORKERS` e pool HTTP (`janus/app/config.py:86`, `139-141`).
  - Ollama (CPU/GPU): `OLLAMA_*` aplicados no LLM (`janus/app/config.py:165-170`).
  - Cache/memória: `MEMORY_*`, `CONTEXT_WEB_*` (`janus/app/config.py:54-61`, `270-271`).
  - SSE/latência: `CHAT_*` usados via `os.getenv` em serviços de chat (`janus/app/services/chat_service.py`).
  - Observabilidade: `OTEL_*`, `LOG_SAMPLING_RATE` (`janus/app/config.py:286-291`).

# Limitações Importantes
- `.env` não altera afinidade de CPU, prioridade de processo ou plano de energia do Windows por si só; isso requer comandos/sistema. Incluiremos chaves descritivas para futura automação e instruções nos comentários.
- `OLLAMA_GPU_LAYERS` é altamente dependente do modelo/quantização; manteremos auto (omitido) para evitar OOM entre variantes 8GB e 16GB da 4060 Ti.

# Proposta de Conteúdo para `janus/app/.env`
```env
# ===== Ambiente e Identidade =====
ENVIRONMENT=production
APP_NAME=Janus
APP_VERSION=0.1.0
AGENT_IDENTITY_NAME=Janus
IDENTITY_ENFORCEMENT_ENABLED=true

# ===== Paralelização e Multithreading =====
# Máximo de workers para executores de LLM; 8 dá boa latência/concurrency no i9‑13900F
LLM_EXECUTOR_MAX_WORKERS=8
# Threads de CPU para Ollama/llama.cpp; recomendação: ~cores físicos totais (24)
OLLAMA_NUM_THREAD=24
# Tamanho máximo do pool de clientes LLM (reuso de conexões/objetos)
LLM_POOL_MAX_SIZE=8
LLM_POOL_TTL_SECONDS=3600

# Variáveis de threads de bibliotecas científicas (aplicadas a libs como OpenMP/MKL)
# Ajuste para evitar over-subscription; alinhar a núcleos físicos
OMP_NUM_THREADS=24
MKL_NUM_THREADS=24
NUMEXPR_NUM_THREADS=24

# Afinidade e prioridade (somente descritivo; requer aplicação no launcher/OS)
# CPU_AFFINITY_MASK=0xFFFFFFFF      # Exemplo: usa 32 CPUs lógicas; aplique via script
# PROCESS_PRIORITY=high             # Sugerido: high; aplique via start /HIGH ou psutil

# ===== Otimizações para GPU (RTX 4060 Ti) =====
# Host do servidor Ollama local (GPU)
OLLAMA_HOST=http://localhost:11434
# Manter modelos quentes por mais tempo para reduzir cold-start
OLLAMA_KEEP_ALIVE=60m
# Contexto e batch; maiores valores aumentam throughput e uso de VRAM
OLLAMA_NUM_CTX=4096
OLLAMA_NUM_BATCH=64
# Omitir OLLAMA_GPU_LAYERS para autoajuste conforme VRAM/modelo
# OLLAMA_GPU_LAYERS=                # auto (não definir)

# CUDA runtime (efeito depende do driver/runtime)
# Aumenta conexões internas para melhor concorrência
CUDA_DEVICE_MAX_CONNECTIONS=32
# Cache de código JIT do driver (bytes); 512MB reduz recompilações
CUDA_CACHE_MAXSIZE=536870912
# Visibilidade de dispositivos (útil em containers); não afeta host direto
NVIDIA_VISIBLE_DEVICES=all

# ===== Memória DDR5 / Buffers / Cache =====
# Aumenta capacidade de memória de curto prazo do app
MEMORY_SHORT_TTL_SECONDS=900
MEMORY_SHORT_MAX_ITEMS=1024
MEMORY_SHORT_SCAN_MAX_ITEMS=512
MEMORY_MAX_CONTENT_CHARS=40000
# Cache de contexto web (crawl/RAG)
CONTEXT_WEB_CACHE_TTL_SECONDS=3600
CONTEXT_WEB_CACHE_MAX_ITEMS=2048
# Resposta de LLM em MsgPack para menor overhead
LLM_RESPONSE_CACHE_USE_MSGPACK=true

# ===== Timeouts e Retentativas =====
LLM_DEFAULT_TIMEOUT_SECONDS=60
LLM_RETRY_MAX_ATTEMPTS=3
LLM_RETRY_INITIAL_BACKOFF_SECONDS=0.5
LLM_RETRY_MAX_BACKOFF_SECONDS=5.0
TIMEOUT_AUTO_TUNE_ENABLED=true
TIMEOUT_AUTO_TUNE_PERCENTILE=0.95
TIMEOUT_AUTO_TUNE_PAD_SECONDS=0.5

# ===== SSE/Chat (latência/estabilidade) =====
CHAT_MAX_MESSAGE_BYTES=1048576
CHAT_DEFAULT_TIMEOUT_SECONDS=90
CHAT_HEARTBEAT_INTERVAL_SECONDS=10
CHAT_SSE_PROTOCOL_VERSION=2
# Deprecar parciais antigos após X segundos para reduzir backlog
CHAT_SSE_PARTIAL_DEPRECATE_AT=120
# Circuit breaker de chat
CHAT_CB_COOLDOWN_SECONDS=30
CHAT_CB_FAILURE_THRESHOLD=5

# ===== OpenAI/Gemini HTTP Pooling =====
OPENAI_HTTP_MAX_CONNECTIONS=200
OPENAI_HTTP_MAX_KEEPALIVE=50
OPENAI_HTTP_TIMEOUT_SECONDS=60
# Ajuste semelhante pode ser feito para Gemini se necessário

# ===== Modelos e Orquestração (Ollama) =====
OLLAMA_ORCHESTRATOR_MODEL=llama3.1:8b
OLLAMA_CODER_MODEL=llama3.1:8b
OLLAMA_CURATOR_MODEL=llama3.1:8b

# ===== Observabilidade e Logs =====
OTEL_ENABLED=true
OTEL_OTLP_ENDPOINT=http://localhost:4318
OTEL_SERVICE_NAME=janus-backend
LOG_SAMPLING_RATE=1.0
AUDIT_PURGE_INTERVAL_SECONDS=3600
AUDIT_RETENTION_DAYS=30

# ===== Estáticos / Frontend (Vite) =====
SERVE_STATIC_FILES=true
STATIC_FILES_DIR=front/janus-angular/public
# Frontend: SSE e métricas de UX
VITE_API_BASE_URL=http://localhost:8000
VITE_FEATURE_SSE=true
VITE_UX_METRICS_SAMPLING=1.0
VITE_SSE_RETRY_MAX_SECONDS=30
```

# Racional de Valores
- i9‑13900F: `LLM_EXECUTOR_MAX_WORKERS=8` equilibra latência/concurrency sem saturar E‑cores; `OLLAMA_NUM_THREAD=24` alinha com núcleos físicos totais. `OMP/MKL/NUMEXPR=24` evita over‑subscription em libs nativas.
- RTX 4060 Ti: manter `OLLAMA_GPU_LAYERS` em auto previne OOM em 8GB e aproveita a variante 16GB. `NUM_BATCH=64` melhora throughput; reduza para 32 se houver OOM.
- DDR5 64GB: aumentar limites de cache/buffers (`MEMORY_*`, `CONTEXT_WEB_*`) melhora hit‑rate sem pressionar GC.
- HTTP pooling: `OPENAI_HTTP_MAX_CONNECTIONS=200` e `KEEPALIVE=50` aumentam vazão sob carga alta; ajuste conforme observabilidade.

# Windows: Energia, Afinidade e Prioridade
- Plano de energia: aplique fora do `.env` com `powercfg` (admin):
  - `powercfg /S 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c` (High Performance)
- Afinidade/prioridade: usar launcher (PowerShell/psutil) para ler `CPU_AFFINITY_MASK` e `PROCESS_PRIORITY` e aplicar ao processo.
- Prioridade de E/S: similarmente via `SetPriorityClass`/`SetFileInformationByHandle` em um wrapper; `.env` serve como fonte de configuração.

# Validação Proposta
- Medir latência média/p95 por rota LLM e throughput de SSE antes/depois; observar OOM.
- Monitorar `OTEL` traces e erro por segundo; ajustar `NUM_BATCH`/threads conforme picos.

# Próximos Passos
- Após aprovação, vou atualizar `janus/app/.env` com o conteúdo acima.
- Se desejar afinidade/prioridade reais no Windows, proponho um pequeno launcher que aplica máscaras/prioridades lendo as chaves comentadas do `.env`. 