# Knowledge Space MVP

## Objetivo
Fluxo mínimo para trabalhar com conhecimento longo, sequencial e isolado por fonte sem misturar obras, edições ou coleções.

## Fluxo cliente
1. Criar o `knowledge space`.
2. Anexar um documento já ingerido ao espaço.
3. Publicar a consolidação estrutural.
4. Consultar o status até o espaço ficar `ready` ou `partial`.
5. Consultar o espaço em `quick_lookup` ou `canonical_answer`.
6. Enviar `knowledge_space_id` no chat para o roteamento automático do fluxo principal.

## Endpoints
### Criar espaço
`POST /api/v1/knowledge/spaces`

```json
{
  "name": "Livro de Álgebra Linear",
  "user_id": "55",
  "source_type": "book",
  "source_id": "isbn-123",
  "edition_or_version": "3a-edicao",
  "language": "pt-BR"
}
```

### Associar documento
`POST /api/v1/knowledge/spaces/{knowledge_space_id}/documents/{doc_id}/attach`

```json
{
  "user_id": "55",
  "source_type": "book",
  "edition_or_version": "3a-edicao"
}
```

### Publicar consolidação
`POST /api/v1/knowledge/spaces/{knowledge_space_id}/consolidate`

```json
{
  "user_id": "55",
  "limit_docs": 20
}
```

Resposta esperada:

```json
{
  "message": "Consolidação estrutural publicada.",
  "stats": {
    "status": "ok",
    "task_id": "uuid",
    "status_url": "/api/v1/knowledge/spaces/ks:55:abc?user_id=55"
  }
}
```

### Consultar status
`GET /api/v1/knowledge/spaces/{knowledge_space_id}?user_id=55`

Campos principais:
- `consolidation_status`
- `documents_total`
- `documents_indexed`
- `documents_processing`
- `chunks_total`
- `chunks_indexed`
- `progress`

### Consultar espaço
`POST /api/v1/knowledge/spaces/{knowledge_space_id}/query`

```json
{
  "user_id": "55",
  "question": "Qual a sequência recomendada do conteúdo?",
  "mode": "auto",
  "limit": 5
}
```

Resposta mínima:

```json
{
  "answer": "Base consolidada indica: ...",
  "mode_used": "canonical_answer",
  "base_used": "consolidated",
  "source_scope": {
    "knowledge_space_id": "ks:55:abc",
    "consolidation_status": "ready"
  },
  "citations": [],
  "confidence": 0.91,
  "gaps_or_conflicts": []
}
```

## Chat principal
O chat principal aceita `knowledge_space_id` em:
- `POST /api/v1/chat/message`
- `GET /api/v1/chat/stream/{conversation_id}`

Payload REST:

```json
{
  "conversation_id": "123",
  "message": "Monte um plano de estudo do capítulo 1 ao 4.",
  "role": "orchestrator",
  "priority": "high_quality",
  "user_id": "55",
  "knowledge_space_id": "ks:55:abc"
}
```

Comportamento esperado:
- perguntas pontuais tendem a `quick_lookup`;
- perguntas sequenciais, processuais ou com dependência tendem a `canonical_answer`;
- se o espaço ainda não estiver consolidado, a resposta volta em `chunk_only` com CTA para consolidação.
