#!/usr/bin/env bash
# PC2 Quick Reference - i9-13900F + 64GB + 4060 Ti 16GB

cat << 'EOF'

╔═══════════════════════════════════════════════════════════════════════════════╗
║                    JANUS PC2 HARDWARE REFERENCE CARD                          ║
║           Intel i9-13900F + 64GB DDR5-5600 + RTX 4060 Ti 16GB                 ║
╚═══════════════════════════════════════════════════════════════════════════════╝


┌─────────────────────────────────────────────────────────────────────────────┐
│ 📋 QUICK START                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

1. Copy environment template:
   cp .env.pc2.example .env.pc2

2. Edit with your secrets:
   nano .env.pc2

3. Start services:
   docker compose -f docker-compose.pc2.yml up -d

4. Monitor startup:
   docker compose -f docker-compose.pc2.yml logs -f


┌─────────────────────────────────────────────────────────────────────────────┐
│ 🎯 SERVICE ALLOCATION                                                       │
└─────────────────────────────────────────────────────────────────────────────┘

Neo4j (Graph Database)
  ├─ Cores:      10 (cpuset 0-9: 8 P-cores + 2 E-cores)
  ├─ Memory:     20GB heap + 12GB page cache (22GB limit)
  ├─ Purpose:    Knowledge graph, entity relationships
  └─ Port:       7687 (Bolt), 7474 (HTTP)

Qdrant (Vector Search)
  ├─ Cores:      6 (cpuset 10-15: E-cores)
  ├─ Memory:     12GB (in-memory HNSW)
  ├─ Purpose:    Semantic search, embeddings
  └─ Port:       6333 (API), 6334 (gRPC)

Ollama (LLM Inference)
  ├─ Cores:      8 (cpuset 16-23: E-cores) + GPU
  ├─ Memory:     20GB RAM + 16GB VRAM (4060 Ti)
  ├─ Purpose:    Local model inference, token generation
  ├─ Port:       11434 (HTTP)
  └─ Models:     Load up to 2 simultaneously (~15GB)


┌─────────────────────────────────────────────────────────────────────────────┐
│ ⚡ CPU CORE MAPPING (i9-13900F)                                             │
└─────────────────────────────────────────────────────────────────────────────┘

                  P-cores (Performance)      E-cores (Efficiency)
                  3.0-5.6 GHz                2.5-4.3 GHz
                       │                          │
    ┌──────────────────┼──────────────────────────┼──────────────┐
    │ 0  1  2  3  4  5  6  7 │ 8  9 │10 11 12 13 14 15│16 17 18 19 20 21 22 23│
    └──────────────────┼──────────────────────────┼──────────────┘
         Neo4j (8)        Neo4j Qdrant (6)        Ollama (8)
                          (2)

Distribution:
  • Neo4j:   Cores 0-9   (P-core dominant for low-latency queries)
  • Qdrant:  Cores 10-15 (E-core efficient for vectorization)
  • Ollama:  Cores 16-23 (E-core + GPU for inference)


┌─────────────────────────────────────────────────────────────────────────────┐
│ 💾 MEMORY ALLOCATION (64GB DDR5)                                            │
└─────────────────────────────────────────────────────────────────────────────┘

Total: 64 GB DDR5-5600

  Neo4j:
    • Heap:          20 GB (JVM objects, indexes)
    • Page Cache:    12 GB (graph node/relationship data)
    └─ Total:        32 GB (soft limit)

  Qdrant:
    • Storage:       12 GB (vector indexes, in-memory)
    └─ Total:        12 GB

  Ollama:
    • RAM (CPU):     20 GB (context window, attention buffer)
    • VRAM (GPU):    16 GB (4060 Ti max, shared models)
    └─ Total:        36 GB

  System/Reserved:
    • OS kernel:     ~2 GB
    • Page tables:   ~1 GB
    • Buffers:       ~1 GB
    └─ Total:        ~4 GB

Memory Headroom: ~8 GB (for peak loads and swapping)


┌─────────────────────────────────────────────────────────────────────────────┐
│ 🎮 GPU SPECIFICATIONS (RTX 4060 Ti)                                         │
└─────────────────────────────────────────────────────────────────────────────┘

GPU Memory:        16 GB GDDR6 (128-bit bus, 432 GB/s bandwidth)
CUDA Cores:        2560
Tensor Float 32:   ~10 TFLOPs

Recommended Model Sizes:
  ├─ 7B params:    ~4-5 GB VRAM (e.g., mistral, neural-chat)
  ├─ 13B params:   ~8-9 GB VRAM (e.g., ministral-3:14b)
  ├─ 20B params:   ~11 GB VRAM (e.g., gpt-oss:20b)
  └─ 35B+ params:  ❌ Exceeds 16GB (requires quantization or MPS)

Loading Strategy:
  • Maximum 2 models loaded simultaneously
  • Example: gpt-oss:20b (11GB) + deepseek-coder:6.7b (4GB) = 15GB
  • Keep-alive: 30 minutes (auto-unload after 30min idle)


┌─────────────────────────────────────────────────────────────────────────────┐
│ 🔥 PERFORMANCE MODES                                                        │
└─────────────────────────────────────────────────────────────────────────────┘

BALANCED (Default - Recommended)
  Use this for most workloads

  NEO4J_HEAP_MAX=20G
  QDRANT_MEM_LIMIT=12g
  OLLAMA_NUM_PARALLEL=1
  OLLAMA_KEEP_ALIVE=30m

  ✅ Pros:  Safe, stable, leaves headroom
  ❌ Cons:  Not maximum throughput


AGGRESSIVE (High Performance)
  Use when system is dedicated to these services

  NEO4J_HEAP_MAX=25G
  QDRANT_MEM_LIMIT=16g
  OLLAMA_NUM_PARALLEL=2
  OLLAMA_KEEP_ALIVE=60m

  ✅ Pros:  Maximum throughput, larger caches
  ❌ Cons:  Risk of swapping, less headroom


CONSERVATIVE (Stability)
  Use for shared systems or mixed workloads

  NEO4J_HEAP_MAX=16G
  QDRANT_MEM_LIMIT=10g
  OLLAMA_NUM_PARALLEL=1
  OLLAMA_KEEP_ALIVE=10m

  ✅ Pros:  Stable under load, predictable
  ❌ Cons:  Slower inference, less caching


┌─────────────────────────────────────────────────────────────────────────────┐
│ 📊 MONITORING                                                               │
└─────────────────────────────────────────────────────────────────────────────┘

Real-time GPU metrics:
  nvidia-smi dmon -s pucm

Container resource usage:
  docker stats --no-stream --no-stream

CPU affinity check:
  docker inspect janus_neo4j_pc2 | grep CpusetCpus
  docker inspect janus_qdrant_pc2 | grep CpusetCpus
  docker inspect janus_ollama_pc2 | grep CpusetCpus

Ollama running models:
  curl http://localhost:11434/api/tags | jq

Qdrant collections:
  curl -H "api-key: YOUR_KEY" http://localhost:6333/collections | jq


┌─────────────────────────────────────────────────────────────────────────────┐
│ ⏱️  STARTUP TIMES                                                            │
└─────────────────────────────────────────────────────────────────────────────┘

First Boot (with model downloads):
  • Neo4j init:          ~30-60s
  • Qdrant init:         ~10-20s
  • Ollama init:         ~5-10s
  • Model download:      ~10-15m (network-dependent)
  └─ TOTAL:              ~20-30 minutes

Warm Start (models cached):
  • Neo4j startup:       ~30-45s
  • Qdrant startup:      ~10-15s
  • Ollama startup:      ~30-60s
  └─ TOTAL:              ~2-3 minutes


┌─────────────────────────────────────────────────────────────────────────────┐
│ 🧪 PERFORMANCE TUNING TIPS                                                  │
└─────────────────────────────────────────────────────────────────────────────┘

Neo4j Slow Queries:
  PROFILE MATCH (n:Node) RETURN n LIMIT 1000
  → Analyze execution plans, add indexes on frequently filtered properties

Qdrant High Latency:
  curl http://localhost:6333/collections → check vector count
  → If > 10M vectors, consider increasing memory or sharding

Ollama Out of Memory:
  docker stats → Watch VRAM usage
  → Reduce OLLAMA_NUM_PARALLEL or OLLAMA_KEEP_ALIVE

System Swapping:
  vmstat 1 10 → Check si/so columns
  → Reduce memory allocation or restart services


┌─────────────────────────────────────────────────────────────────────────────┐
│ 🔗 PC1 ↔ PC2 CONNECTIVITY                                                   │
└─────────────────────────────────────────────────────────────────────────────┘

Set in PC1's .env file:
  NEO4J_URI=bolt://PC2_TAILSCALE_IP:7687
  QDRANT_HOST=PC2_TAILSCALE_IP
  QDRANT_PORT=6333
  OLLAMA_HOST=http://PC2_TAILSCALE_IP:11434

Get PC2 Tailscale IP:
  tailscale ip -4

Test connectivity from PC1:
  curl bolt://PC2_TAILSCALE_IP:7687
  curl http://PC2_TAILSCALE_IP:6333/health
  curl http://PC2_TAILSCALE_IP:11434/api/tags


┌─────────────────────────────────────────────────────────────────────────────┐
│ 📌 HARDWARE LIMITS & BOTTLENECKS                                             │
└─────────────────────────────────────────────────────────────────────────────┘

Memory Bandwidth:
  DDR5-5600 @ 2-channel = ~89 GB/s (theoretical)
  → Neo4j loves bandwidth (many pointer chases)
  → Qdrant utilizes fully (HNSW distance computation)
  → GPU: 432 GB/s (5x higher, excellent for inference)

CPU Cache:
  L1:  32 KB/core (low latency for hot loops)
  L2:  256 KB/core (per-core private)
  L3:  36 MB shared (8 P-cores heavily use this)
  → Neo4j benefits most (graph traversal)
  → Qdrant moderate (vector operations)
  → Ollama low (working set in main memory)

GPU Bottlenecks:
  • Model loading: PCIe Gen 4 x16 (64 GB/s) - fast
  • Inference: VRAM bandwidth (432 GB/s) - saturates easily
  • Large batch sizes: CUDA cores (2560) - becomes compute-bound

Optimal Configuration:
  ✅ Do: Load 2 models, run 1 inference at a time
  ❌ Don't: Load 4 models or run parallel inference


┌─────────────────────────────────────────────────────────────────────────────┐
│ 🚀 NEXT STEPS                                                               │
└─────────────────────────────────────────────────────────────────────────────┘

1. Configure .env.pc2 with secure passwords
2. Start with BALANCED mode: docker compose -f docker-compose.pc2.yml up -d
3. Monitor for 24 hours: docker stats, nvidia-smi dmon
4. Adjust memory/CPU allocation if needed
5. Set up monitoring (Prometheus, Grafana)
6. Configure PC1 to connect via Tailscale


For detailed guide, see: ./scripts/ops/pc2-tuning-guide.sh

EOF
