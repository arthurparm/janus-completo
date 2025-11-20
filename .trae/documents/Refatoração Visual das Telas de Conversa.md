## Objetivos de UX
- CTA “Nova conversa” proeminente e fluxo claro para criar/abrir conversas.
- Visual moderno, profissional e acessível, alinhado à marca Janus.
- Ajuda contextual nas principais ações (upload, enviar, citações) e feedback visual consistente.

## Lista de Conversas (Conversations)
- Header com título “Conversas” + CTA primário “Nova conversa”.
- Barra de busca com:
  - Texto livre (título/última mensagem).
  - Período (data inicial/final) com rótulos claros.
- Cards responsivos (1–3 colunas):
  - Título, snippet da última mensagem, horários (criada/atualizada), ícones grandes.
  - Chips de estado com cores acessíveis: “Nova” (sem mensagens), “Em andamento” (atualizada recentemente), “Resolvida” (marcada manualmente ou heurística > N dias sem atualização).
  - Ações: Abrir, Renomear, Excluir.
- Skeletons durante carregamento; estados vazios com instrução (“Nenhuma conversa. Clique em ‘Nova conversa’”).
- Acessibilidade: foco visível, `aria-label` nos inputs/botões, leitura por teclado completa.

## Detalhe da Conversa (Chat)
- Header com breadcrumb “Conversas > [Título/ID]”, botão voltar e chip de estado.
- Layout em 2 áreas (ajusta para 1 coluna em telas pequenas):
  - Mensagens: bubbles legíveis, timestamps, Markdown com copiar código.
  - Lateral/aba: anexos (drag-and-drop com progresso), citações com fonte/score/link, ajuda contextual.
- Barra de entrada simplificada (textarea + “Enviar”): atalhos (Enter para enviar, Shift+Enter para nova linha), indicador de streaming com “Cancelar”.
- Acessibilidade: `aria-live` para novas mensagens/feedback, ordem de tab previsível.

## Consistência Visual e Design System
- Tokens de design (cores, tipografia, espaçamentos, radius, sombras) alinhados à paleta já usada.
- Componentes reutilizáveis: Button primário/secundário, Card, Chip de estado, Input com label, Skeleton.

## Ajuda Contextual
- Tooltips/ícones “i” próximos a Upload, Enviar e Citações com textos simples e diretos.
- Link “Como funciona” levando para documentação breve no próprio app.

## Mockups e Entregáveis de Design
- Mockups desktop e mobile (estados normal, carregando, erro, vazio) para ambas as telas.
- Especificações de componentes (tamanhos, cores, espaçamentos, estados de foco/hover).

## Testes de Usabilidade
- Tarefas: iniciar nova conversa, buscar conversa antiga, anexar arquivo, abrir citação, enviar mensagem.
- Público: adultos e pessoas mais velhas; 6–8 participantes (mínimo).
- Métricas: tempo por tarefa, taxa de sucesso, erros, SUS/CSAT, feedback qualitativo.
- Iteração: compilar achados, ajustar textos/layout e repetir teste curto de verificação.

## Implementação Técnica (Fases)
1) Lista de conversas: CTA, cards, chips (heurística inicial), busca por período, loaders e mensagens.
2) Chat: breadcrumb, layout acessível, ajuda contextual, lateral de anexos/citações refinada.
3) Acessibilidade: `aria-*`, foco, atalhos; testes unitários nos estados e navegação.
4) Opção futura: estado “Resolvida” vindo do backend (se necessário), com persistência.

## Arquivos-Alvo
- Lista: `front/src/app/features/chat/conversations/*` (HTML/TS/SCSS).
- Chat: `front/src/app/features/chat/chat/*` (HTML/TS/SCSS).
- Shared UI: criação de componentes/barras/inputs conforme necessidade.

Confirme para eu produzir os mockups (desktop/mobile) e, após sua validação, iniciar a implementação faseada com testes e acessibilidade.