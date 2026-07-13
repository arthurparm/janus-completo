# TODO_TECHNICAL_DEBT

## Dividas Priorizadas

| ID | Item | Impacto | Risco | Esforco | Prioridade | Evidencia |
|---|---|---|---|---|---|---|
| TD-001 | Triar uso de `any` em contratos frontend ligados a Health, chat e servicos API. | medio | medio | medio | P1 | Busca por `any` em `frontend/src/app`. |
| TD-002 | Triar blocos `pass` em servicos backend para diferenciar fallback intencional de erro silencioso. | medio | medio | medio | P1 | Busca por `pass$` em `backend/app`. |
| TD-003 | Consolidar comandos de validacao por tipo de mudanca nos arquivos de memoria e guias existentes. | medio | baixo | baixo | P2 | `AGENTS.md`, `OPS_QA.md` e workflows ja possuem comandos, mas ficam dispersos. |
| TD-004 | Investigar aviso de vulnerabilidades Dependabot reportado pelo GitHub no push anterior. | alto | medio | medio | P1 | Parcial: audit frontend removeu 1 critica direta em Vitest; ainda restam highs/moderates. |
| TD-005 | Atualizar Angular 20.3.x para patch seguro e validar build/testes. | alto | medio | medio | P1 | Concluido parcialmente: Angular runtime/build atualizados; audit caiu de 30 para 19 vulnerabilidades e highs de 15 para 4. |
| TD-006 | Triar `allow-scripts` pendentes do npm antes de aprovar scripts de instalacao. | medio | medio | baixo | P1 | `npm update vitest` reportou pacotes com install/postinstall pendentes. |
| TD-007 | Atualizar DOMPurify direto para patch seguro e validar Markdown/sanitizacao. | medio | baixo | baixo | P1 | Concluido: `dompurify` atualizado para `3.4.11`; audit caiu de 19 para 18 vulnerabilidades e removeu `dompurify` do mapa. |
| TD-008 | Avaliar remocao futura de APIs Angular deprecated (`@angular/animations`, `@angular/platform-browser-dynamic`). | medio | medio | medio | P2 | `npm update` reportou avisos de deprecacao desses pacotes. |
| TD-009 | Triar highs transientes restantes do audit frontend por cadeia de dependencia antes de upgrades major. | alto | medio | medio | P1 | `npm audit` ainda reporta highs em `@grpc/grpc-js`, `hono`, `protobufjs` e `ws`. |
| TD-010 | Executar contratos backend reais em Python 3.11/3.12 ou Docker oficial apos guardrail de runtime. | alto | medio | medio | P1 | Concluido parcialmente: `py -3.12 tooling/dev.py qa` passou completo; falta validacao Docker/PC1/PC2 real. |
| TD-011 | Validar boot full-stack PC2 -> PC1 com `python tooling/dev.py up` e diagnosticos. | alto | medio | medio | P1 | Concluido parcialmente: `py -3.12 tooling/dev.py up` passou; `doctor localhost` agora passou com `overall_ok=true`; compose focado manual ainda exige overrides locais. |
| TD-012 | Tornar o caminho LLM local operacional e mensuravel. | alto | medio | medio | P1 | Concluido para smoke local: `/api/v1/llm/invoke` e `/api/v1/chat/message` responderam via `ollama/gpt-oss:20b`. |
| TD-013 | Separar modo local e modo split no `tooling/dev.py doctor`. | medio | medio | baixo | P1 | Concluido: `quick_diagnostics.py` distingue `local` e `split`; testes e doctor real local passaram. |
| TD-014 | Validar `tooling/dev.py doctor --host localhost` e fluxo real de chat apos Docker Desktop voltar. | alto | medio | baixo | P1 | Concluido: Docker voltou, doctor local passou, auth local + chat/start + chat/message retornaram resposta via Ollama. |
| TD-015 | Reavaliar fallback local do rate limiter em ambiente multi-replica. | medio | medio | medio | P2 | Ciclo 9 ampliou fallback local para chat; isso preserva disponibilidade, mas nao e rate limit distribuido. |
| TD-016 | Fortalecer testes de intent/secret memory contra falsos positivos em perguntas comuns. | medio | medio | baixo | P1 | Ciclo 9 corrigiu recall explicito para secret memory e adicionou teste direto; ainda cabe matriz maior de frases comuns. |
| TD-017 | Formalizar provisionamento de `AUDIT_LEDGER_HMAC_KEY` por secret manager/cofre. | alto | medio | medio | P1 | Ciclo 10 tornou a chave obrigatoria e gerou valor local; producao distribuida precisa gestao centralizada de segredo. |
| TD-018 | Ativar TLS fim a fim para Qdrant com API key. | alto | medio | medio | P1 | Concluido localmente no Ciclo 13: Qdrant HTTPS, API com CA, doctor HTTPS e warning inseguro zerado. |
| TD-019 | Formalizar snapshot/restore antes de upgrades de Qdrant. | alto | medio | medio | P1 | Concluido localmente no Ciclo 15: backup, restore descartavel e verify reais por HTTPS com manifest/SHA-256. |
| TD-020 | Definir rotacao e distribuicao segura da CA Qdrant. | alto | medio | medio | P1 | Ciclo 13 gerou CA local em `.secrets/qdrant`; producao precisa PKI/secret manager, validade, rotacao e rollout documentados. |
| TD-021 | Validar restore Qdrant em ambiente descartavel. | alto | medio | medio | P1 | Concluido no Ciclo 15 com `janus_qdrant_restore_test`, TLS, API key, restore de 5 colecoes e verify `status=ok`. |
| TD-022 | Definir retencao/offsite para snapshots Qdrant. | alto | medio | medio | P1 | Parcial no Ciclo 17: retencao local auditavel com `prune` e integridade SHA-256 pre-restore; falta offsite, criptografia externa e agendamento. |
| TD-023 | Agendar e monitorar backup/prune data-plane. | medio | medio | medio | P1 | O comando existe e foi validado manualmente; falta job agendado, alerta de falha e evidencia periodica. |
| TD-024 | Tornar manifesto/SHA-256 obrigatorio para restore em producao. | medio | medio | baixo | P1 | Ciclo 17 preservou compatibilidade com backups legados usando `integrity-check=skipped`; ambientes produtivos devem exigir manifesto verificavel apos rollout. |

## Regra de Uso

Cada ciclo deve escolher no maximo uma divida principal, validar o impacto esperado e atualizar este arquivo com decisao: manter, ajustar, remover ou escalar.
