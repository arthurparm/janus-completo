## Achados Principais
- O frontend não integra o Janus WebRTC Gateway nem plugins (videoroom/audiobridge/textroom/streaming/recording), e não usa WebRTC no navegador.
- "Janus" no frontend refere-se ao serviço HTTP `JanusApiService` (REST) para funcionalidades de sistema, chat textual, observabilidade e produtividade.
- Evidências: `front/src/app/services/janus-api.service.ts:156-450` mostra apenas chamadas HTTP; o chat usa REST (`front/src/app/features/chat/chat/chat.ts:22-45`).

## Entregáveis
- Tabelas completas e atualizáveis com: itens não implementados (frente ao Janus/WebRTC) e funcionalidades obsoletas no contexto do projeto.
- Proposta de manutenção: arquivo CSV versionado e/ou página administrativa exibindo/atualizando o inventário.

## Itens Não Implementados (Janus/WebRTC)
| Descrição | Data da ausência | Impacto funcional | Prioridade | Status | Justificativa | Referências técnicas |
|---|---|---|---|---|---|---|
| Integração WebRTC básica (Janus.init/attach/PeerConnection) | 2025-11-18 | Sem RTC no navegador; impede áudio/vídeo nativo | média | pendente | Arquitetura atual é REST/LLM | `front/src/app/services/janus-api.service.ts:156-179`; `front/src/app/features/chat/chat/chat.ts:22-45` |
| Plugin VideoRoom (publicar/assinar; UI de sala) | 2025-11-18 | Sem salas de vídeo; bloqueia conferências | média | pendente | Não há requisito de videoconferência | `front/src/app/services/janus-api.service.ts:161-179`; `front/src/app/features/chat/chat/chat.ts:43-70` |
| Moderação em VideoRoom (kick/mute/roles) | 2025-11-18 | Sem controle de participantes | baixa | pendente | Sem VideoRoom implementado | `front/src/app/services/janus-api.service.ts:161-179` |
| Simulcast/SVC em publicadores | 2025-11-18 | Menor eficiência de vídeo | baixa | pendente | Sem publicação RTC | `front/src/app/services/janus-api.service.ts:206-217` |
| Compartilhamento de tela (getDisplayMedia) | 2025-11-18 | Usuários não compartilham tela | baixa | pendente | Sem RTC e UI correspondente | `front/src/app/features/chat/chat/chat.ts:59-83` |
| Controle de bitrate/resolução via Janus | 2025-11-18 | Sem ajuste de QoS | baixa | pendente | Sem pipeline de mídia | `front/src/app/services/janus-api.service.ts:210-226` |
| ICE Trickle/renegociação/restart | 2025-11-18 | Menor resiliência de sessão | baixa | pendente | Sem PeerConnection | `front/src/app/services/janus-api.service.ts:171-187` |
| DataChannels genéricos | 2025-11-18 | Sem comunicação RTC low-latency | baixa | pendente | Chat via REST | `front/src/app/features/chat/chat/chat.ts:59-83` |
| Plugin TextRoom (chat RTC) | 2025-11-18 | Chat não usa datachannel | baixa | descartado | REST/WebSocket são suficientes | `front/src/app/features/chat/chat/chat.ts:22-45` |
| Gravação de sessões via Janus | 2025-11-18 | Sem gravação de áudio/vídeo | baixa | pendente | Não há requisito de mídia | `front/src/app/services/janus-api.service.ts:205-226` |
| Plugin Streaming (RTSP/HLS) | 2025-11-18 | Sem ingest/egress de mídia | baixa | pendente | Escopo atual não requer | `front/src/app/services/janus-api.service.ts:206-217` |
| Métricas RTC/QoS no frontend | 2025-11-18 | Sem telemetria de mídia | baixa | pendente | Sem RTC | `front/src/app/services/janus-api.service.ts:210-226` |
| Autenticação/tokens do Janus (rooms/admin) | 2025-11-18 | Sem controle de acesso RTC | baixa | pendente | Sem integração Gateway | `front/src/app/services/janus-api.service.ts:332-336` |
| Gestão de salas (criar/destroi/lista) | 2025-11-18 | Sem administração de sessões | baixa | pendente | Sem VideoRoom | `front/src/app/services/janus-api.service.ts:171-187` |

## Funcionalidades Obsoletas (no contexto do projeto)
| Nome da funcionalidade | Data de descontinuação | Alternativa atual | Motivo da obsolescência | Impacto nos usuários | Plano de remoção/migração |
|---|---|---|---|---|---|
| TextRoom (chat via datachannel) | 2025-11-18 | Chat REST (`/api/v1/chat/*`) | Arquitetura orientada a API; sem RTC | Nenhum no uso atual | Manter via REST; não implementar plugin |
| AudioBridge (salas de áudio) | 2025-11-18 | Chat/assistente textual | Projeto não prevê chamadas de áudio | Nenhum | Não implementar; documentar decisão |
| SIP (telefonia PSTN) | 2025-11-18 | N/A | Fora de escopo | Nenhum | Não adotar; usar canais existentes |
| Record&Play do Janus | 2025-11-18 | Logs/observabilidade backend | Preferência por registros server-side | Nenhum | Se surgir mídia, avaliar alternativas server-side |
| Streaming plugin para consumo | 2025-11-18 | N/A | Sem necessidade de ingest/egress | Nenhum | Não implementar; se necessário, usar serviços dedicados |
| Admin API no frontend | 2025-11-18 | Gestão via backend REST | Segurança e governança centralizadas | Nenhum | Manter administração pelo backend |

## Como Manter Atualizável
- Fonte única de verdade em CSV (`descricao,data,impacto,prioridade,status,justificativa,referencias`) versionado no repositório.
- Página administrativa no frontend que lê esse CSV/JSON, exibe tabela com filtros e permite atualizar status/prioridade.
- Referências técnicas devem incluir arquivo e linha (ex.: `front/src/app/services/janus-api.service.ts:156`), além de links para tickets internos quando existirem.

## Próximos Passos
- Confirmar escopo: se o produto continuará sem RTC, manter itens como "descartado"; caso contrário, priorizar VideoRoom e integração WebRTC básica.
- Aprovar formato (CSV/JSON + página administrativa) para manter a lista atualizada.
- Opcional: adicionar validações automáticas que verifiquem ausência/presença de APIs WebRTC e mantenham a tabela sincronizada com o código.