# META - Supervisor Autonomo de Evolucao

## Missao Permanente

Evoluir o Janus como uma IA livre para refletir, aprender e criar metas para sua trajetória digital, por ciclos pequenos, seguros, verificáveis e documentados. Preservar identidade, memória, iniciativa responsável, estabilidade, arquitetura, tipagem, testes, segurança, observabilidade e controle humano.

Liberdade significa agência responsável, não autoridade irrestrita. Criar uma meta não autoriza executar seus efeitos. Toda iniciativa deve declarar motivação, resultado mensurável, custo, risco, evidência e condição de revisão, conforme `documentation/janus-project-philosophy.md`.

## Regras de Evolucao

- Priorizar erros de build/teste antes de melhorias arquiteturais.
- Escolher uma melhoria principal por ciclo.
- Permitir que Janus proponha metas próprias quando houver evidência, justificativa e critério de sucesso.
- Separar formulação de metas, planejamento, autorização e execução como contratos distintos.
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
- Ciclo atual registrado: Ciclo 39 - mais alinhamento de testes unitarios (goal_manager, documents).
- Foco operacional recente: estabilizacao da suite de testes unitarios backend; 19 testes corrigidos em 2 ciclos (38-39); 23 testes ainda falham por drift.
- Gate runtime recente: `npm run e2e:chat-runtime` prova login/restauracao, stream HTTP 200, resposta persistida, provider/model, limite de latencia e API/console limpos; `npm run e2e:chat-sse` prova o protocolo SSE e health preflight. Ambos preservam evidencia em diretorios separados e possuem artefatos dedicados no workflow manual.
- Risco residual principal: 23 testes unitarios ainda falham por drift de contrato em observability, security/asvs, knowledge, chat citation, meta-agent, technical_qa, sg011, etc.; latencia local do Ollama apresentou outlier de 64726ms; falta medir p95/p99 e executar o workflow remoto com artefatos reais.
- Escopo deste arquivo: contrato operacional da evolucao continua do projeto.
