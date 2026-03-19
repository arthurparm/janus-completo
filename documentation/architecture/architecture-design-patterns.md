# Arquitetura e Design Patterns do Janus

## Visão Geral da Arquitetura

O Janus é construído sobre uma arquitetura de microserviços moderna, seguindo princípios de Domain-Driven Design (DDD) e Clean Architecture. O sistema é projetado para ser escalável, resiliente e manutenível.

### Arquitetura de Alto Nível

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend Layer                           │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   Angular 20    │   WebSocket     │        PWA Support          │
│   (TypeScript)  │   (Real-time)   │     (Service Worker)       │
└─────────────────┴─────────────────┴─────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway Layer                          │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   FastAPI       │   Rate Limit    │     Authentication         │
│   (Python)      │   Circuit Breaker│     Authorization          │
└─────────────────┴─────────────────┴─────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Business Logic Layer                        │
├─────────────────┬─────────────────┬─────────────────────────────┤
│  LLM Services   │  Chat Services  │    Memory Services        │
│  (Multi-agent)  │  (Real-time)    │   (Vector Storage)        │
└─────────────────┴─────────────────┴─────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Data Access Layer                          │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   PostgreSQL    │     Redis       │    Vector Databases       │
│   (Relational)  │   (Cache/Queue) │  (Qdrant/PGVector)       │
└─────────────────┴─────────────────┴─────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Infrastructure Layer                          │
├─────────────────┬─────────────────┬─────────────────────────────┤
│    Docker       │   Kubernetes    │     Monitoring            │
│   (Containers)  │   (Orchestration)│   (Prometheus/Grafana)    │
└─────────────────┴─────────────────┴─────────────────────────────┘
```

## Design Patterns Implementados

### 1. Domain-Driven Design (DDD)

#### Entidades de Domínio

```python
# backend/app/domain/entities/user.py
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime

@dataclass
class User:
    """Entidade de domínio representando um usuário"""
    id: str
    email: str
    name: str
    created_at: datetime
    updated_at: datetime
    is_active: bool = True
    
    def activate(self):
        """Método de negócio para ativar usuário"""
        self.is_active = True
        self.updated_at = datetime.utcnow()
    
    def deactivate(self):
        """Método de negócio para desativar usuário"""
        self.is_active = False
        self.updated_at = datetime.utcnow()

@dataclass
class ChatSession:
    """Entidade de domínio para sessões de chat"""
    id: str
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List['ChatMessage'] = None
    
    def add_message(self, message: 'ChatMessage'):
        """Adicionar mensagem à sessão"""
        if self.messages is None:
            self.messages = []
        self.messages.append(message)
        self.updated_at = datetime.utcnow()
```

#### Objetos de Valor

```python
# backend/app/domain/value_objects.py
from dataclasses import dataclass
from typing import Dict, Any
import uuid

@dataclass(frozen=True)
class LLMConfig:
    """Objeto de valor para configuração de LLM"""
    provider: str
    model: str
    temperature: float
    max_tokens: int
    
    def validate(self):
        """Validar configuração"""
        if not 0 <= self.temperature <= 2:
            raise ValueError("Temperature must be between 0 and 2")
        if self.max_tokens <= 0:
            raise ValueError("Max tokens must be positive")

@dataclass(frozen=True)
class MessageId:
    """Objeto de valor para ID de mensagem"""
    value: str
    
    def __post_init__(self):
        if not self.value:
            self.value = str(uuid.uuid4())
    
    def __str__(self):
        return self.value
```

### 2. Repository Pattern

```python
# backend/app/domain/repositories/base.py
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional

T = TypeVar('T')

class Repository(ABC, Generic[T]):
    """Interface base para repositórios"""
    
    @abstractmethod
    async def find_by_id(self, id: str) -> Optional[T]:
        """Buscar entidade por ID"""
        pass
    
    @abstractmethod
    async def find_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """Buscar todas as entidades"""
        pass
    
    @abstractmethod
    async def save(self, entity: T) -> T:
        """Salvar entidade"""
        pass
    
    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Deletar entidade"""
        pass

# backend/app/domain/repositories/user_repository.py
from typing import Optional
from .base import Repository
from ..entities.user import User

class UserRepository(Repository[User]):
    """Repositório para usuários"""
    
    async def find_by_email(self, email: str) -> Optional[User]:
        """Buscar usuário por email"""
        # Implementação específica
        pass
    
    async def find_active_users(self) -> List[User]:
        """Buscar usuários ativos"""
        # Implementação específica
        pass
```

### 3. Service Layer Pattern

```python
# backend/app/application/services/chat_service.py
from typing import List, Optional
from domain.entities import ChatSession, ChatMessage
from domain.repositories import ChatRepository, UserRepository
from domain.value_objects import LLMConfig
from infrastructure.llm.factory import LLMFactory

class ChatService:
    """Serviço de aplicação para gerenciamento de chat"""
    
    def __init__(
        self,
        chat_repository: ChatRepository,
        user_repository: UserRepository,
        llm_factory: LLMFactory
    ):
        self.chat_repository = chat_repository
        self.user_repository = user_repository
        self.llm_factory = llm_factory
    
    async def create_session(self, user_id: str, title: str) -> ChatSession:
        """Criar nova sessão de chat"""
        user = await self.user_repository.find_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        session = ChatSession(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=title,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        return await self.chat_repository.save(session)
    
    async def process_message(
        self,
        session_id: str,
        content: str,
        llm_config: LLMConfig
    ) -> ChatMessage:
        """Processar mensagem usando LLM"""
        session = await self.chat_repository.find_by_id(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Criar mensagem do usuário
        user_message = ChatMessage(
            id=str(uuid.uuid4()),
            session_id=session_id,
            content=content,
            role="user",
            created_at=datetime.utcnow()
        )
        
        # Obter resposta do LLM
        llm_service = self.llm_factory.create(llm_config)
        response = await llm_service.generate_response(
            messages=session.get_messages_for_llm() + [user_message]
        )
        
        # Criar mensagem de resposta
        assistant_message = ChatMessage(
            id=str(uuid.uuid4()),
            session_id=session_id,
            content=response.content,
            role="assistant",
            model=llm_config.model,
            tokens_used=response.tokens_used,
            created_at=datetime.utcnow()
        )
        
        # Salvar mensagens
        await self.chat_repository.save_message(user_message)
        await self.chat_repository.save_message(assistant_message)
        
        return assistant_message
```

### 4. Factory Pattern

```python
# backend/app/infrastructure/llm/factory.py
from typing import Dict, Type
from domain.value_objects import LLMConfig
from .base import LLMProvider
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .google_provider import GoogleProvider
from .ollama_provider import OllamaProvider

class LLMFactory:
    """Factory para criar provedores de LLM"""
    
    def __init__(self):
        self._providers: Dict[str, Type[LLMProvider]] = {
            "openai": OpenAIProvider,
            "anthropic": AnthropicProvider,
            "google": GoogleProvider,
            "ollama": OllamaProvider,
        }
    
    def create(self, config: LLMConfig) -> LLMProvider:
        """Criar provedor de LLM baseado na configuração"""
        provider_class = self._providers.get(config.provider)
        if not provider_class:
            raise ValueError(f"Unsupported LLM provider: {config.provider}")
        
        return provider_class(config)
    
    def register_provider(self, name: str, provider_class: Type[LLMProvider]):
        """Registrar novo provedor"""
        self._providers[name] = provider_class
```

### 5. Strategy Pattern

```python
# backend/app/domain/strategies/memory_strategies.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from domain.entities import ChatMessage

class MemoryStrategy(ABC):
    """Estratégia base para gerenciamento de memória"""
    
    @abstractmethod
    async def store_memory(
        self,
        user_id: str,
        session_id: str,
        messages: List[ChatMessage]
    ) -> None:
        """Armazenar memória"""
        pass
    
    @abstractmethod
    async def retrieve_relevant_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Recuperar memórias relevantes"""
        pass

class VectorMemoryStrategy(MemoryStrategy):
    """Estratégia usando vetores para memória"""
    
    def __init__(self, vector_store, embedding_service):
        self.vector_store = vector_store
        self.embedding_service = embedding_service
    
    async def store_memory(
        self,
        user_id: str,
        session_id: str,
        messages: List[ChatMessage]
    ) -> None:
        """Armazenar memória usando embeddings"""
        for message in messages:
            embedding = await self.embedding_service.embed(message.content)
            await self.vector_store.add(
                collection=f"user_{user_id}",
                embedding=embedding,
                metadata={
                    "session_id": session_id,
                    "message_id": message.id,
                    "content": message.content,
                    "timestamp": message.created_at.isoformat()
                }
            )
    
    async def retrieve_relevant_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Recuperar memórias relevantes usando similaridade vetorial"""
        query_embedding = await self.embedding_service.embed(query)
        results = await self.vector_store.search(
            collection=f"user_{user_id}",
            embedding=query_embedding,
            limit=limit
        )
        
        return [
            {
                "content": result.metadata["content"],
                "score": result.score,
                "timestamp": result.metadata["timestamp"]
            }
            for result in results
        ]

class GraphMemoryStrategy(MemoryStrategy):
    """Estratégia usando grafo de conhecimento para memória"""
    
    def __init__(self, graph_store):
        self.graph_store = graph_store
    
    async def store_memory(
        self,
        user_id: str,
        session_id: str,
        messages: List[ChatMessage]
    ) -> None:
        """Armazenar memória como grafo de conhecimento"""
        # Criar nós e relações no grafo
        for message in messages:
            await self.graph_store.create_node(
                label="Message",
                properties={
                    "id": message.id,
                    "content": message.content,
                    "user_id": user_id,
                    "session_id": session_id
                }
            )
    
    async def retrieve_relevant_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Recuperar memórias usando queries de grafo"""
        cypher_query = """
        MATCH (m:Message {user_id: $user_id})
        WHERE m.content CONTAINS $query
        RETURN m.content as content, m.timestamp as timestamp
        LIMIT $limit
        """
        
        results = await self.graph_store.query(
            cypher_query,
            parameters={
                "user_id": user_id,
                "query": query,
                "limit": limit
            }
        )
        
        return results
```

### 6. Observer Pattern

```python
# backend/app/domain/events/base.py
from abc import ABC, abstractmethod
from typing import List, Callable, Any

class Event(ABC):
    """Evento base do domínio"""
    
    def __init__(self, aggregate_id: str):
        self.aggregate_id = aggregate_id
        self.timestamp = datetime.utcnow()

class DomainEventHandler(ABC):
    """Handler base para eventos de domínio"""
    
    @abstractmethod
    async def handle(self, event: Event) -> None:
        """Manipular evento"""
        pass

class EventBus:
    """Barramento de eventos para comunicação desacoplada"""
    
    def __init__(self):
        self._handlers: Dict[str, List[DomainEventHandler]] = {}
    
    def subscribe(self, event_type: str, handler: DomainEventHandler):
        """Inscrever handler para tipo de evento"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    async def publish(self, event: Event) -> None:
        """Publicar evento"""
        event_type = event.__class__.__name__
        handlers = self._handlers.get(event_type, [])
        
        for handler in handlers:
            try:
                await handler.handle(event)
            except Exception as e:
                # Log error but don't stop other handlers
                logger.error(f"Error handling event {event_type}: {e}")

# Eventos específicos do domínio
class ChatMessageCreated(Event):
    """Evento disparado quando uma mensagem é criada"""
    
    def __init__(self, message_id: str, session_id: str, content: str):
        super().__init__(session_id)
        self.message_id = message_id
        self.content = content

class LLMResponseGenerated(Event):
    """Evento disparado quando LLM gera resposta"""
    
    def __init__(self, response_id: str, session_id: str, model: str, tokens_used: int):
        super().__init__(session_id)
        self.response_id = response_id
        self.model = model
        self.tokens_used = tokens_used
```

### 7. Decorator Pattern

```python
# backend/app/infrastructure/decorators.py
import functools
import time
import logging
from typing import Callable, Any
from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)

# Métricas
function_calls = Counter('janus_function_calls_total', 'Total function calls', ['function_name'])
function_duration = Histogram('janus_function_duration_seconds', 'Function duration', ['function_name'])

def measure_performance(func: Callable) -> Callable:
    """Decorator para medir performance de funções"""
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        function_name = func.__name__
        
        try:
            function_calls.labels(function_name=function_name).inc()
            result = await func(*args, **kwargs)
            
            duration = time.time() - start_time
            function_duration.labels(function_name=function_name).observe(duration)
            
            return result
        except Exception as e:
            logger.error(f"Error in {function_name}: {e}")
            raise
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        function_name = func.__name__
        
        try:
            function_calls.labels(function_name=function_name).inc()
            result = func(*args, **kwargs)
            
            duration = time.time() - start_time
            function_duration.labels(function_name=function_name).observe(duration)
            
            return result
        except Exception as e:
            logger.error(f"Error in {function_name}: {e}")
            raise
    
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """Decorator para retry em caso de falha"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Max retries reached for {func.__name__}")
                        raise
                    
                    logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}")
                    await asyncio.sleep(delay * (2 ** attempt))  # Exponential backoff
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Max retries reached for {func.__name__}")
                        raise
                    
                    logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}")
                    time.sleep(delay * (2 ** attempt))  # Exponential backoff
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

def cache_result(ttl: int = 3600):
    """Decorator para cache de resultados"""
    def decorator(func: Callable) -> Callable:
        cache = {}
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            cache_key = str(args) + str(sorted(kwargs.items()))
            
            if cache_key in cache:
                result, timestamp = cache[cache_key]
                if time.time() - timestamp < ttl:
                    return result
            
            result = await func(*args, **kwargs)
            cache[cache_key] = (result, time.time())
            return result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            cache_key = str(args) + str(sorted(kwargs.items()))
            
            if cache_key in cache:
                result, timestamp = cache[cache_key]
                if time.time() - timestamp < ttl:
                    return result
            
            result = func(*args, **kwargs)
            cache[cache_key] = (result, time.time())
            return result
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator
```

## Arquitetura de Microserviços

### 1. Decomposição de Serviços

```yaml
# docker-compose.services.yml
version: '3.8'

services:
  # API Gateway
  api-gateway:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - SERVICE_NAME=api-gateway
      - AUTH_SERVICE_URL=http://auth-service:8001
      - CHAT_SERVICE_URL=http://chat-service:8002
      - LLM_SERVICE_URL=http://llm-service:8003
    depends_on:
      - auth-service
      - chat-service
      - llm-service

  # Auth Service
  auth-service:
    build: ./backend/services/auth
    ports:
      - "8001:8001"
    environment:
      - SERVICE_NAME=auth-service
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - POSTGRES_URL=${POSTGRES_URL}
    depends_on:
      - postgres

  # Chat Service
  chat-service:
    build: ./backend/services/chat
    ports:
      - "8002:8002"
    environment:
      - SERVICE_NAME=chat-service
      - REDIS_URL=${REDIS_URL}
      - POSTGRES_URL=${POSTGRES_URL}
    depends_on:
      - postgres
      - redis

  # LLM Service
  llm-service:
    build: ./backend/services/llm
    ports:
      - "8003:8003"
    environment:
      - SERVICE_NAME=llm-service
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
    depends_on:
      - qdrant
      - ollama

  # Memory Service
  memory-service:
    build: ./backend/services/memory
    ports:
      - "8004:8004"
    environment:
      - SERVICE_NAME=memory-service
      - NEO4J_URL=${NEO4J_URL}
      - QDRANT_URL=${QDRANT_URL}
    depends_on:
      - neo4j
      - qdrant

  # Notification Service
  notification-service:
    build: ./backend/services/notification
    ports:
      - "8005:8005"
    environment:
      - SERVICE_NAME=notification-service
      - RABBITMQ_URL=${RABBITMQ_URL}
      - SMTP_HOST=${SMTP_HOST}
    depends_on:
      - rabbitmq
```

### 2. Comunicação entre Serviços

```python
# backend/app/infrastructure/messaging/service_communication.py
from typing import Dict, Any, Optional
import httpx
import asyncio
from contextlib import asynccontextmanager

class ServiceCommunication:
    """Comunicação assíncrona entre serviços"""
    
    def __init__(self, service_urls: Dict[str, str]):
        self.service_urls = service_urls
        self._clients: Dict[str, httpx.AsyncClient] = {}
    
    @asynccontextmanager
    async def get_client(self, service_name: str):
        """Obter cliente HTTP para serviço"""
        if service_name not in self._clients:
            base_url = self.service_urls.get(service_name)
            if not base_url:
                raise ValueError(f"Service {service_name} not configured")
            
            self._clients[service_name] = httpx.AsyncClient(
                base_url=base_url,
                timeout=30.0,
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
            )
        
        yield self._clients[service_name]
    
    async def call_service(
        self,
        service_name: str,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Chamar serviço com retry e circuit breaker"""
        
        async with self.get_client(service_name) as client:
            request_func = getattr(client, method.lower())
            
            try:
                response = await request_func(
                    endpoint,
                    json=data,
                    headers=headers
                )
                response.raise_for_status()
                return response.json()
            
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error calling {service_name}{endpoint}: {e}")
                raise ServiceCommunicationError(f"Service {service_name} returned {e.response.status_code}")
            
            except httpx.RequestError as e:
                logger.error(f"Request error calling {service_name}{endpoint}: {e}")
                raise ServiceCommunicationError(f"Failed to connect to {service_name}")

# Implementação de Circuit Breaker
class CircuitBreaker:
    """Circuit breaker para proteção de serviços"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, func: Callable, *args, **kwargs):
        """Chamar função com proteção de circuit breaker"""
        
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
            else:
                raise CircuitBreakerOpenError("Circuit breaker is open")
        
        try:
            result = await func(*args, **kwargs)
            
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            
            return result
        
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                logger.error(f"Circuit breaker opened due to {self.failure_count} failures")
            
            raise
```

### 3. Service Discovery

```python
# backend/app/infrastructure/service_discovery.py
import asyncio
import aiohttp
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class ServiceInstance:
    """Instância de serviço"""
    id: str
    name: str
    host: str
    port: int
    health_check_url: str
    metadata: Dict[str, Any]
    last_heartbeat: float

class ServiceDiscovery:
    """Descoberta de serviços com health checking"""
    
    def __init__(self, consul_url: str):
        self.consul_url = consul_url
        self.services: Dict[str, List[ServiceInstance]] = {}
        self._health_check_task = None
    
    async def register_service(
        self,
        service_name: str,
        service_id: str,
        host: str,
        port: int,
        health_check_url: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Registrar serviço no Consul"""
        registration = {
            "ID": service_id,
            "Name": service_name,
            "Address": host,
            "Port": port,
            "Check": {
                "HTTP": f"http://{host}:{port}{health_check_url}",
                "Interval": "10s",
                "Timeout": "5s"
            },
            "Meta": metadata or {}
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.put(
                f"{self.consul_url}/v1/agent/service/register",
                json=registration
            ) as response:
                response.raise_for_status()
    
    async def discover_service(self, service_name: str) -> List[ServiceInstance]:
        """Descobrir instâncias de serviço"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.consul_url}/v1/health/service/{service_name}"
            ) as response:
                services_data = await response.json()
                
                instances = []
                for service_data in services_data:
                    service = service_data["Service"]
                    checks = service_data["Checks"]
                    
                    # Verificar se serviço está saudável
                    if all(check["Status"] == "passing" for check in checks):
                        instance = ServiceInstance(
                            id=service["ID"],
                            name=service["Service"],
                            host=service["Address"],
                            port=service["Port"],
                            health_check_url=f"http://{service['Address']}:{service['Port']}/health",
                            metadata=service.get("Meta", {}),
                            last_heartbeat=time.time()
                        )
                        instances.append(instance)
                
                self.services[service_name] = instances
                return instances
    
    def get_healthy_instance(self, service_name: str) -> Optional[ServiceInstance]:
        """Obter instância saudável (round-robin)"""
        instances = self.services.get(service_name, [])
        healthy_instances = [inst for inst in instances if self._is_instance_healthy(inst)]
        
        if not healthy_instances:
            return None
        
        # Round-robin simples
        import random
        return random.choice(healthy_instances)
    
    def _is_instance_healthy(self, instance: ServiceInstance) -> bool:
        """Verificar se instância está saudável"""
        # Verificar tempo desde último heartbeat
        if time.time() - instance.last_heartbeat > 30:  # 30 segundos
            return False
        
        return True
    
    async def start_health_checking(self):
        """Iniciar verificação periódica de saúde"""
        async def health_check_loop():
            while True:
                try:
                    for service_name, instances in self.services.items():
                        healthy_instances = []
                        
                        for instance in instances:
                            try:
                                async with aiohttp.ClientSession() as session:
                                    async with session.get(
                                        instance.health_check_url,
                                        timeout=5
                                    ) as response:
                                        if response.status == 200:
                                            instance.last_heartbeat = time.time()
                                            healthy_instances.append(instance)
                            except Exception:
                                # Instance is unhealthy
                                pass
                        
                        self.services[service_name] = healthy_instances
                    
                    await asyncio.sleep(10)  # Check every 10 seconds
                
                except Exception as e:
                    logger.error(f"Error in health check: {e}")
                    await asyncio.sleep(10)
        
        self._health_check_task = asyncio.create_task(health_check_loop())
```

## Padrões de Resiliência

### 1. Retry Pattern

```python
# backend/app/infrastructure/resilience/retry.py
import asyncio
import random
from typing import Callable, Any
from functools import wraps

class RetryConfig:
    """Configuração para retry"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

def with_retry(config: RetryConfig = None):
    """Decorator para retry com backoff exponencial"""
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            delay = config.initial_delay
            
            for attempt in range(config.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == config.max_attempts - 1:
                        # Last attempt, don't retry
                        raise
                    
                    # Calculate delay with optional jitter
                    if config.jitter:
                        delay = random.uniform(delay * 0.5, delay * 1.5)
                    
                    await asyncio.sleep(min(delay, config.max_delay))
                    
                    # Exponential backoff
                    delay = min(delay * config.exponential_base, config.max_delay)
            
            # Should never reach here
            raise RuntimeError("Retry logic failed")
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            delay = config.initial_delay
            
            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == config.max_attempts - 1:
                        raise
                    
                    if config.jitter:
                        delay = random.uniform(delay * 0.5, delay * 1.5)
                    
                    time.sleep(min(delay, config.max_delay))
                    delay = min(delay * config.exponential_base, config.max_delay)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

# Usage examples
@with_retry(RetryConfig(max_attempts=5, initial_delay=0.1))
async def call_external_api():
    """Chamar API externa com retry"""
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com/data")
        response.raise_for_status()
        return response.json()
```

### 2. Bulkhead Pattern

```python
# backend/app/infrastructure/resilience/bulkhead.py
import asyncio
import threading
from typing import Callable, Any, Optional
from concurrent.futures import ThreadPoolExecutor

class Bulkhead:
    """Bulkhead pattern para isolar recursos"""
    
    def __init__(
        self,
        name: str,
        max_concurrent_calls: int = 10,
        max_queue_size: int = 100,
        timeout: float = 30.0
    ):
        self.name = name
        self.max_concurrent_calls = max_concurrent_calls
        self.max_queue_size = max_queue_size
        self.timeout = timeout
        
        self._semaphore = asyncio.Semaphore(max_concurrent_calls)
        self._queue = asyncio.Queue(maxsize=max_queue_size)
        self._executor = ThreadPoolExecutor(max_workers=max_concurrent_calls)
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Executar função dentro do bulkhead"""
        
        # Try to acquire semaphore with timeout
        try:
            await asyncio.wait_for(self._semaphore.acquire(), timeout=self.timeout)
        except asyncio.TimeoutError:
            raise BulkheadFullError(f"Bulkhead {self.name} is full")
        
        try:
            # Execute function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                # Run sync function in thread pool
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(self._executor, func, *args, **kwargs)
            
            return result
        
        finally:
            self._semaphore.release()
    
    def get_stats(self) -> Dict[str, Any]:
        """Obter estatísticas do bulkhead"""
        return {
            "name": self.name,
            "max_concurrent_calls": self.max_concurrent_calls,
            "current_calls": self.max_concurrent_calls - self._semaphore._value,
            "queue_size": self._queue.qsize(),
            "available_slots": self._semaphore._value
        }

class BulkheadManager:
    """Gerenciador de bulkheads"""
    
    def __init__(self):
        self.bulkheads: Dict[str, Bulkhead] = {}
    
    def create_bulkhead(
        self,
        name: str,
        max_concurrent_calls: int = 10,
        max_queue_size: int = 100,
        timeout: float = 30.0
    ) -> Bulkhead:
        """Criar novo bulkhead"""
        bulkhead = Bulkhead(name, max_concurrent_calls, max_queue_size, timeout)
        self.bulkheads[name] = bulkhead
        return bulkhead
    
    def get_bulkhead(self, name: str) -> Optional[Bulkhead]:
        """Obter bulkhead por nome"""
        return self.bulkheads.get(name)
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Obter estatísticas de todos os bulkheads"""
        return {name: bulkhead.get_stats() for name, bulkhead in self.bulkheads.items()}

# Usage examples
bulkhead_manager = BulkheadManager()

# Create bulkheads for different resources
llm_bulkhead = bulkhead_manager.create_bulkhead(
    "llm_service",
    max_concurrent_calls=5,
    max_queue_size=50
)

database_bulkhead = bulkhead_manager.create_bulkhead(
    "database",
    max_concurrent_calls=20,
    max_queue_size=200
)

# Usage in service
async def call_llm_with_bulkhead(llm_request):
    """Chamar LLM com proteção de bulkhead"""
    return await llm_bulkhead.execute(
        llm_service.generate_response,
        llm_request
    )
```

### 3. Timeout Pattern

```python
# backend/app/infrastructure/resilience/timeout.py
import asyncio
import signal
from typing import Callable, Any, Optional
from functools import wraps

class TimeoutConfig:
    """Configuração para timeout"""
    
    def __init__(
        self,
        default_timeout: float = 30.0,
        enable_cancellation: bool = True,
        timeout_multiplier: float = 1.5
    ):
        self.default_timeout = default_timeout
        self.enable_cancellation = enable_cancellation
        self.timeout_multiplier = timeout_multiplier

class TimeoutManager:
    """Gerenciador de timeouts para operações"""
    
    def __init__(self, config: TimeoutConfig = None):
        self.config = config or TimeoutConfig()
        self._active_timeouts: Dict[str, asyncio.Task] = {}
    
    async def with_timeout(
        self,
        func: Callable,
        timeout: Optional[float] = None,
        *args,
        **kwargs
    ) -> Any:
        """Executar função com timeout"""
        
        if timeout is None:
            timeout = self.config.default_timeout
        
        # Create timeout task
        if asyncio.iscoroutinefunction(func):
            # For async functions
            return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
        else:
            # For sync functions
            loop = asyncio.get_event_loop()
            return await asyncio.wait_for(
                loop.run_in_executor(None, func, *args, **kwargs),
                timeout=timeout
            )
    
    def create_timeout_context(self, timeout: float):
        """Criar contexto de timeout para múltiplas operações"""
        return TimeoutContext(self, timeout)

class TimeoutContext:
    """Contexto de timeout para múltiplas operações"""
    
    def __init__(self, manager: TimeoutManager, timeout: float):
        self.manager = manager
        self.timeout = timeout
        self._operations: List[asyncio.Task] = []
    
    async def add_operation(self, func: Callable, *args, **kwargs) -> Any:
        """Adicionar operação ao contexto"""
        task = asyncio.create_task(func(*args, **kwargs))
        self._operations.append(task)
        
        try:
            return await asyncio.wait_for(task, timeout=self.timeout)
        except asyncio.TimeoutError:
            # Cancel all operations in this context
            await self.cancel_all()
            raise
    
    async def cancel_all(self):
        """Cancelar todas as operações no contexto"""
        for task in self._operations:
            if not task.done():
                task.cancel()
        
        # Wait for all tasks to complete
        await asyncio.gather(*self._operations, return_exceptions=True)

def with_timeout(timeout: float = 30.0):
    """Decorator para timeout simples"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, we need to run in executor
            loop = asyncio.get_event_loop()
            return loop.run_in_executor(None, func, *args, **kwargs)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

# Usage examples
timeout_manager = TimeoutManager()

@with_timeout(timeout=10.0)
async def fetch_data_with_timeout():
    """Buscar dados com timeout de 10 segundos"""
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com/data")
        return response.json()

# Complex timeout scenario
async def complex_operation_with_timeout():
    """Operação complexa com timeout gerenciado"""
    async with timeout_manager.create_timeout_context(timeout=30.0) as context:
        # Multiple operations sharing the same timeout
        data1 = await context.add_operation(fetch_data_from_source1)
        data2 = await context.add_operation(fetch_data_from_source2)
        
        # Process data
        result = await context.add_operation(process_data, data1, data2)
        
        return result
```

## Padrões de Segurança

### 1. Authentication & Authorization

```python
# backend/app/infrastructure/security/auth.py
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthManager:
    """Gerenciador de autenticação e autorização"""
    
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
    
    def hash_password(self, password: str) -> str:
        """Hash de senha"""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verificar senha"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def create_access_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Criar token de acesso"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        
        return encoded_jwt
    
    def create_refresh_token(self, user_id: str) -> str:
        """Criar token de refresh"""
        expire = datetime.utcnow() + timedelta(days=7)
        
        to_encode = {
            "sub": user_id,
            "exp": expire,
            "type": "refresh"
        }
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def decode_token(self, token: str) -> Dict[str, Any]:
        """Decodificar token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    def get_current_user_id(
        self,
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> str:
        """Obter ID do usuário atual a partir do token"""
        token = credentials.credentials
        payload = self.decode_token(token)
        
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        return user_id

# Role-based authorization
def require_role(allowed_roles: List[str]):
    """Decorator para requerer papel específico"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current user (assuming it's injected)
            current_user = kwargs.get("current_user")
            if not current_user:
                raise HTTPException(status_code=401, detail="User not authenticated")
            
            user_roles = current_user.get("roles", [])
            if not any(role in user_roles for role in allowed_roles):
                raise HTTPException(
                    status_code=403,
                    detail=f"User lacks required roles: {allowed_roles}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Permission-based authorization
def require_permission(permission: str):
    """Decorator para requerer permissão específica"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get("current_user")
            if not current_user:
                raise HTTPException(status_code=401, detail="User not authenticated")
            
            user_permissions = current_user.get("permissions", [])
            if permission not in user_permissions:
                raise HTTPException(
                    status_code=403,
                    detail=f"User lacks required permission: {permission}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

### 2. Rate Limiting

```python
# backend/app/infrastructure/security/rate_limit.py
import time
import asyncio
from typing import Dict, Optional
from collections import defaultdict, deque
from dataclasses import dataclass

@dataclass
class RateLimitConfig:
    """Configuração de rate limiting"""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_size: int = 10
    key_prefix: str = "rate_limit"

class RateLimiter:
    """Rate limiter usando sliding window"""
    
    def __init__(self, redis_client, config: RateLimitConfig):
        self.redis = redis_client
        self.config = config
    
    async def is_allowed(self, key: str) -> bool:
        """Verificar se requisição é permitida"""
        current_time = int(time.time())
        
        # Check minute limit
        minute_key = f"{self.config.key_prefix}:{key}:minute:{current_time // 60}"
        minute_count = await self.redis.incr(minute_key)
        await self.redis.expire(minute_key, 60)
        
        if minute_count > self.config.requests_per_minute:
            return False
        
        # Check hour limit
        hour_key = f"{self.config.key_prefix}:{key}:hour:{current_time // 3600}"
        hour_count = await self.redis.incr(hour_key)
        await self.redis.expire(hour_key, 3600)
        
        if hour_count > self.config.requests_per_hour:
            return False
        
        return True
    
    async def get_remaining_requests(self, key: str) -> Dict[str, int]:
        """Obter número de requisições restantes"""
        current_time = int(time.time())
        
        minute_key = f"{self.config.key_prefix}:{key}:minute:{current_time // 60}"
        hour_key = f"{self.config.key_prefix}:{key}:hour:{current_time // 3600}"
        
        minute_count = int(await self.redis.get(minute_key) or 0)
        hour_count = int(await self.redis.get(hour_key) or 0)
        
        return {
            "minute_remaining": max(0, self.config.requests_per_minute - minute_count),
            "hour_remaining": max(0, self.config.requests_per_hour - hour_count)
        }

class TokenBucketRateLimiter:
    """Rate limiter usando token bucket algorithm"""
    
    def __init__(self, redis_client, capacity: int, refill_rate: float):
        self.redis = redis_client
        self.capacity = capacity
        self.refill_rate = refill_rate
    
    async def is_allowed(self, key: str, tokens: int = 1) -> bool:
        """Verificar se tokens estão disponíveis"""
        bucket_key = f"token_bucket:{key}"
        
        script = """
        local key = KEYS[1]
        local capacity = tonumber(ARGV[1])
        local refill_rate = tonumber(ARGV[2])
        local tokens_requested = tonumber(ARGV[3])
        local now = tonumber(ARGV[4])
        
        local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
        local tokens = tonumber(bucket[1]) or capacity
        local last_refill = tonumber(bucket[2]) or now
        
        -- Calculate tokens to add based on time elapsed
        local elapsed = now - last_refill
        local tokens_to_add = elapsed * refill_rate
        tokens = math.min(capacity, tokens + tokens_to_add)
        
        -- Check if enough tokens are available
        if tokens >= tokens_requested then
            tokens = tokens - tokens_requested
            redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
            redis.call('EXPIRE', key, 3600)
            return 1
        else
            redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
            redis.call('EXPIRE', key, 3600)
            return 0
        end
        """
        
        current_time = time.time()
        result = await self.redis.eval(
            script,
            1,
            bucket_key,
            self.capacity,
            self.refill_rate,
            tokens,
            current_time
        )
        
        return result == 1

# Usage in FastAPI
from fastapi import Request, HTTPException

async def rate_limit_middleware(request: Request, call_next):
    """Middleware de rate limiting"""
    
    # Get client identifier (IP or user ID)
    client_ip = request.client.host
    user_id = getattr(request.state, 'user_id', None)
    rate_limit_key = f"user:{user_id}" if user_id else f"ip:{client_ip}"
    
    # Check rate limit
    if not await rate_limiter.is_allowed(rate_limit_key):
        remaining = await rate_limiter.get_remaining_requests(rate_limit_key)
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Remaining-Minute": str(remaining["minute_remaining"]),
                "X-RateLimit-Remaining-Hour": str(remaining["hour_remaining"])
            }
        )
    
    response = await call_next(request)
    
    # Add rate limit headers
    remaining = await rate_limiter.get_remaining_requests(rate_limit_key)
    response.headers["X-RateLimit-Remaining-Minute"] = str(remaining["minute_remaining"])
    response.headers["X-RateLimit-Remaining-Hour"] = str(remaining["hour_remaining"])
    
    return response
```

## Padrões de Performance

### 1. Connection Pooling

```python
# backend/app/infrastructure/database/pool.py
from typing import Optional
import asyncpg
from contextlib import asynccontextmanager

class DatabasePool:
    """Pool de conexões de banco de dados"""
    
    def __init__(
        self,
        database_url: str,
        min_connections: int = 10,
        max_connections: int = 100,
        command_timeout: float = 60.0
    ):
        self.database_url = database_url
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.command_timeout = command_timeout
        self._pool: Optional[asyncpg.Pool] = None
    
    async def initialize(self):
        """Inicializar pool de conexões"""
        self._pool = await asyncpg.create_pool(
            self.database_url,
            min_size=self.min_connections,
            max_size=self.max_connections,
            command_timeout=self.command_timeout,
            server_settings={
                "application_name": "janus_app",
                "jit": "off"  # Disable JIT for better performance
            }
        )
    
    async def close(self):
        """Fechar pool de conexões"""
        if self._pool:
            await self._pool.close()
    
    @asynccontextmanager
    async def acquire(self):
        """Adquirir conexão do pool"""
        if not self._pool:
            raise RuntimeError("Database pool not initialized")
        
        async with self._pool.acquire() as connection:
            yield connection
    
    async def execute(self, query: str, *args):
        """Executar query"""
        async with self.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetch(self, query: str, *args):
        """Buscar dados"""
        async with self.acquire() as conn:
            return await conn.fetch(query, *args)
    
    async def fetchrow(self, query: str, *args):
        """Buscar uma linha"""
        async with self.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetchval(self, query: str, *args):
        """Buscar um valor"""
        async with self.acquire() as conn:
            return await conn.fetchval(query, *args)

# Redis connection pool
import aioredis

class RedisPool:
    """Pool de conexões Redis"""
    
    def __init__(
        self,
        redis_url: str,
        max_connections: int = 100,
        socket_keepalive: bool = True,
        socket_keepalive_options: Optional[Dict] = None
    ):
        self.redis_url = redis_url
        self.max_connections = max_connections
        self.socket_keepalive = socket_keepalive
        self.socket_keepalive_options = socket_keepalive_options or {}
        self._pool: Optional[aioredis.ConnectionPool] = None
        self._redis: Optional[aioredis.Redis] = None
    
    async def initialize(self):
        """Inicializar pool Redis"""
        self._pool = aioredis.ConnectionPool.from_url(
            self.redis_url,
            max_connections=self.max_connections,
            socket_keepalive=self.socket_keepalive,
            socket_keepalive_options=self.socket_keepalive_options
        )
        self._redis = aioredis.Redis(connection_pool=self._pool)
    
    async def close(self):
        """Fechar pool Redis"""
        if self._pool:
            await self._pool.disconnect()
    
    @property
    def redis(self) -> aioredis.Redis:
        """Obter cliente Redis"""
        if not self._redis:
            raise RuntimeError("Redis pool not initialized")
        return self._redis

# HTTP connection pool
import httpx

class HTTPPool:
    """Pool de conexões HTTP"""
    
    def __init__(
        self,
        max_keepalive_connections: int = 20,
        max_connections: int = 100,
        keepalive_expiry: float = 30.0,
        timeout: float = 30.0
    ):
        self.max_keepalive_connections = max_keepalive_connections
        self.max_connections = max_connections
        self.keepalive_expiry = keepalive_expiry
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def initialize(self):
        """Inicializar cliente HTTP"""
        limits = httpx.Limits(
            max_keepalive_connections=self.max_keepalive_connections,
            max_connections=self.max_connections,
            keepalive_expiry=self.keepalive_expiry
        )
        
        timeout = httpx.Timeout(
            connect=5.0,
            read=self.timeout,
            write=self.timeout,
            pool=self.timeout
        )
        
        self._client = httpx.AsyncClient(
            limits=limits,
            timeout=timeout,
            http2=True  # Enable HTTP/2 for better performance
        )
    
    async def close(self):
        """Fechar cliente HTTP"""
        if self._client:
            await self._client.aclose()
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Obter cliente HTTP"""
        if not self._client:
            raise RuntimeError("HTTP client not initialized")
        return self._client
```

### 2. Caching Strategies

```python
# backend/app/infrastructure/cache/strategies.py
import json
import pickle
import hashlib
from typing import Any, Optional, Callable
from datetime import datetime, timedelta

class CacheStrategy(ABC):
    """Estratégia base para cache"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Obter valor do cache"""
        pass
    
    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """Definir valor no cache"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Deletar valor do cache"""
        pass
    
    @abstractmethod
    async def clear_pattern(self, pattern: str) -> int:
        """Limpar chaves por padrão"""
        pass

class RedisCacheStrategy(CacheStrategy):
    """Estratégia de cache usando Redis"""
    
    def __init__(self, redis_client, default_ttl: int = 3600):
        self.redis = redis_client
        self.default_ttl = default_ttl
    
    async def get(self, key: str) -> Optional[Any]:
        """Obter valor do Redis"""
        value = await self.redis.get(key)
        if value is None:
            return None
        
        try:
            # Try JSON first
            return json.loads(value)
        except json.JSONDecodeError:
            # Fall back to pickle for complex objects
            return pickle.loads(value)
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """Definir valor no Redis"""
        if ttl is None:
            ttl = self.default_ttl
        
        # Serialize value
        try:
            serialized = json.dumps(value)
        except (TypeError, ValueError):
            # Use pickle for complex objects
            serialized = pickle.dumps(value)
        
        await self.redis.setex(key, ttl, serialized)
    
    async def delete(self, key: str) -> bool:
        """Deletar valor do Redis"""
        result = await self.redis.delete(key)
        return result > 0
    
    async def clear_pattern(self, pattern: str) -> int:
        """Limpar chaves por padrão"""
        keys = await self.redis.keys(pattern)
        if keys:
            return await self.redis.delete(*keys)
        return 0

class MemoryCacheStrategy(CacheStrategy):
    """Estratégia de cache em memória (para desenvolvimento)"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, tuple[Any, float]] = {}
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Obter valor do cache em memória"""
        async with self._lock:
            if key not in self.cache:
                return None
            
            value, expiry = self.cache[key]
            if time.time() > expiry:
                del self.cache[key]
                return None
            
            return value
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """Definir valor no cache em memória"""
        if ttl is None:
            ttl = self.default_ttl
        
        async with self._lock:
            # Implement LRU eviction if cache is full
            if len(self.cache) >= self.max_size and key not in self.cache:
                # Remove oldest item
                oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
                del self.cache[oldest_key]
            
            expiry = time.time() + ttl
            self.cache[key] = (value, expiry)
    
    async def delete(self, key: str) -> bool:
        """Deletar valor do cache em memória"""
        async with self._lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """Limpar chaves por padrão (simplificado para memória)"""
        async with self._lock:
            keys_to_delete = [key for key in self.cache.keys() if pattern in key]
            for key in keys_to_delete:
                del self.cache[key]
            return len(keys_to_delete)

# Cache-aside pattern implementation
class CacheAside:
    """Implementação do padrão Cache-Aside"""
    
    def __init__(self, cache_strategy: CacheStrategy):
        self.cache = cache_strategy
    
    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Any],
        ttl: Optional[int] = None
    ) -> Any:
        """Obter do cache ou executar factory se não existir"""
        
        # Try to get from cache
        value = await self.cache.get(key)
        if value is not None:
            return value
        
        # Generate value using factory
        if asyncio.iscoroutinefunction(factory):
            value = await factory()
        else:
            value = factory()
        
        # Store in cache
        await self.cache.set(key, value, ttl)
        
        return value
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidar cache por padrão"""
        return await self.cache.clear_pattern(pattern)

# Cache key generation utilities
def generate_cache_key(*args, **kwargs) -> str:
    """Gerar chave de cache única"""
    key_parts = []
    
    # Add positional arguments
    for arg in args:
        key_parts.append(str(arg))
    
    # Add keyword arguments (sorted for consistency)
    for key, value in sorted(kwargs.items()):
        key_parts.append(f"{key}:{value}")
    
    # Generate hash
    key_string = ":".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()

def cache_result(
    cache: CacheStrategy,
    ttl: Optional[int] = None,
    key_prefix: str = ""
):
    """Decorator para cache de resultados"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            cache_key = f"{key_prefix}:{generate_cache_key(*args, **kwargs)}"
            
            # Try to get from cache
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            await cache.set(cache_key, result, ttl)
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            cache_key = f"{key_prefix}:{generate_cache_key(*args, **kwargs)}"
            
            # For sync functions, we need to handle cache operations synchronously
            # This is a simplified version - in production, use async functions
            return func(*args, **kwargs)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator
```

## Conclusão

Esta documentação cobre os principais padrões de arquitetura e design implementados no Janus. Os padrões foram escolhidos para garantir:

- **Escalabilidade**: Arquitetura de microserviços permite escalar componentes independentemente
- **Resiliência**: Padrões como Circuit Breaker, Retry e Bulkhead protegem contra falhas
- **Manutenibilidade**: Clean Architecture e DDD facilitam manutenção e evolução
- **Performance**: Caching, connection pooling e estratégias de otimização
- **Segurança**: Autenticação, autorização e rate limiting implementados

Para mais informações sobre implementações específicas, consulte os arquivos de código no repositório.