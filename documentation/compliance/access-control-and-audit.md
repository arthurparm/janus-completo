# Controle de Acesso e Auditoria de Artefatos (Internal-Only)

Classificação: internal-only  
Escopo: documentos de compliance/governança (ex.: DPIA/LIA, matriz de rastreabilidade, registro de terceiros).

## Objetivo

Garantir que:

- os artefatos sejam acessíveis somente a equipes internas autorizadas; e
- exista trilha de auditoria de **alterações** (versionamento) e de **acessos** (leitura/clone/pull) para responsabilização (LGPD).

## Modelo de controle (padrão do projeto)

### 1) Versionamento e trilha de alterações

- Fonte canônica: Git (commits + PRs + revisão).
- Evidência: histórico Git e revisões aprovadas.

### 2) Controle de alteração (write access)

- CODEOWNERS restringe mudanças nos artefatos de compliance: [.github/CODEOWNERS](file:///h:/repos/janus-completo/.github/CODEOWNERS)
- Operação esperada (plataforma Git):
  - branch protection habilitada;
  - exigência de revisão de code owners para alterações em `/documentation/compliance/`;
  - proibição de push direto na branch principal.

### 3) Log de acesso (read access)

O Git por si só não registra leituras. O requisito de “registro de acessos” é atendido pela **auditoria da plataforma Git** (GitHub Enterprise/GitLab/Bitbucket), que registra eventos como:

- clone/pull/fetch (quando habilitado);
- acesso via UI (quando disponível);
- permissões concedidas/revogadas;
- downloads de artefatos (quando aplicável).

## Checklist operacional (para auditoria)

- Repositório marcado como privado/interno na plataforma corporativa.
- Logs de auditoria da plataforma habilitados e retidos conforme política.
- Permissões por grupo/equipe aplicadas (somente equipes autorizadas).
- Branch protection + review obrigatório para `documentation/compliance/`.

