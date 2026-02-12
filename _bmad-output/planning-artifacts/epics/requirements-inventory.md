# Requirements Inventory

### Functional Requirements

- FR1: Usuários podem pertencer a um tenant específico para operar o produto.
- FR2: Administradores podem criar e manter configurações de tenant.
- FR3: Administradores podem definir políticas de acesso por tenant.
- FR4: Usuários podem autenticar-se por provedores externos suportados.
- FR5: Administradores podem revogar sessões e acessos ativos de usuários.
- FR6: Sistema pode aplicar segregação de dados por tenant em todas as capacidades funcionais.
- FR7: Sistema pode classificar ações por nível de risco.
- FR8: Usuários podem fornecer consentimento explícito antes de ações sensíveis.
- FR9: Sistema pode exigir aprovação humana para ações classificadas como alto risco.
- FR10: Aprovadores podem aprovar ou rejeitar ações pendentes com justificativa.
- FR11: Sistema pode bloquear execução de ação quando pré-condições de governança não forem atendidas.
- FR12: Usuários podem visualizar o estado de governança de cada ação solicitada.
- FR13: Usuários podem interagir com o Janus por conversação contínua.
- FR14: Sistema pode sugerir próximas ações com base no contexto da conversa.
- FR15: Usuários podem aceitar, ajustar ou recusar sugestões proativas.
- FR16: Sistema pode registrar o contexto utilizado para cada sugestão apresentada.
- FR17: Usuários podem retomar contexto de conversas anteriores relevantes.
- FR18: Sistema pode operar em modo assistivo não proativo quando necessário.
- FR19: Usuários podem iniciar execuções assistidas de tarefas operacionais.
- FR20: Sistema pode orquestrar execução em múltiplas etapas com estado rastreável.
- FR21: Usuários podem cancelar execuções em andamento quando permitido por política.
- FR22: Sistema pode retomar fluxo após falha recuperável sem perda de contexto.
- FR23: Usuários podem visualizar resultado final da execução com evidências associadas.
- FR24: Sistema pode acionar fallback operacional quando execução automática não for segura.
- FR25: Usuários podem conectar contas externas suportadas via fluxo de autorização.
- FR26: Sistema pode detectar estado inválido de autorização e solicitar reautorização.
- FR27: Sistema pode aplicar quotas de uso por usuário e por tenant.
- FR28: Usuários podem visualizar motivo de falha de integração e próxima ação recomendada.
- FR29: Sistema pode manter catálogo de integrações habilitadas por tenant.
- FR30: Administradores podem ativar ou desativar integrações por tenant.
- FR31: Sistema pode registrar trilha de auditoria para ações e decisões relevantes.
- FR32: Auditores podem consultar eventos por usuário, tenant, ação e período.
- FR33: Sistema pode preservar evidências de decisão automática (razão, contexto, confiança e fallback).
- FR34: Usuários autorizados podem solicitar acesso aos próprios dados.
- FR35: Usuários autorizados podem solicitar exportação de dados em formato suportado.
- FR36: Usuários autorizados podem solicitar exclusão de dados conforme política aplicável.
- FR37: Sistema pode versionar contratos funcionais de APIs e eventos suportados.
- FR38: Usuários técnicos podem consultar mudanças de contrato e status de depreciação.
- FR39: Administradores podem visualizar painéis de uso e auditoria por tenant.
- FR40: Operações podem registrar e acompanhar incidentes operacionais com vínculo às capacidades afetadas.

### NonFunctional Requirements

- NFR1: Fluxos de interação de chat devem apresentar primeira resposta parcial em até 2 segundos (p95) em condições normais de operação, medido continuamente por APM.
- NFR2: Ações de produtividade síncronas devem retornar status inicial em até 3 segundos para pelo menos 95% das requisições, medido por tracing de API.
- NFR3: Painéis de auditoria por tenant devem carregar filtros principais em até 5 segundos para pelo menos 95% das consultas padrão, medido por monitoramento sintético diário.
- NFR4: Dados em trânsito devem usar criptografia TLS 1.2+ em 100% das comunicações externas e internas sensíveis, verificado por scanner de segurança semanal.
- NFR5: Dados em repouso devem permanecer criptografados com AES-256 em 100% dos armazenamentos de produção, verificado por varredura automatizada diária e auditoria mensal.
- NFR6: Segredos e chaves devem ser rotacionados no máximo a cada 90 dias, com 100% dos segredos catalogados por ambiente e conformidade medida por job diário de inventário.
- NFR7: Ações classificadas como alto risco devem exigir aprovação humana em 100% dos casos antes da execução, auditado mensalmente por trilhas de governança.
- NFR8: Operações de DSAR (acesso, exportação, exclusão) devem manter trilha auditável completa em 100% dos casos; SLA: acesso/exportação em até 15 dias corridos e exclusão em até 30 dias, medido mensalmente.
- NFR9: Quotas, trilhas e políticas devem ser aplicadas com particionamento por tenant em 100% dos fluxos críticos, validado por testes mensais de isolamento.
- NFR10: Transferências para provedores externos/LLMs devem aplicar política de residência de dados em 100% das requisições, com bloqueio automático em violações e medição por logs do policy engine.
- NFR11: Fluxos críticos (chat stream, execução assistida e auditoria) devem operar com SLO definido e monitoramento ativo.
- NFR12: Incidentes de falha OAuth, falha de contrato e falha de segurança devem possuir runbook acionável com RTO de até 60 minutos e RPO de até 15 minutos, testado trimestralmente.
- NFR13: Regressões de contrato REST/SSE em endpoints críticos devem bloquear 100% dos merges com breaking changes detectados por testes de contrato no pipeline CI.
- NFR14: O sistema deve suportar crescimento de até 3x da carga base por tenant sem violar SLOs dos fluxos críticos, validado por teste de carga semestral.
- NFR15: Mecanismos de limitação de consumo por usuário e tenant devem manter degradação de latência p95 abaixo de 20% em picos de até 2x da carga nominal, validado por teste de carga trimestral.
- NFR16: Integrações OAuth devem detectar expiração/revogação em até 60 segundos e concluir recuperação guiada em até 5 minutos para 95% dos casos, medido por eventos de integração.
- NFR17: Mudanças de contrato REST/SSE devem seguir versionamento semântico, changelog obrigatório e janela mínima de depreciação de 90 dias antes de breaking changes, verificado por gate de release.
- NFR18: Erros de integração devem expor causa classificada e próxima ação recomendada em 100% dos retornos de erro, validado por testes de contrato automatizados no CI.
- NFR19: Toda ação proativa deve registrar razão, contexto, nível de confiança, fallback e request_id em 100% dos eventos, auditado semanalmente.
- NFR20: Trilhas de auditoria devem garantir integridade verificável com cadeia de hash e retenção imutável mínima de 180 dias, validado automaticamente diariamente em 100% dos lotes.
- NFR21: Observabilidade deve permitir correlação por tenant, usuário, ação e fluxo em 100% dos eventos críticos, com consultas operacionais em até 5 segundos no p95, medido por dashboards de observabilidade.
- NFR22: Interfaces críticas de operação e aprovação devem atender WCAG 2.1 AA em 100% dos fluxos essenciais, validado por testes automáticos e auditoria manual mensal.
- NFR23: Fluxos de erro/sucesso devem fornecer feedback textual claro e navegação por teclado em 100% das jornadas críticas, validado por testes automáticos WCAG e checklist quinzenal.

### Additional Requirements

- Starter/Template: adotar Nx incremental monorepo init sobre stack atual (sem rebootstrap front/back).
- Arquitetura canônica de backend: endpoint -> service -> repository; workloads longos em workers via broker.
- Contratos de API: REST + SSE como padrão, versionamento /api/v1 e gates de contract tests no CI.
- Contrato de erro padrão: application/problem+json e padronização de erros SSE.
- Multi-tenancy obrigatório: scoping por tenant_id em dados, quotas, auditoria e telemetria.
- Segurança: TLS 1.2+, criptografia em repouso, rotação de segredos, RBAC tenant-aware.
- Observabilidade por fluxo crítico (chat stream, execução assistida, auditoria) com SLO/error budget.
- Resiliência de integrações OAuth/quotas com recuperação guiada e retentativas controladas.
- Migrações de schema: Alembic-first, eliminando drift de SQL manual.
- UX: layout operacional 3 painéis no desktop (contexto | chat/plano | auditoria/estados).
- UX: comportamento responsivo com colapso progressivo (esquerda -> direita), mantendo chat/plano fixo.
- UX: confirmação forte para ações sensíveis (nível de risco, impacto, escopo, confirmação explícita).
- UX: timeline de evidências sempre visível durante execução (run_id, estado, logs/objetos afetados).
- UX: fluxo keyboard-first (atalhos + command palette) como requisito de produtividade.
- UX: padrões de feedback determinístico para sucesso/erro com próxima ação recomendada.
- Acessibilidade: WCAG 2.1 AA global no MVP (prioridade nos fluxos críticos).
- Componentes customizados prioritários: Risk Approval Sheet, Execution Evidence Timeline, OAuth/Quota Recovery Banner, Next Best Action Panel.

### FR Coverage Map

### FR Coverage Map

FR1: Epic 1 - Tenant, Identidade e Controle de Acesso
FR2: Epic 1 - Tenant, Identidade e Controle de Acesso
FR3: Epic 1 - Tenant, Identidade e Controle de Acesso
FR4: Epic 1 - Tenant, Identidade e Controle de Acesso
FR5: Epic 1 - Tenant, Identidade e Controle de Acesso
FR6: Epic 1 - Tenant, Identidade e Controle de Acesso
FR7: Epic 3 - Execução Assistida com Governança de Risco
FR8: Epic 3 - Execução Assistida com Governança de Risco
FR9: Epic 3 - Execução Assistida com Governança de Risco
FR10: Epic 3 - Execução Assistida com Governança de Risco
FR11: Epic 3 - Execução Assistida com Governança de Risco
FR12: Epic 3 - Execução Assistida com Governança de Risco
FR13: Epic 2 - Conversa Contextual e Assistência Proativa
FR14: Epic 2 - Conversa Contextual e Assistência Proativa
FR15: Epic 2 - Conversa Contextual e Assistência Proativa
FR16: Epic 2 - Conversa Contextual e Assistência Proativa
FR17: Epic 2 - Conversa Contextual e Assistência Proativa
FR18: Epic 2 - Conversa Contextual e Assistência Proativa
FR19: Epic 3 - Execução Assistida com Governança de Risco
FR20: Epic 3 - Execução Assistida com Governança de Risco
FR21: Epic 3 - Execução Assistida com Governança de Risco
FR22: Epic 3 - Execução Assistida com Governança de Risco
FR23: Epic 3 - Execução Assistida com Governança de Risco
FR24: Epic 3 - Execução Assistida com Governança de Risco
FR25: Epic 4 - Integrações Externas e Recuperação Operacional
FR26: Epic 4 - Integrações Externas e Recuperação Operacional
FR27: Epic 4 - Integrações Externas e Recuperação Operacional
FR28: Epic 4 - Integrações Externas e Recuperação Operacional
FR29: Epic 4 - Integrações Externas e Recuperação Operacional
FR30: Epic 4 - Integrações Externas e Recuperação Operacional
FR31: Epic 5 - Auditoria, Compliance e Direitos de Dados
FR32: Epic 5 - Auditoria, Compliance e Direitos de Dados
FR33: Epic 5 - Auditoria, Compliance e Direitos de Dados
FR34: Epic 5 - Auditoria, Compliance e Direitos de Dados
FR35: Epic 5 - Auditoria, Compliance e Direitos de Dados
FR36: Epic 5 - Auditoria, Compliance e Direitos de Dados
FR37: Epic 6 - Contratos de Produto e Administração Operacional
FR38: Epic 6 - Contratos de Produto e Administração Operacional
FR39: Epic 6 - Contratos de Produto e Administração Operacional
FR40: Epic 6 - Contratos de Produto e Administração Operacional
