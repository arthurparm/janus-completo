## Objetivos
- Consolidar segurança (JWT/RBAC) e auditoria em todos os fluxos
- Evoluir UI HITL com guardas e gráficos
- Implementar UI de consentimentos/OAuth no frontend
- Documentar APIs (Swagger/OpenAPI) e reforçar conformidade (LGPD)
- Preparar integração real com provedores (Google/Microsoft)

## Backend — Segurança e RBAC
- Padronizar autenticação JWT em todos endpoints sensíveis (HITL, auditoria, produtividade, consents)
- Adicionar verificações de papéis REVISOR/AUDITOR/ADMIN via repositório de usuários
- Propagar `actor_user_id` em middlewares e registrar no `AuditEvent`

## Backend — Auditoria e Observabilidade
- Expandir `AuditEvent` com campos e índices necessários para busca eficiente
- Expor filtros avançados e paginação em auditoria (já iniciado) e manter sanitização por padrão nos exports
- Adicionar endpoints agregados de métricas por revisor e relatórios por período (já iniciado); completar testes e documentação

## Backend — Produtividade (OAuth real)
- Implementar fluxo completo OAuth2 para Google/Microsoft:
  - Start: gerar `authorize_url` com escopos
  - Callback: trocar `code` por tokens (usar provider SDK/HTTP), persistir em `oauth_tokens`
  - Refresh: renovar tokens e `expires_at`
- Rate limits por escopo e auditoria de ações; sanitização de payloads sensíveis

## Frontend — Auth/JWT e Guardas
- Implementar página de login com fluxo real (troca de credenciais ou impersonation segura) e armazenamento do token
- Adicionar guardas de rota por papel em `/hitl` e áreas administrativas
- Exibir papel do usuário e permitir logout

## Frontend — HITL UI
- Filtros avançados (search, type, reason, confiança), paginação e ordenação
- Gráficos de métricas por revisor (linhas/barras) e relatórios diários/semanais/mensais
- Export com seleção de campos e sanitização opcional

## Frontend — Consents e OAuth UI
- Tela para listar/grant/revoke consentimentos por escopo
- Fluxo de OAuth: iniciar, redirecionar, callback e refresh com feedback de estado
- Indicadores de escopos ativos e próximos de expirar

## RAG Híbrido
- Pesos adaptativos dinâmicos (confiança/similaridade) e citação estruturada
- Limites de expansão por tipo/`max_depth` e cache por usuário/sessão

## LGPD e Conformidade
- Minimizar coleta/exposição de PII; sanitização por padrão em export administrativos
- Consentimentos explícitos para ações sensíveis com trilhas exportáveis
- Políticas de retenção e acesso (Policy Engine básico)

## Swagger/OpenAPI
- Documentar todos endpoints novos (HITL, auditoria, métricas, export, consents, OAuth/produtividade) com descrições, parâmetros, RBAC e exemplos

## Testes e Validação
- Unit/integration para HITL, auditoria, consents, OAuth, RAG e produtividade
- Usabilidade: testes com usuários da UI HITL (justificativas e fluxos)
- Performance: carga em listagem de auditoria/quarentena; latência aceitável

## Entregáveis e Critérios
- RBAC/guardas ativos no backend e frontend
- UI HITL com gráficos e export; UI consents e fluxo OAuth com feedback
- Swagger atualizado e LGPD atendida (sanitização por padrão)
- Métricas e relatórios operacionais validados; dashboards atualizados