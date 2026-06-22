# RBAC (Admin, Usuário e System Actor)

Classificação: internal-only (referência técnica)

## Objetivo

- Aplicar menor privilégio com separação clara entre:
  - usuários humanos (ex.: USER, ADMIN)
  - ator do sistema (SYSTEM) para automações internas
- Eliminar qualquer “admin implícito” por guard nominal.

## Controles implementados

### 1) Guard admin-only com checagem real de role

- Implementação: [require_admin_actor](file:///h:/repos/janus-completo/backend/app/core/security/request_guard.py)
- Regra:
  - exige autenticação (`actor_user_id`)
  - exige role `ADMIN` no banco
  - bloqueia explicitamente ator com role `SYSTEM` mesmo que tenha `ADMIN` (hard separation)

### 2) Guard “same user or admin”

- Implementação: [require_same_user_or_admin](file:///h:/repos/janus-completo/backend/app/core/security/request_guard.py)
- Regra:
  - permite o próprio usuário
  - permite admin (role `ADMIN`)

### 3) Endpoints admin-only usando guard central

- Deployment: [deployment.py](file:///h:/repos/janus-completo/backend/app/api/v1/endpoints/deployment.py)
- Users (assign_role): [users.py](file:///h:/repos/janus-completo/backend/app/api/v1/endpoints/users.py) (role SYSTEM é reservado e não pode ser atribuído via API)
- Resources (GPU budgets): [resources.py](file:///h:/repos/janus-completo/backend/app/api/v1/endpoints/resources.py)

## Evidências automatizadas

- Testes unitários: [test_security_request_guard_rbac.py](file:///h:/repos/janus-completo/backend/tests/unit/test_security_request_guard_rbac.py)
