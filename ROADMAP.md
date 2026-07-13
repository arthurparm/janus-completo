# ROADMAP

## Fase 1 - Base de Governanca Tecnica

- Criar arquivos de memoria obrigatorios da meta continua.
- Manter rastreabilidade de ciclos, testes, decisoes e dividas tecnicas.
- Consolidar comandos de validacao por tipo de mudanca.

## Fase 2 - Estabilidade e Gates

- Priorizar falhas que impedem testes, lint ou build.
- Reduzir regressao silenciosa em Health, workers, auth e contratos API.
- Ampliar testes de contrato onde houver risco operacional.

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

## Fase 5 - Preparacao para Features Futuras

- Documentar contratos estaveis.
- Reduzir acoplamento em servicos grandes.
- Manter backlog tecnico priorizado.
