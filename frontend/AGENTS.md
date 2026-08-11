# AGENTS.md — Frontend Janus

Aplica-se a `frontend/` e complementa o contrato da raiz.

## Navegação e arquitetura

Comece em `frontend/src/app/app.routes.ts` e siga:

```text
feature -> domain/API service -> model -> shared/core dependency
```

- `core/` contém auth, guards, interceptors, layout e estado global.
- `features/` contém telas e comportamento específico.
- `services/` integra APIs e domínios; `models/` espelha contratos do backend.
- `shared/` contém componentes e utilitários reutilizáveis sem regra de negócio específica.

Mantenha modelos TypeScript alinhados às respostas reais do backend. Não duplique regra de domínio do servidor no componente.

## Experiência funcional

- Corrija a integração real; não esconda backend indisponível com dados de demonstração apresentados como runtime.
- Não apresente `unknown`, zero ou “indisponível” como estado definitivo antes de concluir a tentativa e tratar erro/timeout.
- Respostas do chat devem vir do fluxo real; não injete frases automáticas para simular inteligência ou capacidade.
- Preserve loading, vazio, erro, retry, navegação, teclado, foco, semântica e `prefers-reduced-motion`.
- Mudança visual exige inspeção no viewport afetado; build isolado não prova funcionalidade.
- Console sem erro não prova integração: inspecione também rede, payloads e estado persistido quando aplicável.

Referências: [FRONTEND_ANGULAR.md](../FRONTEND_ANGULAR.md), `frontend/package.json` e `frontend/src/app/app.routes.ts`.

## Implementação

- Use Node.js 20, o package manager e lockfile existentes.
- Reuse componentes, services, signals/observables e padrões adjacentes.
- Evite `any`, subscriptions órfãs, estado duplicado e efeitos no template.
- Preserve guards, interceptors, sanitização e fronteiras de autenticação.
- Não adicione dependência ou atualize pacote não relacionado sem justificativa.

## Validação

Rode os testes direcionados durante a implementação e, antes de concluir uma mudança frontend:

```powershell
Set-Location frontend
npm run lint
npm run test
npm run build -- --configuration development
```

Se UI, navegação, autenticação ou integração mudarem, valide também no navegador como usuário real:

- fluxo feliz e falha/recuperação;
- viewport relevante e responsividade;
- teclado, foco e estados acessíveis;
- console e requisições sem falhas inesperadas;
- REST/SSE, persistência e atualização de tela quando fizerem parte do fluxo.

Use produção (`npm run build -- --configuration production --base-href /`) quando o empacotamento ou deploy for afetado. Não altere testes para aceitar fallback demonstrativo ou resposta artificial.
