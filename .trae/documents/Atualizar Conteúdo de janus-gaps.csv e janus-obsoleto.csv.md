## Objetivo
- Refletir no inventário (CSV) as entregas realizadas e decisões de obsolescência.
- Manter o consumo atual dos CSVs pela página `JanusGaps` sem alterar contratos.

## Mudanças Planejadas
- `front/public/janus-gaps.csv`:
  - Atualizar o item "Integração WebRTC básica (Janus.init/attach/PeerConnection)" de `status=pendente` para `status=entregue` e ajustar referências às linhas atuais:
    - `front/src/app/services/janus-api.service.ts` (bloco WebRTC adicionado próximo de 181+)
    - `front/src/app/features/chat/chat/chat.ts` (integração mídia: 50-79; stop: 127-131)
  - Manter pendentes: VideoRoom (pub/sub e UI), moderação, simulcast/SVC, compartilhamento de tela, controle de bitrate, ICE trickle/renegociação, métricas RTC/QoS.
  - Manter descartado: TextRoom (chat RTC) e datachannels genéricos para chat textual.
- `front/public/janus-obsoleto.csv`:
  - Confirmar linha "TextRoom (chat via datachannel)" como obsoleto; alternativa `Chat REST (/api/v1/chat/*)`, motivo `Arquitetura orientada a API, sem RTC`.
  - Sem alterações nas demais linhas (mantêm escopo fora do projeto).

## Compatibilidade
- Nenhuma alteração em componentes Angular: `JanusGapsComponent` já lê ambos CSVs (front/src/app/pages/janus-gaps/janus-gaps.ts:41-50).
- O formato CSV (cabecalho, separador `;`) permanece igual; UI continua renderizando estados e referências.

## Verificação
- Rodar dev server já em execução e abrir `/janus-gaps` para validar que o item WebRTC aparece com `status=entregue` e que os demais permanecem pendentes/descartados.

## Observações
- Não adicionaremos novos campos/colunas; apenas atualizaremos valores.
- Caso deseje, em próximo passo podemos padronizar estilos para `entregue` na UI, mas não é necessário para esta atualização.

Confirma estas alterações nos CSVs? Após confirmação, aplico os updates e valido na página Janus Gaps.