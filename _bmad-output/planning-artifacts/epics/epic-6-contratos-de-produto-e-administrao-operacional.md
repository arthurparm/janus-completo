# Epic 6: Contratos de Produto e Administração Operacional

Viabilizar governança de contratos e operação administrativa contínua com visibilidade de uso/incidentes.

### Story 6.1: Registro versionado de contratos REST e eventos

As a usuário técnico,
I want publicar e consultar versões de contratos de API/eventos,
So that integrações evoluam com previsibilidade e controle de breaking changes.

**FRs:** FR37, FR38, FR39, FR40

**Acceptance Criteria:**

**Given** uma nova versão de contrato pronta para publicação
**When** ela é registrada
**Then** recebe versão semântica e status de suporte
**And** o histórico de versões anteriores permanece acessível.

**Given** tentativa de publicar mudança breaking sem regra de depreciação
**When** o gate de contrato avalia a versão
**Then** a publicação é bloqueada
**And** o motivo do bloqueio é reportado no pipeline.

### Story 6.2: Portal de mudanças e depreciação de contratos

As a desenvolvedor integrador,
I want consultar changelog e janela de depreciação dos contratos,
So that eu planeje atualizações sem interrupção de serviço.

**FRs:** FR37, FR38, FR39, FR40

**Acceptance Criteria:**

**Given** contratos ativos e em depreciação
**When** o usuário técnico abre o portal
**Then** visualiza mudanças por versão, impacto e data-limite
**And** consegue filtrar por serviço e tipo de evento.

**Given** contrato próximo do fim de suporte
**When** o período crítico é atingido
**Then** o sistema destaca risco operacional
**And** recomenda ação de migração.

### Story 6.3: Painéis administrativos de uso e auditoria por tenant

As a administrador de tenant,
I want visualizar painéis de uso e auditoria em uma visão operacional única,
So that eu monitore adoção, risco e saúde do ambiente.

**FRs:** FR37, FR38, FR39, FR40

**Acceptance Criteria:**

**Given** o admin acessa o dashboard
**When** seleciona período e escopo
**Then** enxerga métricas de uso, execução, governança e auditoria
**And** os dados são filtrados exclusivamente pelo tenant.

**Given** um indicador fora do esperado
**When** o admin abre o detalhe
**Then** há link para eventos e execuções relacionadas
**And** existe recomendação de ação operacional.

### Story 6.4: Gestão de incidentes operacionais vinculados às capacidades

As a equipe de operações,
I want registrar e acompanhar incidentes com vínculo às capacidades afetadas,
So that resposta e aprendizado operacional sejam estruturados.

**FRs:** FR37, FR38, FR39, FR40

**Acceptance Criteria:**

**Given** uma falha relevante em produção
**When** um incidente é criado
**Then** ele inclui severidade, capacidade afetada, impacto e responsável
**And** fica correlacionado com eventos de execução e auditoria.

**Given** um incidente em tratamento
**When** o status é atualizado
**Then** a linha do tempo registra marcos de resposta
**And** o encerramento exige resumo de causa raiz e ação preventiva.



