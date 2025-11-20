## Status

* Dedupe de conceitos implementado com `RELATES_TO` nos dois sentidos e auditoria/métricas: `janus/app/repositories/knowledge_repository.py:202-264` (registro do tipo em `:221`, merges em `:231` e `:238`, contadores/auditoria em `:209`, `:251`, `:255`).

* Dedupe de funções/classes implementado com `CALLS/IMPLEMENTS` e auditoria/métricas: `:266-351`.

* Dedupe de arquivos com `RELATES_TO` e auditoria/métricas: `:353-402`.

* Contadores Prometheus para quarentena, mentions, dedupe e limpeza definidos: `:24-33`.

* Duplicidade de `find_entity_relationships` não aparece na versão atual; há apenas uma definição navegacional: `:495-519`.

## Ajustes Sugeridos

* Registrar globalmente tipos de relacionamento usados (`CALLS`, `IMPLEMENTS`, `RELATES_TO`) em um método de inicialização do repositório (opcional, melhora consistência).

* Acrescentar testes de integração rápidos para `dedupe_*` com grafo mínimo (garante não regressão).

## Próximos Passos (quando aprovado)

* Implementar registro central de tipos de relacionamento.

* Adicionar suíte de testes de dedupe com cenários de duplicatas e validação de reanexação.

* Expor um endpoint administrativo para `dedupe_report()` e health.

