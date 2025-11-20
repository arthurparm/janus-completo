## Diretrizes de Acessibilidade e Inclusão
- Remover completamente seleções de avatar e funções/roles: nenhuma configuração técnica exposta ao usuário.
- Linguagem clara e direta: textos curtos, objetivos, sem jargões.
- Design limpo: fontes maiores (16–18px base), alto contraste, espaçamento generoso.
- Teclado primeiro: navegação tabulável, ordens de foco previsíveis, atalhos úteis (Enter/Shift+Enter).
- Ajuda contextual: dicas discretas próximas às ações, texto de orientação nos estados vazios.

## Navegação e Fluxos
- Página inicial de Conversas `/conversations` como ponto de entrada.
- CTA primário “Nova conversa” destacado; cria conversa e navega para `/chat/:id`.
- Detalhe em `/chat/:id`; se sem ID, cria automaticamente e mostra uma dica inicial.
- Breadcrumb simples “Conversas > [Título/ID]”, link claro de retorno.

## Tela: Lista de Conversas (simplificada)
- Header com título (“Conversas”) e botão primário “Nova conversa”.
- Busca por texto com placeholder claro (“Busque por título ou conteúdo”).
- Filtros essenciais: período; opcionalmente projeto (sem termos técnicos).
- Cartões grandes e legíveis: título, último trecho, data/horário; ícones grandes com rótulos (“Abrir”, “Renomear”, “Excluir”).
- Estados da conversa em chips legíveis (“Nova”, “Em andamento”, “Resolvida”) com cores acessíveis.
- Responsivo: grid 1–3 colunas; skeletons durante carga; mensagens claras em vazios/erros.

## Tela: Chat (detalhe, simplificada)
- Header com título e status; remover controles de persona/role/priority.
- Área de mensagens com bubbles grandes, tipografia legível; timestamps e rótulos simples (“Você”, “Assistente”).
- Renderização de Markdown com botões “Copiar” visíveis; evitar excesso de ornamentos.
- Barra de entrada simplificada: textarea, botão “Enviar” (primário), “Cancelar” quando streaming.
- Anexos: drag-and-drop com texto claro, progresso grande e lista legível; sem configurações técnicas.
- Citações: cards simples com fonte e link, texto auxiliar “Clique para abrir a fonte”.
- Ajuda contextual: pequenos “i” tooltips ao lado de upload, envio e citações.

## Acessibilidade Técnica
- Roles/aria para regiões: `role="main"`, `role="status"`, `aria-live` para novas mensagens e carregamentos.
- Foco visível e consistente; evitar traps; ordem de tab lógica.
- Atalhos: Enter para enviar; Shift+Enter quebra linha; Esc para fechar ajuda.
- Contraste mínimo WCAG AA; verificar com temas claros.

## Implementação Técnica
- Remover controles de avatar/persona/role no `ChatComponent` e cabeçalho.
- Ajustar rotas para `'/chat/:conversationId'` (detalhe) e manter `'/conversations'` como default.
- Atualizar `ConversationsComponent` para cards, CTA e filtros acessíveis; loaders e mensagens de erro claras.
- Estilos SCSS com tokens: tamanho de fonte, espaço, cores; responsivo com CSS Grid/Flex.
- Notificações e banners de erro com linguagem direta (“Não foi possível carregar. Tente novamente”).

## Feedback Visual
- Skeletons em cards e mensagens; spinner grande em uploads.
- Banners de erro acessíveis; toasts para sucesso moderados.
- Estados vazios com instruções simples (“Nenhuma conversa ainda. Clique em ‘Nova conversa’.“).

## Testes
- Unitários: 
  - Conversas: criação, busca, chips de estado, navegação para chat.
  - Chat: envio, cancelamento, anexos (erro/404), citações.
- Acessibilidade: navegação por teclado, foco, `aria-*`, contraste.
- Usabilidade com usuários reais:
  - Tarefas: iniciar conversa, enviar mensagem, anexar arquivo, abrir citação, buscar conversa antiga.
  - Métricas: tempo por tarefa, taxa de sucesso, satisfação; coletar feedback e iterar antes do desenvolvimento final.

## Entregáveis
- Mockups (desktop/mobile) e especificações de componentes.
- Plano de testes de usabilidade e checklist de acessibilidade.

Confirme para eu iniciar a implementação: remover controles técnicos, refatorar lista e chat com design simplificado e acessível, atualizar rotas e adicionar testes.