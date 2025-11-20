## Status
- Dedupe de conceitos implementado com `RELATES_TO` nos dois sentidos: `janus/app/repositories/knowledge_repository.py:203-246`.
- Dedupe de funções/classes e arquivos implementados e usando `GraphRelationship.*`: `knowledge_repository.py:267-352` e `knowledge_repository.py:354-403`.
- Métricas e auditoria presentes nos dedupes: contadores e eventos (`graph_dedupe_*`, `record_audit_event_direct`).
- Registro de tipos de relacionamento e constraints ativo: `knowledge_repository.py:640-664` e chamado no início do consolidator: `janus/app/core/workers/knowledge_consolidator.py:36-38`.
- Pendências menores: duplicidade de `find_entity_relationships` (`knowledge_repository.py:453-479` e `523-547`) e import duplicado (`knowledge_repository.py:6` e `8`).

## O que farei para concluir a Fase 0
1. Remover a duplicidade de `find_entity_relationships`, mantendo a versão com navegação e filtros atuais.
2. Eliminar o import duplicado de `record_audit_event_direct`.
3. Adicionar um teste rápido de integridade do dedupe (conceitos, funções e arquivos) para garantir não regressão.

## Entregável
- Repositório de conhecimento sem duplicidades de função/import, dedupe validado e estável, mantendo métricas e auditoria existentes.