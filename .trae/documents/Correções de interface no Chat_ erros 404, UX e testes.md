## Objetivo
Corrigir o problema de 404 ao listar anexos e elevar a qualidade da interface do chat com tratamento de erros, feedback visual, verificação de URL, estados de carregamento, validação de parâmetros e testes.

## Diagnóstico
- O 404 reportado em `GET /api/v1/documents/list?conversation_id=11` indica rota inexistente ou indisponível no backend atual; a UI deve tratar isso de forma clara e resiliente.
- O frontend chama endpoints REST diretamente com paths absolutos; há interceptores de erro já registrados que geram notificações, mas o componente não informa o usuário no contexto da seção de anexos quando falha.

## Melhorias Frontend
### Tratamento de erros (404) e feedback visual
- `ChatComponent.loadAttachments()`:
  - Adicionar `attachmentsLoading` para spinner durante a carga.
  - Capturar erros (incluindo 404):
    - Atualizar estado local (`attachmentsError` com mensagem clara: “Anexos indisponíveis (404)”).
    - Disparar `NotificationService.notifyError` com título e detalhe (interceptor já exibe banner global).
  - Ocultar/colapsar lista de anexos quando houver 404, com texto de orientação.
- Upload e deleção:
  - Mensagens de sucesso/erro amigáveis e consistentes; usar `NotificationService` para feedback.

### Verificação de URL de requisição
- `JanusApiService`: criar util `buildUrl(path: string)` que garanta prefixo correto (`API_BASE_URL`) e registre em dev um warning se o path não começar por `/api/`.
- Migrar chamadas (`documents`, `chat`, etc.) para usar `buildUrl`, evitando inconsistências.

### Validação de parâmetros
- Antes de chamar `listAttachments`, validar `conversation_id`:
  - Regex simples (`^[A-Za-z0-9:-]+$`) e comprimento mínimo; se inválido, não requisitar e informar usuário.
- Validação no upload: tipos, tamanho (já há checagem), e obrigatoriedade de `conversation_id`.

### UX e acessibilidade
- UI responsiva:
  - Ajustar `chat.html`/`chat.scss`: melhorar layout da seção de anexos (cartões, ícones, estados vazios), aplicar `aria-live`/`role="status"` para loaders e mensagens.
  - Botões com `aria-label`, foco visível, contraste adequado.
- Citações:
  - Exibir fonte/score com ícone e tooltip; links acessíveis com `rel="noopener"`.

### Indicadores de carregamento
- `attachmentsLoading` com skeleton/spinner enquanto carrega lista.
- Spinner no upload (já há `uploading/progress`), padronizar e melhorar visibilidade.

## Testes
- Unit tests (Jasmine/Karma):
  - `ChatComponent`:
    - `loadAttachments()` com 404: não quebra, define `attachmentsError`, exibe mensagem; `attachmentsLoading` alterna corretamente.
    - Parâmetro inválido para `conversation_id`: não chama API e notifica usuário.
    - Upload sucesso/erro: atualiza lista e notifica.
  - `JanusApiService.buildUrl`: monta URL com `API_BASE_URL` e emite warning em dev se path incorreto.
- Cobertura mínima para fluxos assíncronos e interceptores (verificar que `NotificationService` é acionado).

## Entregáveis
- Código do frontend atualizado (serviço + componente + estilos).
- Mensagens de erro claras e acessíveis; loaders consistentes.
- Testes unitários cobrindo cenários críticos.

## Observações
- Se o backend não tiver a rota `/api/v1/documents/list` disponível, a UI passa a informar “Funcionalidade indisponível” em vez de falhar silenciosamente e evitar novas tentativas erradas.

Confirme para aplicar as mudanças no frontend, refatorar o serviço para verificar URLs, melhorar a UX do chat e adicionar os testes.