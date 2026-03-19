# Documentação Completa da API Janus

## Visão Geral

A API Janus é uma plataforma de agentes de IA multi-modais que fornece endpoints para chat, autenticação, gerenciamento de memória, conhecimento, observabilidade e administração do sistema. A API é construída com FastAPI e oferece suporte para autenticação via tokens, streaming de mensagens e integração com múltiplos provedores de LLM.

## Base URL

```
http://localhost:8000/api/v1
```

## Autenticação

A API suporta múltiplos métodos de autenticação:

### 1. Token JWT (Bearer)
```
Authorization: Bearer <token>
```

### 2. Firebase Auth
```
POST /auth/firebase/exchange
```

### 3. Supabase Auth  
```
POST /auth/supabase/exchange
```

### 4. Auth Local (Email/Senha)
```
POST /auth/local/login
POST /auth/local/register
```

---

## 1. Endpoints de Chat/Conversa

### 1.1 Iniciar Nova Conversa

**POST** `/chat/start`

Inicia uma nova conversa e retorna um conversation_id.

**Request Body:**
```json
{
  "persona": "assistant",
  "user_id": "user123",
  "project_id": "proj456",
  "title": "Minha Conversa"
}
```

**Response:**
```json
{
  "conversation_id": "conv-abc123"
}
```

**Códigos de Erro:**
- `401`: Authentication required (`CHAT_AUTH_REQUIRED`)
- `422`: Invalid request format

### 1.2 Enviar Mensagem

**POST** `/chat/message`

Envia uma mensagem e recebe resposta do LLM com streaming opcional.

**Request Body:**
```json
{
  "conversation_id": "conv-abc123",
  "message": "Qual é a capital do Brasil?",
  "role": "auto",
  "priority": "fast_and_cheap",
  "timeout_seconds": 30,
  "user_id": "user123",
  "project_id": "proj456"
}
```

**Response:**
```json
{
  "response": "A capital do Brasil é Brasília.",
  "provider": "openai",
  "model": "gpt-4",
  "role": "assistant",
  "conversation_id": "conv-abc123",
  "message_id": "msg-789",
  "citations": [
    {
      "source": "wikipedia",
      "text": "Brasília é a capital federal do Brasil",
      "score": 0.95
    }
  ],
  "citation_status": {
    "mode": "optional",
    "status": "found",
    "count": 1,
    "reason": null
  },
  "understanding": {
    "intent": "question",
    "summary": "User asking about Brazil's capital",
    "confidence": 0.92,
    "confidence_band": "high",
    "low_confidence": false,
    "requires_confirmation": false,
    "routing": {
      "requested_role": "auto",
      "selected_role": "assistant",
      "intent": "question",
      "risk_level": "low",
      "confidence": 0.92
    }
  },
  "confirmation": {
    "required": false,
    "reason": null,
    "pending_action_id": null
  },
  "delivery_status": "completed",
  "agent_state": {
    "state": "responding",
    "confidence_band": "high",
    "requires_confirmation": false
  }
}
```

**Códigos de Erro:**
- `401`: Authentication required (`CHAT_AUTH_REQUIRED`)
- `404`: Conversation not found (`CHAT_CONVERSATION_NOT_FOUND`)
- `413`: Message too large (`CHAT_MESSAGE_TOO_LARGE`)
- `422`: Invalid role or priority (`CHAT_INVALID_ROLE_OR_PRIORITY`)
- `403`: Access denied (`CHAT_ACCESS_DENIED`)
- `500`: Internal server error (`CHAT_INVOCATION_ERROR`)

### 1.3 Histórico da Conversa

**GET** `/chat/{conversation_id}/history`

**Parâmetros Query:**
- `limit` (opcional): Número máximo de mensagens
- `offset` (opcional): Offset para paginação
- `before_ts` (opcional): Timestamp limite superior
- `after_ts` (opcional): Timestamp limite inferior

**Response:**
```json
{
  "conversation_id": "conv-abc123",
  "persona": "assistant",
  "messages": [
    {
      "message_id": "msg-123",
      "timestamp": 1710000000.0,
      "role": "user",
      "text": "Olá, como você está?",
      "citations": [],
      "provider": "openai",
      "model": "gpt-4"
    },
    {
      "message_id": "msg-124", 
      "timestamp": 1710000001.0,
      "role": "assistant",
      "text": "Estou bem, obrigado! Como posso ajudar você hoje?",
      "citations": [],
      "provider": "openai",
      "model": "gpt-4"
    }
  ]
}
```

### 1.4 Listar Conversas

**GET** `/chat/conversations`

**Parâmetros Query:**
- `user_id` (opcional): Filtrar por usuário
- `project_id` (opcional): Filtrar por projeto
- `limit` (opcional, default: 50): Número máximo de conversas

**Response:**
```json
[
  {
    "conversation_id": "conv-abc123",
    "title": "Conversa sobre Python",
    "created_at": 1710000000.0,
    "updated_at": 1710003600.0,
    "last_message": {
      "message_id": "msg-124",
      "timestamp": 1710003600.0,
      "role": "assistant",
      "text": "Aqui está o código que você solicitou...",
      "provider": "openai",
      "model": "gpt-4"
    },
    "message_count": 15,
    "tags": ["python", "coding"],
    "last_message_at": "2024-03-10T12:00:00Z"
  }
]
```

---

## 2. Endpoints de Autenticação

### 2.1 Token JWT

**POST** `/auth/token`

Emite um token JWT para um usuário específico.

**Request Body:**
```json
{
  "user_id": 123,
  "expires_in": 3600
}
```

**Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Códigos de Erro:**
- `403`: Forbidden (usuário não pode emitir token para outro usuário)

### 2.2 Firebase Exchange

**POST** `/auth/firebase/exchange`

Troca token Firebase por token interno.

**Request Body:**
```json
{
  "token": "firebase_id_token"
}
```

**Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "123",
    "roles": ["user"],
    "permissions": ["read"]
  }
}
```

**Códigos de Erro:**
- `503`: Firebase auth disabled ou not configured
- `401`: Invalid token
- `422`: Missing uid/email

### 2.3 Supabase Exchange

**POST** `/auth/supabase/exchange`

Troca token Supabase por token interno.

**Request Body:**
```json
{
  "token": "supabase_jwt_token"
}
```

**Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### 2.4 Registro Local

**POST** `/auth/local/register`

Registra novo usuário com email/senha.

**Request Body:**
```json
{
  "email": "usuario@example.com",
  "password": "senhaSegura123",
  "username": "usuario123",
  "full_name": "João Silva",
  "cpf": "123.456.789-09",
  "phone": "+5511999999999",
  "terms": true
}
```

**Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "123",
    "email": "usuario@example.com",
    "username": "usuario123",
    "display_name": "João Silva",
    "roles": ["user"],
    "permissions": ["read"]
  }
}
```

**Códigos de Erro:**
- `422`: Terms not accepted, invalid CPF
- `409`: Email/username/CPF already registered

### 2.5 Login Local

**POST** `/auth/local/login`

Login com email/senha ou username/senha.

**Request Body:**
```json
{
  "email": "usuario@example.com",
  "password": "senhaSegura123"
}
```

**Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "123",
    "email": "usuario@example.com",
    "username": "usuario123",
    "display_name": "João Silva",
    "roles": ["user"],
    "permissions": ["read"]
  }
}
```

**Códigos de Erro:**
- `401`: Invalid credentials

### 2.6 Perfil do Usuário

**GET** `/auth/local/me`

Obtém informações do usuário autenticado.

**Response:**
```json
{
  "id": "123",
  "email": "usuario@example.com",
  "username": "usuario123",
  "display_name": "João Silva",
  "roles": ["user", "admin"],
  "permissions": ["read"]
}
```

### 2.7 Reset de Senha

**POST** `/auth/local/request-reset`

Solicita reset de senha.

**Request Body:**
```json
{
  "email": "usuario@example.com"
}
```

**Response:**
```json
{
  "status": "ok",
  "reset_token": "token_aleatorio"  // apenas em ambientes de teste
}
```

**POST** `/auth/local/reset`

Confirma reset de senha.

**Request Body:**
```json
{
  "token": "token_aleatorio",
  "password": "novaSenhaSegura123"
}
```

**Response:**
```json
{
  "status": "ok",
  "reset_token": null
}
```

**Códigos de Erro:**
- `400`: Invalid token ou token expired

---

## 3. Endpoints de Admin/Monitoramento

### 3.1 Status do Sistema

**GET** `/system/status`

Verifica o estado geral da aplicação.

**Response:**
```json
{
  "app_name": "janus-api",
  "version": "1.0.0",
  "environment": "development",
  "status": "healthy",
  "timestamp": "2024-03-10T12:00:00Z",
  "uptime_seconds": 3600.0,
  "system": {
    "cpu_percent": 15.2,
    "memory_percent": 45.8,
    "disk_usage_percent": 62.1
  },
  "process": {
    "memory_mb": 256.5,
    "threads": 12
  },
  "performance": {
    "requests_per_second": 2.5,
    "average_response_time_ms": 120
  },
  "config": {
    "debug": false,
    "max_workers": 4
  }
}
```

### 3.2 Saúde dos Serviços

**GET** `/system/health/services`

Verifica saúde dos microsserviços.

**Response:**
```json
{
  "services": [
    {
      "key": "agent",
      "name": "Agent Service",
      "status": "healthy",
      "metric_text": "Agentes: 5"
    },
    {
      "key": "knowledge",
      "name": "Knowledge Service",
      "status": "healthy",
      "metric_text": "Ontologias: 1,234"
    },
    {
      "key": "memory",
      "name": "Memory Service",
      "status": "ok",
      "metric_text": "Uso: 512MB"
    },
    {
      "key": "llm",
      "name": "LLM Gateway",
      "status": "healthy",
      "metric_text": "CB Abertos: 0, Cache: 15"
    }
  ]
}
```

### 3.3 Status por Usuário

**GET** `/system/status/user?user_id={user_id}`

Obtém métricas específicas de um usuário.

**Response:**
```json
{
  "user_id": "user123",
  "conversations": 15,
  "messages": 234,
  "approx_in_tokens": 4567,
  "approx_out_tokens": 8901,
  "vector_points": 1234
}
```

**Códigos de Erro:**
- `401`: Unauthorized
- `403`: Forbidden (usuário não pode ver métricas de outros)

### 3.4 Validação de Schema

**GET** `/system/db/validate`

Valida schema do banco de dados.

**POST** `/system/db/migrate`

Executa migrações do banco de dados.

---

## 4. Endpoints de Observabilidade

### 4.1 Health Checks

**GET** `/observability/health/system`

Saúde agregada do sistema.

**POST** `/observability/health/check-all`

Força execução de todos os health checks.

**GET** `/observability/health/components/llm_router`

Health do componente LLM Router.

**GET** `/observability/health/components/multi_agent_system`

Health do sistema multi-agente.

**GET** `/observability/health/components/poison_pill_handler`

Health do handler de poison pills.

### 4.2 Poison Pills

**GET** `/observability/poison-pills/quarantined?queue={queue}`

Lista mensagens em quarentena.

**POST** `/observability/poison-pills/release`

Libera mensagem da quarentena.

**Request Body:**
```json
{
  "message_id": "msg-123",
  "allow_retry": true
}
```

**POST** `/observability/poison-pills/cleanup`

Limpa mensagens expiradas da quarentena.

**GET** `/observability/poison-pills/stats?queue={queue}`

Estatísticas de poison pills.

### 4.3 Métricas e SLOs

**GET** `/observability/metrics/summary`

Resumo de métricas chave do sistema.

**GET** `/observability/slo/domains?window_minutes={min}&min_events={count}`

SLOs por domínio (chat/rag/tools/workers) com alertas ativos.

**GET** `/observability/anomalies/predictive?window_hours={hours}&bucket_minutes={min}&min_events={count}`

Detecção preditiva de anomalias.

**GET** `/observability/llm/usage?start_ts={start}&end_ts={end}`

Resumo de uso de LLMs.

### 4.4 Auditoria

**GET** `/observability/audit/events?user_id={id}&tool={tool}&status={status}&start_ts={start}&end_ts={end}&limit={limit}&offset={offset}`

Lista eventos de auditoria.

**GET** `/observability/audit/export?format=csv&fields=id,user_id,status&user_id={id}`

Exporta eventos de auditoria (CSV/JSON).

**GET** `/observability/errors/taxonomy`

Catálogo padronizado de erros.

### 4.5 Dashboard por Request

**GET** `/observability/requests/{request_id}/dashboard?limit={limit}&include_details={bool}`

Dashboard de pipeline por request_id.

### 4.6 Métricas de Usuário

**GET** `/observability/user_summary?user_id={id}`

Resumo de uso por usuário.

**GET** `/observability/metrics/user?user_id={id}`

Métricas agregadas por usuário.

**GET** `/observability/activity/user?user_id={id}`

Atividade agregada por usuário.

**POST** `/observability/metrics/ux`

Registra métrica de UX de chat.

**Request Body:**
```json
{
  "ttft_ms": 150.5,
  "latency_ms": 1200.3,
  "outcome": "success",
  "retries": 0,
  "provider": "openai",
  "model": "gpt-4",
  "timestamp": 1710000000.0
}
```

---

## 5. Endpoints de Memória e Conhecimento

### 5.1 Memória de Timeline

**GET** `/memory/timeline?start_date={ISO}&end_date={ISO}&query={text}&limit={limit}&min_score={score}&user_id={id}`

Recupera memórias dentro de um período específico com filtro semântico.

**Response:**
```json
[
  {
    "content": "O usuário perguntou sobre Python",
    "ts_ms": 1710000000000,
    "metadata": {
      "conversation_id": "conv-123",
      "memory_class": "episodic",
      "importance": 0.8
    },
    "score": 0.95,
    "composite_id": "mem-456",
    "memory_class": "episodic",
    "retention_policy": "auto",
    "recall_policy": "contextual",
    "sensitivity": "public",
    "stability_score": 0.9,
    "scope": "user123"
  }
]
```

### 5.2 Memória Generativa

**GET** `/memory/generative?query={text}&limit={limit}&type={type}&user_id={id}&conversation_id={id}`

Recupera memórias usando scoring generativo (Recency × Importance × Relevance).

**POST** `/memory/generative`

Adiciona memória ao stream generativo.

**Request Body:**
```json
{
  "content": "O usuário preferencia por código Python limpo",
  "importance": 8.5,
  "type": "semantic",
  "user_id": "user123",
  "conversation_id": "conv-456",
  "session_id": "sess-789"
}
```

### 5.3 Preferências do Usuário

**GET** `/memory/preferences?user_id={id}&conversation_id={id}&query={text}&limit={limit}&active_only={bool}`

Lista preferências do usuário.

**Response:**
```json
[
  {
    "id": "pref-123",
    "content": "Prefere respostas em português",
    "ts_ms": 1710000000000,
    "preference_kind": "language",
    "instruction_text": "Sempre responder em português",
    "scope": "user123",
    "confidence": 0.95,
    "active": true,
    "origin": "user_explicit",
    "memory_class": "semantic"
  }
]
```

### 5.4 Segredos do Usuário

**GET** `/memory/secrets?user_id={id}&conversation_id={id}&query={text}&limit={limit}&active_only={bool}`

Lista segredos do usuário (valores mascarados).

**POST** `/memory/secrets`

Armazena segredo do usuário.

**Request Body:**
```json
{
  "label": "API_KEY_OPENAI",
  "value": "sk-1234567890abcdef",
  "secret_type": "api_key",
  "secret_scope": "global",
  "conversation_id": "conv-123",
  "user_id": "user123"
}
```

**Response:**
```json
{
  "id": "secret-456",
  "secret_label": "API_KEY_OPENAI",
  "secret_type": "api_key",
  "secret_scope": "global",
  "masked_value": "sk-****7890",
  "active": true,
  "conversation_id": "conv-123",
  "memory_class": "secret",
  "sensitivity": "secret"
}
```

---

## 6. Endpoints de Conhecimento (Graph RAG)

### 6.1 Indexação de Código

**POST** `/knowledge/index`

Inicia indexação da base de código.

**Response:**
```json
{
  "message": "Indexação iniciada",
  "summary": "Processando 1,234 arquivos"
}
```

### 6.2 Estatísticas do Grafo

**GET** `/knowledge/stats`

Estatísticas do grafo de conhecimento.

### 6.3 Entidades de Código

**GET** `/knowledge/entities?file_path={path}`

Lista entidades de código.

### 6.4 Relacionamentos de Entidades

**GET** `/knowledge/entity/{entity_name}/relationships?rel_type={type}&direction={dir}&max_depth={depth}&limit={limit}&skip={offset}`

Navega relacionamentos de uma entidade.

**Response:**
```json
{
  "results": [
    {
      "related_entity": "UserRepository",
      "related_type": "class",
      "relationship": "imports",
      "distance": 1
    }
  ]
}
```

### 6.5 Limpar Grafo

**DELETE** `/knowledge/clear`

Limpa todo o grafo de conhecimento.

**Response:**
```json
{
  "status": "success",
  "message": "Grafo de conhecimento limpo com sucesso",
  "remaining_nodes": 0
}
```

### 6.6 Consulta de Conhecimento (Graph RAG)

**POST** `/knowledge/query`

Consulta o grafo de conhecimento semanticamente.

**Request Body:**
```json
{
  "query": "Como funciona o sistema de autenticação?",
  "limit": 10
}
```

**Response:**
```json
{
  "answer": "O sistema de autenticação utiliza JWT tokens com validação de claims..."
}
```

### 6.7 Consulta de Código com Citações

**POST** `/knowledge/query/code`

Pergunta sobre código com citações de arquivo e linha.

**Request Body:**
```json
{
  "question": "Onde é definida a classe UserRepository?",
  "limit": 10,
  "citation_limit": 8
}
```

**Response:**
```json
{
  "answer": "A classe UserRepository é definida em app/repositories/user_repository.py",
  "citations": [
    {
      "type": "class",
      "name": "UserRepository",
      "file_path": "app/repositories/user_repository.py",
      "line": 15,
      "full_name": "app.repositories.user_repository.UserRepository",
      "relevance": 95
    }
  ]
}
```

### 6.8 Conceitos Relacionados

**POST** `/knowledge/concepts/related`

Busca conceitos relacionados no grafo.

**Request Body:**
```json
{
  "concept": "autenticação",
  "max_depth": 2,
  "limit": 10,
  "skip": 0
}
```

### 6.9 Reindexação

**POST** `/knowledge/concepts/reindex`

Reindexa conceitos que não possuem embeddings.

**Request Body:**
```json
{
  "batch_size": 50,
  "labels": ["class", "function", "module"]
}
```

**Response:**
```json
{
  "status": "success",
  "updated_count": 234
}
```

### 6.10 Health Check do Conhecimento

**GET** `/knowledge/health`

Health check da memória semântica.

**Response:**
```json
{
  "status": "healthy",
  "neo4j_connected": true,
  "qdrant_connected": true,
  "circuit_breaker_open": false,
  "total_nodes": 1234,
  "total_relationships": 5678
}
```

**GET** `/knowledge/health/detailed`

Status detalhado incluindo circuit breaker.

**POST** `/knowledge/health/reset-circuit-breaker`

Reseta circuit breaker manualmente.

### 6.11 Consolidação de Conhecimento

**POST** `/knowledge/consolidate`

Dispara consolidação de conhecimento via fila.

**Request Body:**
```json
{
  "mode": "batch",
  "limit": 10,
  "min_score": 0.7,
  "experience_id": "exp-123",
  "experience_content": "Conteúdo da experiência",
  "metadata": {"source": "user_input"}
}
```

**POST** `/knowledge/consolidate/document`

Consolida conhecimento a partir de documento.

**Request Body:**
```json
{
  "user_id": "user123",
  "doc_id": "doc-456",
  "limit": 50
}
```

### 6.12 Tipos de Relacionamento

**GET** `/knowledge/node-types`

Lista tipos de nós presentes no grafo.

**POST** `/knowledge/relationship-types/register`

Registra tipo canônico de relacionamento.

**Request Body:**
```json
{
  "name": "implements"
}
```

### 6.13 Quarentena do Grafo

**GET** `/knowledge/quarantine?limit={limit}`

Lista itens em quarentena no grafo.

**POST** `/knowledge/quarantine/promote`

Promove item de quarentena para relação no grafo.

**Request Body:**
```json
{
  "from_name": "UserService",
  "to_name": "UserRepository",
  "type": "depends_on",
  "source_experience": "Análise de código mostrou dependência"
}
```

### 6.14 Análise de Código Avançada

**GET** `/knowledge/functions/calling?name={function_name}`

Lista funções que chamam a função informada.

**GET** `/knowledge/files/importing?module={module_name}`

Lista arquivos que importam o módulo informado.

**GET** `/knowledge/classes/implementations?protocol={protocol_name}`

Lista classes que implementam o protocolo/interface informado.

---

## 7. Endpoints de Workers e Tarefas

### 7.1 Gerenciamento de Workers

**POST** `/workers/start-all`

Inicia todos os workers gerenciados pelo orquestrador.

**Response:**
```json
{
  "status": "started",
  "workers": [
    {
      "name": "agent_worker",
      "running": true,
      "done": false,
      "cancelled": false,
      "exception": null,
      "state": "running"
    }
  ],
  "count": 5
}
```

**POST** `/workers/stop-all`

Para todos os workers.

**Response:**
```json
{
  "status": "stopped",
  "stopped_count": 5
}
```

**GET** `/workers/status`

Obtém status dos workers.

**Response:**
```json
{
  "tracked": 5,
  "workers": [
    {
      "name": "agent_worker",
      "running": true,
      "done": false,
      "state": "running"
    }
  ]
}
```

---

## 8. Estrutura de Respostas de Erro

Todos os erros seguem o formato Problem Details (RFC 7807):

```json
{
  "type": "about:blank",
  "title": "Unauthorized",
  "status": 401,
  "detail": "Authentication required",
  "instance": "/api/v1/chat/message",
  "code": "CHAT_AUTH_REQUIRED",
  "category": "auth",
  "retryable": false,
  "http_status": 401
}
```

### Categorias de Erro

- `auth`: Erros de autenticação
- `authz`: Erros de autorização
- `validation`: Erros de validação de dados
- `not_found`: Recurso não encontrado
- `internal`: Erros internos do servidor
- `rate_limit`: Limite de taxa excedido

### Códigos de Erro Comuns

| Código | Descrição | HTTP Status | Retryable |
|--------|-----------|-------------|-----------|
| `CHAT_AUTH_REQUIRED` | Autenticação necessária | 401 | false |
| `CHAT_CONVERSATION_NOT_FOUND` | Conversa não encontrada | 404 | false |
| `CHAT_MESSAGE_TOO_LARGE` | Mensagem muito grande | 413 | false |
| `CHAT_INVALID_ROLE_OR_PRIORITY` | Role ou prioridade inválida | 422 | false |
| `CHAT_ACCESS_DENIED` | Acesso negado | 403 | false |
| `CHAT_INVOCATION_ERROR` | Erro interno | 500 | true |

---

## 9. Exemplos de Uso Completo

### 9.1 Fluxo Completo de Chat

```bash
# 1. Obter token (se não tiver)
curl -X POST http://localhost:8000/api/v1/auth/local/login \\\n  -H "Content-Type: application/json" \\\n  -d '{"email": "user@example.com", "password": "senha123"}'

# 2. Iniciar conversa
curl -X POST http://localhost:8000/api/v1/chat/start \\\n  -H "Authorization: Bearer <token>" \\\n  -H "Content-Type: application/json" \\\n  -d '{"persona": "assistant", "title": "Teste de API"}'

# 3. Enviar mensagem
curl -X POST http://localhost:8000/api/v1/chat/message \\\n  -H "Authorization: Bearer <token>" \\\n  -H "Content-Type: application/json" \\\n  -d '{
    "conversation_id": "conv-abc123",
    "message": "Explique o conceito de machine learning",
    "role": "auto",
    "priority": "balanced"
  }'

# 4. Ver histórico
curl -X GET "http://localhost:8000/api/v1/chat/conv-abc123/history?limit=10" \\\n  -H "Authorization: Bearer <token>"
```

### 9.2 Consulta de Conhecimento com Citações

```bash
# Consultar sobre código com citações
curl -X POST http://localhost:8000/api/v1/knowledge/query/code \\\n  -H "Authorization: Bearer <token>" \\\n  -H "Content-Type: application/json" \\\n  -d '{
    "question": "Como é implementada a autenticação JWT?",
    "limit": 5,
    "citation_limit": 3
  }'
```

### 9.3 Gerenciamento de Memória

```bash
# Adicionar memória generativa
curl -X POST http://localhost:8000/api/v1/memory/generative \\\n  -H "Authorization: Bearer <token>" \\\n  -H "Content-Type: application/json" \\\n  -d '{
    "content": "O usuário é desenvolvedor Python experiente",
    "importance": 9.0,
    "type": "semantic",
    "user_id": "user123"
  }'

# Buscar memórias relevantes
curl -X GET "http://localhost:8000/api/v1/memory/generative?query=python developer&limit=5&user_id=user123" \\\n  -H "Authorization: Bearer <token>"
```

### 9.4 Monitoramento e Observabilidade

```bash
# Ver status do sistema
curl -X GET http://localhost:8000/api/v1/system/status

# Ver saúde dos serviços
curl -X GET http://localhost:8000/api/v1/system/health/services

# Ver SLOs por domínio
curl -X GET "http://localhost:8000/api/v1/observability/slo/domains?window_minutes=60&min_events=20" \\\n  -H "Authorization: Bearer <token>"

# Ver mensagens em quarentena
curl -X GET http://localhost:8000/api/v1/observability/poison-pills/quarantined \\\n  -H "Authorization: Bearer <token>"
```

---

## 10. Rate Limiting e Performance

### Limites de Taxa
- Auth endpoints: 5 requests/minuto por IP/usuário
- Chat endpoints: 30 requests/minuto por usuário
- Knowledge endpoints: 60 requests/minuto por usuário

### Timeouts
- Chat message: 30s padrão (configurável via `timeout_seconds`)
- Knowledge queries: 60s
- System health: 10s

### Prioridades de Modelo
- `fast_and_cheap`: Modelos rápidos e econômicos
- `balanced`: Balance entre velocidade e qualidade
- `high_quality`: Melhor qualidade, mais lento
- `reasoning`: Modelos com capacidade de raciocínio

---

## 11. Streaming e Eventos

### Server-Sent Events (SSE)

O endpoint `/chat/message` suporta SSE quando o header `Accept: text/event-stream` é enviado.

**Formato dos eventos:**
```
event: token
data: {"text":"Olá","timestamp":1710000000.0}

event: citation
data: {"source":"doc1","text":"referência"}

event: done
data: [DONE]
```

### Tipos de Eventos
- `protocol`: Informações do protocolo
- `token`: Tokens de resposta do LLM
- `citation`: Citações encontradas
- `understanding`: Análise de intenção
- `error`: Erros durante processamento
- `done`: Fim do stream

---

## 12. Considerações de Segurança

### Validação de Entrada
- Todos os inputs são validados e sanitizados
- SQL injection protegido via ORM
- XSS protegido via escape automático
- Limites de tamanho em todos os campos

### Criptografia
- Tokens JWT assinados com HMAC-SHA256
- Senhas hasheadas com bcrypt
- Segredos armazenados com criptografia AES-256

### Auditoria
- Todos os eventos de chat são auditados
- Mudanças em dados sensíveis são logadas
- Acessos administrativos são monitorados

### Conformidade
- LGPD/GDPR: Dados pessoais são anonimizados
- Consentimentos são registrados e versionados
- Direito ao esquecimento implementado
- Portabilidade de dados disponível

---

## 13. Suporte e Troubleshooting

### Logs e Debugging
- Logs estruturados em JSON
- Níveis: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Trace IDs para correlação de requests
- Métricas de performance coletadas

### Health Checks
```bash
# Verificar se API está respondendo
curl -f http://localhost:8000/health

# Verificar health detalhado
curl -f http://localhost:8000/healthz

# Verificar status do sistema
curl http://localhost:8000/api/v1/system/status

# Verificar workers
curl http://localhost:8000/api/v1/workers/status
```

### Diagnostic Tools
```bash
# Gerar diagnóstico completo
python tooling/dev.py doctor

# Verificar cobertura de API
python tooling/generate_api_coverage_report.py

# Testar endpoints críticos
python test_scenario1_apis.py
```

---

Esta documentação cobre todos os endpoints principais da API Janus. Para atualizações e mudanças, consulte o repositório oficial e os testes de contrato em `/qa/`.