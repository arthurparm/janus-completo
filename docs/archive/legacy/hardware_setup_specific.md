# 🚀 Configuração Otimizada Janus - i9 13900F + 64GB + RTX 4060 Ti 16GB

## 📋 Resumo das Otimizações

Este setup é otimizado para aproveitar ao máximo seu hardware de alto desempenho:

### 💪 CPU i9 13900F (24 cores/32 threads)
- **32 threads** para processamento paralelo
- **16 workers** para LLM executor
- **Pool de 12 conexões** para reuso máximo

### 🎮 RTX 4060 Ti 16GB VRAM
- **Modelos grandes**: Llama 3.1 8B, Phi3 14B, CodeLlama 7B
- **8K contexto** para melhor compreensão
- **48 camadas GPU** para aceleração máxima
- **2GB CUDA cache** para performance

### 🏃‍♂️ 64GB DDR5
- **Cache expandido**: 3x mais itens em memória
- **TTL maior**: 30min de cache curto
- **6x mais cache web** para RAG

## 🔧 Arquivos de Configuração

### 1. Backend (.env)
```bash
# Copie o arquivo otimizado
cp janus/config/.env.optimized janus/config/.env

# Ou use o existente (já está bom)
cp janus/config/.env janus/config/.env.backup
```

### 2. Setup Ollama
```bash
# Execute o script de setup
bash janus/scripts/setup-ollama-optimized.sh

# Ou instale manualmente os modelos:
ollama pull llama3.1:8b-instruct-q5_K_M
ollama pull codellama:7b-instruct-q5_K_M
ollama pull phi3:14b-instruct-q4_K_M
```

### 3. Frontend (.env)
```bash
# Configure o frontend
echo "VITE_API_BASE_URL=http://localhost:8000" >> front/.env
```

## 🎯 Modelos Recomendados por Uso

| Uso | Modelo | VRAM | Performance |
|-----|--------|------|-------------|
| **Geral** | `llama3.1:8b-instruct-q5_K_M` | ~6GB | ⭐⭐⭐⭐⭐ Excelente |
| **Código** | `codellama:7b-instruct-q5_K_M` | ~5GB | ⭐⭐⭐⭐⭐ Excelente |
| **Contexto Longo** | `phi3:14b-instruct-q4_K_M` | ~8GB | ⭐⭐⭐⭐ Muito Bom |
| **Chat** | `neural-chat:7b-v3.3-q5_K_M` | ~5GB | ⭐⭐⭐⭐ Muito Bom |

## 📊 Monitoramento

### Verificar uso de recursos:
```bash
# GPU/VRAM
nvidia-smi

# CPU/RAM
htop  # ou top

# Logs do backend
docker logs janus_api

# Logs do Ollama
journalctl -u ollama -f
```

### Performance esperada:
- **Tempo de resposta**: 1-3 segundos (modelos 7-8B)
- **Throughput**: 50-100 tokens/segundo
- **Contexto**: 8K tokens
- **Memória RAM**: 20-30GB em uso
- **VRAM**: 10-14GB em uso

## 🚀 Iniciar o Sistema

```bash
# 1. Iniciar backend com Docker
docker-compose up -d

# 2. Verificar se está rodando
curl http://localhost:8000/healthz

# 3. Iniciar frontend
cd front && npm run start

# 4. Acessar
http://localhost:4201
```

## 🔍 Troubleshooting

### Se os eventos SSE não chegarem:
1. Verifique CORS: `CORS_ALLOW_ORIGINS` no .env
2. Confirme proxy: `proxy.conf.json` apontando para localhost:8000
3. Teste direto: `curl http://localhost:8000/api/v1/chat/stream/1?message=teste`

### Se Ollama não responder:
1. Verifique se está rodando: `ollama list`
2. Teste modelo: `ollama run llama3.1:8b "Hello"`
3. Confirme VRAM: `nvidia-smi`

### Performance lenta:
1. Reduza `OLLAMA_NUM_CTX` para 4096
2. Use modelos menores (q4 instead of q5)
3. Ajuste `LLM_EXECUTOR_MAX_WORKERS` para 8

## 💡 Dicas Extras

- **Monitore sempre**: Use `nvidia-smi` para VRAM e `htop` para RAM
- **Modelos quentes**: Configure `LLM_POOL_WARM_PROVIDERS` para manter modelos carregados
- **Contexto**: Aumente `OLLAMA_NUM_CTX` se precisar de mais contexto (usa mais VRAM)
- **Qualidade**: q5_K_M é sweet spot para qualidade/velocidade
- **Batch**: Aumente `OLLAMA_NUM_BATCH` para melhor throughput (usa mais VRAM)

Seu setup é excelente! Você deve conseguir rodar modelos de 7-14B com excelente performance. 🎉