# Epic 5: Auditoria, Compliance e Direitos de Dados

Garantir rastreabilidade, evidência e operação de direitos de dados com visão de auditoria por tenant/usuário/ação.

### Story 5.1: Trilha de auditoria imutável para ações e decisões

As a equipe de compliance,
I want registrar eventos críticos com integridade verificável,
So that auditorias internas e externas tenham evidência confiável.

**FRs:** FR31, FR32, FR33, FR34, FR35, FR36

**Acceptance Criteria:**

**Given** qualquer ação ou decisão relevante do fluxo operacional
**When** o evento é persistido
**Then** inclui quem, o quê, quando, tenant, política aplicada e resultado
**And** o registro participa de cadeia de hash imutável.

**Given** verificação periódica de integridade
**When** um lote é validado
**Then** inconsistências são sinalizadas automaticamente
**And** incidentes de integridade são abertos para operação.

### Story 5.2: Painel de auditoria com filtros e detalhe de evidências

As a auditor,
I want consultar eventos por usuário, tenant, ação e período,
So that eu investigue rapidamente comportamentos e conformidade.

**FRs:** FR31, FR32, FR33, FR34, FR35, FR36

**Acceptance Criteria:**

**Given** o painel de auditoria aberto
**When** o auditor aplica filtros principais
**Then** os resultados retornam em formato navegável e consistente
**And** cada linha permite abrir detalhe completo do evento.

**Given** um evento sensível selecionado
**When** o detalhe é exibido
**Then** mostra aprovação, escopo, impacto e evidências associadas
**And** permite exportar referência para investigação formal.

### Story 5.3: Evidência explicável de decisões automáticas

As a gestor de risco,
I want registrar razão e confiança de decisões automáticas do Janus,
So that a automação seja auditável e contestável quando necessário.

**FRs:** FR31, FR32, FR33, FR34, FR35, FR36

**Acceptance Criteria:**

**Given** uma decisão automática proativa ou de execução
**When** o evento é finalizado
**Then** a evidência inclui razão, contexto, confiança, fallback e `request_id`
**And** há vínculo com thread e `run_id` quando aplicável.

**Given** uma revisão de falso positivo/negativo
**When** o analista consulta o evento
**Then** ele encontra os critérios aplicados
**And** consegue registrar ação de governança corretiva.

### Story 5.4: Solicitação de direitos de dados com validação de autorização

As a usuário autorizado,
I want solicitar acesso, exportação ou exclusão dos meus dados,
So that meus direitos de dados sejam exercidos conforme política.

**FRs:** FR31, FR32, FR33, FR34, FR35, FR36

**Acceptance Criteria:**

**Given** um usuário autenticado com permissão adequada
**When** abre uma solicitação DSAR
**Then** o tipo de solicitação é registrado com identificador único
**And** o sistema valida elegibilidade antes de aceitar.

**Given** solicitação por usuário não autorizado
**When** o pedido é submetido
**Then** o sistema rejeita com justificativa
**And** registra a tentativa para auditoria.

### Story 5.5: Fluxo de acesso/exportação com SLA e rastreabilidade

As a operador de privacidade,
I want processar solicitações de acesso/exportação com SLA monitorado,
So that o atendimento ocorra no prazo e com evidência completa.

**FRs:** FR31, FR32, FR33, FR34, FR35, FR36

**Acceptance Criteria:**

**Given** uma solicitação DSAR de acesso ou exportação aceita
**When** o processamento é iniciado
**Then** o workflow acompanha status e prazo restante
**And** gera pacote em formato suportado para entrega segura.

**Given** conclusão do atendimento
**When** o operador finaliza o caso
**Then** o sistema registra data/hora, responsável e artefato entregue
**And** mantém trilha auditável ponta a ponta.

### Story 5.6: Fluxo de exclusão conforme política aplicável

As a operador de privacidade,
I want executar exclusão de dados com checagem de retenção e bloqueios legais,
So that o pedido seja cumprido sem violar obrigações regulatórias.

**FRs:** FR31, FR32, FR33, FR34, FR35, FR36

**Acceptance Criteria:**

**Given** uma solicitação de exclusão elegível
**When** o workflow valida retenção e restrições legais
**Then** apenas dados permitidos são removidos
**And** exceções são documentadas com justificativa.

**Given** exclusão concluída
**When** o usuário consulta o status
**Then** recebe confirmação do resultado e escopo aplicado
**And** a evidência fica disponível para auditoria.
