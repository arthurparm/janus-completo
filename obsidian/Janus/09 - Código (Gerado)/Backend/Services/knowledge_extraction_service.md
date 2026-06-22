---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/knowledge_extraction_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# knowledge_extraction_service

## Arquivos-fonte
- `backend/app/services/knowledge_extraction_service.py`

## Fluxos de uso (chamadores)
- `backend/app/core/workers/knowledge_consolidator_worker.py`

## Símbolos
- class: `KnowledgeExtractionService`
  - Serviço responsável por extrair conhecimento estruturado (entidades, relacionamentos)
de texto bruto usando LLMs.
- method: `KnowledgeExtractionService.__init__(self)`
- method: `KnowledgeExtractionService.is_llm_temporarily_unavailable(self)` -> `bool`
- method: `KnowledgeExtractionService.llm_unavailable_remaining_seconds(self)` -> `float`
- method: `KnowledgeExtractionService._ensure_llm(self)`
- method: `KnowledgeExtractionService.extract_from_text(self, text: str, metadata: dict[str, Any] = None)` -> `dict[str, Any]`
  - Extrai entidades e relacionamentos de um texto.
- method: `KnowledgeExtractionService._parse_json_response(self, content: str)` -> `dict[str, Any]`
  - Tenta parsear a resposta do LLM como JSON, lidando com blocos de código markdown.
- function: `get_knowledge_extraction_service()`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
