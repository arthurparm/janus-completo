# LGPD Compliance Review

Data: 2026-02-23
Escopo: Privacidade de Dados, Retenção, Consentimento.

## 1. Princípios de Privacidade (Privacy by Design)

O sistema Janus processa dados pessoais (mensagens de chat, emails, eventos de calendário) e deve aderir aos princípios de minimização e transparência.

## 2. Mapa de Riscos de PII

| Componente | Tipo de Dado | Risco | Mitigação Atual | Gaps |
|---|---|---|---|---|
| `ChatService` | Mensagens de usuário | Alto (pode conter nomes, CPFs, endereços) | Nenhuma sanitização automática na ingestão. | Mensagens persistidas em texto claro no banco/vetor. |
| `CollaborationService` | Artefatos e mensagens entre agentes | Médio | Logs de execução. | Logs podem vazar conteúdo sensível se não redaçados. |
| `ProductivityTools` | Calendário e Emails | Alto | Escopos de consentimento (`calendar.read`, `mail.send`). | Armazenamento em memória (`_notes`, `_calendar_events`) não criptografado. |
| `Auth` | Dados cadastrais (Email, Nome, CPF) | Alto | Hashing de senha. | CPF e telefone em `LocalRegisterRequest` são opcionais, mas armazenados se fornecidos. |
| `Logs` | Trace de execução | Médio | Filtro de senhas (`_redact_secrets`). | Não detecta padrões de CPF/Cartão em payloads JSON aninhados. |

## 3. Retenção e Expurgo

### Política Atual
- **Logs:** Retenção indefinida ou dependente da rotação do arquivo `janus.log` (sem rotação automática configurada no código).
- **Banco de Dados (SQL):** Dados de usuário persistem até deleção explícita.
- **Vetores (Qdrant):** `DataRetentionService` existe para limpar artefatos, mas depende de eventos síncronos frágeis (`sync_events.py`).

### Recomendações
1. **TTL em Logs:** Implementar rotação de logs e retenção máxima de 30 dias para logs de aplicação.
2. **"Direito ao Esquecimento":** Criar endpoint `POST /api/v1/user/forget` que dispara o `DataRetentionService` de forma confiável (background task robusta) para apagar SQL, Vetores e Grafo.
3. **Criptografia em Repouso:** Avaliar criptografia de colunas sensíveis no Postgres (pgcrypto) ou na aplicação para campos críticos.

## 4. Gestão de Consentimento

- O sistema utiliza `ConsentRepository` para rastrear escopos (`terms_v1`, `calendar.read`, etc.).
- **Gap:** Não há interface clara para o usuário revogar consentimentos específicos via API (apenas adição implícita ou via fluxo OAuth).
- **Ação:** Criar endpoint `DELETE /api/v1/consents/{scope}`.

## 5. Plano de Ação LGPD

1. **(P0) Sanitização de Logs:** Melhorar `logging_config.py` para usar regex de detecção de CPF/Email em todos os campos de mensagem.
2. **(P1) Endpoint de Esquecimento:** Operacionalizar o fluxo de deleção total de dados do usuário.
3. **(P2) Transparência:** Publicar política de privacidade acessível via endpoint `/api/v1/privacy-policy`.
