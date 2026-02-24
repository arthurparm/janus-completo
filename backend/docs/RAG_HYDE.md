# RAG com HyDE (Hypothetical Document Embeddings)

## Visão Geral

O Janus implementa a técnica **HyDE** (Hypothetical Document Embeddings) para melhorar a precisão da recuperação de informações no seu módulo **GraphRAG**.

### O que é HyDE?

Em vez de usar a pergunta do usuário diretamente para buscar documentos similares, o HyDE:
1.  Usa um LLM para gerar uma **resposta hipotética** ideal para a pergunta.
2.  Calcula os embeddings (vetores) dessa resposta hipotética.
3.  Usa esses embeddings para buscar documentos reais no banco de dados.

**Benefício:** A resposta hipotética, mesmo que contenha alucinações factuais, geralmente possui estrutura e vocabulário muito mais próximos dos documentos relevantes do que a pergunta original curta.

## Implementação no Janus

A implementação está integrada ao `NativeGraphRAG` em `app/core/memory/graph_rag_core.py`.

### Fluxo de Dados

1.  **Entrada:** Pergunta do usuário.
2.  **Verificação:** Se `RAG_HYDE_ENABLED` for `True`.
3.  **Geração:** O serviço `app.services.reasoning_rag_service.generate_hypothetical_answer` é chamado.
4.  **Recuperação:** O texto gerado é passado para o `HybridRetriever` (Neo4j GraphRAG), que o utiliza para busca vetorial e/ou fulltext.
5.  **Síntese:** Os documentos recuperados são usados para gerar a resposta final.

### Configuração

A funcionalidade é controlada via variáveis de ambiente ou `app/config.py`:

*   `RAG_HYDE_ENABLED`: `True` ou `False` (Padrão: `True`)

## Como Validar

Um script de validação está disponível em `scripts/validate_rag_hyde.py`:

```bash
python scripts/validate_rag_hyde.py
```

Ao executar, observe os logs para confirmar que a geração HyDE está ocorrendo:
*   `Generating HyDE answer for query`
*   `Using HyDE query`

## Trade-offs

*   **Latência:** Adiciona uma chamada extra ao LLM antes da busca, aumentando o tempo total de resposta.
*   **Custo:** Consome tokens adicionais para gerar a resposta hipotética.
*   **Qualidade:** Geralmente melhora o recall para perguntas ambíguas ou que não compartilham palavras-chave diretas com os documentos.
