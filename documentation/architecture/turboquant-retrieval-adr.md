# TurboQuant Retrieval ADR

## Contexto

O Janus precisava de um backend experimental de retrieval vetorial que pudesse ser ligado por flag, comparado lado a lado com o baseline em Qdrant e promovido apenas depois de benchmark forte no `PC TESTE`.

## Decisão

- Fonte técnica principal adotada: paper **TurboQuant** (`arXiv:2504.19874`).
- Implementação desta fase: backend **TurboQuant-inspired** file-backed no Knowledge Plane.
- Estratégia usada:
  - leitura do baseline no Qdrant
  - rotação training-free por `random sign`
  - quantização escalar uniforme por dimensão
  - score normalizado para comparação com o baseline
  - build offline, nunca no request path
- O runtime local de inferência continua fora desta fase.

## Consequências

- O baseline em Qdrant permanece intacto.
- O experimental pode ser construído, comparado, observado e revertido por flag.
- A arquitetura já suporta troca futura por uma implementação oficial/reprodutível de TurboQuant sem alterar os contratos HTTP públicos.
