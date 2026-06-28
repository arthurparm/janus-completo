# Project Memory Index

## Purpose

These persistent knowledge files provide AI agents with deep, contextual understanding of the Janus monorepo architecture, runtime behavior, operational practices, and risk landscape. They are designed to reduce context-switching, prevent costly mistakes, and accelerate onboarding for any AI agent working on the codebase. Each file captures a distinct domain of knowledge that would otherwise require scanning hundreds of source files to reconstruct.

## Table of Contents

| File | Description |
|---|---|
| [CODEBASE_MAP.md](file:///h:/repos/janus-completo/CODEBASE_MAP.md) | Full navigation map of the monorepo: directory structure, data flow diagrams, design patterns, backend and frontend navigation maps, and key architectural principles. |
| [BACKEND_RUNTIME.md](file:///h:/repos/janus-completo/BACKEND_RUNTIME.md) | Deep backend analysis covering all 10 major subsystems: Kernel lifecycle, Hybrid Brain/LLM Router, Multi-Agent System, RAG/Knowledge, Neo4j graph, Message Broker, Memory, Evolution, Security, Observability, and Tool Executor. |
| [FRONTEND_ANGULAR.md](file:///h:/repos/janus-completo/FRONTEND_ANGULAR.md) | Deep frontend analysis: Angular 20 standalone architecture, auth system, SSE chat streaming, global state, interceptors, WebRTC, observability dashboard, admin autonomy panel, and build/deploy pipeline. |
| [OPS_QA.md](file:///h:/repos/janus-completo/OPS_QA.md) | Deep operational analysis: PC1/PC2 split deployment, test structure, QA tooling, offline eval gate, Docker Compose architecture with resource limits, secret validator, URL safety egress policy, and rate limiting. |
| [AUTONOMY_RISK.md](file:///h:/repos/janus-completo/AUTONOMY_RISK.md) | Deep autonomy and risk analysis: Self-Study loop, EvolutionManager, ReflectorAgent, SafeEvolutionManager with JanusLab, risk assessment matrix per component, and unaddressed security boundaries. |

## How to Use

1. **Before making changes**: Read the relevant memory file(s) for your domain. For a full-stack change, start with CODEBASE_MAP.md, then read the domain-specific file.
2. **When investigating issues**: Use BACKEND_RUNTIME.md to trace endpoint -> service -> repository -> core paths. Use FRONTEND_ANGULAR.md to understand component hierarchy and data flow.
3. **For deployment and validation**: Consult OPS_QA.md for the correct boot order, quality gates, and validation commands.
4. **For autonomy and evolution work**: Read AUTONOMY_RISK.md to understand the safety mechanisms, risk classification, and unaddressed boundaries.
5. **Keep in sync**: These files summarize the codebase at a point in time. If you discover discrepancies, update the relevant file and update the Last Updated timestamp below.

## Last Updated

2026-06-22
