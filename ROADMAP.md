# ROADMAP

## Fase 1 - Base de Governanca Tecnica

- Criar arquivos de memoria obrigatorios da meta continua.
- Manter rastreabilidade de ciclos, testes, decisoes e dividas tecnicas.
- Consolidar comandos de validacao por tipo de mudanca.

## Fase 2 - Estabilidade e Gates

- Priorizar falhas que impedem testes, lint ou build.
- Reduzir regressao silenciosa em Health, workers, auth e contratos API.
- Ampliar testes de contrato onde houver risco operacional.
- Manter gate real de chat/SSE para evitar regressao do fluxo `/api/v1/chat/stream/{conversation_id}`.

## Fase 3 - Arquitetura e Tipagem

- Reduzir uso de `any` em contratos frontend/backend de maior risco.
- Isolar parsing e normalizacao de payloads externos.
- Remover duplicacao entre endpoints e servicos quando houver cobertura.

## Fase 4 - Observabilidade e Operacao

- Consolidar sinais de Health e readiness.
- Melhorar logs estruturados e testes de falha parcial.
- Mapear dependencias PC1/PC2 em diagnosticos operacionais.
- Separar claramente diagnostico local (`host.docker.internal`) de diagnostico split PC1/PC2.
- Validar fluxo LLM real apos disponibilidade de modelo Ollama ou provider externo.
- Executar workflow manual `.github/workflows/frontend-e2e-real.yml` em GitHub Actions com segredos reais e coletar artefatos `frontend-chat-sse-evidence` retidos por 30 dias.
- Definir frequencia de execucao do workflow E2E real: manual por release, nightly ou ambos.

## Fase 4.1 - Status de Chat/SSE

- Concluido localmente: teste unitario de streaming leve, contrato HTTP de citacoes, smoke Playwright `e2e:chat-sse`, timeout operacional alinhado ao limite configurado, preflight `/healthz` obrigatoriamente saudavel e sem dependencias degradadas na evidencia, comando npm, documentacao e integracao no workflow manual.
- Parcial: evidencia local com contrato `runtime_preflight`, contagem de dependencias degradadas, Step Summary com escape Markdown e retencao de 30 dias do artefato SSE estao definidos.
- Concluido localmente no Ciclo 36: chat autenticado por UI em `localhost` e `127.0.0.1`, stream 200, persistencia apos reload, `delivery_status=completed`, provider/model reais, sem 429 ou erro de console; rate limit isolado por usuario autenticado.
- Concluido localmente no Ciclo 37: memoria generativa criada, buscada e recarregada pela UI com isolamento por usuario/conversa; stream de eventos fecha sem erro no reload.
- Pendente: medir p50/p95/p99 do chat real em serie controlada e explicar outliers acima de 60s.
- Pendente: execucao remota do workflow real e decisao de cadencia de release/nightly.

## Fase 5 - Preparacao para Features Futuras

- Documentar contratos estaveis.
- Reduzir acoplamento em servicos grandes.
- Manter backlog tecnico priorizado.
