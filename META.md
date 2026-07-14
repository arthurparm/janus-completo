# META - Supervisor Autonomo de Evolucao

## Missao Permanente

Evoluir o Janus por ciclos pequenos, seguros, verificaveis e documentados, preservando estabilidade, arquitetura, tipagem, testes, seguranca, observabilidade e experiencia do desenvolvedor.

## Regras de Evolucao

- Priorizar erros de build/teste antes de melhorias arquiteturais.
- Escolher uma melhoria principal por ciclo.
- Preservar contratos publicos salvo justificativa explicita.
- Evitar dependencias novas sem necessidade tecnica forte.
- Registrar evidencias, testes executados, limitacoes e riscos.
- Nao declarar melhoria sem validacao proporcional ao risco.

## Criterios de Qualidade

- Mudanca relevantes, reversivel e auditavel.
- Teste, lint ou build executado quando aplicavel.
- Documentacao atualizada no mesmo ciclo.
- Riscos residuais registrados.
- Proximo ciclo recomendado.

## Estado Atual

- Status: meta continua ativa.
- Ciclo atual registrado: Ciclo 37 - memoria generativa real no chat e lifecycle do stream.
- Foco operacional recente: funcionamento real do chat Janus, streaming SSE leve, Qdrant atualizado e evidencias E2E runtime.
- Gate runtime recente: `npm run e2e:chat-runtime` prova login/restauracao, stream HTTP 200, resposta persistida, provider/model, limite de latencia e API/console limpos; `npm run e2e:chat-sse` prova o protocolo SSE e health preflight. Ambos preservam evidencia em diretorios separados e possuem artefatos dedicados no workflow manual.
- Risco residual principal: latencia local do Ollama apresentou outlier de 64726ms; falta medir p95/p99 e executar o workflow remoto com artefatos reais.
- Escopo deste arquivo: contrato operacional da evolucao continua do projeto.
