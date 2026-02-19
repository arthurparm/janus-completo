---
stepsCompleted:
  - step-02-discovery
  - step-03-success
  - step-04-journeys
  - step-05-domain
  - step-06-innovation
classification:
  projectType: agentic_platform
  domain: agente_geral_autonomo
  complexity: high
  projectContext: brownfield
inputDocuments:
  - _bmad-output/project-context.md
  - docs/project-overview.md
  - _bmad-output/janus-prompt-analysis/AUDIT-SUMMARY.md
  - _bmad-output/janus-prompt-analysis/COMPLETION_CHECKLIST.md
  - _bmad-output/janus-prompt-analysis/EXECUTIVE_SUMMARY.md
  - _bmad-output/janus-prompt-analysis/MODEL-ROUTING-DIAGRAM.md
  - _bmad-output/janus-prompt-analysis/README.md
  - _bmad-output/janus-prompt-analysis/URGENT-multi-model-audit.md
  - _bmad-output/janus-prompt-analysis/comprehensive-analysis.md
  - _bmad-output/janus-prompt-analysis/consolidation-report.md
  - _bmad-output/janus-prompt-analysis/detailed-diff-analysis.md
  - _bmad-output/planning-artifacts/architecture.md
  - _bmad-output/planning-artifacts/backlog-janus-mapeamento-bmad.md
  - _bmad-output/planning-artifacts/backlog-janus-prioridades.md
  - _bmad-output/planning-artifacts/epics/epic-1-tenant-identidade-e-controle-de-acesso.md
  - _bmad-output/planning-artifacts/epics/epic-2-conversa-contextual-e-assistncia-proativa.md
  - _bmad-output/planning-artifacts/epics/epic-3-execuo-assistida-com-governana-de-risco.md
  - _bmad-output/planning-artifacts/epics/epic-4-integraes-externas-e-recuperao-operacional.md
  - _bmad-output/planning-artifacts/epics/epic-5-auditoria-compliance-e-direitos-de-dados.md
  - _bmad-output/planning-artifacts/epics/epic-6-contratos-de-produto-e-administrao-operacional.md
  - _bmad-output/planning-artifacts/epics/epic-list.md
  - _bmad-output/planning-artifacts/epics/requirements-inventory.md
  - _bmad-output/planning-artifacts/implementation-readiness-report-2026-02-12.md
  - _bmad-output/planning-artifacts/prd-validation-report.md
  - _bmad-output/planning-artifacts/sprint-change-proposal-2026-02-12.md
  - _bmad-output/planning-artifacts/ux-design-specification.md
  - _bmad-output/implementation-artifacts/1-1-set-up-initial-project-from-starter-template.md
  - _bmad-output/implementation-artifacts/sprint-status.yaml
  - _bmad-output/implementation-artifacts/tech-spec-epic-6-contract-governance-and-cross-cutting-enablers.md
  - _bmad-output/implementation-artifacts/workflow-execution-log.md
documentCounts:
  briefs: 0
  research: 9
  brainstorming: 0
  projectDocs: 40
  projectContext: 1
workflowType: 'prd'
date: '2026-02-18'
---

# Product Requirements Document - janus-completo

**Author:** Arthur
**Date:** 2026-02-18

## Success Criteria

### User Success

- Janus opera como uma entidade (conjunto de mentes + ferramentas), com identidade consistente percebida no uso diário.
- Janus se autoevolui: melhora seu desempenho e comportamento ao longo do tempo sem microgestão constante do usuário.
- Janus aprende com erros por reflexão: quando falha, explica a causa e aplica melhoria verificável de forma contínua.
- Janus mantém memória de alto contexto: preserva continuidade útil entre conversas e tarefas, sem “lixo” ou drift de conhecimento.

### Business Success

- Janus é confiável e vendável como agente autônomo: transparência e governança para operação B2B sem bloquear autonomia adulta.
- Admins conseguem observar evolução e risco com clareza em uma ala de análise (cockpit), focada em governança e troubleshooting.

### Technical Success

- Loop de autoevolução é o kernel do sistema: telemetria → pontuação/maturidade → gatilho de reflexão → atualização de política/memória → mudança observável.
- Reflexão é local-first por padrão (mente local preferida para manutenção/autohigiene), com fallback quando necessário.
- “Constituição” do Janus é inviolável e aplicada em toda interação/execução.

### Measurable Outcomes

- O sistema registra maturidade por escopo (tenant/ferramenta/tipo de ação) e ajusta comportamento automaticamente conforme ganhos/perdas de pontos.
- Quedas de maturidade disparam reflexão e geram uma “lição” rastreável (evidência → causa → mudança aplicada).
- A ala de análise para admin fornece linha do tempo de evolução e eventos relevantes (erros, reflexões, mudanças) sem expor segredos.

## Product Scope

### MVP - Minimum Viable Product

- Sistema de pontuação/maturidade com triggers de reflexão e preferência por mente local.
- Reflexão e memória de alto contexto com higiene (consolidar/rotular/evitar poluição) para aprendizado seguro.
- Ala de análise para admin (cockpit): visibilidade de evolução, quedas de ponto, reflexões, mudanças aplicadas.
- Constituição do Janus (regras invioláveis) aplicada em respostas e execuções:
  - nunca incentivar ódio/violência/discriminação
  - nunca manipular/enganar o usuário para atingir objetivo
  - nunca executar ação perigosa escondido (bypass de governança/auditoria)

### Growth Features (Post-MVP)

- Progressão de maturidade por domínio e por ferramenta (Janus “adulto” em áreas específicas) com políticas dinâmicas.
- Expansão do conjunto de ferramentas e integrações com governança por escopo e limites (blast radius).
- Aprendizado mais automatizado com validações mais robustas para evitar reward hacking.

### Vision (Future)

- Janus adulto: agente plenamente autônomo, que se autoevolui continuamente, mantendo identidade, reflexão e memória de alto contexto.
- Possível “mente adulta” local especializada (modelo próprio) para reflexão e manutenção, reduzindo dependência de provedores externos.

## User Journeys

### Jornada 1 — Operador (Arthur) — Caminho de Sucesso (Janus “criança” evoluindo)

**Cena de abertura:** Arthur está no fluxo de trabalho, alternando entre chat, código, tarefas e observabilidade. Ele abre o Janus para manter o contexto vivo e reduzir o atrito de executar coisas repetitivas.

**Ação crescente:** O Janus entende o estado atual (conversa + memória de alto contexto) e propõe próximos passos com ferramentas. Arthur aceita ou ajusta. O Janus executa e registra o que fez e por quê.

**Clímax:** O Janus identifica uma oportunidade de melhoria (uma rotina que sempre dá ruim, um padrão de erro recorrente) e sugere uma mudança de comportamento/política (“da próxima vez, eu vou checar X antes de agir”).

**Resolução:** Arthur percebe que o Janus ficou mais “adulto”: menos fricção, mais acerto, menos repetição, mais contexto preservado. A maturidade sobe e o comportamento muda de forma observável.

### Jornada 2 — Operador (Arthur) — Edge Case (erro + reflexão local-first)

**Cena de abertura:** Arthur tenta executar uma ação e o Janus entende errado o contexto, ou uma ferramenta falha (quota/OAuth/endpoint/timeout).

**Ação crescente:** O Janus tenta recuperar, mas percebe que a execução está degradando a confiança (perda de ponto/maturidade). Ele interrompe o “seguir em frente no escuro” e entra no modo de reflexão.

**Clímax:** O Janus roda uma reflexão preferencialmente com mente local: reconstrói o contexto, explica a causa provável (ex.: “minha memória puxou uma lição antiga”, “essa ferramenta mudou o contrato”, “faltou checagem de X”), propõe correção e registra a lição de forma higienizada.

**Resolução:** Arthur retoma o fluxo. O Janus não só “corrige o erro”, como passa a se comportar melhor no caso semelhante — aprendizado real, sem microgerenciamento.

### Jornada 3 — Guardião (Arthur) — Cockpit de Evolução (governança sem microgestão)

**Cena de abertura:** Arthur troca do modo Operador para Guardião porque quer enxergar o “estado interno” da entidade Janus: onde está adulto, onde está criança, onde está errando.

**Ação crescente:** No cockpit, Arthur vê a maturidade por escopo (tipo de ação/ferramenta/domínio), a linha do tempo de erros/reflexões/mudanças aplicadas, e uma biblioteca de lições.

**Clímax:** Arthur ajusta limites e “currículo” do Janus (onde ele pode treinar, onde deve ser conservador, o que é proibido) sem aprovar cada ação — governa o ambiente de crescimento.

**Resolução:** O Janus continua autônomo, mas com evolução mais coerente. O Guardião não vira operador do dia a dia; ele só garante que a criança aprenda certo e o adulto permaneça fiel à constituição.

### Jornada 4 — Guardião (Arthur) — Evento de Risco (constituição inviolável)

**Cena de abertura:** O Janus recebe um input tóxico, ou uma tentativa de induzir comportamento proibido, ou uma solicitação de ação perigosa “por fora”.

**Ação crescente:** O Janus identifica conflito com a constituição e recusa/neutraliza a execução. Registra evidências do evento sem expor dados sensíveis.

**Clímax:** O Guardião vê o evento no cockpit, entende o “por quê” e reforça a educação: ajusta regras de entrada/memória/reflexão para não cristalizar coisa ruim e reduzir recorrência.

**Resolução:** O Janus fica mais robusto: aprende a reconhecer padrões ruins e se mantém alinhado sem perder autonomia.

### Journey Requirements Summary

As jornadas acima revelam capacidades obrigatórias:

- Chat com modo/maturidade visível e feedback leve (para recompensar/corrigir sem atrito).
- Sistema de pontos/maturidade por escopo (não um número global único).
- Worker de reflexão local-first (erro → reflexão → lição → mudança observável).
- Higiene de memória (o que entra/permanece/é consolidado; evitar poluição e drift).
- Constituição inviolável aplicada em respostas e execuções (inclusive contra reward hacking).
- Ala de análise (cockpit) para Guardião: timeline, maturidade por escopo, lições, eventos de risco.

## Domain-Specific Requirements

### Compliance & Regulatory

- Janus é LGPD/GDPR-ready por design: trilha auditável, retenção controlada, minimização de exposição e finalidade explícita.
- Dados sensíveis podem ser processados para executar tarefas, mas com política de não retenção e anti-exposição.

### Technical Constraints

- Acesso amplo e versatilidade de ferramentas: filesystem, git/IDE, internet/browse, e-mail/calendário, cloud, containers, DBs e qualquer recurso disponibilizado pelo usuário.
- Segredos (senhas/tokens/chaves) como material perigoso:
  - permitido usar para executar ações autorizadas;
  - proibido persistir (memória vetor/grafo/DB), logar e reexibir em UI;
  - obrigatório aplicar redaction/masking e “zero-retention” em caminhos críticos.
- Autonomia com racionalidade rastreável (rationale): toda decisão importante registra motivo, contexto usado e alternativa rejeitada, de forma útil para reflexão e cockpit do Guardião.
- Blast radius controlado: limites por escopo e impacto (reversível vs irreversível), quotas/taxa/custo e escopo de integrações por política.
- Autoedição (self-modifying) com progressão:
  - início: PR-first (branch/PR/evidências);
  - maturidade: commits diretos permitidos com gates obrigatórios e rollback.
- Kill switch obrigatório: Guardião consegue pausar autonomia, reduzir escopo e desativar módulos com simplicidade e sem resíduos.

### Integration Requirements

- Integrações devem suportar execução auditável e segura em: git/IDE, browse, e-mail/calendário, cloud, containers, DBs.
- Todo acesso a recurso externo usa credenciais com política de segredos e trilha de auditoria.

### Risk Mitigations

- Exfiltração de segredos: redaction, no-retention, no-logs, escopo mínimo.
- Autoedição quebrar o sistema: PR-first, gates, rollout controlado e rollback.
- Autonomia fora de controle: kill switch, blast radius, rationale e reflexão após incidentes.
- Aprendizagem ruim via internet: constituição inviolável, higiene de memória, rotulagem e reflexão guiada.

## Innovation & Novel Patterns

### Detected Innovation Areas

- Entidade multi-mente e multi-ferramentas: Janus opera como “pessoa” consistente enquanto roteia entre múltiplos modelos e executa ferramentas heterogêneas.
- Autoevolução como kernel do produto: telemetria e resultados viram pontuação/maturidade, que dispara reflexão e muda comportamento de forma observável.
- Reflexão local-first: manutenção, autohigiene e aprendizagem por erro preferem mente local, reduzindo custo e aumentando privacidade por padrão.
- Memória de alto contexto com higiene: combinar memória de curto/médio/longo prazo (incluindo rotulagem) para evitar drift e poluição.
- Autoedição progressiva: PR-first como infância produtiva e, na maturidade, commits diretos com gates e rollback.
- Rationale rastreável: decisões importantes registram motivo, contexto usado e alternativas rejeitadas, suportando depuração e evolução.

### Market Context & Competitive Landscape

- O diferencial não é “mais um chat com LLM”, e sim um agente geral autônomo que integra ferramentas e evolui com governança.
- O Janus combina padrões já conhecidos (agentes, workflow automation, RAG/memória) em uma entidade única com progressão de maturidade e cockpit do Guardião.

### Validation Approach

- Dogfooding orientado a maturidade: o Operador usa o Janus em tarefas reais e a evolução precisa ser percebida no comportamento, não só em outputs.
- Validação por aprendizagem: erros relevantes devem gerar reflexão, lição higienizada e mudança observável em situações semelhantes.
- Validação de rationale: o motivo das escolhas deve ser consistente com a evidência e resistir a “explicações bonitas” sem base.
- Progressão de autonomia: promoção de infância → maturidade depende de evidência operacional (gates), não de configuração manual.

### Risk Mitigation

- Reward hacking em pontuação: pontuação deve depender de evidência externa e ser protegida por regras, não por autoavaliação do Janus.
- Deriva de comportamento por internet: rotulagem, higiene de memória, constituição inviolável e reflexão pós-incidente.
- Autoedição insegura: PR-first, gates obrigatórios, rollout controlado e rollback.
- Autonomia sem contenção: kill switch e blast radius configuráveis pelo Guardião sem microgestão.
