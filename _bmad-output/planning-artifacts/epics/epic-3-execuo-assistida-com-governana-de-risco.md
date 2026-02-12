# Epic 3: Execução Assistida com Governança de Risco

Permitir execução operacional assistida com classificação de risco, consentimento/aprovação e fluxo resiliente.

### Story 3.1: Planejamento de execução com classificação de risco por ação

As a operador,
I want receber um plano inicial com ações classificadas por risco e impacto,
So that eu saiba rapidamente o que pode ser automático e o que exige validação.

**FRs:** FR7, FR8, FR9, FR10, FR11, FR12, FR19, FR20, FR21, FR22, FR23, FR24

**Acceptance Criteria:**

**Given** uma tarefa operacional solicitada no chat
**When** Janus propõe o plano inicial
**Then** cada ação vem com nível de risco, escopo e impacto estimado
**And** o plano explicita pré-condições de governança.

**Given** que uma ação não pode ser classificada com segurança
**When** o plano é montado
**Then** a ação é marcada para revisão humana
**And** o sistema impede execução automática dessa etapa.

### Story 3.2: Fluxo de consentimento explícito para ações sensíveis

As a usuário responsável pela operação,
I want confirmar ações sensíveis com contexto completo antes de executar,
So that eu permaneça no comando com segurança.

**FRs:** FR7, FR8, FR9, FR10, FR11, FR12, FR19, FR20, FR21, FR22, FR23, FR24

**Acceptance Criteria:**

**Given** uma ação classificada como risco médio ou alto
**When** o usuário tenta iniciar execução
**Then** o Risk Approval Sheet exibe risco, impacto, escopo e efeito externo
**And** a execução fica bloqueada até confirmação explícita.

**Given** que o usuário não confirma ou cancela
**When** o timeout/recusa ocorre
**Then** a ação não é executada
**And** o sistema oferece próximo passo seguro no chat.

### Story 3.3: Aprovação humana obrigatória para alto risco

As a aprovador,
I want aprovar ou rejeitar ações de alto risco com justificativa registrada,
So that a política de governança seja cumprida com rastreabilidade.

**FRs:** FR7, FR8, FR9, FR10, FR11, FR12, FR19, FR20, FR21, FR22, FR23, FR24

**Acceptance Criteria:**

**Given** uma ação marcada como alto risco
**When** entra na fila de aprovação
**Then** somente aprovadores autorizados podem decidir
**And** a decisão exige justificativa textual.

**Given** uma ação rejeitada
**When** o operador acompanha a execução
**Then** o estado final mostra bloqueio por governança
**And** apresenta alternativa de replanejamento seguro.

### Story 3.4: Orquestração de execução multi-etapas com estado rastreável

As a operador,
I want acompanhar execução em estados explícitos (pendente, em andamento, concluído, falhou),
So that eu tenha visibilidade confiável do progresso ponta a ponta.

**FRs:** FR7, FR8, FR9, FR10, FR11, FR12, FR19, FR20, FR21, FR22, FR23, FR24

**Acceptance Criteria:**

**Given** um plano aprovado para execução
**When** a execução inicia
**Then** o sistema retorna `ack` em até 1 segundo com `run_id`
**And** a timeline de evidências é exibida imediatamente.

**Given** etapas em progresso
**When** o estado muda
**Then** a timeline é atualizada com transições e timestamps
**And** o painel direito mantém rastreabilidade contínua.

### Story 3.5: Cancelamento controlado, recuperação e fallback operacional

As a operador,
I want cancelar execuções permitidas e retomar após falha recuperável,
So that eu minimize impacto sem perder contexto.

**FRs:** FR7, FR8, FR9, FR10, FR11, FR12, FR19, FR20, FR21, FR22, FR23, FR24

**Acceptance Criteria:**

**Given** uma execução cancelável segundo política
**When** o usuário solicita cancelamento
**Then** etapas não iniciadas são interrompidas com segurança
**And** o estado final registra cancelamento com motivo.

**Given** falha externa recuperável durante execução
**When** o sistema detecta erro classificado
**Then** Janus oferece retomada do ponto seguro ou fallback manual
**And** preserva contexto e evidências já coletadas.

### Story 3.6: Resultado final verificável com evidências e próximos passos

As a usuário final,
I want ver status final confiável com evidências técnicas e ação seguinte recomendada,
So that eu conclua a tarefa com confiança operacional.

**FRs:** FR7, FR8, FR9, FR10, FR11, FR12, FR19, FR20, FR21, FR22, FR23, FR24

**Acceptance Criteria:**

**Given** uma execução concluída ou concluída com ressalvas
**When** o usuário abre o resumo final
**Then** vê estado final, `run_id`, objetos afetados e logs relevantes
**And** há recomendação explícita de próximo passo.

**Given** uma execução com falha
**When** o resumo final é exibido
**Then** a causa é classificada e compreensível
**And** o usuário recebe caminho claro de recuperação.
