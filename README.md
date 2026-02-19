# Janus - Arquiteto de Software Autônomo e Assistente Inteligente

![Status](https://img.shields.io/badge/Status-Active-brightgreen)
![Version](https://img.shields.io/badge/Version-0.5.44-blue)
![License](https://img.shields.io/badge/License-MIT-green)

O **Janus** é um sistema agêntico avançado projetado para atuar como um arquiteto de software autônomo e assistente inteligente. Ele combina o poder de múltiplos modelos de linguagem (LLMs) com memória de longo prazo (vetorial e semântica) e capacidade de execução de ferramentas para auxiliar no desenvolvimento de software e tomada de decisões.

---

## 📚 Documentação Oficial

A documentação completa do projeto foi atualizada e está disponível na pasta `docs/`. Recomendamos a leitura na seguinte ordem:

1.  **[Manual de Arquitetura](docs/MANUAL_ARQUITETURA.md)**: Entenda como o sistema funciona por dentro (Frontend, Backend, Workers, Memória).
2.  **[Manual de Operação e Instalação](docs/MANUAL_OPERACAO.md)**: Guia passo-a-passo para rodar o projeto (Docker e Local).
3.  **[Melhorias Possíveis e Análise Crítica](melhorias-possiveis.md)**: Uma visão honesta sobre o estado atual do código, débitos técnicos e oportunidades de evolução.

Além destes, a pasta `docs/` contém documentos gerados automaticamente (BMAD) que podem servir de referência adicional.

---

## 🚀 Funcionalidades Principais

*   **Agentes Especializados**: Orquestrador, Gerador de Código, Curador de Conhecimento, Auditor de Segurança e mais.
*   **Memória Bicameral**:
    *   **Episódica (Rápida)**: Busca vetorial (Qdrant) em logs de chat.
    *   **Semântica (Profunda)**: Grafo de conhecimento (Neo4j) construído automaticamente a partir das conversas.
*   **RAG Híbrido**: Recuperação Aumentada por Geração combinando busca vetorial e grafo para respostas precisas.
*   **Autonomia (OODA Loop)**: Capacidade de planejar e executar tarefas complexas em background (via RabbitMQ).
*   **Interface Moderna**: Frontend em Angular 20 com streaming real-time (SSE) e observabilidade integrada.

---

## 🛠️ Stack Tecnológico

O projeto é um **Monorepo** dividido em:

### Frontend (`front/`)
*   **Framework**: Angular 20
*   **Estilo**: TailwindCSS + Angular Material
*   **Estado**: Signals + RxJS
*   **Comunicação**: Server-Sent Events (SSE)

### Backend (`janus/`)
*   **API**: FastAPI (Python 3.11+)
*   **IA**: LangChain, LangGraph
*   **Infraestrutura**:
    *   **PostgreSQL**: Dados relacionais.
    *   **RabbitMQ**: Mensageria e filas de tarefas.
    *   **Redis**: Cache e Rate Limiting.
    *   **Neo4j**: Knowledge Graph.
    *   **Qdrant**: Vector Database.
    *   **Prometheus/Grafana**: Monitoramento.

---

## ⚡ Como Começar (Rápido)

Para rodar o sistema completo em containers:

1.  **Clone o repositório**:
    ```bash
    git clone https://github.com/seu-usuario/janus-completo.git
    cd janus-completo
    ```

2.  **Configure as Chaves de API**:
    Edite `janus/app/.env` e adicione sua `OPENAI_API_KEY` (ou outro provedor).

3.  **Suba o Ambiente**:
    ```bash
    docker compose up -d
    ```

4.  **Acesse**:
    *   **Frontend**: http://localhost:4200
    *   **API Docs**: http://localhost:8000/docs
    *   **Grafana**: http://localhost:3000

Para mais detalhes, consulte o **[Manual de Operação](docs/MANUAL_OPERACAO.md)**.

---

## 🤝 Contribuição

Contribuições são bem-vindas! Consulte o `docs/MANUAL_ARQUITETURA.md` para entender onde suas mudanças se encaixam.

## 📄 Licença

Este projeto está sob a licença MIT.
