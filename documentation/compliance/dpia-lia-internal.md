# DPIA/LIA Simplificado (Internal-Only)

Classificação: internal-only  
Sistema: Janus (janus-completo)  
Escopo: backend + frontend + workers + integrações externas  
Responsáveis: Security/Governança + Engineering  

## 1) Finalidade do tratamento

- Operar uma plataforma interna corporativa para conversas, execução controlada de ferramentas, automação, memória/knowledge, observabilidade e produtividade.
- Prover rastreabilidade operacional (auditoria), detecção de anomalias e suporte a investigações internas.

## 2) Categorias de dados tratados

- Identificadores de usuário (user_id, e-mail/username quando configurado).
- Conteúdo de conversas e prompts (pode conter PII por decisão do usuário).
- Documentos ingeridos (pode conter PII e/ou informações internas).
- Metadados operacionais (trace_id, timestamps, eventos, status, latências).
- Segredos fornecidos pelo usuário (secret memory) e credenciais de integração (tokens OAuth, chaves de API).

## 3) Titulares, Controlador e Operadores

- Titulares: colaboradores/usuários internos que utilizam o sistema.
- Controlador: organização proprietária do Janus.
- Operadores: provedores de infraestrutura/serviços terceirizados (quando habilitados).

## 4) Base legal (LGPD)

Base legal deve ser confirmada com Jurídico/DPO. Referência típica para ferramenta interna:

- Execução de contrato (art. 7º, V) e/ou legítimo interesse (art. 7º, IX), conforme aplicável ao contexto interno.
- Cumprimento de obrigação legal/regulatória (art. 7º, II) para trilhas de auditoria quando aplicável.

## 5) Fluxos de tratamento (alto nível)

- Autenticação e identificação de ator (human vs system).
- Processamento de chat (entrada do usuário → orquestração → execução de ferramentas/LLMs → resposta).
- Armazenamento de memória/knowledge (Qdrant/Neo4j/Postgres).
- Observabilidade e auditoria (eventos persistidos em Postgres).

## 6) Retenção (baseline)

Baseline inicial (ajustável por categoria/subsistema):

- PII: 90 dias
- SECRET: 180 dias
- INTERNAL: 365 dias
- Auditoria: 365 dias

As retenções efetivas devem ser implementadas como “retention by design” com job de expurgo verificável e geração de evidências operacionais.

## 7) Controles de segurança implementados (evidências)

- RBAC com checagem explícita de ADMIN em rotas administrativas: [request_guard.py](file:///h:/repos/janus-completo/backend/app/core/security/request_guard.py)
- Política de egress HTTP para ferramentas (deny-by-default + allowlist + mitigação SSRF) com auditoria de bloqueios: [egress_policy.py](file:///h:/repos/janus-completo/backend/app/core/security/egress_policy.py) e [url_safety.py](file:///h:/repos/janus-completo/backend/app/core/security/url_safety.py)
- Trilha de auditoria imutável (append-only) em Postgres via `audit_ledger_events` + hash-chain + assinatura: [audit_ledger_models.py](file:///h:/repos/janus-completo/backend/app/models/audit_ledger_models.py) e [audit_ledger_repository.py](file:///h:/repos/janus-completo/backend/app/repositories/audit_ledger_repository.py)
- Validação automatizada de evidências: [validate_compliance_matrix.py](file:///h:/repos/janus-completo/tooling/validate_compliance_matrix.py)

Matriz de rastreabilidade: [compliance-traceability-matrix.json](file:///h:/repos/janus-completo/documentation/compliance/compliance-traceability-matrix.json)

## 8) Acesso ao artefato e responsabilização (LGPD)

- Versionamento e trilha de alterações: Git (histórico de commits + revisão obrigatória quando habilitada).
- Controle de acesso: permissões do repositório (equipes internas autorizadas).
- Log de acessos: auditoria da plataforma Git (GitHub/GitLab) para eventos de leitura/clone/pull, complementado por revisões internas.

## 9) Riscos residuais e mitigação

- Egress em nível de container/host ainda depende de configuração do ambiente (Docker Compose): a mitigação em código cobre URLs controladas por usuário/ferramentas, mas não substitui firewall/segmentação.
- Trilhas de auditoria ainda são mutáveis por design (ex.: expurgo por retenção): para auditoria imutável, é necessário ledger append-only/WORM.
- O Janus implementa ledger append-only em Postgres com triggers anti-mutation; a retenção deve ser aplicada por expurgo apenas em dados não-ledger (o ledger permanece imutável).
