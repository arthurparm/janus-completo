## Contexto
- O ambiente não possui Janus JS disponível. O frontend já trata a ausência de Janus (`typeof Janus === 'undefined'`) e mantém o chat REST funcional.

## Mudanças Propostas
- Remover a tag `<script>` de `janus.js` em `front/src/index.html` para evitar tentativas de download e erros de política do navegador.
- Manter o módulo WebRTC no serviço com fallback: quando Janus não estiver disponível, o estado exibe "unavailable" e a UI de mídia segue desativada sem impacto no chat REST.
- Sem alterações adicionais; contratos REST e UI de chat permanecem iguais.

## Verificação
- Rebuild automático pelo dev server; abrir `/chat` para validar fluxo REST.
- Revisar `/janus-gaps` (inventário) para confirmar que status de WebRTC básico entregue permanece documentado (como integração opcional/fallback).

Confirma a remoção da tag `<script>`? Após confirmação, aplico o ajuste e valido no dev server.