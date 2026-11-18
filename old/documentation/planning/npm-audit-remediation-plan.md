# Plano de Remediação Segmentada do `npm audit`

## Objetivo

Transformar o relatório de segurança do frontend em um backlog auditável de correções segmentadas, com validação funcional por lote e sem uso de `npm audit fix --force`.

## Linha de base congelada

- Data de referência da spec: `2026-08-03`
- Baseline operacional aceito para planejamento: `25 advisories`, incluindo `1` crítico
- Origem da baseline: evidência operacional citada na spec aprovada
- Observação: o repositório já registra progresso parcial em `TODO_TECHNICAL_DEBT.md`, mas esta frente mantém a baseline da spec como referência de planejamento até a próxima revalidação formal

## Comandos de coleta e validação

Coletar o relatório bruto:

```powershell
npm --prefix "frontend" audit --json | Tee-Object -FilePath "outputs/qa/npm-audit-frontend.json"
```

Gerar visão humana do lote:

```powershell
npm --prefix "frontend" audit
```

Validar regressão funcional mínima após cada lote:

```powershell
npm --prefix "frontend" run build
npm --prefix "frontend" run test
```

Quando o lote afetar runtime autenticado ou toolchain sensível, acrescentar:

```powershell
npm --prefix "frontend" run e2e:chat-runtime
npm --prefix "frontend" run e2e:chat-sse
```

## Triagem segura por famílias de advisories

### Lote A: transitivos já controlados por `overrides`

Pacotes a observar no `package.json` atual:

- `hono`
- `@hono/node-server`
- `path-to-regexp`
- `tar`
- `ip-address`
- `immutable`

Estratégia:

- preferir atualização transitive via `overrides` já existentes;
- revalidar `build` e `test` logo após o lote;
- evitar upgrades maiores se o advisory puder ser mitigado por patch/minor.

### Lote B: cadeia MCP/CLI e dependências de ferramenta

Pacotes já sinalizados no backlog técnico:

- `@grpc/grpc-js`
- `protobufjs`

Possíveis cadeias:

- `@modelcontextprotocol/sdk`
- dependências indiretas da `@angular/cli` e tooling relacionado

Estratégia:

- mapear com `npm ls @grpc/grpc-js protobufjs`;
- tratar como lote separado do runtime da aplicação;
- exigir `build`, `test` e revisão manual de compatibilidade antes de aceitar upgrade maior.

### Lote C: websockets e runtime de teste

Pacote já sinalizado:

- `ws`

Possíveis áreas afetadas:

- Playwright
- Vitest/Vite
- tooling de dev server

Estratégia:

- mapear com `npm ls ws`;
- tratar separadamente de autenticação e chat;
- validar `build`, `test` e, quando houver impacto em runtime autenticado, ao menos um smoke E2E.

## Regras de decisão por advisory

### Corrigir agora

Aplicar no lote atual quando o advisory:

- tiver correção patch/minor;
- não exigir troca major de framework;
- tiver cadeia curta e facilmente validável;
- não ampliar escopo além do frontend/tooling imediato.

### Escalar para janela controlada

Não aplicar no lote atual quando o advisory:

- exigir upgrade major;
- alterar contratos de toolchain;
- afetar Angular, Vite, Playwright ou SDKs compartilhados em mais de um fluxo;
- depender de atualização indireta sem clareza de compatibilidade.

## Registro mínimo por lote

Cada lote deve gerar um bloco de evidências com:

- data da execução;
- advisories atacados;
- pacote raiz e cadeia transitiva afetada;
- comando usado para atualização;
- resultado de `npm audit`;
- resultado de `build` e `test`;
- riscos remanescentes aceitos ou blockers abertos.

## Mapa inicial de risco residual

| Família | Criticidade operacional | Estratégia | Situação desta entrega |
|---|---|---|---|
| `hono` / `@hono/node-server` / `path-to-regexp` | média | correção transitive guiada por `overrides` | triada |
| `@grpc/grpc-js` / `protobufjs` | alta | lote isolado com revisão de compatibilidade | triada |
| `ws` | média a alta | lote próprio com smoke adicional | triada |
| demais advisories de patch/minor | variável | atacar por lote curto com validação padrão | pendente de execução |

## Riscos remanescentes

- O relatório real precisa ser reemitido antes da janela de release para confirmar se a baseline ainda é `25/1 crítico`.
- Dependências transitivas de toolchain podem exigir upgrades maiores mesmo sem mudança direta no código da aplicação.
- Sem executar lotes de atualização, as vulnerabilidades seguem abertas ou apenas mitigadas por planejamento.
- O uso de `npm audit fix --force` continua proibido por risco de churn funcional não controlado.

## Decisão operacional desta entrega

Esta entrega fecha somente:

- classificação inicial dos advisories por família, cadeia e criticidade;
- estratégia segura de tratamento segmentado;
- comandos mínimos de coleta e validação;
- registro explícito dos riscos remanescentes.

Esta entrega não fecha:

- atualização efetiva de dependências;
- execução de `build`, `test` ou `e2e` após lotes de correção;
- redução comprovada do total de advisories.
