# Guia de Contribuição Avançada - Janus

## Visão Geral

Este guia destina-se a desenvolvedores experientes que desejam contribuir com features avançadas, otimizações de performance e melhorias arquiteturais no projeto Janus.

## Fluxo de Desenvolvimento Avançado

### 1. Arquitetura de Branch Avançada

```
main (produção)
├── staging (pré-produção)
├── develop (integração)
├── feature/epic-{nome} (epics grandes)
│   ├── feature/{epic}-{subfeature}
│   └── feature/{epic}-{subfeature}
├── refactor/{componente}
├── perf/{otimização}
└── hotfix/{correção-crítica}
```

### 2. Processo de Desenvolvimento de Features Complexas

```mermaid
graph TD
    A[Identificar Necessidade] --> B[Criar RFC/ADR]
    B --> C[Revisão Arquitetural]
    C --> D[Implementação]
    D --> E[Testes de Performance]
    E --> F[Security Review]
    F --> G[Code Review]
    G --> H[Merge]
```

## Padrões de Design Avançados

### 1. Domain-Driven Design (DDD)

#### Entidades de Domínio

```python
# backend/app/domain/entities/chat.py
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
from enum import Enum

class MessageRole(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

@dataclass
class Message:
    id: str
    role: MessageRole
    content: str
    timestamp: datetime
    metadata: Optional[dict] = None
    
    def validate(self) -> bool:
        """Validar consistência da mensagem"""
        if not self.content.strip():
            raise ValueError("Message content cannot be empty")
        if len(self.content) > 10000:
            raise ValueError("Message content too long")
        return True
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }

@dataclass
class ChatSession:
    id: str
    user_id: str
    messages: List[Message]
    created_at: datetime
    updated_at: datetime
    metadata: Optional[dict] = None
    
    def add_message(self, message: Message) -> None:
        """Adicionar mensagem com validação de domínio"""
        message.validate()
        self.messages.append(message)
        self.updated_at = datetime.utcnow()
    
    def get_context_window(self, max_tokens: int = 4096) -> List[Message]:
        """Obter janela de contexto respeitando limites de tokens"""
        total_tokens = 0
        context_messages = []
        
        # Começar do final (mensagens mais recentes)
        for message in reversed(self.messages):
            message_tokens = len(message.content.split()) * 1.3  # Estimativa
            if total_tokens + message_tokens <= max_tokens:
                context_messages.insert(0, message)
                total_tokens += message_tokens
            else:
                break
        
        return context_messages
```

#### Objetos de Valor

```python
# backend/app/domain/value_objects/llm_config.py
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum

class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"

@dataclass(frozen=True)
class LLMConfig:
    """Objeto de valor imutável para configuração de LLM"""
    provider: LLMProvider
    model: str
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 30
    
    def __post_init__(self):
        """Validações de domínio"""
        if not 0 <= self.temperature <= 2:
            raise ValueError("Temperature must be between 0 and 2")
        if self.max_tokens <= 0:
            raise ValueError("Max tokens must be positive")
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")
    
    def to_provider_params(self) -> Dict[str, Any]:
        """Converter para parâmetros específicos do provedor"""
        base_params = {
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout
        }
        
        if self.provider == LLMProvider.OPENAI:
            return {**base_params, "model": self.model}
        elif self.provider == LLMProvider.ANTHROPIC:
            return {**base_params, "model": self.model}
        elif self.provider == LLMProvider.GOOGLE:
            return {**base_params, "model": self.model}
        elif self.provider == LLMProvider.OLLAMA:
            return {**base_params, "model": self.model}
        else:
            return base_params

@dataclass(frozen=True)
class TokenUsage:
    """Objeto de valor para uso de tokens"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    
    def __post_init__(self):
        if self.total_tokens != self.prompt_tokens + self.completion_tokens:
            raise ValueError("Total tokens must equal prompt + completion")
    
    def calculate_cost(self, cost_per_1k_tokens: float) -> float:
        """Calcular custo estimado"""
        return (self.total_tokens / 1000) * cost_per_1k_tokens
```

### 2. Repository Pattern Avançado

```python
# backend/app/infrastructure/repositories/base.py
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
import logging

T = TypeVar('T')
logger = logging.getLogger(__name__)

class BaseRepository(Generic[T], ABC):
    """Repository base genérico com operações CRUD avançadas"""
    
    def __init__(self, session: Session):
        self.session = session
    
    @abstractmethod
    def get_model_class(self) -> type:
        """Retornar a classe do modelo SQLAlchemy"""
        pass
    
    def create(self, entity: T) -> T:
        """Criar nova entidade com validação"""
        try:
            self.session.add(entity)
            self.session.flush()
            logger.info(f"Created {self.__class__.__name__}: {getattr(entity, 'id', 'unknown')}")
            return entity
        except Exception as e:
            logger.error(f"Error creating entity: {str(e)}")
            self.session.rollback()
            raise
    
    def get_by_id(self, entity_id: str) -> Optional[T]:
        """Buscar entidade por ID com cache opcional"""
        return self.session.query(self.get_model_class()).filter_by(id=entity_id).first()
    
    def get_all(self, limit: Optional[int] = None, offset: int = 0) -> List[T]:
        """Buscar todas as entidades com paginação"""
        query = self.session.query(self.get_model_class())
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)
        return query.all()
    
    def update(self, entity_id: str, updates: Dict[str, Any]) -> Optional[T]:
        """Atualizar entidade parcialmente"""
        entity = self.get_by_id(entity_id)
        if entity:
            for key, value in updates.items():
                if hasattr(entity, key):
                    setattr(entity, key, value)
            logger.info(f"Updated {self.__class__.__name__}: {entity_id}")
        return entity
    
    def delete(self, entity_id: str) -> bool:
        """Deletar entidade (soft delete opcional)"""
        entity = self.get_by_id(entity_id)
        if entity:
            self.session.delete(entity)
            logger.info(f"Deleted {self.__class__.__name__}: {entity_id}")
            return True
        return False
    
    def find_by_criteria(self, criteria: Dict[str, Any], 
                        order_by: Optional[str] = None,
                        limit: Optional[int] = None) -> List[T]:
        """Buscar por múltiplos critérios"""
        query = self.session.query(self.get_model_class())
        
        conditions = []
        for key, value in criteria.items():
            if hasattr(self.get_model_class(), key):
                if isinstance(value, list):
                    conditions.append(getattr(self.get_model_class(), key).in_(value))
                else:
                    conditions.append(getattr(self.get_model_class(), key) == value)
        
        if conditions:
            query = query.filter(and_(*conditions))
        
        if order_by:
            if order_by.startswith('-'):
                query = query.order_by(desc(order_by[1:]))
            else:
                query = query.order_by(asc(order_by))
        
        if limit:
            query = query.limit(limit)
        
        return query.all()

# Implementação específica
class ChatSessionRepository(BaseRepository[ChatSession]):
    """Repository especializado para sessões de chat"""
    
    def get_model_class(self) -> type:
        from app.infrastructure.models import ChatSessionModel
        return ChatSessionModel
    
    def get_by_user_id(self, user_id: str, limit: int = 50) -> List[ChatSession]:
        """Buscar sessões por usuário com limite"""
        return self.find_by_criteria(
            {"user_id": user_id},
            order_by="-updated_at",
            limit=limit
        )
    
    def get_active_sessions(self, user_id: str, 
                          max_age_hours: int = 24) -> List[ChatSession]:
        """Buscar sessões ativas (últimas 24h por padrão)"""
        from datetime import datetime, timedelta
        
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        return self.session.query(self.get_model_class()).filter(
            and_(
                self.get_model_class().user_id == user_id,
                self.get_model_class().updated_at >= cutoff_time
            )
        ).order_by(desc("updated_at")).all()
    
    def cleanup_old_sessions(self, max_age_days: int = 30) -> int:
        """Limpar sessões antigas"""
        from datetime import datetime, timedelta
        
        cutoff_time = datetime.utcnow() - timedelta(days=max_age_days)
        
        deleted_count = self.session.query(self.get_model_class()).filter(
            self.get_model_class().updated_at < cutoff_time
        ).delete()
        
        logger.info(f"Deleted {deleted_count} old chat sessions")
        return deleted_count
```

### 3. Service Layer Pattern

```python
# backend/app/application/services/chat_service.py
from typing import List, Optional, Dict, Any
from uuid import uuid4
from datetime import datetime
import asyncio
import logging

from app.domain.entities.chat import ChatSession, Message, MessageRole
from app.domain.value_objects.llm_config import LLMConfig, LLMProvider
from app.infrastructure.repositories.chat_repository import ChatSessionRepository
from app.infrastructure.repositories.llm_repository import LLMRepository
from app.infrastructure.cache.redis_cache import RedisCache
from app.core.exceptions import ChatNotFoundError, RateLimitExceededError

logger = logging.getLogger(__name__)

class ChatService:
    """Serviço de aplicação para gerenciamento de chats"""
    
    def __init__(
        self,
        chat_repository: ChatSessionRepository,
        llm_repository: LLMRepository,
        cache: RedisCache,
        llm_service_factory
    ):
        self.chat_repository = chat_repository
        self.llm_repository = llm_repository
        self.cache = cache
        self.llm_service_factory = llm_service_factory
    
    async def create_session(self, user_id: str, metadata: Optional[Dict] = None) -> ChatSession:
        """Criar nova sessão de chat"""
        session = ChatSession(
            id=str(uuid4()),
            user_id=user_id,
            messages=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            metadata=metadata or {}
        )
        
        # Adicionar mensagem de sistema inicial
        system_message = Message(
            id=str(uuid4()),
            role=MessageRole.SYSTEM,
            content="You are a helpful AI assistant.",
            timestamp=datetime.utcnow()
        )
        session.add_message(system_message)
        
        # Salvar no repositório
        self.chat_repository.create(session)
        
        # Cache para performance
        await self.cache.set(f"chat_session:{session.id}", session.to_dict(), ttl=3600)
        
        logger.info(f"Created chat session {session.id} for user {user_id}")
        return session
    
    async def add_message(self, session_id: str, role: MessageRole, content: str, 
                         metadata: Optional[Dict] = None) -> Message:
        """Adicionar mensagem à sessão"""
        # Buscar sessão
        session = await self.get_session(session_id)
        if not session:
            raise ChatNotFoundError(f"Chat session {session_id} not found")
        
        # Verificar rate limit
        await self._check_rate_limit(session.user_id)
        
        # Criar mensagem
        message = Message(
            id=str(uuid4()),
            role=role,
            content=content,
            timestamp=datetime.utcnow(),
            metadata=metadata
        )
        
        # Adicionar à sessão
        session.add_message(message)
        
        # Atualizar repositório
        self.chat_repository.update(session_id, {"messages": session.messages})
        
        # Atualizar cache
        await self.cache.set(f"chat_session:{session_id}", session.to_dict(), ttl=3600)
        
        logger.info(f"Added message {message.id} to session {session_id}")
        return message
    
    async def generate_response(self, session_id: str, provider: LLMProvider = LLMProvider.OPENAI,
                              model: Optional[str] = None) -> Message:
        """Gerar resposta usando LLM"""
        # Buscar sessão
        session = await self.get_session(session_id)
        if not session:
            raise ChatNotFoundError(f"Chat session {session_id} not found")
        
        # Obter configuração do LLM
        llm_config = await self._get_llm_config(provider, model)
        
        # Obter serviço LLM
        llm_service = self.llm_service_factory.create(llm_config)
        
        # Preparar contexto
        context_messages = session.get_context_window()
        
        # Gerar resposta
        response_content = await llm_service.chat(
            messages=[msg.to_dict() for msg in context_messages],
            model=llm_config.model
        )
        
        # Criar mensagem de resposta
        response_message = Message(
            id=str(uuid4()),
            role=MessageRole.ASSISTANT,
            content=response_content,
            timestamp=datetime.utcnow(),
            metadata={
                "provider": provider.value,
                "model": llm_config.model,
                "tokens_used": llm_service.get_token_usage()
            }
        )
        
        # Adicionar à sessão
        session.add_message(response_message)
        
        # Atualizar repositório
        self.chat_repository.update(session_id, {"messages": session.messages})
        
        # Atualizar cache
        await self.cache.set(f"chat_session:{session_id}", session.to_dict(), ttl=3600)
        
        logger.info(f"Generated response for session {session_id} using {provider.value}")
        return response_message
    
    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Buscar sessão com cache"""
        # Tentar cache primeiro
        cached_session = await self.cache.get(f"chat_session:{session_id}")
        if cached_session:
            return ChatSession.from_dict(cached_session)
        
        # Buscar no banco
        session = self.chat_repository.get_by_id(session_id)
        if session:
            # Cachear para próximas requisições
            await self.cache.set(f"chat_session:{session_id}", session.to_dict(), ttl=3600)
        
        return session
    
    async def get_user_sessions(self, user_id: str, limit: int = 10) -> List[ChatSession]:
        """Buscar sessões do usuário"""
        cache_key = f"user_sessions:{user_id}"
        
        # Tentar cache
        cached_sessions = await self.cache.get(cache_key)
        if cached_sessions:
            return [ChatSession.from_dict(s) for s in cached_sessions[:limit]]
        
        # Buscar no banco
        sessions = self.chat_repository.get_by_user_id(user_id, limit)
        
        # Cachear
        if sessions:
            sessions_dict = [s.to_dict() for s in sessions]
            await self.cache.set(cache_key, sessions_dict, ttl=1800)
        
        return sessions
    
    async def _check_rate_limit(self, user_id: str) -> None:
        """Verificar rate limit por usuário"""
        rate_limit_key = f"rate_limit:{user_id}"
        current_count = await self.cache.get(rate_limit_key) or 0
        
        # Limite: 100 mensagens por hora
        if current_count >= 100:
            raise RateLimitExceededError("Rate limit exceeded")
        
        # Incrementar contador
        await self.cache.incr(rate_limit_key)
        await self.cache.expire(rate_limit_key, 3600)
    
    async def _get_llm_config(self, provider: LLMProvider, model: Optional[str] = None) -> LLMConfig:
        """Obter configuração do LLM com fallback"""
        # Buscar configuração do repositório
        config = self.llm_repository.get_config(provider)
        
        # Usar modelo especificado ou padrão
        model_name = model or config.model
        
        return LLMConfig(
            provider=provider,
            model=model_name,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            timeout=config.timeout
        )
```

## Otimizações de Performance

### 1. Connection Pooling Avançado

```python
# backend/app/infrastructure/database/connection_pool.py
from sqlalchemy import create_engine, event
from sqlalchemy.pool import QueuePool, NullPool
from sqlalchemy.orm import sessionmaker, scoped_session
import logging

logger = logging.getLogger(__name__)

class AdvancedConnectionPool:
    """Pool de conexões com configurações otimizadas"""
    
    def __init__(self, database_url: str, pool_config: dict = None):
        self.database_url = database_url
        self.pool_config = pool_config or {}
        self.engine = None
        self.SessionLocal = None
        self._setup_pool()
    
    def _setup_pool(self):
        """Configurar pool de conexões com parâmetros otimizados"""
        # Configurações baseadas no ambiente
        is_production = "production" in self.database_url
        
        if is_production:
            # Produção: Pool robusto com limites
            pool_class = QueuePool
            pool_size = self.pool_config.get("pool_size", 20)
            max_overflow = self.pool_config.get("max_overflow", 30)
            pool_timeout = self.pool_config.get("pool_timeout", 30)
            pool_recycle = self.pool_config.get("pool_recycle", 3600)
        else:
            # Desenvolvimento: Pool mais simples
            pool_class = QueuePool
            pool_size = self.pool_config.get("pool_size", 5)
            max_overflow = self.pool_config.get("max_overflow", 10)
            pool_timeout = self.pool_config.get("pool_timeout", 10)
            pool_recycle = self.pool_config.get("pool_recycle", 1800)
        
        # Criar engine com pool
        self.engine = create_engine(
            self.database_url,
            poolclass=pool_class,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            pool_pre_ping=True,  # Verificar conexões antes de usar
            echo=False,  # Desabilitar SQL logging em produção
        )
        
        # Configurar eventos de monitoramento
        self._setup_event_listeners()
        
        # Criar session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        logger.info(f"Connection pool configured: size={pool_size}, max_overflow={max_overflow}")
    
    def _setup_event_listeners(self):
        """Configurar listeners para monitoramento"""
        
        @event.listens_for(self.engine, "connect")
        def connect(dbapi_connection, connection_record):
            logger.debug(f"New connection created: {connection_record}")
        
        @event.listens_for(self.engine, "checkout")
        def checkout(dbapi_connection, connection_record, connection_proxy):
            logger.debug(f"Connection checked out: {connection_record}")
        
        @event.listens_for(self.engine, "checkin")
        def checkin(dbapi_connection, connection_record):
            logger.debug(f"Connection checked in: {connection_record}")
    
    def get_session(self):
        """Obter sessão do pool"""
        return self.SessionLocal()
    
    def get_session_context_manager(self):
        """Obter context manager para sessão"""
        return self.SessionLocal()
    
    def get_connection_stats(self) -> dict:
        """Obter estatísticas do pool"""
        if hasattr(self.engine.pool, 'size'):
            return {
                "pool_size": self.engine.pool.size(),
                "checked_in": self.engine.pool.checkedin(),
                "checked_out": self.engine.pool.checkedout(),
                "overflow": self.engine.pool.overflow()
            }
        return {}

# Uso global
connection_pool = AdvancedConnectionPool(
    database_url="postgresql://user:pass@localhost/janus",
    pool_config={
        "pool_size": 30,
        "max_overflow": 50,
        "pool_timeout": 30,
        "pool_recycle": 3600
    }
)

def get_db():
    """Dependency para FastAPI"""
    db = connection_pool.get_session()
    try:
        yield db
    finally:
        db.close()
```

### 2. Caching Estratégico

```python
# backend/app/infrastructure/cache/strategic_cache.py
import json
import hashlib
from typing import Any, Optional, Callable, List
from datetime import datetime, timedelta
import asyncio
import aioredis
import logging

logger = logging.getLogger(__name__)

class StrategicCache:
    """Cache estratégico com múltiplas políticas"""
    
    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client
        self.cache_policies = {
            "user_data": {"ttl": 3600, "strategy": "lazy"},  # 1 hora
            "chat_history": {"ttl": 1800, "strategy": "write_through"},  # 30 min
            "llm_responses": {"ttl": 86400, "strategy": "cache_aside"},  # 24 horas
            "system_config": {"ttl": 300, "strategy": "refresh_ahead"},  # 5 min
        }
    
    async def get_or_compute(
        self,
        key: str,
        compute_func: Callable,
        cache_type: str = "default",
        force_refresh: bool = False
    ) -> Any:
        """Obter do cache ou computar com estratégia específica"""
        
        policy = self.cache_policies.get(cache_type, {"ttl": 3600, "strategy": "lazy"})
        ttl = policy["ttl"]
        strategy = policy["strategy"]
        
        if strategy == "lazy":
            return await self._lazy_loading(key, compute_func, ttl, force_refresh)
        elif strategy == "write_through":
            return await self._write_through(key, compute_func, ttl)
        elif strategy == "cache_aside":
            return await self._cache_aside(key, compute_func, ttl, force_refresh)
        elif strategy == "refresh_ahead":
            return await self._refresh_ahead(key, compute_func, ttl)
        else:
            return await self._lazy_loading(key, compute_func, ttl, force_refresh)
    
    async def _lazy_loading(self, key: str, compute_func: Callable, 
                           ttl: int, force_refresh: bool) -> Any:
        """Lazy loading: só computa se não estiver em cache"""
        
        if not force_refresh:
            cached = await self.get(key)
            if cached is not None:
                logger.debug(f"Cache hit for key: {key}")
                return cached
        
        # Computar valor
        logger.debug(f"Computing value for key: {key}")
        value = await compute_func()
        
        # Armazenar em cache
        await self.set(key, value, ttl)
        
        return value
    
    async def _write_through(self, key: str, compute_func: Callable, ttl: int) -> Any:
        """Write-through: sempre atualiza cache ao computar"""
        
        value = await compute_func()
        await self.set(key, value, ttl)
        
        return value
    
    async def _cache_aside(self, key: str, compute_func: Callable, 
                           ttl: int, force_refresh: bool) -> Any:
        """Cache-aside: aplicação gerencia cache explicitamente"""
        
        if not force_refresh:
            cached = await self.get(key)
            if cached is not None:
                return cached
        
        # Computar e armazenar
        value = await compute_func()
        await self.set(key, value, ttl)
        
        return value
    
    async def _refresh_ahead(self, key: str, compute_func: Callable, ttl: int) -> Any:
        """Refresh-ahead: renova cache antes de expirar"""
        
        cached = await self.get(key)
        
        if cached is None:
            # Primeira vez ou expirou
            value = await compute_func()
            await self.set(key, value, ttl)
            return value
        
        # Verificar se está próximo de expirar (20% do TTL)
        ttl_remaining = await self.redis.ttl(key)
        refresh_threshold = ttl * 0.2
        
        if ttl_remaining < refresh_threshold:
            # Renovar em background
            asyncio.create_task(self._refresh_in_background(key, compute_func, ttl))
        
        return cached
    
    async def _refresh_in_background(self, key: str, compute_func: Callable, ttl: int):
        """Renovar cache em background"""
        try:
            logger.debug(f"Background refresh for key: {key}")
            value = await compute_func()
            await self.set(key, value, ttl)
        except Exception as e:
            logger.error(f"Background refresh failed for key {key}: {str(e)}")
    
    async def get(self, key: str) -> Optional[Any]:
        """Obter valor do cache"""
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {str(e)}")
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """Armazenar valor no cache"""
        try:
            serialized = json.dumps(value, default=str)
            await self.redis.setex(key, ttl, serialized)
            logger.debug(f"Cached key: {key} with TTL: {ttl}")
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {str(e)}")
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidar múltiplas chaves por padrão"""
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                deleted = await self.redis.delete(*keys)
                logger.info(f"Invalidated {deleted} keys with pattern: {pattern}")
                return deleted
        except Exception as e:
            logger.error(f"Cache invalidation error for pattern {pattern}: {str(e)}")
        return 0
    
    async def get_cache_stats(self) -> dict:
        """Obter estatísticas do cache"""
        try:
            info = await self.redis.info()
            return {
                "used_memory": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(info)
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}")
            return {}
    
    def _calculate_hit_rate(self, info: dict) -> float:
        """Calcular taxa de acerto do cache"""
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        
        if total > 0:
            return (hits / total) * 100
        return 0.0

# Decorator para cache automático
def cached(cache_type: str = "default", ttl: int = 3600):
    """Decorator para cache automático de funções"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Gerar chave única baseada em args e kwargs
            key_parts = [func.__name__] + [str(arg) for arg in args]
            key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
            cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()
            
            # Usar cache estratégico
            cache = StrategicCache(redis_client)  # Global ou injetado
            
            async def compute():
                return await func(*args, **kwargs)
            
            return await cache.get_or_compute(cache_key, compute, cache_type)
        
        return wrapper
    return decorator

# Exemplo de uso
@cached(cache_type="user_data", ttl=1800)
async def get_user_profile(user_id: str) -> dict:
    """Buscar perfil do usuário com cache automático"""
    # Simular busca no banco de dados
    await asyncio.sleep(0.1)
    return {
        "id": user_id,
        "name": f"User {user_id}",
        "email": f"user{user_id}@example.com",
        "created_at": datetime.utcnow().isoformat()
    }
```

## Testes Avançados

### 1. Testes de Performance

```python
# backend/tests/performance/test_chat_performance.py
import asyncio
import time
import statistics
from typing import List, Dict
import pytest
import aiohttp
from concurrent.futures import ThreadPoolExecutor

class ChatPerformanceTest:
    """Testes de performance para endpoints de chat"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = []
    
    async def test_concurrent_chat_requests(self, num_requests: int = 100):
        """Testar múltiplas requisições de chat simultâneas"""
        
        async def single_chat_request(session_id: str, message: str):
            start_time = time.time()
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/v1/chat/{session_id}/messages"
                data = {
                    "role": "user",
                    "content": message
                }
                
                try:
                    async with session.post(url, json=data) as response:
                        response_time = time.time() - start_time
                        
                        if response.status == 200:
                            return {
                                "success": True,
                                "response_time": response_time,
                                "status_code": response.status
                            }
                        else:
                            return {
                                "success": False,
                                "response_time": response_time,
                                "status_code": response.status,
                                "error": await response.text()
                            }
                except Exception as e:
                    return {
                        "success": False,
                        "response_time": time.time() - start_time,
                        "error": str(e)
                    }
        
        # Criar sessão de teste
        session_id = await self._create_test_session()
        
        # Executar requisições concorrentes
        tasks = []
        for i in range(num_requests):
            message = f"Test message {i}"
            task = single_chat_request(session_id, message)
            tasks.append(task)
        
        # Executar todas as requisições
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analisar resultados
        successful_requests = [r for r in results if isinstance(r, dict) and r["success"]]
        failed_requests = [r for r in results if isinstance(r, dict) and not r["success"]]
        exceptions = [r for r in results if isinstance(r, Exception)]
        
        # Calcular métricas
        response_times = [r["response_time"] for r in successful_requests]
        
        metrics = {
            "total_requests": num_requests,
            "successful_requests": len(successful_requests),
            "failed_requests": len(failed_requests),
            "exceptions": len(exceptions),
            "success_rate": len(successful_requests) / num_requests * 100,
            "total_time": total_time,
            "requests_per_second": num_requests / total_time,
            "response_time_stats": {
                "min": min(response_times) if response_times else 0,
                "max": max(response_times) if response_times else 0,
                "mean": statistics.mean(response_times) if response_times else 0,
                "median": statistics.median(response_times) if response_times else 0,
                "p95": statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else 0,
                "p99": statistics.quantiles(response_times, n=100)[98] if len(response_times) > 100 else 0
            }
        }
        
        self.results.append({
            "test": "concurrent_chat_requests",
            "metrics": metrics,
            "timestamp": time.time()
        })
        
        return metrics
    
    async def test_llm_response_times(self, providers: List[str] = None):
        """Testar tempos de resposta de diferentes LLMs"""
        
        if providers is None:
            providers = ["openai", "anthropic", "google"]
        
        test_message = "What is the capital of France?"
        results = {}
        
        for provider in providers:
            provider_times = []
            
            for i in range(10):  # 10 testes por provedor
                start_time = time.time()
                
                try:
                    response = await self._call_llm(provider, test_message)
                    response_time = time.time() - start_time
                    provider_times.append(response_time)
                    
                    # Pequena pausa entre requisições
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error testing {provider}: {str(e)}")
                    continue
            
            if provider_times:
                results[provider] = {
                    "mean_time": statistics.mean(provider_times),
                    "median_time": statistics.median(provider_times),
                    "min_time": min(provider_times),
                    "max_time": max(provider_times),
                    "requests": len(provider_times)
                }
        
        return results
    
    async def test_memory_usage(self, num_sessions: int = 1000):
        """Testar uso de memória com múltiplas sessões"""
        
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Criar múltiplas sessões
        session_ids = []
        for i in range(num_sessions):
            session_id = await self._create_test_session(f"user_{i}")
            session_ids.append(session_id)
            
            # Adicionar mensagens à sessão
            for j in range(10):
                await self._add_message(session_id, f"Message {j}")
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        return {
            "initial_memory_mb": initial_memory,
            "final_memory_mb": final_memory,
            "memory_increase_mb": memory_increase,
            "memory_per_session_mb": memory_increase / num_sessions,
            "sessions_created": num_sessions
        }
    
    async def _create_test_session(self, user_id: str = "test_user") -> str:
        """Criar sessão de teste"""
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/api/v1/chat/sessions"
            data = {"user_id": user_id}
            
            async with session.post(url, json=data) as response:
                if response.status == 201:
                    result = await response.json()
                    return result["id"]
                else:
                    raise Exception(f"Failed to create session: {response.status}")
    
    async def _add_message(self, session_id: str, content: str):
        """Adicionar mensagem à sessão"""
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/api/v1/chat/{session_id}/messages"
            data = {
                "role": "user",
                "content": content
            }
            
            async with session.post(url, json=data) as response:
                if response.status != 201:
                    raise Exception(f"Failed to add message: {response.status}")
    
    async def _call_llm(self, provider: str, message: str) -> str:
        """Chamar API de LLM"""
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/api/v1/llm/{provider}/chat"
            data = {
                "messages": [
                    {"role": "user", "content": message}
                ]
            }
            
            async with session.post(url, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("content", "")
                else:
                    raise Exception(f"LLM call failed: {response.status}")

# Testes pytest
@pytest.mark.asyncio
async def test_chat_concurrent_performance():
    """Testar performance de chat com múltiplas requisições"""
    tester = ChatPerformanceTest()
    
    metrics = await tester.test_concurrent_chat_requests(num_requests=50)
    
    # Asserts
    assert metrics["success_rate"] >= 95, f"Success rate too low: {metrics['success_rate']}%"
    assert metrics["requests_per_second"] >= 10, f"RPS too low: {metrics['requests_per_second']}"
    assert metrics["response_time_stats"]["p95"] < 2.0, f"P95 too high: {metrics['response_time_stats']['p95']}s"

@pytest.mark.asyncio
async def test_llm_provider_performance():
    """Testar performance de diferentes provedores LLM"""
    tester = ChatPerformanceTest()
    
    results = await tester.test_llm_response_times()
    
    # Verificar que todos os provedores respondem em tempo razoável
    for provider, metrics in results.items():
        assert metrics["mean_time"] < 5.0, f"{provider} mean time too high: {metrics['mean_time']}s"
        assert metrics["max_time"] < 10.0, f"{provider} max time too high: {metrics['max_time']}s"

@pytest.mark.asyncio
async def test_memory_efficiency():
    """Testar eficiência de memória"""
    tester = ChatPerformanceTest()
    
    memory_metrics = await tester.test_memory_usage(num_sessions=100)
    
    # Verificar uso de memória razoável
    assert memory_metrics["memory_per_session_mb"] < 1.0, \
        f"Memory per session too high: {memory_metrics['memory_per_session_mb']}MB"
```

### 2. Testes de Carga com Locust

```python
# backend/tests/load/locustfile.py
from locust import HttpUser, task, between, events
import random
import json
import time

class JanusLoadTest(HttpUser):
    wait_time = between(1, 3)  # Esperar 1-3 segundos entre requisições
    
    def on_start(self):
        """Setup inicial para cada usuário simulado"""
        self.session_id = None
        self.user_id = f"load_test_user_{random.randint(1000, 9999)}"
        self._create_session()
    
    def _create_session(self):
        """Criar sessão de chat"""
        response = self.client.post(
            "/api/v1/chat/sessions",
            json={"user_id": self.user_id}
        )
        
        if response.status_code == 201:
            self.session_id = response.json()["id"]
        else:
            print(f"Failed to create session: {response.status_code}")
    
    @task(3)  # Peso 3 - mais frequente
    def send_chat_message(self):
        """Enviar mensagem de chat"""
        if not self.session_id:
            return
        
        messages = [
            "Hello, how are you?",
            "What's the weather like today?",
            "Can you help me with Python?",
            "Tell me a joke",
            "What is machine learning?",
            "How do I implement caching?",
            "Explain async/await in Python",
            "What's the best Python framework?"
        ]
        
        message = random.choice(messages)
        
        response = self.client.post(
            f"/api/v1/chat/{self.session_id}/messages",
            json={
                "role": "user",
                "content": message
            }
        )
        
        if response.status_code != 201:
            print(f"Failed to send message: {response.status_code}")
    
    @task(1)  # Peso 1 - menos frequente
    def generate_llm_response(self):
        """Gerar resposta LLM"""
        if not self.session_id:
            return
        
        providers = ["openai", "anthropic", "google"]
        provider = random.choice(providers)
        
        response = self.client.post(
            f"/api/v1/llm/{provider}/chat",
            json={
                "messages": [
                    {"role": "user", "content": "What is the capital of France?"}
                ]
            }
        )
        
        if response.status_code != 200:
            print(f"Failed to generate LLM response: {response.status_code}")
    
    @task(2)  # Peso 2 - frequência média
    def get_user_sessions(self):
        """Buscar sessões do usuário"""
        response = self.client.get(
            f"/api/v1/chat/sessions",
            params={"user_id": self.user_id, "limit": 10}
        )
        
        if response.status_code != 200:
            print(f"Failed to get sessions: {response.status_code}")
    
    @task(1)
    def get_system_status(self):
        """Verificar status do sistema"""
        response = self.client.get("/api/v1/system/status")
        
        if response.status_code != 200:
            print(f"Failed to get system status: {response.status_code}")

# Event handlers para métricas customizadas
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, **kwargs):
    """Coletar métricas adicionais"""
    if response.status_code >= 400:
        print(f"Request failed: {name} - Status: {response.status_code}")

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Executar antes do início do teste"""
    print(f"Starting load test with {environment.runner.target_user_count} users")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Executar após o término do teste"""
    print("Load test completed")
    
    # Imprimir estatísticas
    stats = environment.runner.stats
    print(f"Total requests: {stats.num_requests}")
    print(f"Failed requests: {stats.num_failures}")
    print(f"Average response time: {stats.avg_response_time:.2f}ms")
    print(f"95th percentile: {stats.get_response_time_percentile(0.95):.2f}ms")
    print(f"99th percentile: {stats.get_response_time_percentile(0.99):.2f}ms")

# Configurações avançadas
class AdvancedJanusLoadTest(HttpUser):
    """Teste de carga com comportamentos mais complexos"""
    
    weight = 3  # Este teste tem peso 3 comparado ao básico
    wait_time = between(2, 5)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message_count = 0
        self.max_messages = random.randint(5, 15)
    
    def on_start(self):
        """Comportamento mais complexo no início"""
        super().on_start()
        self._authenticate_user()
        self._load_user_preferences()
    
    def _authenticate_user(self):
        """Simular autenticação"""
        # Em um teste real, você usaria tokens JWT reais
        self.headers = {
            "Authorization": f"Bearer test_token_{self.user_id}"
        }
    
    def _load_user_preferences(self):
        """Carregar preferências do usuário"""
        response = self.client.get(
            f"/api/v1/users/{self.user_id}/preferences",
            headers=self.headers
        )
        
        if response.status_code == 200:
            self.preferences = response.json()
        else:
            self.preferences = {}
    
    @task
    def realistic_chat_flow(self):
        """Fluxo de chat realista com múltiplas mensagens"""
        if self.message_count >= self.max_messages:
            return
        
        # Mensagem contextual baseada no histórico
        if self.message_count == 0:
            message = "Hello, I need help with Python programming"
        elif self.message_count == 1:
            message = "Can you explain how async/await works?"
        elif self.message_count == 2:
            message = "Show me an example with error handling"
        else:
            message = random.choice([
                "That's helpful, thanks!",
                "Can you give me another example?",
                "What about performance implications?",
                "How does this compare to threading?"
            ])
        
        response = self.client.post(
            f"/api/v1/chat/{self.session_id}/messages",
            json={
                "role": "user",
                "content": message
            },
            headers=self.headers
        )
        
        if response.status_code == 201:
            self.message_count += 1
            
            # Pequena pausa para simular tempo de leitura
            time.sleep(random.uniform(1, 3))
            
            # Gerar resposta LLM ocasionalmente
            if random.random() < 0.3:  # 30% de chance
                self.client.post(
                    f"/api/v1/llm/openai/chat",
                    json={
                        "messages": [
                            {"role": "user", "content": message}
                        ]
                    },
                    headers=self.headers
                )

# Executar testes
# locust -f locustfile.py --host=http://localhost:8000 --users=100 --spawn-rate=10 --time=30s
```

## Padrões de Segurança Avançados

### 1. Content Security Policy (CSP)

```typescript
// frontend/src/security/csp-config.ts
export const CSPConfig = {
  directives: {
    'default-src': ["'self'"],
    'script-src': [
      "'self'",
      "'unsafe-inline'", // Necessário para Angular
      'https://cdn.jsdelivr.net',
      'https://unpkg.com'
    ],
    'style-src': [
      "'self'",
      "'unsafe-inline'",
      'https://fonts.googleapis.com'
    ],
    'font-src': [
      "'self'",
      'https://fonts.gstatic.com'
    ],
    'img-src': [
      "'self'",
      'data:',
      'https:'
    ],
    'connect-src': [
      "'self'",
      'https://api.janus.com',
      'wss://api.janus.com' // WebSocket
    ],
    'frame-ancestors': ["'none'"],
    'form-action': ["'self'"],
    'base-uri': ["'self'"]
  }
};

// Middleware CSP para Angular
export class CSPMiddleware implements HttpInterceptor {
  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    const cspHeader = Object.entries(CSPConfig.directives)
      .map(([directive, sources]) => `${directive} ${sources.join(' ')}`)
      .join('; ');
    
    const modifiedReq = req.clone({
      setHeaders: {
        'Content-Security-Policy': cspHeader,
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': 'camera=(), microphone=(), geolocation=()'
      }
    });
    
    return next.handle(modifiedReq);
  }
}
```

### 2. Rate Limiting Avançado

```python
# backend/app/core/security/rate_limiter.py
import time
import asyncio
from typing import Dict, Optional, List
from collections import defaultdict, deque
from dataclasses import dataclass
import redis.asyncio as redis
import logging

logger = logging.getLogger(__name__)

@dataclass
class RateLimitConfig:
    """Configuração de rate limiting"""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_capacity: int = 10
    window_size: int = 60  # segundos
    key_prefix: str = "rate_limit"

class AdvancedRateLimiter:
    """Rate limiter com múltiplas estratégias"""
    
    def __init__(self, redis_client: redis.Redis, config: RateLimitConfig):
        self.redis = redis_client
        self.config = config
        self.strategies = {
            "sliding_window": self._sliding_window_check,
            "token_bucket": self._token_bucket_check,
            "leaky_bucket": self._leaky_bucket_check
        }
    
    async def check_rate_limit(
        self,
        identifier: str,
        strategy: str = "sliding_window",
        increment: bool = True
    ) -> tuple[bool, dict]:
        """
        Verificar rate limit
        
        Returns:
            tuple: (allowed, info)
        """
        if strategy not in self.strategies:
            strategy = "sliding_window"
        
        return await self.strategies[strategy](identifier, increment)
    
    async def _sliding_window_check(self, identifier: str, increment: bool) -> tuple[bool, dict]:
        """Sliding window rate limiting"""
        
        now = int(time.time())
        window_start = now - self.config.window_size
        
        key = f"{self.config.key_prefix}:sliding:{identifier}"
        
        # Limpar requests antigos
        await self.redis.zremrangebyscore(key, 0, window_start)
        
        # Contar requests no window atual
        current_count = await self.redis.zcard(key)
        
        allowed = current_count < self.config.requests_per_minute
        
        if increment and allowed:
            # Adicionar request atual
            await self.redis.zadd(key, {str(now): now})
            await self.redis.expire(key, self.config.window_size)
        
        # Obter informações adicionais
        ttl = await self.redis.ttl(key)
        reset_time = now + ttl if ttl > 0 else now + self.config.window_size
        
        info = {
            "current_count": current_count,
            "limit": self.config.requests_per_minute,
            "remaining": max(0, self.config.requests_per_minute - current_count),
            "reset_time": reset_time,
            "window_size": self.config.window_size
        }
        
        return allowed, info
    
    async def _token_bucket_check(self, identifier: str, increment: bool) -> tuple[bool, dict]:
        """Token bucket rate limiting"""
        
        key = f"{self.config.key_prefix}:bucket:{identifier}"
        
        # Obter estado atual
        bucket_data = await self.redis.hmget(key, "tokens", "last_refill")
        tokens = float(bucket_data[0] or self.config.requests_per_minute)
        last_refill = float(bucket_data[1] or time.time())
        
        now = time.time()
        time_passed = now - last_refill
        
        # Recarregar tokens baseado no tempo passado
        tokens_to_add = (time_passed / self.config.window_size) * self.config.requests_per_minute
        tokens = min(self.config.requests_per_minute, tokens + tokens_to_add)
        
        allowed = tokens >= 1
        
        if increment and allowed:
            tokens -= 1
        
        # Atualizar estado
        await self.redis.hmset(key, {
            "tokens": tokens,
            "last_refill": now
        })
        await self.redis.expire(key, self.config.window_size)
        
        info = {
            "tokens": tokens,
            "capacity": self.config.requests_per_minute,
            "remaining": int(tokens),
            "last_refill": last_refill
        }
        
        return allowed, info
    
    async def _leaky_bucket_check(self, identifier: str, increment: bool) -> tuple[bool, dict]:
        """Leaky bucket rate limiting"""
        
        key = f"{self.config.key_prefix}:leaky:{identifier}"
        
        # Obter fila atual
        queue_length = await self.redis.llen(key)
        
        # Taxa de vazamento (requests por segundo)
        leak_rate = self.config.requests_per_minute / 60
        
        allowed = queue_length < self.config.burst_capacity
        
        if increment:
            if allowed:
                # Adicionar à fila
                await self.redis.lpush(key, time.time())
                await self.redis.expire(key, self.config.window_size)
            else:
                # Bucket overflow
                pass
        
        # Simular vazamento (em produção, usar job agendado)
        if queue_length > 0:
            # Remover requests antigos baseado na taxa de vazamento
            current_time = time.time()
            old_requests = await self.redis.lrange(key, 0, -1)
            
            valid_requests = []
            for request_time in old_requests:
                if float(request_time) > current_time - (1 / leak_rate):
                    valid_requests.append(request_time)
            
            # Reconstruir fila
            await self.redis.delete(key)
            if valid_requests:
                await self.redis.lpush(key, *valid_requests)
                await self.redis.expire(key, self.config.window_size)
        
        info = {
            "queue_length": queue_length,
            "burst_capacity": self.config.burst_capacity,
            "leak_rate": leak_rate,
            "remaining": max(0, self.config.burst_capacity - queue_length)
        }
        
        return allowed, info
    
    async def get_rate_limit_info(self, identifier: str) -> dict:
        """Obter informações detalhadas sobre rate limit"""
        info = {}
        
        for strategy in self.strategies.keys():
            allowed, strategy_info = await self.strategies[strategy](identifier, increment=False)
            info[strategy] = {
                "allowed": allowed,
                "details": strategy_info
            }
        
        return info
    
    async def reset_rate_limit(self, identifier: str) -> bool:
        """Resetar rate limit para um identificador"""
        try:
            # Deletar todas as chaves de rate limit para este identificador
            patterns = [
                f"{self.config.key_prefix}:sliding:{identifier}",
                f"{self.config.key_prefix}:bucket:{identifier}",
                f"{self.config.key_prefix}:leaky:{identifier}"
            ]
            
            for pattern in patterns:
                await self.redis.delete(pattern)
            
            logger.info(f"Rate limit reset for identifier: {identifier}")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting rate limit for {identifier}: {str(e)}")
            return False

# Decorator para rate limiting
def rate_limit(
    identifier_func: Optional[Callable] = None,
    strategy: str = "sliding_window",
    key_prefix: str = "rate_limit"
):
    """Decorator para rate limiting em funções"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Gerar identificador
            if identifier_func:
                identifier = identifier_func(*args, **kwargs)
            else:
                # Usar IP do request ou user_id
                identifier = kwargs.get("user_id", "anonymous")
            
            # Obter config e cliente Redis (assumindo global ou injetado)
            config = RateLimitConfig(key_prefix=key_prefix)
            rate_limiter = AdvancedRateLimiter(redis_client, config)
            
            # Verificar rate limit
            allowed, info = await rate_limiter.check_rate_limit(identifier, strategy)
            
            if not allowed:
                raise RateLimitExceededError(f"Rate limit exceeded: {info}")
            
            # Executar função
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

# Exemplo de uso
@rate_limit(identifier_func=lambda user_id, **kwargs: f"user:{user_id}")
async def send_chat_message(user_id: str, message: str) -> dict:
    """Enviar mensagem de chat com rate limiting"""
    # Lógica de envio de mensagem
    return {"status": "sent", "message": message}
```

## Conclusão

Este guia cobre padrões avançados de desenvolvimento para o Janus, incluindo:

- **Domain-Driven Design** com entidades e objetos de valor ricos
- **Repository Pattern** com operações avançadas e otimizações
- **Service Layer Pattern** com lógica de negócios complexa
- **Otimizações de Performance** com connection pooling e caching estratégico
- **Testes Avançados** de performance e carga
- **Segurança Avançada** com CSP e rate limiting sofisticado

Para contribuições avançadas, sempre:

1. **Documente** suas decisões arquiteturais
2. **Teste** performance antes de merge
3. **Revise** segurança com a equipe
4. **Monitore** métricas em produção
5. **Mantenha** compatibilidade backward

Para suporte técnico ou dúvidas sobre padrões avançados, entre em contato com a equipe de arquitetura.