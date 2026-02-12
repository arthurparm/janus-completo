# Epic 1: Tenant, Identidade e Controle de Acesso

Permitir operação segura por tenant com autenticação, segregação e políticas de acesso como base funcional independente.

### Story 1.1: Set up initial project from starter template

As a engenheiro de plataforma,
I want inicializar o monorepo com Nx incremental sobre a base atual e preparar o módulo inicial de tenant,
So that o time tenha fundação técnica e escopo multi-tenant prontos para evoluir com segurança.

**FRs:** FR1, FR2, FR3, FR4, FR5, FR6

**Acceptance Criteria:**

**Given** o repositório atual com frontend e backend existentes
**When** a inicialização incremental do Nx é executada e validada em CI
**Then** o workspace fica configurado sem rebootstrap dos apps existentes
**And** comandos de build/test/lint podem ser executados por projetos afetados.

**Given** a fundação inicial criada
**When** o módulo base de tenant é provisionado no backend
**Then** a aplicação passa a operar com contexto explícito de `tenant_id`
**And** o setup inicial fica registrado com evidência de execução e auditoria.

### Story 1.2: Gestão de configurações base por tenant

As a administrador de tenant,
I want editar configurações operacionais básicas do meu tenant,
So that o comportamento padrão do Janus reflita regras da minha organização.

**FRs:** FR1, FR2, FR3, FR4, FR5, FR6

**Acceptance Criteria:**

**Given** que o admin de tenant abre a área de configurações
**When** altera parâmetros permitidos e salva
**Then** as mudanças ficam persistidas no escopo do tenant
**And** um evento de auditoria registra quem alterou, o quê e quando.

**Given** que um usuário sem privilégio administrativo tenta alterar configuração
**When** envia uma atualização
**Then** o sistema rejeita a alteração
**And** retorna mensagem de permissão insuficiente.

### Story 1.3: Políticas de acesso e RBAC tenant-aware

As a administrador de tenant,
I want definir políticas de acesso por papel para ações e telas,
So that usuários só executem o que é permitido pela governança local.

**FRs:** FR1, FR2, FR3, FR4, FR5, FR6

**Acceptance Criteria:**

**Given** uma política RBAC configurada para o tenant
**When** um usuário tenta executar ação fora do seu papel
**Then** a ação é negada antes da execução
**And** o motivo da negação fica visível no retorno.

**Given** que a política foi atualizada
**When** novos acessos são avaliados
**Then** a nova regra é aplicada imediatamente
**And** acessos são sempre avaliados com `tenant_id` no contexto.

### Story 1.4: Autenticação por provedor externo com contexto de tenant

As a usuário final,
I want autenticar por provedor externo suportado já no contexto do tenant,
So that eu entre no sistema com baixo atrito e escopo correto.

**FRs:** FR1, FR2, FR3, FR4, FR5, FR6

**Acceptance Criteria:**

**Given** que o tenant tem um provedor externo habilitado
**When** o usuário conclui login federado com sucesso
**Then** a sessão é criada com identidade e `tenant_id` corretos
**And** o usuário é redirecionado para a experiência principal.

**Given** que o retorno do provedor não corresponde a um tenant válido
**When** o callback é processado
**Then** o login é bloqueado
**And** o usuário recebe erro claro com próximo passo.

### Story 1.5: Revogação de sessões e acessos ativos

As a administrador de tenant,
I want revogar sessões ativas de usuários específicos,
So that eu contenha risco operacional de forma imediata.

**FRs:** FR1, FR2, FR3, FR4, FR5, FR6

**Acceptance Criteria:**

**Given** que há sessões ativas para um usuário
**When** o admin solicita revogação
**Then** todas as sessões alvo são invalidadas
**And** novas requisições exigem autenticação novamente.

**Given** que uma sessão revogada tenta chamar API protegida
**When** a chamada chega ao backend
**Then** o sistema responde não autorizado
**And** registra evento de segurança com referência do tenant.

### Story 1.6: Isolamento de dados por tenant em fluxos críticos

As a líder de segurança,
I want garantir segregação de dados por tenant em chat, execução e auditoria,
So that não exista vazamento cruzado entre organizações.

**FRs:** FR1, FR2, FR3, FR4, FR5, FR6

**Acceptance Criteria:**

**Given** duas organizações distintas com dados semelhantes
**When** um usuário consulta dados no seu tenant
**Then** somente registros do próprio `tenant_id` são retornados
**And** consultas sem escopo explícito são rejeitadas.

**Given** um evento crítico de observabilidade
**When** ele é persistido
**Then** contém `tenant_id` e contexto de usuário
**And** fica disponível para correlação operacional posterior.
