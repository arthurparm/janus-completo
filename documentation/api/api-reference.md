# Janus API Reference

## Overview

The Janus API is a multi-agent AI platform that provides endpoints for chat, authentication, memory management, knowledge, observability, and system administration. Built with FastAPI, it supports token authentication, message streaming, and integration with multiple LLM providers.

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

The API supports multiple authentication methods:

### 1. JWT Token (Bearer)
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

### 4. Local Auth (Email/Password)
```
POST /auth/local/login
POST /auth/local/register
```

---

## 1. Chat/Conversation Endpoints

### 1.1 Start New Conversation

**POST** `/chat/start`

Starts a new conversation and returns a conversation_id.

**Request Body:**
```json
{
  "persona": "assistant",
  "user_id": "user123",
  "project_id": "proj456",
  "title": "My Conversation"
}
```

**Response:**
```json
{
  "conversation_id": "conv-abc123"
}
```

**Error Codes:**
- `401`: Authentication required (`CHAT_AUTH_REQUIRED`)
- `422`: Invalid request format

### 1.2 Send Message

**POST** `/chat/message`

Sends a message and receives LLM response with optional streaming.

**Request Body:**
```json
{
  "conversation_id": "conv-abc123",
  "message": "What is the capital of Brazil?",
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
  "response": "The capital of Brazil is Brasília.",
  "provider": "openai",
  "model": "gpt-4",
  "role": "assistant",
  "conversation_id": "conv-abc123",
  "message_id": "msg-789",
  "citations": [
    {
      "source": "wikipedia",
      "text": "Brasília is the federal capital of Brazil",
      "url": "https://en.wikipedia.org/wiki/Bras%C3%ADlia"
    }
  ],
  "tokens_used": 45,
  "cost_usd": 0.00135
}
```

**Streaming Response:**
For streaming responses, use `Accept: text/event-stream` header.

### 1.3 Get Conversation History

**GET** `/chat/history/{conversation_id}`

Retrieves the complete conversation history.

**Query Parameters:**
- `limit` (optional): Number of messages to return (default: 50)
- `offset` (optional): Pagination offset

**Response:**
```json
{
  "conversation_id": "conv-abc123",
  "title": "My Conversation",
  "messages": [
    {
      "message_id": "msg-123",
      "role": "user",
      "content": "What is the capital of Brazil?",
      "timestamp": "2024-01-15T10:30:00Z"
    },
    {
      "message_id": "msg-789",
      "role": "assistant",
      "content": "The capital of Brazil is Brasília.",
      "timestamp": "2024-01-15T10:30:01Z"
    }
  ],
  "total_messages": 2
}
```

### 1.4 Delete Conversation

**DELETE** `/chat/conversation/{conversation_id}`

Deletes a conversation and all its messages.

**Response:**
```json
{
  "status": "deleted",
  "conversation_id": "conv-abc123"
}
```

---

## 2. Authentication Endpoints

### 2.1 JWT Authentication

**POST** `/auth/jwt/login`

Authenticates user and returns JWT token.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "user123",
    "email": "user@example.com",
    "name": "John Doe"
  }
}
```

### 2.2 Refresh Token

**POST** `/auth/jwt/refresh`

Refreshes an expired JWT token.

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### 2.3 Firebase Authentication

**POST** `/auth/firebase/exchange`

Exchanges Firebase token for Janus JWT token.

**Request Body:**
```json
{
  "firebase_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6I..."
}
```

### 2.4 Supabase Authentication

**POST** `/auth/supabase/exchange`

Exchanges Supabase token for Janus JWT token.

**Request Body:**
```json
{
  "supabase_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### 2.5 Local Registration

**POST** `/auth/local/register`

Registers a new user with email and password.

**Request Body:**
```json
{
  "email": "newuser@example.com",
  "password": "securepassword",
  "name": "Jane Doe",
  "cpf": "12345678901"
}
```

**Response:**
```json
{
  "user_id": "user456",
  "email": "newuser@example.com",
  "name": "Jane Doe",
  "message": "Registration successful"
}
```

---

## 3. Memory Management Endpoints

### 3.1 Store Memory

**POST** `/memory/store`

Stores a memory item for future reference.

**Request Body:**
```json
{
  "user_id": "user123",
  "content": "User prefers dark mode",
  "category": "preference",
  "tags": ["ui", "theme"],
  "importance": "high",
  "expiration_days": 365
}
```

**Response:**
```json
{
  "memory_id": "mem-abc123",
  "status": "stored"
}
```

### 3.2 Retrieve Memories

**GET** `/memory/retrieve`

Retrieves relevant memories for a user.

**Query Parameters:**
- `user_id` (required): User ID
- `query` (optional): Search query
- `category` (optional): Memory category
- `limit` (optional): Maximum results (default: 10)

**Response:**
```json
{
  "memories": [
    {
      "memory_id": "mem-abc123",
      "content": "User prefers dark mode",
      "category": "preference",
      "tags": ["ui", "theme"],
      "importance": "high",
      "created_at": "2024-01-15T10:30:00Z",
      "relevance_score": 0.95
    }
  ],
  "total": 1
}
```

### 3.3 Delete Memory

**DELETE** `/memory/{memory_id}`

Deletes a specific memory item.

**Response:**
```json
{
  "status": "deleted",
  "memory_id": "mem-abc123"
}
```

### 3.4 Get Memory Timeline

**GET** `/memory/timeline/{user_id}`

Retrieves chronological memory timeline for a user.

**Query Parameters:**
- `start_date` (optional): Start date (ISO 8601)
- `end_date` (optional): End date (ISO 8601)
- `category` (optional): Filter by category

**Response:**
```json
{
  "timeline": [
    {
      "date": "2024-01-15",
      "memories": [
        {
          "memory_id": "mem-abc123",
          "content": "User prefers dark mode",
          "category": "preference",
          "timestamp": "2024-01-15T10:30:00Z"
        }
      ]
    }
  ]
}
```

---

## 4. Knowledge Graph Endpoints

### 4.1 Index Document

**POST** `/knowledge/index`

Indexes a document into the knowledge graph.

**Request Body:**
```json
{
  "content": "Artificial Intelligence is the simulation of human intelligence...",
  "title": "Introduction to AI",
  "source": "wikipedia",
  "source_url": "https://en.wikipedia.org/wiki/Artificial_intelligence",
  "tags": ["ai", "technology", "machine-learning"],
  "metadata": {
    "author": "John Doe",
    "publication_date": "2024-01-01"
  }
}
```

**Response:**
```json
{
  "document_id": "doc-xyz789",
  "chunks_indexed": 12,
  "entities_extracted": 8,
  "relationships_created": 15
}
```

### 4.2 Query Knowledge Graph

**POST** `/knowledge/query`

Queries the knowledge graph for relevant information.

**Request Body:**
```json
{
  "query": "What are the main applications of AI?",
  "top_k": 5,
  "filters": {
    "source": "wikipedia",
    "tags": ["ai", "applications"]
  }
}
```

**Response:**
```json
{
  "results": [
    {
      "document_id": "doc-xyz789",
      "title": "Introduction to AI",
      "content": "AI has applications in healthcare, finance, transportation...",
      "relevance_score": 0.92,
      "source": "wikipedia",
      "metadata": {
        "author": "John Doe"
      }
    }
  ],
  "total_results": 1
}
```

### 4.3 Get Entity Relationships

**GET** `/knowledge/entity/{entity_name}/relationships`

Retrieves relationships for a specific entity.

**Response:**
```json
{
  "entity": "Artificial Intelligence",
  "relationships": [
    {
      "relationship_type": "related_to",
      "target_entity": "Machine Learning",
      "strength": 0.95,
      "document_sources": ["doc-xyz789", "doc-abc123"]
    }
  ]
}
```

---

## 5. Observability Endpoints

### 5.1 System Status

**GET** `/observability/system/status`

Returns overall system health and status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "rabbitmq": "healthy",
    "ollama": "healthy"
  },
  "metrics": {
    "active_conversations": 15,
    "total_messages_today": 2341,
    "average_response_time_ms": 850
  }
}
```

### 5.2 Get Metrics

**GET** `/observability/metrics`

Retrieves system metrics with optional filtering.

**Query Parameters:**
- `metric_type` (optional): Type of metric (cpu, memory, requests)
- `time_range` (optional): Time range (1h, 24h, 7d)
- `service` (optional): Specific service

**Response:**
```json
{
  "metrics": [
    {
      "metric_name": "api_requests_total",
      "value": 15420,
      "timestamp": "2024-01-15T10:30:00Z",
      "labels": {
        "service": "chat",
        "status": "200"
      }
    }
  ]
}
```

### 5.3 Get SLO Report

**GET** `/observability/slo/domains`

Retrieves Service Level Objectives (SLO) report.

**Query Parameters:**
- `window_minutes` (optional): Time window in minutes
- `min_events` (optional): Minimum events for reporting

**Response:**
```json
{
  "domains": [
    {
      "domain": "chat",
      "slo_target": 0.99,
      "current_slo": 0.987,
      "total_events": 15420,
      "error_budget_remaining": 0.65
    }
  ]
}
```

---

## 6. Admin Endpoints

### 6.1 System Health

**GET** `/admin/health`

Returns detailed system health information.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.2.3",
  "uptime_seconds": 86400,
  "services": {
    "api": "healthy",
    "database": "healthy",
    "cache": "healthy"
  }
}
```

### 6.2 Get Configuration

**GET** `/admin/config`

Retrieves current system configuration (admin only).

**Response:**
```json
{
  "llm_providers": {
    "openai": {"enabled": true, "model": "gpt-4"},
    "gemini": {"enabled": true, "model": "gemini-pro"}
  },
  "features": {
    "chat_streaming": true,
    "memory_enabled": true,
    "knowledge_graph": true
  }
}
```

### 6.3 Update Configuration

**PUT** `/admin/config`

Updates system configuration (admin only).

**Request Body:**
```json
{
  "llm_providers": {
    "openai": {"enabled": false}
  }
}
```

---

## 7. Worker Management Endpoints

### 7.1 List Workers

**GET** `/workers/list`

Lists all active workers and their status.

**Response:**
```json
{
  "workers": [
    {
      "worker_id": "worker-123",
      "type": "chat_processor",
      "status": "active",
      "last_heartbeat": "2024-01-15T10:30:00Z",
      "tasks_processed": 1542
    }
  ],
  "total_workers": 1
}
```

### 7.2 Worker Status

**GET** `/workers/status`

Returns overall worker system status.

**Response:**
```json
{
  "total_workers": 5,
  "active_workers": 4,
  "idle_workers": 1,
  "failed_workers": 0,
  "queue_depth": 23
}
```

---

## Error Handling

### Error Response Format

All errors follow a consistent format:

```json
{
  "error": {
    "code": "CHAT_AUTH_REQUIRED",
    "message": "Authentication is required to access this resource",
    "details": {
      "field": "authorization",
      "provided": null
    }
  },
  "request_id": "req-abc123",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `AUTH_INVALID_TOKEN` | 401 | Invalid or expired token |
| `AUTH_INSUFFICIENT_PERMISSIONS` | 403 | Insufficient permissions |
| `CHAT_CONVERSATION_NOT_FOUND` | 404 | Conversation not found |
| `MEMORY_NOT_FOUND` | 404 | Memory item not found |
| `RATE_LIMIT_EXCEEDED` | 429 | Rate limit exceeded |
| `INTERNAL_SERVER_ERROR` | 500 | Internal server error |

---

## Rate Limiting

- **Standard**: 100 requests per minute per user
- **Chat endpoints**: 50 requests per minute per user  
- **Authentication**: 10 requests per minute per IP
- **Admin endpoints**: 20 requests per minute per user

Rate limit headers are included in all responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1642249800
```

---

## SDK Examples

### Python
```python
import requests

# Authentication
auth_response = requests.post(
    "http://localhost:8000/api/v1/auth/jwt/login",
    json={"email": "user@example.com", "password": "password"}
)
token = auth_response.json()["access_token"]

# Send message
headers = {"Authorization": f"Bearer {token}"}
response = requests.post(
    "http://localhost:8000/api/v1/chat/message",
    headers=headers,
    json={
        "conversation_id": "conv-123",
        "message": "Hello, how are you?"
    }
)
print(response.json())
```

### JavaScript
```javascript
// Authentication
const authResponse = await fetch('http://localhost:8000/api/v1/auth/jwt/login', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'password'
  })
});
const { access_token } = await authResponse.json();

// Send message
const response = await fetch('http://localhost:8000/api/v1/chat/message', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${access_token}`
  },
  body: JSON.stringify({
    conversation_id: 'conv-123',
    message: 'Hello, how are you?'
  })
});
const data = await response.json();
console.log(data);
```

### cURL
```bash
# Authentication
curl -X POST "http://localhost:8000/api/v1/auth/jwt/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'

# Send message (using token from auth response)
curl -X POST "http://localhost:8000/api/v1/chat/message" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "conversation_id": "conv-123",
    "message": "Hello, how are you?"
  }'
```

---

## Postman Collection

Download our Postman collection for easy testing:
```bash
curl -O https://raw.githubusercontent.com/your-org/janus/main/docs/janus-api-postman.json
```

---

## OpenAPI Specification

Access the interactive API documentation at:
```
http://localhost:8000/docs
```

Or download the OpenAPI specification:
```
http://localhost:8000/openapi.json
```

---

*This API reference is maintained by the Janus development team. For questions or contributions, please open an issue on GitHub.*