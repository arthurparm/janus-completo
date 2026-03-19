# Janus Architecture Overview

## System Architecture

Janus is a multi-agent AI system built with a modern microservices architecture, combining an Angular frontend with a FastAPI backend that orchestrates multiple AI agents and services.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Angular 20)                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   Chat UI       │  │  Admin Panel    │  │   Dashboards    │  │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  │
│           │                    │                    │           │
│           └────────────────────┴────────────────────┘           │
│                              │                                 │
│                         HTTP/SSE                             │
└──────────────────────────────┬─────────────────────────────────┘
                               │
                               │
┌──────────────────────────────┴─────────────────────────────────┐
│                      API Gateway (FastAPI)                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  Auth Service   │  │  Rate Limiting  │  │  Validation     │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└──────────────────────────────┬─────────────────────────────────┘
                               │
┌──────────────────────────────┴─────────────────────────────────┐
│                     Core Services Layer                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ Chat Service    │  │ Agent Manager   │  │ Memory Service  │  │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  │
│           │                    │                    │           │
│  ┌────────┴────────┐  ┌────────┴────────┐  ┌────────┴────────┐  │
│  │ RAG Service     │  │ Tool Executor   │  │ Knowledge Graph │  │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  │
│           │                    │                    │           │
│           └────────────────────┴────────────────────┘           │
│                              │                                 │
└──────────────────────────────┬─────────────────────────────────┘
                               │
┌──────────────────────────────┴─────────────────────────────────┐
│                      Data Layer                                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   PostgreSQL    │  │     Neo4j       │  │    Qdrant       │  │
│  │  (Relational)   │  │   (Graph DB)    │  │  (Vector DB)    │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │     Redis       │  │    RabbitMQ     │  │    MinIO        │  │
│  │   (Caching)     │  │  (Message Bus)  │  │   (Storage)     │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Component Breakdown

### Frontend Architecture

**Technology Stack:**
- **Framework:** Angular 20 with TypeScript
- **UI Library:** Angular Material + TailwindCSS
- **State Management:** RxJS for reactive programming
- **Testing:** Vitest + Testing Library
- **Build:** Angular CLI with Vite

**Key Components:**
- **Chat Interface:** Real-time messaging with SSE support
- **Admin Panel:** System administration and monitoring
- **Dashboards:** Analytics and observability views
- **Shared Module:** Reusable components and services

### Backend Architecture

**Technology Stack:**
- **Framework:** FastAPI (Python 3.11+)
- **Database:** PostgreSQL with pgvector for vector operations
- **Graph Database:** Neo4j for knowledge relationships
- **Vector Database:** Qdrant for embeddings and similarity search
- **Message Queue:** RabbitMQ for async processing
- **Cache:** Redis for session and data caching
- **LLM Integration:** OpenAI, Gemini, Ollama, OpenRouter

**Core Services:**

#### 1. Chat Service
- Handles real-time conversations
- Manages conversation history and context
- Implements streaming responses via Server-Sent Events (SSE)
- Provides citation tracking and source attribution

#### 2. Agent Manager
- Orchestrates multiple AI agents
- Manages agent lifecycle and coordination
- Implements debate and collaboration patterns
- Handles agent specialization and routing

#### 3. Memory Service
- **Short-term:** Working memory for current conversation
- **Medium-term:** Session memory across conversations
- **Long-term:** Persistent user and system memory
- **Graph Memory:** Knowledge graph relationships

#### 4. RAG Service
- Hybrid retrieval combining dense and sparse methods
- Document parsing and chunking
- Embedding generation and storage
- Context injection and relevance scoring

#### 5. Tool Executor
- Safe execution of external tools
- Sandboxed environment for code execution
- Integration with external APIs and services
- Result validation and error handling

## Data Flow

### Chat Message Flow
```
User Input → Frontend → API Gateway → Chat Service → Agent Manager
                                           ↓
                                    Memory Service (context)
                                           ↓
                                    RAG Service (knowledge)
                                           ↓
                                    Tool Executor (actions)
                                           ↓
Response ← Frontend ← API Gateway ← Chat Service ← Agent Manager
```

### Memory Storage Flow
```
Conversation → Working Memory → Session Memory → Long-term Memory
      ↓              ↓               ↓               ↓
    Redis        PostgreSQL       PostgreSQL      Neo4j + Qdrant
```

## Security Architecture

### Authentication & Authorization
- JWT-based authentication with refresh tokens
- Role-based access control (RBAC)
- API key management for external services
- Rate limiting and abuse prevention

### Data Protection
- Encryption at rest for sensitive data
- Secure communication channels (HTTPS/WSS)
- Data anonymization and pseudonymization
- Audit logging for compliance

### Privacy Controls
- Consent management system
- Data retention policies
- Right to be forgotten implementation
- GDPR compliance features

## Scalability & Performance

### Horizontal Scaling
- Stateless API design for easy scaling
- Database connection pooling
- Redis cluster for distributed caching
- Message queue for async processing

### Performance Optimizations
- Response caching with Redis
- Database query optimization
- Vector search optimization in Qdrant
- Connection pooling and keep-alive

### Monitoring & Observability
- OpenTelemetry for distributed tracing
- Prometheus metrics collection
- Grafana dashboards for visualization
- Structured logging with correlation IDs

## Deployment Architecture

### PC1/PC2 Split
- **PC1:** Application services (API, frontend, databases)
- **PC2:** AI/ML services (Ollama, vector databases)
- Network isolation with Tailscale VPN
- Resource optimization per component

### Container Strategy
- Multi-stage Docker builds for optimization
- Non-root container execution
- Health checks and auto-restart
- Resource limits and quotas

## Integration Patterns

### Event-Driven Architecture
- RabbitMQ for decoupled communication
- Event sourcing for audit trails
- CQRS pattern for read/write separation
- Saga pattern for distributed transactions

### API Design
- RESTful principles with consistent naming
- GraphQL for complex queries (planned)
- WebSocket for real-time features
- Webhook support for integrations

## Future Considerations

### Planned Improvements
- GraphQL API layer for flexible queries
- Edge computing for reduced latency
- Multi-region deployment support
- Advanced caching strategies

### Technology Evolution
- Kubernetes migration path
- Service mesh implementation
- Advanced observability tools
- AI/ML pipeline optimization

---

*This architecture overview is maintained by the Janus team. For detailed technical specifications, see the component-specific documentation.*