# Epic 4: Integrações Externas e Recuperação Operacional

Habilitar integrações com autorização, quotas e recuperação guiada para manter continuidade operacional.

### Story 4.1: Catálogo de integrações habilitáveis por tenant

As a administrador de tenant,
I want habilitar ou desabilitar integrações suportadas por tenant,
So that eu controle o perímetro operacional permitido.

**FRs:** FR25, FR26, FR27, FR28, FR29, FR30

**Acceptance Criteria:**

**Given** o admin acessa catálogo de integrações
**When** ativa ou desativa uma integração permitida
**Then** o status é persistido no tenant
**And** o evento de mudança fica auditado.

**Given** uma integração desabilitada
**When** um usuário tenta acioná-la no chat
**Then** a execução é bloqueada por política
**And** o sistema sugere alternativa disponível.

### Story 4.2: Fluxo OAuth de conexão de conta externa

As a usuário operacional,
I want conectar minha conta externa com fluxo OAuth seguro,
So that Janus possa executar ações autorizadas em meu nome.

**FRs:** FR25, FR26, FR27, FR28, FR29, FR30

**Acceptance Criteria:**

**Given** uma integração habilitada no tenant
**When** o usuário inicia conexão OAuth e concede consentimento
**Then** o token é armazenado de forma segura e escopada
**And** a integração fica marcada como conectada.

**Given** retorno OAuth com erro do provedor
**When** o callback é processado
**Then** a conexão é marcada como falha
**And** o usuário recebe causa e próxima ação recomendada.

### Story 4.3: Detecção de autorização inválida e reautorização guiada

As a operador,
I want que o sistema detecte token inválido rapidamente e peça reautorização,
So that eu retome a execução sem perder histórico.

**FRs:** FR25, FR26, FR27, FR28, FR29, FR30

**Acceptance Criteria:**

**Given** token expirado ou revogado
**When** uma ação integrada é disparada
**Then** o bloqueio é detectado e sinalizado em até 60 segundos
**And** o OAuth/Quota Recovery Banner oferece reautorizar agora.

**Given** que a reautorização foi concluída com sucesso
**When** o usuário retorna ao chat
**Then** a execução pode ser retomada do ponto seguro
**And** o `run_id` original permanece correlacionado.

### Story 4.4: Aplicação de quotas por usuário e por tenant

As a administrador de operação,
I want aplicar limites de uso por usuário e tenant,
So that consumo e custo fiquem sob controle com previsibilidade.

**FRs:** FR25, FR26, FR27, FR28, FR29, FR30

**Acceptance Criteria:**

**Given** políticas de quota configuradas
**When** uma requisição excede o limite vigente
**Then** a ação é bloqueada antes de gerar efeito externo
**And** o motivo do bloqueio é retornado de forma objetiva.

**Given** consumo próximo ao limite
**When** o usuário prepara uma execução
**Then** o sistema alerta risco de quota
**And** sugere alternativa de menor impacto.

### Story 4.5: Recuperação operacional em bloqueios de integração

As a usuário final,
I want escolher entre reautorizar, replanejar em modo seguro ou cancelar,
So that eu mantenha controle durante bloqueios externos.

**FRs:** FR25, FR26, FR27, FR28, FR29, FR30

**Acceptance Criteria:**

**Given** execução bloqueada por OAuth/quota
**When** Janus apresenta opções de recuperação
**Then** o usuário pode selecionar reautorizar, replanejar ou cancelar
**And** cada opção informa impacto e consequências.

**Given** que o usuário escolhe replanejar
**When** o plano seguro é gerado
**Then** ele evita ações bloqueadas
**And** mantém objetivo operacional principal quando possível.
