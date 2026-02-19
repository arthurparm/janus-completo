---
stepsCompleted:
  - step-01-init
  - step-02-discovery
  - step-03-success
  - step-04-journeys
  - step-05-domain
  - step-06-innovation
  - step-07-project-type
  - step-08-scoping
  - step-09-functional
  - step-10-nonfunctional
  - step-11-polish
  - step-12-complete
  - step-e-01-discovery
  - step-e-02-review
  - step-e-03-edit
inputDocuments:
  - '_bmad-output/project-context.md'
  - 'docs/api-contracts-front.md'
  - 'docs/api-contracts-janus.md'
  - 'docs/architecture-front.md'
  - 'docs/architecture-janus.md'
  - 'docs/component-inventory-front.md'
  - 'docs/component-inventory-janus.md'
  - 'docs/contribution-guide.md'
  - 'docs/data-models-front.md'
  - 'docs/data-models-janus.md'
  - 'docs/deployment-guide.md'
  - 'docs/development-guide-front.md'
  - 'docs/development-guide-janus.md'
  - 'docs/index.md'
  - 'docs/integration-architecture.md'
  - 'docs/project-overview.md'
  - 'docs/source-tree-analysis.md'
documentCounts:
  briefs: 0
  research: 0
  brainstorming: 0
  projectDocs: 16
  projectContext: 1
workflowType: 'prd'
workflow: 'edit'
date: '2026-02-12T00:00:00-03:00'
lastEdited: '2026-02-12T00:30:00-03:00'
editHistory:
  - date: '2026-02-12T00:30:00-03:00'
    changes: 'Refinamento completo de Success Criteria de negócio, Subscription Tiers, cadência de Validation Approach e critérios de saída por fase.'
classification:
  projectType: saas_b2b
  domain: general
  complexity: high
  projectContext: brownfield
---
# Product Requirements Document - janus-completo

**Author:** Arthur
**Date:** 2026-02-11T19:55:22-03:00

## Executive Summary

Janus Completo é uma plataforma SaaS B2B de operações técnicas assistidas por IA, com foco em produtividade, governança e auditabilidade.

O produto resolve o problema de execução operacional fragmentada entre múltiplas ferramentas, oferecendo conversa contextual, automação assistida e controles explícitos de risco.

O diferencial do MVP é combinar proatividade, human-in-the-loop para ações sensíveis, integrações OAuth com telemetria ponta a ponta e trilhas de compliance prontas para auditoria.

## Success Criteria
### User Success

- Usuários de operações técnicas recebem sugestões contextuais e acionáveis em tempo real durante o chat, com contexto de memória/RAG e estado das integrações.
- Usuários concluem ações assistidas sensíveis com consentimento explícito e aprovação humana, com feedback claro de sucesso/erro ponta a ponta.
- O momento de valor percebido ocorre quando o usuário delega uma tarefa operacional e o Janus conduz execução assistida com governança, sem perda de controle.

### Business Success

- Aumentar em 25% a adoção de fluxos assistidos em contas B2B ativas até 2 trimestres após o release do MVP, medido por usuários ativos semanais em jornadas assistidas.
- Reduzir em 30% o tempo médio de conclusão de tarefas operacionais recorrentes em até 6 meses, medido por comparação pré e pós-implantação.
- Atingir taxa mínima de 70% de aceitação de sugestões proativas qualificadas até o fim do 2º trimestre pós-MVP, medido por telemetria de sugestões aceitas vs. exibidas.


### Technical Success

- Ações sensíveis exigem consentimento explícito e trilha de aprovação humana auditável por usuário, ação e timestamp.
- Endpoints críticos REST/SSE possuem testes de contrato automatizados e bloqueio de regressão no pipeline de CI.
- Fluxos OAuth Google, quotas e tratamento de erro/sucesso são consistentes no backend, frontend e telemetria operacional.
- SLOs operacionais, alertas e painéis de auditoria/uso por usuário são definidos e ativos para monitoramento contínuo.

### Measurable Outcomes

- 100% das ações classificadas como sensíveis passam por consentimento explícito e checkpoint de aprovação humana antes da execução.
- 100% dos endpoints REST/SSE classificados como críticos são cobertos por testes de contrato automatizados no CI.
- 100% dos fluxos OAuth/quotas instrumentados com eventos de sucesso/erro fim-a-fim e rastreabilidade por usuário.
- SLOs definidos para fluxos críticos de conversa/execução com alertas ativos e evidência em painéis operacionais.

## Product Scope

### MVP - Minimum Viable Product

- Governança de ações sensíveis com consentimento explícito e human-in-the-loop obrigatório.
- Testes de contrato para endpoints críticos REST/SSE com validação contínua em CI.
- Integração OAuth Google funcional com quotas claras e UX de erro/sucesso ponta a ponta.
- Baseline operacional com SLOs iniciais, alertas e painel de auditoria/uso por usuário.
- Meta de maturidade de compliance explícita no produto: baseline LGPD/GDPR-ready e trilhas SOC2-ready.

### Growth Features (Post-MVP)

- Políticas de governança adaptativas por tenant/perfil de risco com regras mais granulares de aprovação.
- Expansão de integrações de produtividade (e-mail, calendário, notas) com automações compostas entre sistemas.
- Evolução de observabilidade para análises preditivas de uso, risco operacional e qualidade de execução agêntica.

### Vision (Future)

- Janus opera como copiloto proativo de operações técnicas, antecipando necessidades com autonomia assistida e governança contínua.
- Orquestração multiagente confiável, auditável e personalizável por domínio/empresa com políticas de compliance por região.
- Plataforma de automação de trabalho do conhecimento com memória contextual persistente e execução segura em larga escala.

### Out of Scope

- Desenvolvimento de aplicativo mobile nativo (iOS/Android) no MVP.
- Cobertura de integrações não produtivas além do escopo definido em Integration List.
- Automação totalmente autônoma sem checkpoints de governança para ações sensíveis.

## User Journeys

### Jornada 1 - Usuario Primario (Operacoes Tecnicas) - Caminho de Sucesso

**Abertura:** Camila, analista de operacoes, inicia o dia com varias demandas cruzadas entre chat, e-mail e calendario. Ela abre o Janus para priorizar o que executar primeiro.

**Ascensao:** Durante a conversa, o Janus usa contexto de memoria/RAG e sinaliza proximas acoes recomendadas. Camila valida as sugestoes, ajusta parametros e escolhe executar uma automacao assistida.

**Climax:** Em uma acao classificada como sensivel, o sistema exige consentimento explicito e checkpoint de aprovacao humana. Camila aprova com clareza do impacto esperado.

**Resolucao:** A execucao conclui com retorno fim-a-fim (status, evidencias e proximo passo). Camila reduz retrabalho e conclui a tarefa com rastreabilidade completa.

### Jornada 2 - Usuario Primario (Operacoes Tecnicas) - Edge Case e Recuperacao

**Abertura:** Rafael tenta executar uma automacao em horario critico, com dependencia de integracao externa e limite de quota proximo do teto.

**Ascensao:** O Janus inicia o fluxo, mas detecta erro de quota/OAuth e bloqueia continuidade insegura. Rafael recebe feedback objetivo sobre causa, impacto e acao recomendada.

**Climax:** Rafael reautoriza acesso OAuth e replaneja a execucao com parametros seguros. O sistema reaproveita contexto anterior sem perder historico.

**Resolucao:** A tarefa e retomada com sucesso e o incidente fica registrado para auditoria. O usuario sente controle mesmo em falha parcial, com recuperacao guiada.

### Jornada 3 - Admin de Governanca e Compliance

**Abertura:** Julia, administradora da plataforma, precisa revisar acoes sensiveis executadas por equipes e validar aderencia a politicas internas.

**Ascensao:** Ela acessa painel de auditoria por usuario/acao/tenant, filtra eventos de alto risco e identifica fluxos que exigiram aprovacao humana.

**Climax:** Julia encontra uma tentativa de execucao sem requisitos completos e confirma que o bloqueio de governanca foi aplicado corretamente.

**Resolucao:** Ela ajusta politicas de aprovacao para reduzir risco operacional e exporta trilha de auditoria para revisao de compliance.

### Jornada 4 - Operacoes/SRE

**Abertura:** Diego, responsavel por confiabilidade, monitora qualidade do servico em periodo de alta carga.

**Ascensao:** Alertas apontam degradacao em fluxo SSE critico. Diego correlaciona latencia, erros de contrato e falhas de worker em um unico painel.

**Climax:** Ele aplica acao de mitigacao (rollback controlado e reprocessamento), acompanhando impacto no SLO em tempo real.

**Resolucao:** O servico volta ao alvo acordado e o postmortem fica associado a metricas, logs e eventos auditaveis por usuario.

### Jornada 5 - Desenvolvedor de Integracao/API

**Abertura:** Bruno, engenheiro de integracoes, precisa conectar um novo sistema de produtividade ao Janus sem quebrar fluxos existentes.

**Ascensao:** Ele configura OAuth, define quotas e valida contratos REST/SSE em pipeline automatizado. Regras de erro/sucesso sao testadas ponta a ponta.

**Climax:** Um teste de contrato falha antes do deploy, revelando regressao de payload em endpoint critico.

**Resolucao:** Bruno corrige o contrato, reexecuta os testes e publica a integracao com seguranca, evitando incidente em producao.

### Journey Requirements Summary

As jornadas revelam capacidades obrigatorias:

- Motor de sugestoes proativas com contexto em tempo real (chat + memoria/RAG + estado de integracoes).
- Governanca de acoes sensiveis com consentimento explicito, aprovacao humana e trilha auditavel.
- Fluxos resilientes de erro/recuperacao para OAuth, quotas e dependencias externas.
- Contratos REST/SSE versionados e protegidos por testes de contrato no CI.
- Observabilidade operacional com SLOs, alertas e paineis por usuario/tenant/acao.
- Controles de administracao para politicas, auditoria e analise de risco.
- Suporte a integracoes com feedback fim-a-fim e diagnostico orientado a causa.

## Domain-Specific Requirements

### Compliance & Regulatory

- Meta de maturidade: LGPD/GDPR-ready com trilha SOC2-ready.
- DSAR operacional com fluxo explícito para acesso, exportação e exclusão de dados, com SLA e evidência auditável.
- Política de residência e transferência de dados para provedores externos/LLMs e processamento cross-border.
- Política de retenção/exclusão por tipo de dado e por tenant.

### Technical Constraints

- Data governance por tenant com isolamento lógico obrigatório; trilhas e quotas sempre particionadas por tenant.
- Criptografia mandatória em trânsito e em repouso, com rotação de segredos/chaves e inventário de secrets.
- Integridade da auditoria com encadeamento/hash e política anti-tampering (imutabilidade verificável).
- Rastreabilidade de decisão automática: cada ação proativa registra razão, contexto, confiança e fallback aplicado.
- Resiliência de execução: retry controlado, idempotência e compensação/rollback em ações críticas.

### Integration Requirements

- OAuth Google com estados explícitos de autorização, expiração e reautorização.
- Governança de mudanças de contrato: versionamento semântico REST/SSE, janela de depreciação e changelog obrigatório.
- Contratos REST/SSE críticos protegidos por testes de contrato automatizados com gate no CI.
- Telemetria fim-a-fim em integrações: sucesso, falha, causa raiz e impacto no usuário.

### Risk Mitigations

- Matriz de risco de ações com regras de aprovação: baixo automático, médio com confirmação explícita, alto com human-in-the-loop obrigatório.
- Plano de resposta a incidentes com runbooks para falha de OAuth, falha de contrato e incidente de segurança, com RTO/RPO definidos.
- SLO + error budget por fluxo crítico (chat stream, ações de produtividade e auditoria) usados como gate de release.
## Innovation & Novel Patterns

### Detected Innovation Areas

- Assistente agêntico proativo que antecipa necessidades com contexto em tempo real, em vez de responder apenas sob demanda.
- Automação de workflows com governança adaptativa por risco (consentimento, aprovação humana e trilha auditável).
- Combinação operacional de chat, memória/RAG, execução assistida e controles de compliance no mesmo fluxo de valor.

### Market Context & Competitive Landscape

- O diferencial central não é apenas chat com IA, mas execução assistida confiável com controle humano e auditabilidade.
- No contexto B2B, a vantagem competitiva está na confiança operacional: contratos estáveis, rastreabilidade e prevenção de ações indevidas.

### Validation Approach

- Validar proatividade por taxa de aceitação de sugestões e redução do tempo de conclusão de tarefas.
- Validar confiança por adesão ao fluxo de aprovação em ações sensíveis e redução de incidentes operacionais.
- Validar robustez por cobertura de contratos REST/SSE, SLO/error budget por fluxo crítico e estabilidade das integrações OAuth.
- **Cadência de revisão:** operacional semanal (Produto + Engenharia), tática mensal (Produto + SRE + QA) e executiva trimestral (Produto + Liderança).
- **Responsáveis:** PM (metas de produto), Tech Lead (contratos e arquitetura), SRE Lead (SLO/error budget), QA Lead (cobertura e gates).
- **Gatilhos de recalibração:** desvio >10% em KPIs por 2 semanas, estouro de error budget em fluxo crítico, ou regressão de contrato bloqueando release.


### Risk Mitigation

- Fallback obrigatório para modo assistivo não proativo quando a confiança/contexto estiver insuficiente.
- Bloqueio automático de execução para ações de alto risco sem aprovação humana.
- Rollback/compensação para falhas de integração e regressões de contrato detectadas no CI.

## SaaS B2B Specific Requirements

### Project-Type Overview

- Janus será tratado como plataforma SaaS B2B agêntica para operações técnicas, com experiência principal em conversa, automação assistida e execução governada.
- O valor central do tipo de produto está em combinar produtividade operacional com segurança, controle e auditabilidade por tenant.

### Technical Architecture Considerations

- Arquitetura multi-tenant com isolamento lógico obrigatório e particionamento consistente de dados, quotas, auditoria e telemetria por tenant.
- Modelo de autorização baseado em RBAC com suporte a políticas de risco para ações proativas e sensíveis.
- Integrações externas com contratos estáveis REST/SSE, versionamento semântico e janelas de depreciação para evitar quebra em clientes.
- Capacidade operacional para observabilidade por fluxo crítico (chat stream, produtividade, auditoria), com SLO e error budget como gate de release.

### Tenant Model

- Decisão de PRD: multi-tenant com isolamento lógico obrigatório no MVP, incluindo segregação por `tenant_id` em dados operacionais, auditoria e quotas.
- Evolução pós-MVP prevista para controles diferenciados por perfil de risco e requisitos de clientes enterprise.

### RBAC Matrix

- Papéis mínimos no MVP: Owner, Admin, Operator, Auditor e Integration Service.
- Owner/Admin: gestão de tenant, políticas e integrações.
- Operator: execução assistida dentro de políticas de risco.
- Auditor: leitura de trilhas, evidências e conformidade.
- Integration Service: escopo técnico restrito para chamadas automatizadas.

### Subscription Tiers

- **Starter (MVP):** até 5 usuários por tenant, 1 integração OAuth ativa, retenção de auditoria por 90 dias, suporte em horário comercial (8x5).
- **Pro (MVP):** até 50 usuários por tenant, até 3 integrações ativas, retenção de auditoria por 180 dias, suporte estendido (12x5), exportação de auditoria sob demanda.
- **Enterprise (MVP):** usuários e integrações sob contrato, SSO/SAML opcional, retenção mínima de 365 dias, suporte prioritário (24x5), política de governança personalizada por tenant.
- Revisões comerciais de preço e limites ocorrem trimestralmente, mantendo os critérios técnicos mínimos acima como baseline obrigatório do PRD.


### Integration List

- MVP: OAuth Google, fluxos críticos de calendário/e-mail/notas com feedback de erro/sucesso ponta a ponta.
- Pós-MVP: ampliação de integrações de produtividade e automações compostas entre sistemas.
- Todas as integrações devem fornecer telemetria rastreável por usuário, tenant e ação.

### Compliance Requirements

- Compliance forte como requisito de produto: LGPD/GDPR-ready com trilha SOC2-ready.
- DSAR operacional auditável, política de residência/transferência de dados, criptografia mandatória e anti-tampering em auditoria.
- Governança de contratos com changelog obrigatório e depreciação controlada para mudanças de API/SSE.

### Implementation Considerations

- Priorizar implementação incremental: governança + contratos + confiabilidade operacional no núcleo do MVP.
- Tratar requisitos de compliance e observabilidade como capacidades de plataforma, não como pós-processo.
- Garantir rastreabilidade de decisões automáticas (razão, contexto, confiança e fallback) desde a primeira entrega.

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach:** MVP orientado a confiança operacional (risk-first), validando proatividade com governança.
**Resource Requirements:** Time mínimo multifuncional com Produto, Frontend, Backend, QA/Contratos e Operações/SRE.

### MVP Feature Set (Phase 1)

**Core User Journeys Supported:**

- Operador técnico no fluxo de sucesso com sugestão proativa e execução assistida.
- Operador em edge case com recuperação guiada de OAuth/quota.
- Admin/Auditor com trilha auditável e aprovação de ações sensíveis.

**Must-Have Capabilities:**

- Classificação de risco e política de aprovação (baixo automático, médio com confirmação, alto com human-in-the-loop).
- Contratos REST/SSE críticos com testes de contrato em CI como gate.
- OAuth Google com estados claros de erro/sucesso e reautorização.
- SLO + error budget para chat stream, ações de produtividade e auditoria.
- DSAR operacional com evidência auditável básica e segregação por tenant.

**Exit Criteria Phase 1:**

- 100% dos endpoints REST/SSE críticos com testes de contrato em gate de CI.
- >= 95% das ações de alto risco com trilha completa de aprovação humana.
- p95 de primeira resposta do chat <= 2s em ambiente de produção por 4 semanas consecutivas.

### Post-MVP Features

**Phase 2 (Post-MVP):**

- Governança adaptativa por tenant e perfil de risco.
- Expansão de integrações e automações compostas.
- Observabilidade avançada para análise preditiva de risco e uso.
- **Exit Criteria Phase 2:** >= 80% de cobertura de contratos críticos, <= 2 incidentes P1/mês e retenção de uso assistido >= 60% nas contas ativas.

**Phase 3 (Expansion):**

- Orquestração multiagente avançada com políticas por região e compliance.
- Produto proativo em escala com maior autonomia assistida e fallback inteligente.
- Pacotes enterprise com maturidade formal de compliance ampliada.
- **Exit Criteria Phase 3:** expansão para 2+ segmentos enterprise, SLOs críticos estáveis por 2 trimestres e auditoria externa sem não conformidades críticas.


### Risk Mitigation Strategy

**Technical Risks:** regressão de contrato, falhas OAuth/integradores e degradação SSE.
Mitigação: CI com contrato obrigatório, runbooks e rollback/compensação, observabilidade por fluxo.

**Market Risks:** baixa adesão à proatividade por fricção de controle.
Mitigação: medir aceitação de sugestões e calibrar autonomia por risco e tenant.

**Resource Risks:** sobrecarga de escopo entre compliance e confiabilidade no mesmo ciclo.
Mitigação: travar MVP em governança, contratos e SLO; adiar customizações avançadas para fase 2.

## Functional Requirements

### Gestão de Tenant e Identidade

- FR1: Usuários podem pertencer a um tenant específico para operar o produto.
- FR2: Administradores podem criar e manter configurações de tenant.
- FR3: Administradores podem definir políticas de acesso por tenant.
- FR4: Usuários podem autenticar-se por provedores externos suportados.
- FR5: Administradores podem revogar sessões e acessos ativos de usuários.
- FR6: Sistema pode aplicar segregação de dados por tenant em todas as capacidades funcionais.

### Governança de Ações e Aprovação

- FR7: Sistema pode classificar ações por nível de risco.
- FR8: Usuários podem fornecer consentimento explícito antes de ações sensíveis.
- FR9: Sistema pode exigir aprovação humana para ações classificadas como alto risco.
- FR10: Aprovadores podem aprovar ou rejeitar ações pendentes com justificativa.
- FR11: Sistema pode bloquear execução de ação quando pré-condições de governança não forem atendidas.
- FR12: Usuários podem visualizar o estado de governança de cada ação solicitada.

### Conversa Proativa e Assistência Contextual

- FR13: Usuários podem interagir com o Janus por conversação contínua.
- FR14: Sistema pode sugerir próximas ações com base no contexto da conversa.
- FR15: Usuários podem aceitar, ajustar ou recusar sugestões proativas.
- FR16: Sistema pode registrar o contexto utilizado para cada sugestão apresentada.
- FR17: Usuários podem retomar contexto de conversas anteriores relevantes.
- FR18: Sistema pode operar em modo assistivo não proativo quando necessário.

### Execução Assistida de Tarefas

- FR19: Usuários podem iniciar execuções assistidas de tarefas operacionais.
- FR20: Sistema pode orquestrar execução em múltiplas etapas com estado rastreável.
- FR21: Usuários podem cancelar execuções em andamento quando permitido por política.
- FR22: Sistema pode retomar fluxo após falha recuperável sem perda de contexto.
- FR23: Usuários podem visualizar resultado final da execução com evidências associadas.
- FR24: Sistema pode acionar fallback operacional quando execução automática não for segura.

### Integrações e Conectividade

- FR25: Usuários podem conectar contas externas suportadas via fluxo de autorização.
- FR26: Sistema pode detectar estado inválido de autorização e solicitar reautorização.
- FR27: Sistema pode aplicar quotas de uso por usuário e por tenant.
- FR28: Usuários podem visualizar motivo de falha de integração e próxima ação recomendada.
- FR29: Sistema pode manter catálogo de integrações habilitadas por tenant.
- FR30: Administradores podem ativar ou desativar integrações por tenant.

### Auditoria, Compliance e Direitos de Dados

- FR31: Sistema pode registrar trilha de auditoria para ações e decisões relevantes.
- FR32: Auditores podem consultar eventos por usuário, tenant, ação e período.
- FR33: Sistema pode preservar evidências de decisão automática (razão, contexto, confiança e fallback).
- FR34: Usuários autorizados podem solicitar acesso aos próprios dados.
- FR35: Usuários autorizados podem solicitar exportação de dados em formato suportado.
- FR36: Usuários autorizados podem solicitar exclusão de dados conforme política aplicável.

### Contratos de Produto e Administração Operacional

- FR37: Sistema pode versionar contratos funcionais de APIs e eventos suportados.
- FR38: Usuários técnicos podem consultar mudanças de contrato e status de depreciação.
- FR39: Administradores podem visualizar painéis de uso e auditoria por tenant.
- FR40: Operações podem registrar e acompanhar incidentes operacionais com vínculo às capacidades afetadas.

## Non-Functional Requirements

### Performance

- NFR1: Fluxos de interação de chat devem apresentar primeira resposta parcial em até 2 segundos (p95) em condições normais de operação, medido continuamente por APM.
- NFR2: Ações de produtividade síncronas devem retornar status inicial em até 3 segundos para pelo menos 95% das requisições, medido por tracing de API.
- NFR3: Painéis de auditoria por tenant devem carregar filtros principais em até 5 segundos para pelo menos 95% das consultas padrão, medido por monitoramento sintético diário.

### Security

- NFR4: Dados em trânsito devem usar criptografia TLS 1.2+ em 100% das comunicações externas e internas sensíveis, verificado por scanner de segurança semanal.
- NFR5: Dados em repouso devem permanecer criptografados com AES-256 em 100% dos armazenamentos de produção, verificado por varredura automatizada diária e auditoria mensal.
- NFR6: Segredos e chaves devem ser rotacionados no máximo a cada 90 dias, com 100% dos segredos catalogados por ambiente e conformidade medida por job diário de inventário.
- NFR7: Ações classificadas como alto risco devem exigir aprovação humana em 100% dos casos antes da execução, auditado mensalmente por trilhas de governança.

### Compliance & Data Governance

- NFR8: Operações de DSAR (acesso, exportação, exclusão) devem manter trilha auditável completa em 100% dos casos; SLA: acesso/exportação em até 15 dias corridos e exclusão em até 30 dias, medido mensalmente.
- NFR9: Quotas, trilhas e políticas devem ser aplicadas com particionamento por tenant em 100% dos fluxos críticos, validado por testes mensais de isolamento.
- NFR10: Transferências para provedores externos/LLMs devem aplicar política de residência de dados em 100% das requisições, com bloqueio automático em violações e medição por logs do policy engine.

### Reliability

- NFR11: Fluxos críticos (chat stream, execução assistida e auditoria) devem operar com SLO definido e monitoramento ativo.
- NFR12: Incidentes de falha OAuth, falha de contrato e falha de segurança devem possuir runbook acionável com RTO de até 60 minutos e RPO de até 15 minutos, testado trimestralmente.
- NFR13: Regressões de contrato REST/SSE em endpoints críticos devem bloquear 100% dos merges com breaking changes detectados por testes de contrato no pipeline CI.

### Scalability

- NFR14: O sistema deve suportar crescimento de até 3x da carga base por tenant sem violar SLOs dos fluxos críticos, validado por teste de carga semestral.
- NFR15: Mecanismos de limitação de consumo por usuário e tenant devem manter degradação de latência p95 abaixo de 20% em picos de até 2x da carga nominal, validado por teste de carga trimestral.

### Integration

- NFR16: Integrações OAuth devem detectar expiração/revogação em até 60 segundos e concluir recuperação guiada em até 5 minutos para 95% dos casos, medido por eventos de integração.
- NFR17: Mudanças de contrato REST/SSE devem seguir versionamento semântico, changelog obrigatório e janela mínima de depreciação de 90 dias antes de breaking changes, verificado por gate de release.
- NFR18: Erros de integração devem expor causa classificada e próxima ação recomendada em 100% dos retornos de erro, validado por testes de contrato automatizados no CI.

### Auditability & Operability

- NFR19: Toda ação proativa deve registrar razão, contexto, nível de confiança, fallback e request_id em 100% dos eventos, auditado semanalmente.
- NFR20: Trilhas de auditoria devem garantir integridade verificável com cadeia de hash e retenção imutável mínima de 180 dias, validado automaticamente diariamente em 100% dos lotes.
- NFR21: Observabilidade deve permitir correlação por tenant, usuário, ação e fluxo em 100% dos eventos críticos, com consultas operacionais em até 5 segundos no p95, medido por dashboards de observabilidade.

### Accessibility

- NFR22: Interfaces críticas de operação e aprovação devem atender WCAG 2.1 AA em 100% dos fluxos essenciais, validado por testes automáticos e auditoria manual mensal.
- NFR23: Fluxos de erro/sucesso devem fornecer feedback textual claro e navegação por teclado em 100% das jornadas críticas, validado por testes automáticos WCAG e checklist quinzenal.



