# Epic 2: Conversa Contextual e Assistência Proativa

Entregar a experiência de conversa contínua com contexto/memória e recomendações proativas acionáveis.

### Story 2.1: Composer conversacional contínuo no painel central

As a operador,
I want conversar com Janus em um composer único com histórico incremental,
So that eu inicie e conduza tarefas sem trocar de interface.

**FRs:** FR13, FR14, FR15, FR16, FR17, FR18

**Acceptance Criteria:**

**Given** que o usuário abre a área de Conversations
**When** envia uma mensagem
**Then** a resposta começa em streaming no painel central
**And** o histórico da conversa fica persistido por thread.

**Given** que a conversa está ativa
**When** o usuário navega por mensagens via teclado
**Then** foco e leitura permanecem acessíveis
**And** atalhos principais funcionam sem mouse.

### Story 2.2: Memória contextual persistente e retomada de contexto

As a usuário recorrente,
I want que o Janus recupere preferências e contexto operacional relevante de sessões anteriores,
So that eu não precise repetir instruções em cada nova tarefa.

**FRs:** FR13, FR14, FR15, FR16, FR17, FR18

**Acceptance Criteria:**

**Given** que existem preferências e histórico relevantes
**When** uma nova conversa começa
**Then** o sistema carrega contexto permitido por política
**And** indica de forma transparente quais sinais foram usados.

**Given** que o usuário solicita retomada de thread anterior
**When** escolhe uma conversa relevante
**Then** o contexto é reaplicado sem perda de histórico
**And** a nova thread referencia a origem para rastreabilidade.

### Story 2.3: Sugestões proativas de próxima melhor ação

As a operador,
I want receber sugestões acionáveis de próxima etapa com justificativa,
So that eu avance mais rápido no loop operacional.

**FRs:** FR13, FR14, FR15, FR16, FR17, FR18

**Acceptance Criteria:**

**Given** um contexto de conversa com tarefa operacional em aberto
**When** o motor de sugestão avalia intenção e estado
**Then** Janus propõe uma ou mais ações priorizadas
**And** cada sugestão traz razão, impacto esperado e nível de confiança.

**Given** que não há confiança suficiente para proatividade
**When** a sugestão seria gerada
**Then** o sistema muda para modo assistivo não proativo
**And** comunica claramente que está aguardando comando explícito.

### Story 2.4: Ciclo aceitar, ajustar ou rejeitar sugestão

As a usuário final,
I want aceitar, ajustar ou rejeitar sugestões com poucos comandos,
So that eu mantenha controle total sobre a decisão.

**FRs:** FR13, FR14, FR15, FR16, FR17, FR18

**Acceptance Criteria:**

**Given** uma sugestão exibida no fluxo de conversa
**When** o usuário aceita sem ajustes
**Then** o plano correspondente é preparado para execução
**And** a decisão do usuário é registrada.

**Given** que o usuário ajusta ou rejeita a sugestão
**When** envia feedback no próprio composer
**Then** Janus recalcula o próximo plano
**And** preserva o contexto da decisão anterior.

### Story 2.5: Registro auditável do contexto de decisão proativa

As a auditor interno,
I want visualizar o contexto que fundamentou cada sugestão proativa,
So that decisões automáticas sejam explicáveis e verificáveis.

**FRs:** FR13, FR14, FR15, FR16, FR17, FR18

**Acceptance Criteria:**

**Given** uma sugestão proativa emitida
**When** o evento é registrado
**Then** inclui razão, contexto usado, confiança, fallback e `request_id`
**And** pode ser correlacionado com tenant, usuário e thread.

**Given** uma consulta de auditoria sobre sugestão específica
**When** o auditor abre o detalhe do evento
**Then** encontra a justificativa e o resultado da decisão do usuário
**And** consegue navegar para a execução relacionada, se houver.
