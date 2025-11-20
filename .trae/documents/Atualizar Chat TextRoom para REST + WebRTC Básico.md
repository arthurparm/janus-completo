## Estado Atual
- `JanusApiService` expõe a API REST (`/api/v1/chat/*`) já funcional para iniciar conversa, enviar mensagem e listar histórico (front/src/app/services/janus-api.service.ts:310-325).
- `ChatComponent` usa exclusivamente REST (front/src/app/features/chat/chat/chat.ts:22-88). Não há uso de TextRoom/datachannel no código atual.
- Proxy já encaminha `/api` e `/healthz` para `localhost:8000` (front/proxy.conf.json:1-14).

## Objetivo
- Tornar REST a camada principal de comunicação de chat (sem RTC para texto).
- Integrar WebRTC básico para mídia (áudio/vídeo) com Janus JS (init/attach/PeerConnection) e fallback para REST quando WebRTC indisponível.
- Remover qualquer dependência de datachannel para chat textual.

## Mudanças Planejadas
### 1) Camada REST (Chat)
- Manter e reforçar os métodos REST existentes em `JanusApiService`:
  - `startChat(title?)`, `sendChatMessage(conversation_id, content)`, `getChatHistory(conversation_id)`, `listConversations()`.
- Melhorar tratamento de erros (timeouts, status HTTP, mensagens amigáveis) sem alterar contratos.
- Garantir retrocompatibilidade: nenhum endpoint será renomeado ou removido.

### 2) Integração WebRTC com Janus
- Adicionar Janus JS via CDN em `front/src/index.html` (script `janus.js`).
- Criar módulo WebRTC no `JanusApiService` na região solicitada (linhas 156-179):
  - `initJanus(opts)`: chama `Janus.init()` e prepara sessão; retorna estado/erros.
  - `attachPlugin(plugin, opts)`: chama `Janus.attach()` para gerenciar sessão/handle; eventos de conexão e erros.
  - `createPeerConnection(iceServers)`: instancia `RTCPeerConnection`, configura handlers (`ontrack`, `oniceconnectionstatechange`, etc.).
  - Expor Observables/Subjects para estado de mídia (local/remote streams, ICE state) e erros.
- Não usar datachannel para chat; datachannel ficará desativado/omitido.

### 3) Atualizar `ChatComponent` para mídia
- Solicitar mídia com `getUserMedia({audio:true, video:true})` no `ngOnInit`.
- Integrar com `JanusApiService` WebRTC:
  - Inicializar Janus; `attachPlugin` (videoroom/videocall básico).
  - Adicionar tracks do `MediaStream` local ao PeerConnection; assinar `ontrack` para exibir remoto.
- UI: adicionar elementos `<video>` para local/remote, botões de iniciar/parar mídia.
- Fallback: em falha de init/attach/ICE, manter chat REST; desabilitar controles de mídia e mostrar aviso.

### 4) Tratamento de Erros (robusto)
- Categorias: permissão negada (getUserMedia), rede/Janus indisponível, ICE/DTLS falhas.
- Estratégia:
  - Try/catch em init/attach; timeouts configuráveis; mensagens localizadas.
  - Observables para estados (`connected`, `failed`, `disconnected`); UI reage e alterna para REST-only.
  - Logs controlados (sem segredos), com códigos de erro e ação sugerida.

### 5) Proxy/Config (opcional)
- Se gateway Janus estiver em outra porta/host (ex.: `http://localhost:8088/janus`), adicionar entrada de proxy (`/janus`) para desenvolvimento.
- Tornar o endpoint de Janus configurável (env/config Angular) sem impactar `/api/*`.

### 6) Testes
- Unit: `ChatComponent` continua operando chat via REST (mocks de `JanusApiService`).
- Unit: Serviço WebRTC emite estados corretos em erros simulados (mocks Janus, `RTCPeerConnection`).
- E2E básico: abrir chat, enviar mensagem REST, iniciar mídia e ver local preview; em falha de WebRTC, chat REST permanece funcional.

### 7) Documentação
- Atualizar página de Arquitetura para refletir: "Chat textual via REST (primário)" e "WebRTC opcional para mídia"; incluir diagrama simples da dupla pilha (REST vs WebRTC) e estratégia de fallback.
- Adicionar seção em Documentação com fluxos: inicialização Janus, attach plugin, configuração PeerConnection e handling de erros.

## Critérios de Aceitação (mapeamento)
- REST do chat operacional: verificado por testes e uso do `ChatComponent` (até 2025-11-18).
- WebRTC básico implementado/testado: init/attach/PeerConnection, preview local e handling de remoto quando disponível (até 2025-11-18).
- Zero dependências de datachannel para texto: garantido pela ausência de uso no código e pela inspeção.
- Retrocompatibilidade: nenhum contrato REST alterado; UI do chat continua a funcionar para clientes existentes.

## Esboço de Assinaturas (referência)
- `janus-api.service.ts` (na região 156-179):
  - `initJanus(opts: { serverUrl: string; debug?: boolean }): Observable<WebRTCState>`
  - `attachPlugin(plugin: 'videoroom'|'videocall', opts?: any): Observable<JanusHandleState>`
  - `createPeerConnection(iceServers?: RTCIceServer[]): RTCPeerConnection`
  - `localStream$: Observable<MediaStream>` / `remoteStream$: Observable<MediaStream>` / `errors$: Observable<WebRTCError>`
- `chat.ts` (22-45): chamar `initJanus` no `ngOnInit`, iniciar mídia e ligar ao PeerConnection; manter REST para mensagens.

## Observações
- Assumo uso de Janus JS oficial via CDN; se houver restrições, podemos optar por script local.
- Sem alterações nos endpoints `/api/v1/chat/*`.
- Sem armazenamento de segredos em logs; configurações em variáveis de ambiente quando necessário.

Confirma este plano? Após confirmação, implemento as mudanças e executo os testes.