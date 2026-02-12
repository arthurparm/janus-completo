# Sprint Change Proposal - janus-completo

**Data:** 2026-02-12  
**Workflow:** Correct Course  
**Modo:** Batch  
**Autor:** Arthur

## 1. Issue Summary

### Problema que disparou a correção de rota
Durante o readiness e a revisão adversarial, foram identificados problemas de integridade e qualidade nos artefatos de planejamento de épicos/stories, bloqueando um handoff seguro para implementação.

### Contexto de descoberta
- Origem: `_bmad-output/planning-artifacts/implementation-readiness-report-2026-02-12.md`
- Sintomas: inconsistências estruturais em shards, rastreabilidade incompleta e critérios de aceite sem métrica operacional clara.

### Evidências objetivas
- `requirements-inventory.md` com heading `### FR Coverage Map` duplicado.
- `epic-list.md` com resíduo de template (`Repeat for each epic...`).
- Stories sem rastreabilidade explícita de NFR (`NFRs` ausente nas stories).
- Story 1.1 com escopo misto (foundation técnica + funcionalidade de tenant).
- ACs vagas e lacunas em cenários negativos para fluxos sensíveis.

## 2. Impact Analysis

### Epic Impact
- **Epic 1**: impacto alto (Story 1.1 precisa split de escopo).
- **Epics 2-6**: impacto moderado (rastreabilidade NFR por story e ACs mensuráveis).
- Estrutura geral de épicos permanece válida; problemas concentram-se em qualidade de decomposição e governança de requisitos.

### Story Impact
- Stories afetadas diretamente: 1.1 (split), 3.2/3.3/3.5 (hardening de cenários negativos e limites operacionais).
- Stories afetadas transversalmente: todas as 32 stories (adição de mapeamento NFR e padronização de ACs mensuráveis).

### Artifact Conflicts
- **PRD**: sem conflito de visão; precisa reforço de regra story-level (FR/NFR + AC mensurável para sensíveis).
- **Architecture**: sem conflito de direção; precisa contrato explícito de governança de artefatos e qualidade de stories.
- **UX**: alinhado em visão; falta explicitar estados-limite (expiração, concorrência, rollback) nos fluxos sensíveis.
- **Epics shards**: precisam sanitização estrutural e editorial.

### Technical Impact
- Baixo impacto em código neste momento (não há implementação ativa em `implementation-artifacts`).
- Alto impacto em prontidão de implementação, rastreabilidade e confiabilidade do backlog.

## 3. Recommended Approach

### Opções avaliadas
- **Option 1 - Direct Adjustment**: VIÁVEL (recomendado)
- **Option 2 - Potential Rollback**: NÃO VIÁVEL (não há base implementada para rollback)
- **Option 3 - PRD MVP Review**: NÃO RECOMENDADO agora (problema é de qualidade de artefato, não de objetivo de MVP)

### Caminho recomendado
**Direct Adjustment (Option 1)** com hardening de artefatos e backlog antes de Sprint Planning.

### Racional
- Menor risco e menor custo de correção.
- Preserva direção estratégica do produto.
- Remove bloqueios objetivos para implementação controlada.

### Esforço, risco e impacto de cronograma
- **Esforço:** Médio
- **Risco:** Baixo-Médio
- **Impacto de cronograma:** atraso curto para saneamento, compensado por menor retrabalho na implementação.

## 4. Detailed Change Proposals

### A) Epics/Stories (shards)
1. Remover heading duplicado em `requirements-inventory.md` (`FR Coverage Map`).
2. Remover comentário residual de template em `epic-list.md`.
3. Definir artefato canônico `epics.md` em UTF-8 e regenerar shards a partir dele.
4. Split da Story 1.1:
   - 1.1: setup Nx incremental e pipeline (foundation)
   - nova story funcional de tenant (provisionamento inicial)
5. Adicionar `**NFRs:**` explícito por story em todos os épicos.
6. Tornar ACs mensuráveis (SLA/latência/estado/evidência) e remover termos vagos sem métrica.
7. Hardening de fluxos sensíveis (expiração de aprovação, conflito concorrente, idempotência, rollback/compensação).

### B) PRD
Adicionar regra operacional de qualidade de backlog no MVP:
- toda story deve declarar FR/NFR aplicáveis e AC mensurável, incluindo cenários de falha para ações sensíveis.

### C) Architecture
Adicionar subseção de contrato de governança de artefatos:
- canônico UTF-8, shards derivados, sem resíduos de template, rastreabilidade FR/NFR por story, ACs mensuráveis.

### D) UX Specification
Adicionar estados-limite nos componentes e jornadas sensíveis:
- expiração de aprovação, concorrência de decisão, rollback/compensação, feedback confiável desses estados.

## 5. Implementation Handoff

### Classificação de escopo
**Moderate** (requer reorganização de backlog e coordenação PO/SM antes do desenvolvimento).

### Handoff recipients
- **PO/SM:** coordenar ajuste de backlog, split de stories e critérios de aceite.
- **Architect:** validar aderência com Architecture e contrato de artefatos.
- **UX:** validar estados-limite nos fluxos sensíveis.
- **Dev Team:** implementar após backlog saneado e readiness revalidado.

### Responsabilidades
1. Saneamento de artefatos (estrutura + canônico + shards).
2. Refino de stories (FR/NFR/AC mensurável + cenários negativos).
3. Reexecução do readiness check.
4. Só então iniciar sprint planning e create-story/dev-story.

### Critérios de sucesso da correção de rota
- Zero resíduos de template/estrutura inconsistente nos artefatos.
- 100% das stories com FR/NFR explícitos.
- ACs de fluxos sensíveis com métricas e cenários de falha definidos.
- Readiness reexecutado com status apto para implementação.
