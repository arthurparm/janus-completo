# Relatório de Conformidade LGPD (Semanal)

**Data:** 2026-02-14
**Status Geral:** ⚠️ Conformidade Parcial
**Foco:** Retenção, Minimização e Direitos dos Titulares

## 1. Inventário de Dados Pessoais

| Tipo de Dado | Fonte | Armazenamento | Finalidade | Base Legal |
|---|---|---|---|---|
| **Cadastro** | `LocalRegisterRequest` | PostgreSQL (`users`) | Autenticação e Perfil | Execução de Contrato |
| **Identificadores** | CPF, Telefone (Opcional) | PostgreSQL (`users`) | Identificação Única | Legítimo Interesse / Consentimento |
| **Conteúdo de Chat** | Mensagens de Usuário | PostgreSQL (`chat_messages`), Logs | Serviço de IA | Execução de Contrato |
| **Memória Semântica** | Embeddings de Texto | Qdrant (Vetorial) | Contexto de Longo Prazo | Legítimo Interesse |
| **Grafo de Conhecimento** | Entidades Extraídas | Neo4j (Grafo) | Raciocínio Complexo | Legítimo Interesse |

## 2. Gaps Identificados

### 2.1 Retenção e Exclusão de Dados (Direito de Esquecimento)
- **Problema:** O serviço `DataRetentionService` (`janus/app/services/data_retention_service.py`) implementa a exclusão de dados em Qdrant e Neo4j de forma frágil.
- **Detalhe Técnico:** Utiliza `asyncio.create_task` dentro de eventos síncronos ou contextos sem garantia de execução (fire-and-forget). Se o processo falhar ou o servidor reiniciar, os dados do usuário permanecerão "órfãos" nos bancos vetoriais e de grafo, violando o direito de exclusão.
- **Risco:** Alto. Dados supostamente excluídos continuam existindo e podem ser recuperados via RAG.

### 2.2 Minimização de Dados (Logs)
- **Problema:** Logs de aplicação (`janus.log` via `structlog`) podem conter trechos de mensagens de usuários e PII inadvertidamente.
- **Detalhe Técnico:** O `ChatService` loga etapas do processamento. Se um usuário enviar "Meu CPF é 123...", isso pode ser perpetuado nos logs sem retenção definida.
- **Risco:** Médio. Vazamento de dados via arquivos de log não auditados.

### 2.3 Gestão de Consentimento
- **Problema:** O sistema possui apenas um checkbox genérico de "Termos de Uso" no registro (`LocalRegisterRequest`).
- **Detalhe Técnico:** Não há granularidade para consentir com: uso de dados para melhoria do modelo, retenção de histórico para personalização, ou compartilhamento com terceiros (LLMs externas).
- **Risco:** Baixo/Médio. Falta de transparência e controle granular.

## 3. Recomendações e Próximos Passos

### Curto Prazo (P1)
1. **Refatorar `DataRetentionService`:** Substituir `asyncio.create_task` por um sistema de filas persistente (ex: Arq, Celery ou tabela de `background_jobs` no Postgres) para garantir que a exclusão seja tentada até o sucesso.
2. **Auditoria de Logs:** Configurar filtros de redação (redaction) para CPF, Email e Cartão de Crédito nos logs.

### Médio Prazo (P2)
1. **Granularidade de Consentimento:** Criar tabela `user_consents` para gerenciar permissões específicas (ex: `allow_training`, `allow_external_llm`).
2. **Painel de Privacidade:** Criar endpoint/UI onde o usuário possa baixar seus dados ("Takeout") e ver o que está armazenado.

### Longo Prazo (P3)
1. **Política de Retenção Automática:** Implementar TTL (Time-To-Live) automático para mensagens de chat antigas, salvo se o usuário optar por manter.
