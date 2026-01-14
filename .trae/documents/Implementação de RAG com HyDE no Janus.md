# Plano de Implementação de RAG com HyDE (Hypothetical Document Embeddings)

Este plano detalha a integração da técnica HyDE ao sistema Janus, focando especificamente no módulo `GraphRAG` (`NativeGraphRAG`).

## 1. Modificação do GraphRAG Core
O arquivo `janus/app/core/memory/graph_rag_core.py` será atualizado para incorporar o fluxo HyDE.

*   **Importação Dinâmica:** Utilizaremos `generate_hypothetical_answer` do serviço existente `app.services.reasoning_rag_service` dentro do método `query` para evitar dependências circulares (`core` <-> `services`).
*   **Lógica de Fluxo:**
    1.  Verificar se `settings.RAG_HYDE_ENABLED` está ativo.
    2.  Se ativo, invocar o LLM para gerar uma resposta hipotética baseada na pergunta do usuário.
    3.  Substituir a consulta original pela resposta hipotética (ou utilizá-la como contexto enriquecido) na chamada ao `HybridRetriever`.
    4.  Manter o fallback para a pergunta original caso a geração falhe ou HyDE esteja desativado.

## 2. Script de Validação e Benchmark
Criaremos um script dedicado em `janus/scripts/validate_rag_hyde.py` para validar a implementação e comparar resultados.

*   **Funcionalidades:**
    *   Executar consultas de teste com e sem HyDE.
    *   Exibir a "Resposta Hipotética" gerada para inspeção qualitativa.
    *   Comparar os nós recuperados pelo `HybridRetriever` em ambos os cenários.
    *   Medir a latência adicional introduzida pela etapa de geração.

## 3. Documentação Técnica
Criaremos o arquivo `janus/docs/RAG_HYDE.md` contendo:
*   Explicação teórica do HyDE no contexto do Janus.
*   Instruções de configuração (variáveis de ambiente, flags).
*   Guia de uso e interpretação de logs.
*   Análise de trade-offs (latência vs. precisão semântica).

## 4. Estrutura de Arquivos Afetados
*   `janus/app/core/memory/graph_rag_core.py` (Modificação)
*   `janus/scripts/validate_rag_hyde.py` (Novo)
*   `janus/docs/RAG_HYDE.md` (Novo)

Esta abordagem cumpre todos os requisitos: utiliza o módulo de geração existente, integra-se ao pipeline de embeddings do GraphRAG sem alterar a infraestrutura do Neo4j e fornece as ferramentas de validação solicitadas.
