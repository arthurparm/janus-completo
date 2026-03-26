---
tipo: dominio
dominio: frontend
camada: features
fonte-de-verdade: codigo
status: ativo
---

# Features e Experiência

## Objetivo
Registrar o papel de cada feature Angular na experiência do produto.

## Responsabilidades
- Separar jornada por tela.
- Ligar features às capacidades backend.

## Entradas
- `frontend/src/app/features/*`

## Saídas
- Mapa funcional do frontend.

## Dependências
- [[03 - Frontend/Shell e Navegação]]
- [[03 - Frontend/Serviços de Integração]]
- [[03 - Frontend/Observability Frontend]]

## Features
- `home`: landing autenticada com atalhos e widgets.
- `conversations`: centro operacional do produto; concentra chat, docs, memória, RAG, autonomia e feedback dentro de um único componente standalone com lista de conversas, feed principal e rail avançado opcional.
- `observability`: dashboard protegido por `AuthGuard` com operator view (workers + 4 filas fixas) e três widgets (`system status`, `database validation`, `knowledge health`). Auto-refresh independente por widget (5s) com toggle que só controla painel operador.
- `tools`: gerenciamento/exploração de ferramentas.
- `auth/login` e `auth/register`: entrada e criação de sessão.
- `admin/autonomia`: controle administrativo de autonomia.

## Leitura operacional
- `conversations` é a feature mais densa e funciona quase como cockpit.
- Em `conversations`, a tela principal acumula tres camadas de responsabilidade:
  - shell de conversa (`create/list/select/refresh`, histórico e composer)
  - HUD da resposta (`understanding`, confirmações, citações, feedback e thought stream)
  - rail contextual (`Insights`, `Cliente`, `Autonomia`) com subfluxos próprios.
- O rail `Cliente` embute tres ferramentas operacionais na mesma feature:
  - `Docs`: upload, link por URL, busca vetorial e exclusão de documentos da conversa
  - `Memória`: criação de memória generativa, busca e leitura de memória da conversa/usuário. Memórias generativas mostram linha de metadados via `generativeMemoryMetaLine()` (tipo, importância numérica 0-10, score, timestamp). Campo `importance` é opcional ao criar memória.
  - `RAG`: execução manual de consultas `search`, `user-chat`, `user_chat`, `hybrid_search` e `productivity`. O modo `productivity` consulta dados de produtividade do usuário autenticado e devolve `results` (não `answer`).
- O rail `Insights` nao é só observabilidade passiva: ele agrega resumo da última resposta, `thoughtStream` vindo de SSE/event bus e `trace` sob demanda via `getConversationTrace()`. Quick prompts fixos (resumo em 5 pontos, próximos passos, explicação simples) preenchem o composer e disparam envio normal.
- O rail `Autonomia` nao redireciona para outra feature; ele controla loop autônomo, metas e ferramentas direto da tela de conversa.
- O componente também tem um subfluxo admin-only por comando `/code`, que troca o envio normal por `api/v1/autonomy/admin/code-qa`.
- Componentes compartilhados realmente relevantes para a experiência dessa feature:
  - `JarvisAvatarComponent`: expõe visualmente os estados `idle`, `thinking` e `speaking` do chat/stream
  - `MarkdownPipe`: renderiza respostas do assistente, citações expandidas e respostas textuais de RAG
  - `UiBadgeComponent`: sustenta quase todo o HUD de status (`stream`, confiança, citações, autonomia)
  - `SkeletonComponent`: cobre carregamento de histórico, lista e blocos do rail
- `home` é um lançador de intenções e histórico recente.
- `observability` usa `BackendApiService` diretamente, sem facade dedicada.
- `observability` tem polling próprio em todos os blocos a cada 5s, mas o toggle da tela pausa apenas o painel do operador.
- **Limitações de contexto**: A tela não expõe poison pills, SLOs, anomalias, auditoria nem pipeline por request, apesar do nome sugerir cockpit completo.

## Arquivos-fonte
- `frontend/src/app/features/home/home.ts`
- `frontend/src/app/features/conversations/conversations.ts`
- `frontend/src/app/features/observability/observability.ts`
- `frontend/src/app/features/tools/tools.ts`
- `frontend/src/app/features/admin/autonomia/admin-autonomia.ts`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Conversa e Chat]]
- [[04 - Fluxos End-to-End/Autonomia]]
- [[04 - Fluxos End-to-End/Observabilidade]]
- [[03 - Frontend/Observability Frontend]]

## Riscos/Lacunas
- A feature de conversas agrega muitos subfluxos e concentra complexidade de UX e integração.
- A maior parte dessa complexidade fica no próprio `ConversationsComponent`, sem uma facade específica da feature para separar chat, contexto documental, memória, RAG, autonomia e feedback.
- O caminho padrão da UX continua SSE, mas parte relevante do enriquecimento sistêmico do chat continua mais rica no REST; a própria tela precisa conviver com essa assimetria.
- A feature de observability expoe so um subconjunto curto do estado operacional real do backend.
