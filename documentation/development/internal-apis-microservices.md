# APIs Internas e Microserviços - Janus

## Visão Geral

Este documento detalha a arquitetura de microserviços do Janus, incluindo APIs internas, padrões de comunicação, estratégias de descoberta de serviços e implementações específicas de cada domínio.

## Arquitetura de Microserviços

### Mapa de Serviços

```
┌─────────────────────────────────────────────────────────────────┐
│                          API Gateway                             │
│                    (FastAPI + Traefik)                         │
└─────────────────────┬───────────────────────┬───────────────────┘
                     │                       │
         ┌───────────▼──────────┐  ┌─────────▼──────────┐
         │   Core Services      │  │  Support Services  │
         ├──────────────────────┤  ├──────────────────────┤
         │ • Chat Service       │  │ • Auth Service     │
         │ • Knowledge Service  │  │ • User Service     │
         │ • LLM Service        │  │ • Analytics Service │
         │ • Search Service     │  │ • Notification Svc │
         │ • Vector Service     │  │ • Rate Limit Svc   │
         └───────────┬──────────┘  └─────────┬────────────┘
                     │                       │
         ┌───────────▼───────────────────────▼──────────┐
         │              Data Layer                      │
         ├──────────────────────────────────────────────┤
         │ • PostgreSQL (Relational)                    │
         │ • Neo4j (Graph)                             │
         │ • Qdrant (Vector)                          │
         │ • Redis (Cache)                             │
         │ • RabbitMQ (Message Queue)                 │
         └──────────────────────────────────────────────┘
```

### Comunicação entre Serviços

#### Padrões de Comunicação

**1. Síncrono (REST/HTTP)**
- Usado para operações que requerem resposta imediata
- Timeout configurável (padrão: 30s)
- Retry com exponential backoff
- Circuit breaker para resiliência

**2. Assíncrono (Message Queue)**
- Usado para operações de longa duração
- Processamento em background
- Garantia de entrega com RabbitMQ
- Dead letter queues para falhas

**3. Event-Driven (WebSocket/SSE)**
- Real-time updates para clientes
- Event sourcing para auditoria
- Pub/Sub para notificações

### Service Discovery

```python
# backend/app/core/service_discovery.py
import asyncio
import aiohttp
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

class ServiceStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class ServiceInstance:
    name: str
    host: str
    port: int
    version: str
    status: ServiceStatus
    metadata: Dict
    last_check: datetime

class ServiceRegistry:
    """Registro dinâmico de serviços com health checking"""
    
    def __init__(self):
        self.services: Dict[str, List[ServiceInstance]] = {}
        self.health_check_interval = 30  # segundos
        self.circuit_breaker_threshold = 3  # falhas consecutivas
        
    async def register_service(self, instance: ServiceInstance):
        """Registrar nova instância de serviço"""
        if instance.name not in self.services:
            self.services[instance.name] = []
        
        # Remover instâncias antigas do mesmo host/porta
        self.services[instance.name] = [
            s for s in self.services[instance.name]
            if not (s.host == instance.host and s.port == instance.port)
        ]
        
        self.services[instance.name].append(instance)
        print(f"✅ Serviço registrado: {instance.name} em {instance.host}:{instance.port}")
    
    async def discover_service(self, service_name: str) -> Optional[ServiceInstance]:
        """Descobrir instância saudável de um serviço (load balancing)"""
        if service_name not in self.services:
            return None
        
        # Filtrar instâncias saudáveis
        healthy_instances = [
            s for s in self.services[service_name]
            if s.status == ServiceStatus.HEALTHY
        ]
        
        if not healthy_instances:
            # Tentar instâncias degradadas
            degraded_instances = [
                s for s in self.services[service_name]
                if s.status == ServiceStatus.DEGRADED
            ]
            if degraded_instances:
                return self._round_robin_selection(degraded_instances)
            return None
        
        # Seleção round-robin
        return self._round_robin_selection(healthy_instances)
    
    def _round_robin_selection(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Seleção round-robin com peso baseado em performance"""
        # Implementar lógica de seleção inteligente
        # Por enquanto, simples round-robin
        import random
        return random.choice(instances)
    
    async def health_check_all_services(self):
        """Verificar saúde de todos os serviços registrados"""
        async with aiohttp.ClientSession() as session:
            tasks = []
            for service_name, instances in self.services.items():
                for instance in instances:
                    task = self._check_service_health(session, instance)
                    tasks.append(task)
            
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _check_service_health(self, session: aiohttp.ClientSession, instance: ServiceInstance):
        """Verificar saúde de uma instância específica"""
        try:
            health_url = f"http://{instance.host}:{instance.port}/health"
            
            async with session.get(health_url, timeout=5) as response:
                if response.status == 200:
                    health_data = await response.json()
                    
                    # Atualizar status baseado na resposta
                    if health_data.get('status') == 'healthy':
                        instance.status = ServiceStatus.HEALTHY
                    elif health_data.get('status') == 'degraded':
                        instance.status = ServiceStatus.DEGRADED
                    else:
                        instance.status = ServiceStatus.UNHEALTHY
                else:
                    instance.status = ServiceStatus.UNHEALTHY
                    
        except Exception as e:
            print(f"❌ Health check falhou para {instance.name}: {e}")
            instance.status = ServiceStatus.UNHEALTHY
        
        instance.last_check = datetime.now()

# Instância global
service_registry = ServiceRegistry()
```

## Serviços Core

### 1. Chat Service

**Responsabilidades:**
- Gerenciamento de sessões de chat
- Processamento de mensagens
- Integração com LLM Service
- Histórico de conversas
- Contexto e memória de conversa

```python
# backend/app/services/chat_service.py
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass
from app.core.service_discovery import ServiceRegistry, ServiceInstance
from app.models.chat import ChatMessage, ChatResponse, ChatSession
from app.repositories.chat_repository import ChatRepository
from app.services.llm_service import LLMService
from app.services.memory_service import MemoryService
from app.core.rate_limiter import RateLimiter

class ChatService:
    """Serviço principal de chat com integração multi-LLM"""
    
    def __init__(self):
        self.chat_repo = ChatRepository()
        self.llm_service = LLMService()
        self.memory_service = MemoryService()
        self.rate_limiter = RateLimiter()
        self.max_context_length = 4000  # tokens
        
    async def process_message(self, message: ChatMessage) -> ChatResponse:
        """Processar mensagem de chat com contexto e memória"""
        
        # Verificar rate limiting
        if not self.rate_limiter.is_allowed(message.user_id, "chat"):
            return ChatResponse(
                content="Rate limit exceeded. Please try again later.",
                status="error",
                error_code="RATE_LIMIT_EXCEEDED"
            )
        
        # Recuperar sessão ou criar nova
        session = await self._get_or_create_session(message.session_id, message.user_id)
        
        # Buscar contexto relevante
        context = await self._build_context(session, message)
        
        # Enriquecer com memória de longo prazo
        memory_context = await self.memory_service.get_relevant_memory(
            user_id=message.user_id,
            query=message.content,
            limit=5
        )
        
        # Preparar prompt completo
        enriched_message = self._enrich_message_with_context(message, context, memory_context)
        
        # Chamar LLM Service
        llm_response = await self.llm_service.generate_response(
            prompt=enriched_message.content,
            context=enriched_message.metadata.get("context", {}),
            user_id=message.user_id
        )
        
        # Salvar mensagens no histórico
        await self._save_conversation_turn(session, message, llm_response)
        
        # Atualizar memória se necessário
        if llm_response.metadata.get("should_update_memory", False):
            await self.memory_service.store_memory(
                user_id=message.user_id,
                content=llm_response.content,
                metadata=llm_response.metadata
            )
        
        return llm_response
    
    async def _build_context(self, session: ChatSession, current_message: ChatMessage) -> Dict:
        """Construir contexto baseado no histórico recente"""
        
        # Recuperar últimas mensagens
        recent_messages = await self.chat_repo.get_recent_messages(
            session_id=session.id,
            limit=10
        )
        
        # Filtrar mensagens relevantes
        relevant_messages = self._filter_relevant_messages(recent_messages, current_message)
        
        # Construir contexto de conversação
        context = {
            "conversation_history": [
                {
                    "role": "user" if msg.is_user else "assistant",
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat()
                }
                for msg in relevant_messages
            ],
            "session_metadata": session.metadata,
            "user_preferences": await self._get_user_preferences(session.user_id)
        }
        
        return context
    
    def _filter_relevant_messages(self, messages: List[ChatMessage], current_message: ChatMessage) -> List[ChatMessage]:
        """Filtrar mensagens relevantes para o contexto"""
        
        # Implementar lógica de relevância (similaridade, tempo, etc.)
        # Por enquanto, retornar mensagens recentes
        return messages[-5:]  # Últimas 5 mensagens
    
    async def _get_or_create_session(self, session_id: str, user_id: str) -> ChatSession:
        """Recuperar ou criar sessão de chat"""
        
        session = await self.chat_repo.get_session(session_id)
        if not session:
            session = ChatSession(
                id=session_id,
                user_id=user_id,
                created_at=datetime.now(),
                metadata={"source": "api", "version": "1.0"}
            )
            await self.chat_repo.create_session(session)
        
        return session

# Configuração de deployment
CHAT_SERVICE_CONFIG = {
    "replicas": 3,
    "resources": {
        "requests": {"cpu": "500m", "memory": "512Mi"},
        "limits": {"cpu": "2000m", "memory": "2Gi"}
    },
    "autoscaling": {
        "min_replicas": 2,
        "max_replicas": 10,
        "target_cpu_utilization": 70
    }
}
```

### 2. Knowledge Service

**Responsabilidades:**
- Gestão de base de conhecimento
- Indexação vetorial de documentos
- Busca semântica híbrida
- Versionamento de conhecimento
- Integração com múltiplas fontes

```python
# backend/app/services/knowledge_service.py
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
from app.models.knowledge import KnowledgeItem, KnowledgeSource, SearchResult
from app.repositories.knowledge_repository import KnowledgeRepository
from app.services.vector_service import VectorService
from app.services.search_service import SearchService

class KnowledgeService:
    """Serviço de gestão de conhecimento com busca híbrida"""
    
    def __init__(self):
        self.knowledge_repo = KnowledgeRepository()
        self.vector_service = VectorService()
        self.search_service = SearchService()
        self.min_confidence_score = 0.7
        
    async def add_knowledge(self, item: KnowledgeItem, source: KnowledgeSource) -> str:
        """Adicionar novo item de conhecimento"""
        
        # Validar item
        validation_result = await self._validate_knowledge_item(item)
        if not validation_result.is_valid:
            raise ValueError(f"Invalid knowledge item: {validation_result.errors}")
        
        # Gerar embedding vetorial
        embedding = await self.vector_service.generate_embedding(
            content=item.content,
            metadata={"title": item.title, "tags": item.tags}
        )
        
        # Indexar em múltiplos sistemas
        item_id = await self.knowledge_repo.create(item, source)
        await self.vector_service.index_item(item_id, embedding, item.metadata)
        
        # Indexar texto para busca full-text
        await self.search_service.index_document(
            doc_id=item_id,
            content=f"{item.title} {item.content}",
            metadata=item.metadata
        )
        
        # Disparar evento de novo conhecimento
        await self._publish_knowledge_added_event(item_id, item)
        
        return item_id
    
    async def search_knowledge(self, query: str, search_type: str = "hybrid", 
                             limit: int = 10, filters: Optional[Dict] = None) -> List[SearchResult]:
        """Buscar conhecimento usando múltiplas estratégias"""
        
        results = []
        
        if search_type in ["vector", "hybrid"]:
            # Busca vetorial semântica
            vector_results = await self._semantic_search(query, limit, filters)
            results.extend(vector_results)
        
        if search_type in ["text", "hybrid"]:
            # Busca textual tradicional
            text_results = await self._text_search(query, limit, filters)
            results.extend(text_results)
        
        if search_type == "hybrid":
            # Combinar e ranquear resultados
            results = self._hybrid_ranking(results, query)
        
        # Aplicar filtros finais
        if filters:
            results = self._apply_filters(results, filters)
        
        return results[:limit]
    
    async def _semantic_search(self, query: str, limit: int, filters: Optional[Dict]) -> List[SearchResult]:
        """Busca semântica usando embeddings"""
        
        # Gerar embedding da query
        query_embedding = await self.vector_service.generate_embedding(query)
        
        # Buscar similaridades
        vector_results = await self.vector_service.search_similar(
            query_embedding=query_embedding,
            limit=limit * 2,  # Buscar mais para permitir filtragem
            min_score=self.min_confidence_score
        )
        
        # Converter para SearchResult
        results = []
        for vector_result in vector_results:
            knowledge_item = await self.knowledge_repo.get_by_id(vector_result.item_id)
            if knowledge_item:
                results.append(SearchResult(
                    item=knowledge_item,
                    score=vector_result.score,
                    search_type="vector",
                    metadata=vector_result.metadata
                ))
        
        return results
    
    async def update_knowledge(self, item_id: str, updates: Dict) -> bool:
        """Atualizar item de conhecimento com versionamento"""
        
        # Obter versão atual
        current_item = await self.knowledge_repo.get_by_id(item_id)
        if not current_item:
            return False
        
        # Criar nova versão
        new_version = current_item.copy()
        for key, value in updates.items():
            setattr(new_version, key, value)
        
        new_version.version = current_item.version + 1
        new_version.updated_at = datetime.now()
        
        # Atualizar índices
        success = await self.knowledge_repo.update(item_id, new_version)
        if success:
            # Re-indexar embeddings se conteúdo mudou
            if 'content' in updates or 'title' in updates:
                new_embedding = await self.vector_service.generate_embedding(
                    content=new_version.content,
                    metadata={"title": new_version.title, "tags": new_version.tags}
                )
                await self.vector_service.update_index(item_id, new_embedding)
        
        return success

# Configuração específica do serviço
KNOWLEDGE_SERVICE_CONFIG = {
    "replicas": 2,
    "vector_dimension": 768,
    "index_refresh_interval": 300,  # 5 minutos
    "max_content_length": 10000,  # caracteres
    "supported_formats": ["text", "markdown", "pdf", "html"]
}
```

### 3. LLM Service

**Responsabilidades:**
- Integração com múltiplos provedores LLM
- Gestão de modelos e versões
- Rate limiting por provedor
- Caching de respostas
- Monitoramento de custos e performance

```python
# backend/app/services/llm_service.py
from typing import Dict, List, Optional, AsyncGenerator
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod
import asyncio
from app.core.config import settings
from app.core.cache import cache
from app.core.metrics import metrics

class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"

@dataclass
class LLMRequest:
    prompt: str
    model: str
    max_tokens: int = 1000
    temperature: float = 0.7
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop_sequences: Optional[List[str]] = None
    metadata: Optional[Dict] = None

@dataclass
class LLMResponse:
    content: str
    model: str
    usage: Dict  # tokens usados
    cost: float  # custo estimado
    latency: float  # tempo de resposta
    metadata: Optional[Dict] = None

class BaseLLMProvider(ABC):
    """Interface base para provedores LLM"""
    
    @abstractmethod
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Gerar resposta síncrona"""
        pass
    
    @abstractmethod
    async def generate_stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Gerar resposta em streaming"""
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Listar modelos disponíveis"""
        pass
    
    @abstractmethod
    def estimate_cost(self, request: LLMRequest) -> float:
        """Estimar custo da requisição"""
        pass

class OpenAIProvider(BaseLLMProvider):
    """Provedor OpenAI com suporte para GPT-3.5 e GPT-4"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1"
        self.client = None  # Inicializar async client
        
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Implementação específica para OpenAI"""
        
        start_time = asyncio.get_event_loop().time()
        
        # Preparar payload
        payload = {
            "model": request.model,
            "messages": [{"role": "user", "content": request.prompt}],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "frequency_penalty": request.frequency_penalty,
            "presence_penalty": request.presence_penalty,
        }
        
        if request.stop_sequences:
            payload["stop"] = request.stop_sequences
        
        # Fazer requisição
        response = await self._make_request("chat/completions", payload)
        
        # Processar resposta
        content = response["choices"][0]["message"]["content"]
        usage = response["usage"]
        
        # Calcular custo
        cost = self._calculate_cost(request.model, usage)
        
        latency = asyncio.get_event_loop().time() - start_time
        
        return LLMResponse(
            content=content,
            model=request.model,
            usage=usage,
            cost=cost,
            latency=latency,
            metadata={"provider": "openai", "response_id": response["id"]}
        )
    
    async def _make_request(self, endpoint: str, payload: Dict) -> Dict:
        """Fazer requisição HTTP para OpenAI"""
        # Implementar com aiohttp com retry e error handling
        pass

class LLMService:
    """Serviço principal de LLM com suporte multi-provedor"""
    
    def __init__(self):
        self.providers: Dict[LLMProvider, BaseLLMProvider] = {}
        self.provider_priorities = {
            LLMProvider.OPENAI: 1,
            LLMProvider.ANTHROPIC: 2,
            LLMProvider.GEMINI: 3,
            LLMProvider.OLLAMA: 4,
            LLMProvider.OPENROUTER: 5
        }
        self._initialize_providers()
        
    def _initialize_providers(self):
        """Inicializar provedores com configurações"""
        
        # OpenAI
        if settings.OPENAI_API_KEY:
            self.providers[LLMProvider.OPENAI] = OpenAIProvider(settings.OPENAI_API_KEY)
        
        # Adicionar outros provedores...
    
    @cache.cache_result(expire=3600)  # Cache por 1 hora
    async def generate_response(self, prompt: str, provider: Optional[LLMProvider] = None,
                              model: Optional[str] = None, user_id: Optional[str] = None,
                              **kwargs) -> LLMResponse:
        """Gerar resposta usando provedor específico ou melhor disponível"""
        
        # Registrar métricas
        metrics.record_llm_request(provider.value if provider else "auto", user_id or "anonymous")
        
        # Selecionar provedor se não especificado
        if not provider:
            provider = await self._select_best_provider(prompt, user_id)
        
        # Validar provedor disponível
        if provider not in self.providers:
            raise ValueError(f"Provider {provider} not available")
        
        # Preparar requisição
        request = LLMRequest(prompt=prompt, model=model or self._get_default_model(provider), **kwargs)
        
        try:
            # Tentar gerar resposta
            response = await self.providers[provider].generate_response(request)
            
            # Registrar métricas de sucesso
            metrics.record_llm_success(provider.value, response.latency, response.cost)
            
            return response
            
        except Exception as e:
            # Registrar falha
            metrics.record_llm_failure(provider.value, str(type(e).__name__))
            
            # Tentar próximo provedor se disponível
            next_provider = await self._get_next_provider(provider)
            if next_provider:
                return await self.generate_response(prompt, next_provider, model, user_id, **kwargs)
            else:
                raise e
    
    async def _select_best_provider(self, prompt: str, user_id: Optional[str]) -> LLMProvider:
        """Selecionar melhor provedor baseado em disponibilidade, custo e performance"""
        
        # Obter estatísticas de uso recente
        user_stats = await self._get_user_stats(user_id) if user_id else None
        
        # Obter disponibilidade e performance dos provedores
        available_providers = []
        for provider, provider_instance in self.providers.items():
            stats = await self._get_provider_stats(provider)
            
            # Verificar se provedor está saudável
            if stats.get("health_status") == "healthy":
                available_providers.append({
                    "provider": provider,
                    "priority": self.provider_priorities[provider],
                    "avg_latency": stats.get("avg_latency", 0),
                    "error_rate": stats.get("error_rate", 1),
                    "cost_per_1k": stats.get("cost_per_1k", 0)
                })
        
        if not available_providers:
            raise RuntimeError("No healthy LLM providers available")
        
        # Ranquear provedores (prioridade + performance + custo)
        available_providers.sort(key=lambda x: (
            x["priority"],  # Prioridade configurada
            -x["error_rate"],  # Taxa de erro (inverter)
            x["avg_latency"],  # Latência média
            x["cost_per_1k"]  # Custo
        ))
        
        return available_providers[0]["provider"]
    
    async def get_usage_stats(self, user_id: Optional[str] = None, 
                              time_range: str = "24h") -> Dict:
        """Obter estatísticas de uso de LLM"""
        
        return await metrics.get_llm_usage_stats(user_id, time_range)

# Configuração do serviço
LLM_SERVICE_CONFIG = {
    "default_timeout": 30,
    "max_retries": 3,
    "retry_delay": 1,
    "cache_enabled": True,
    "cache_ttl": 3600,
    "providers": {
        "openai": {
            "models": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"],
            "rate_limit": "100/min",
            "max_tokens": 8000
        },
        "anthropic": {
            "models": ["claude-3-sonnet", "claude-3-opus"],
            "rate_limit": "50/min",
            "max_tokens": 10000
        }
    }
}
```

## Serviços de Suporte

### 1. Auth Service

**Responsabilidades:**
- Autenticação e autorização
- Gestão de tokens JWT
- Integração com provedores OAuth
- Controle de sessões
- Rate limiting por usuário

```python
# backend/app/services/auth_service.py
from typing import Optional, Dict
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.core.security import create_access_token, verify_token
from app.core.rate_limiter import RateLimiter

class AuthService:
    """Serviço de autenticação com suporte multi-provider"""
    
    def __init__(self):
        self.user_repo = UserRepository()
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.rate_limiter = RateLimiter()
        self.jwt_secret = settings.JWT_SECRET_KEY
        self.jwt_algorithm = "HS256"
        self.access_token_expire_minutes = 30
        self.refresh_token_expire_days = 7
        
    async def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Autenticar usuário com username/password"""
        
        # Verificar rate limiting
        if not self.rate_limiter.is_allowed(username, "login"):
            raise RateLimitExceededError("Too many login attempts")
        
        # Buscar usuário
        user = await self.user_repo.get_by_username(username)
        if not user:
            return None
        
        # Verificar senha
        if not self._verify_password(password, user.hashed_password):
            # Registrar tentativa falhada
            await self._record_failed_login(username)
            return None
        
        # Gerar tokens
        access_token = self._create_access_token(user.id, user.role)
        refresh_token = self._create_refresh_token(user.id)
        
        # Atualizar último login
        await self.user_repo.update_last_login(user.id)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": self.access_token_expire_minutes * 60,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role.value,
                "permissions": user.permissions
            }
        }
    
    async def authenticate_oauth(self, provider: str, code: str, 
                               redirect_uri: str) -> Optional[Dict]:
        """Autenticar via OAuth2"""
        
        # Implementar fluxo OAuth completo
        # 1. Trocar código por token
        # 2. Obter informações do usuário
        # 3. Criar/atualizar usuário local
        # 4. Gerar tokens JWT
        
        oauth_provider = self._get_oauth_provider(provider)
        user_info = await oauth_provider.get_user_info(code, redirect_uri)
        
        # Criar ou atualizar usuário
        user = await self.user_repo.get_by_email(user_info["email"])
        if not user:
            user = await self._create_oauth_user(user_info, provider)
        
        # Gerar tokens
        return await self._generate_user_tokens(user)
    
    async def refresh_token(self, refresh_token: str) -> Optional[Dict]:
        """Refresh access token using refresh token"""
        
        try:
            payload = jwt.decode(refresh_token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            user_id = payload.get("sub")
            token_type = payload.get("type")
            
            if token_type != "refresh":
                return None
            
            # Verificar se usuário ainda existe
            user = await self.user_repo.get_by_id(user_id)
            if not user:
                return None
            
            # Gerar novo access token
            access_token = self._create_access_token(user.id, user.role)
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": self.access_token_expire_minutes * 60
            }
            
        except jwt.InvalidTokenError:
            return None
    
    async def validate_token(self, token: str) -> Optional[Dict]:
        """Validar e decodificar token JWT"""
        
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            
            # Verificar expiração
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp) < datetime.now():
                return None
            
            # Buscar usuário
            user = await self.user_repo.get_by_id(payload.get("sub"))
            if not user or not user.is_active:
                return None
            
            return {
                "user_id": user.id,
                "username": user.username,
                "role": user.role,
                "permissions": user.permissions
            }
            
        except jwt.InvalidTokenError:
            return None
    
    def _create_access_token(self, user_id: str, role: UserRole) -> str:
        """Criar access token JWT"""
        
        expire = datetime.now() + timedelta(minutes=self.access_token_expire_minutes)
        
        payload = {
            "sub": user_id,
            "role": role.value,
            "type": "access",
            "exp": expire.timestamp(),
            "iat": datetime.now().timestamp()
        }
        
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    def _create_refresh_token(self, user_id: str) -> str:
        """Criar refresh token JWT"""
        
        expire = datetime.now() + timedelta(days=self.refresh_token_expire_days)
        
        payload = {
            "sub": user_id,
            "type": "refresh",
            "exp": expire.timestamp(),
            "iat": datetime.now().timestamp()
        }
        
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)

# Configuração específica
AUTH_SERVICE_CONFIG = {
    "jwt_algorithm": "HS256",
    "token_expiry": {
        "access_token": 30,  # minutos
        "refresh_token": 7,  # dias
        "password_reset": 1   # horas
    },
    "rate_limits": {
        "login": "10/hour",
        "password_reset": "5/hour",
        "token_refresh": "100/hour"
    },
    "oauth_providers": ["google", "github", "microsoft"]
}
```

### 2. Analytics Service

**Responsabilidades:**
- Coleta e agregação de eventos
- Geração de relatórios e dashboards
- Análise de uso e performance
- Exportação de dados
- Integração com BI tools

```python
# backend/app/services/analytics_service.py
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from app.core.events import EventBus
from app.repositories.analytics_repository import AnalyticsRepository
from app.models.analytics import Event, Metric, Report

class AnalyticsService:
    """Serviço de análise e relatórios com processamento em tempo real"""
    
    def __init__(self):
        self.analytics_repo = AnalyticsRepository()
        self.event_bus = EventBus()
        self.processing_batch_size = 1000
        self.real_time_window = 300  # 5 minutos
        
    async def track_event(self, event: Event) -> bool:
        """Registrar evento para análise"""
        
        # Validar evento
        if not self._validate_event(event):
            return False
        
        # Enriquecer evento
        enriched_event = self._enrich_event(event)
        
        # Armazenar evento
        success = await self.analytics_repo.store_event(enriched_event)
        
        # Publicar para processamento em tempo real
        if success:
            await self.event_bus.publish("analytics.event", enriched_event)
        
        return success
    
    async def get_real_time_metrics(self, metric_names: List[str]) -> Dict[str, Metric]:
        """Obter métricas em tempo real"""
        
        metrics = {}
        
        for metric_name in metric_names:
            # Buscar métrica do cache ou calcular
            metric = await self._get_or_calculate_metric(metric_name)
            if metric:
                metrics[metric_name] = metric
        
        return metrics
    
    async def generate_report(self, report_config: Dict) -> Report:
        """Gerar relatório customizado"""
        
        report_type = report_config.get("type")
        time_range = report_config.get("time_range", {"start": "-7d", "end": "now"})
        filters = report_config.get("filters", {})
        aggregations = report_config.get("aggregations", [])
        
        # Coletar dados
        events = await self.analytics_repo.get_events(time_range, filters)
        
        # Processar agregações
        aggregated_data = await self._process_aggregations(events, aggregations)
        
        # Gerar visualizações
        visualizations = await self._generate_visualizations(aggregated_data, report_config)
        
        # Criar relatório
        report = Report(
            id=self._generate_report_id(),
            type=report_type,
            title=report_config.get("title", "Custom Report"),
            description=report_config.get("description", ""),
            data=aggregated_data,
            visualizations=visualizations,
            generated_at=datetime.now(),
            filters=filters,
            time_range=time_range
        )
        
        # Armazenar relatório
        await self.analytics_repo.store_report(report)
        
        return report
    
    async def get_user_analytics(self, user_id: str, period: str = "30d") -> Dict:
        """Obter análise detalhada de usuário específico"""
        
        # Métricas de uso
        usage_stats = await self.analytics_repo.get_user_usage_stats(user_id, period)
        
        # Padrões de comportamento
        behavior_patterns = await self._analyze_user_behavior(user_id, period)
        
        # Engajamento
        engagement_metrics = await self._calculate_engagement_metrics(user_id, period)
        
        # Predições (churn, upgrade, etc.)
        predictions = await self._generate_user_predictions(user_id, usage_stats, behavior_patterns)
        
        return {
            "user_id": user_id,
            "period": period,
            "usage_stats": usage_stats,
            "behavior_patterns": behavior_patterns,
            "engagement_metrics": engagement_metrics,
            "predictions": predictions,
            "generated_at": datetime.now().isoformat()
        }
    
    async def _process_aggregations(self, events: List[Event], 
                                  aggregations: List[Dict]) -> Dict:
        """Processar agregações complexas sobre eventos"""
        
        results = {}
        
        for aggregation in aggregations:
            agg_type = aggregation.get("type")
            field = aggregation.get("field")
            group_by = aggregation.get("group_by", [])
            
            if agg_type == "count":
                results[f"count_{field}"] = await self._count_aggregation(events, field, group_by)
            
            elif agg_type == "sum":
                results[f"sum_{field}"] = await self._sum_aggregation(events, field, group_by)
            
            elif agg_type == "avg":
                results[f"avg_{field}"] = await self._avg_aggregation(events, field, group_by)
            
            elif agg_type == "unique":
                results[f"unique_{field}"] = await self._unique_aggregation(events, field, group_by)
            
            elif agg_type == "percentile":
                percentile = aggregation.get("percentile", 95)
                results[f"p{percentile}_{field}"] = await self._percentile_aggregation(
                    events, field, percentile, group_by
                )
        
        return results

# Configuração do serviço
ANALYTICS_SERVICE_CONFIG = {
    "batch_processing": {
        "enabled": True,
        "batch_size": 1000,
        "flush_interval": 60  # segundos
    },
    "real_time_processing": {
        "enabled": True,
        "window_size": 300,  # 5 minutos
        "update_frequency": 30  # segundos
    },
    "data_retention": {
        "raw_events": "90d",
        "aggregated_metrics": "2y",
        "reports": "5y"
    },
    "export_formats": ["csv", "json", "parquet", "xlsx"]
}
```

## Comunicação entre Serviços

### 1. REST API Patterns

```python
# backend/app/core/service_client.py
import aiohttp
import asyncio
from typing import Dict, Optional, Any
from dataclasses import dataclass
from app.core.config import settings

@dataclass
class ServiceRequest:
    method: str
    endpoint: str
    data: Optional[Dict] = None
    params: Optional[Dict] = None
    headers: Optional[Dict] = None
    timeout: int = 30

@dataclass
class ServiceResponse:
    status: int
    data: Any
    headers: Dict
    latency: float

class ServiceClient:
    """Cliente HTTP para comunicação entre serviços"""
    
    def __init__(self, service_name: str, base_url: str):
        self.service_name = service_name
        self.base_url = base_url.rstrip('/')
        self.session = None
        self.retry_attempts = 3
        self.retry_delay = 1
        self.circuit_breaker_threshold = 5
        self.circuit_breaker_timeout = 60
        self._failure_count = 0
        self._circuit_breaker_open = False
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def request(self, service_request: ServiceRequest) -> ServiceResponse:
        """Fazer requisição para outro serviço com retry e circuit breaker"""
        
        # Verificar circuit breaker
        if self._circuit_breaker_open:
            if self._should_attempt_reset():
                self._circuit_breaker_open = False
                self._failure_count = 0
            else:
                raise CircuitBreakerOpenError(f"Circuit breaker open for {self.service_name}")
        
        # Tentar requisição com retry
        for attempt in range(self.retry_attempts):
            try:
                start_time = asyncio.get_event_loop().time()
                
                async with self.session.request(
                    method=service_request.method,
                    url=f"{self.base_url}{service_request.endpoint}",
                    json=service_request.data,
                    params=service_request.params,
                    headers=service_request.headers,
                    timeout=aiohttp.ClientTimeout(total=service_request.timeout)
                ) as response:
                    
                    latency = asyncio.get_event_loop().time() - start_time
                    response_data = await response.json() if response.content_type == 'application/json' else await response.text()
                    
                    # Sucesso - resetar contador de falhas
                    if response.status < 400:
                        self._failure_count = 0
                        return ServiceResponse(
                            status=response.status,
                            data=response_data,
                            headers=dict(response.headers),
                            latency=latency
                        )
                    
                    # Erro - incrementar contador
                    self._failure_count += 1
                    
                    # Se for erro não-retriável, propagar
                    if response.status >= 500 and attempt == self.retry_attempts - 1:
                        self._check_circuit_breaker()
                    
                    # Aguardar antes de retry
                    if attempt < self.retry_attempts - 1:
                        await asyncio.sleep(self.retry_delay * (2 ** attempt))
                    
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                self._failure_count += 1
                
                if attempt == self.retry_attempts - 1:
                    self._check_circuit_breaker()
                    raise ServiceUnavailableError(f"Service {self.service_name} unavailable: {e}")
                
                # Aguardar antes de retry
                await asyncio.sleep(self.retry_delay * (2 ** attempt))
        
        # Não deve chegar aqui, mas garantir que algo seja retornado
        raise ServiceRequestError(f"Failed to complete request to {self.service_name}")
    
    def _check_circuit_breaker(self):
        """Verificar se circuit breaker deve ser aberto"""
        if self._failure_count >= self.circuit_breaker_threshold:
            self._circuit_breaker_open = True
            # Registrar abertura do circuit breaker
            print(f"🔴 Circuit breaker opened for {self.service_name}")
    
    def _should_attempt_reset(self) -> bool:
        """Verificar se deve tentar resetar circuit breaker"""
        # Implementar lógica de timeout para tentativa de reset
        return True  # Simplificado

# Fábrica de clientes de serviço
class ServiceClientFactory:
    """Fábrica para criar clientes de serviço com descoberta"""
    
    def __init__(self, service_registry: ServiceRegistry):
        self.service_registry = service_registry
        self._clients: Dict[str, ServiceClient] = {}
    
    async def get_client(self, service_name: str) -> ServiceClient:
        """Obter cliente para serviço com load balancing"""
        
        if service_name not in self._clients:
            # Descobrir instância do serviço
            instance = await self.service_registry.discover_service(service_name)
            if not instance:
                raise ServiceNotFoundError(f"Service {service_name} not found")
            
            # Criar cliente
            base_url = f"http://{instance.host}:{instance.port}"
            self._clients[service_name] = ServiceClient(service_name, base_url)
        
        return self._clients[service_name]
    
    async def invalidate_client(self, service_name: str):
        """Invalidar cliente (ex: quando serviço falha)"""
        if service_name in self._clients:
            del self._clients[service_name]

# Instância global
service_client_factory = ServiceClientFactory(service_registry)
```

### 2. Message Queue Patterns

```python
# backend/app/core/messaging.py
import asyncio
import json
from typing import Dict, Callable, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import aio_pika
from app.core.config import settings

class MessagePriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class Message:
    id: str
    type: str
    payload: Dict
    priority: MessagePriority
    timestamp: datetime
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

class MessageBus:
    """Barramento de mensagens com RabbitMQ"""
    
    def __init__(self):
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.exchanges: Dict[str, aio_pika.Exchange] = {}
        self.queues: Dict[str, aio_pika.Queue] = {}
        self.consumers: Dict[str, Callable] = {}
        self._is_connected = False
        
    async def connect(self):
        """Conectar ao RabbitMQ"""
        try:
            self.connection = await aio_pika.connect_robust(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
                login=settings.RABBITMQ_USER,
                password=settings.RABBITMQ_PASSWORD,
                virtualhost=settings.RABBITMQ_VHOST
            )
            
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=10)
            
            self._is_connected = True
            print("✅ Connected to RabbitMQ")
            
        except Exception as e:
            print(f"❌ Failed to connect to RabbitMQ: {e}")
            raise
    
    async def disconnect(self):
        """Desconectar do RabbitMQ"""
        if self.connection:
            await self.connection.close()
            self._is_connected = False
            print("📪 Disconnected from RabbitMQ")
    
    async def publish_message(self, message: Message, exchange: str = ""):
        """Publicar mensagem no barramento"""
        
        if not self._is_connected:
            await self.connect()
        
        # Obter ou criar exchange
        if exchange not in self.exchanges:
            self.exchanges[exchange] = await self.channel.declare_exchange(
                exchange,
                aio_pika.ExchangeType.TOPIC,
                durable=True
            )
        
        # Serializar mensagem
        message_body = json.dumps(asdict(message), default=str).encode()
        
        # Criar mensagem AMQP
        amqp_message = aio_pika.Message(
            message_body,
            message_id=message.id,
            timestamp=message.timestamp,
            priority=message.priority.value,
            correlation_id=message.correlation_id,
            reply_to=message.reply_to,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT
        )
        
        # Publicar mensagem
        routing_key = f"{message.type}.{message.priority.name.lower()}"
        await self.exchanges[exchange].publish(amqp_message, routing_key=routing_key)
        
        print(f"📤 Published message {message.id} to exchange {exchange}")
    
    async def subscribe(self, queue_name: str, message_type: str, 
                       handler: Callable[[Message], Any], 
                       exchange: str = "", auto_ack: bool = False):
        """Inscrever handler para mensagens específicas"""
        
        if not self._is_connected:
            await self.connect()
        
        # Obter ou criar fila
        if queue_name not in self.queues:
            self.queues[queue_name] = await self.channel.declare_queue(
                queue_name,
                durable=True,
                arguments={
                    "x-dead-letter-exchange": "dlx",
                    "x-dead-letter-routing-key": f"{queue_name}.dead"
                }
            )
        
        queue = self.queues[queue_name]
        
        # Vincular fila ao exchange com routing key
        routing_key = f"{message_type}.*"
        if exchange in self.exchanges:
            await queue.bind(self.exchanges[exchange], routing_key=routing_key)
        
        # Registrar handler
        self.consumers[f"{queue_name}:{message_type}"] = handler
        
        # Configurar consumidor
        async def message_handler(amqp_message: aio_pika.IncomingMessage):
            async with amqp_message.process(requeue=not auto_ack):
                try:
                    # Desserializar mensagem
                    message_data = json.loads(amqp_message.body.decode())
                    message = Message(**message_data)
                    
                    # Chamar handler
                    result = await handler(message)
                    
                    # Enviar resposta se houver reply_to
                    if message.reply_to and amqp_message.reply_to:
                        await self._send_reply(message, result)
                    
                    print(f"📥 Processed message {message.id} from queue {queue_name}")
                    
                except Exception as e:
                    print(f"❌ Error processing message: {e}")
                    # Rejeitar mensagem para retry ou dead letter
                    await amqp_message.reject(requeue=False)
        
        await queue.consume(message_handler)
        print(f"📋 Subscribed to queue {queue_name} for message type {message_type}")
    
    async def _send_reply(self, original_message: Message, result: Any):
        """Enviar resposta para mensagem com reply_to"""
        
        reply_message = Message(
            id=f"reply-{original_message.id}",
            type=f"{original_message.type}.reply",
            payload={"result": result, "original_id": original_message.id},
            priority=MessagePriority.NORMAL,
            timestamp=datetime.now(),
            correlation_id=original_message.correlation_id
        )
        
        await self.publish_message(reply_message, exchange="")

# Instância global
message_bus = MessageBus()

# Decorator para handlers assíncronos
def message_handler(queue_name: str, message_type: str, exchange: str = ""):
    """Decorator para registrar handlers de mensagens"""
    
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Registrar handler
            asyncio.create_task(
                message_bus.subscribe(queue_name, message_type, func, exchange)
            )
            return func
        
        return wrapper
    
    return decorator
```

### 3. Event Sourcing

```python
# backend/app/core/event_sourcing.py
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import json
import uuid
from app.repositories.event_store import EventStoreRepository

class EventType(Enum):
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    CHAT_MESSAGE_SENT = "chat.message.sent"
    CHAT_MESSAGE_RECEIVED = "chat.message.received"
    KNOWLEDGE_ITEM_ADDED = "knowledge.item.added"
    KNOWLEDGE_ITEM_UPDATED = "knowledge.item.updated"
    LLM_REQUEST_MADE = "llm.request.made"
    LLM_RESPONSE_RECEIVED = "llm.response.received"

@dataclass
class DomainEvent:
    id: str
    type: EventType
    aggregate_id: str
    aggregate_type: str
    payload: Dict
    metadata: Dict
    timestamp: datetime
    version: int
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None

class EventStore:
    """Event Store para Event Sourcing"""
    
    def __init__(self):
        self.event_store_repo = EventStoreRepository()
        self.event_handlers: Dict[EventType, List[callable]] = {}
    
    async def store_event(self, event: DomainEvent) -> bool:
        """Armazenar evento no event store"""
        
        try:
            # Validar evento
            if not self._validate_event(event):
                return False
            
            # Armazenar evento
            success = await self.event_store_repo.store(event)
            
            if success:
                # Publicar evento para handlers
                await self._publish_event(event)
                
                # Atualizar projeções
                await self._update_projections(event)
            
            return success
            
        except Exception as e:
            print(f"❌ Error storing event: {e}")
            return False
    
    async def get_events(self, aggregate_id: str, 
                        from_version: int = 0) -> List[DomainEvent]:
        """Recuperar eventos de um agregado específico"""
        
        return await self.event_store_repo.get_by_aggregate(
            aggregate_id=aggregate_id,
            from_version=from_version
        )
    
    async def get_event_stream(self, aggregate_id: str) -> 'EventStream':
        """Obter stream de eventos para reconstruir agregado"""
        
        events = await self.get_events(aggregate_id)
        return EventStream(events)
    
    def register_event_handler(self, event_type: EventType, handler: callable):
        """Registrar handler para tipo de evento"""
        
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        
        self.event_handlers[event_type].append(handler)
    
    async def _publish_event(self, event: DomainEvent):
        """Publicar evento para handlers registrados"""
        
        handlers = self.event_handlers.get(event.type, [])
        
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                print(f"❌ Error in event handler for {event.type}: {e}")
                # Não falhar o store do evento por causa de handler
    
    async def _update_projections(self, event: DomainEvent):
        """Atualizar projeções baseadas no evento"""
        
        # Implementar atualização de projeções específicas
        # por tipo de evento
        pass
    
    def _validate_event(self, event: DomainEvent) -> bool:
        """Validar estrutura do evento"""
        
        required_fields = ["id", "type", "aggregate_id", "payload", "timestamp"]
        
        for field in required_fields:
            if not getattr(event, field):
                return False
        
        return True

class EventStream:
    """Stream de eventos para reconstruir estado de agregado"""
    
    def __init__(self, events: List[DomainEvent]):
        self.events = sorted(events, key=lambda e: (e.timestamp, e.version))
        self.current_version = events[-1].version if events else 0
    
    def apply_to(self, aggregate: Any) -> Any:
        """Aplicar todos os eventos ao agregado"""
        
        for event in self.events:
            aggregate.apply_event(event)
        
        return aggregate
    
    def get_events_by_type(self, event_type: EventType) -> List[DomainEvent]:
        """Filtrar eventos por tipo"""
        return [e for e in self.events if e.type == event_type]

# Helper functions
def create_domain_event(event_type: EventType, aggregate_id: str, 
                       aggregate_type: str, payload: Dict,
                       user_id: Optional[str] = None,
                       correlation_id: Optional[str] = None,
                       causation_id: Optional[str] = None) -> DomainEvent:
    """Factory function para criar eventos de domínio"""
    
    return DomainEvent(
        id=str(uuid.uuid4()),
        type=event_type,
        aggregate_id=aggregate_id,
        aggregate_type=aggregate_type,
        payload=payload,
        metadata={"source": "janus-api", "version": "1.0"},
        timestamp=datetime.now(),
        version=1,  # Será atualizado pelo repositório
        user_id=user_id,
        correlation_id=correlation_id or str(uuid.uuid4()),
        causation_id=causation_id
    )

# Instância global
event_store = EventStore()
```

## Monitoramento e Observabilidade

### Métricas de Serviços

```python
# backend/app/core/service_metrics.py
from prometheus_client import Counter, Histogram, Gauge, Info
import time
from functools import wraps
from typing import Callable, Any

# Métricas de serviço
SERVICE_REQUESTS_TOTAL = Counter(
    'janus_service_requests_total',
    'Total number of service requests',
    ['service', 'method', 'status']
)

SERVICE_REQUEST_DURATION = Histogram(
    'janus_service_request_duration_seconds',
    'Service request duration in seconds',
    ['service', 'method']
)

SERVICE_ACTIVE_CONNECTIONS = Gauge(
    'janus_service_active_connections',
    'Number of active connections to service',
    ['service']
)

SERVICE_HEALTH_STATUS = Gauge(
    'janus_service_health_status',
    'Service health status (1=healthy, 0=unhealthy)',
    ['service']
)

SERVICE_INFO = Info(
    'janus_service_info',
    'Service information',
    ['service', 'version', 'environment']
)

def monitor_service(service_name: str):
    """Decorator para monitorar chamadas de serviço"""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            status = "success"
            
            try:
                result = await func(*args, **kwargs)
                return result
                
            except Exception as e:
                status = "error"
                raise e
                
            finally:
                duration = time.time() - start_time
                
                # Registrar métricas
                SERVICE_REQUESTS_TOTAL.labels(
                    service=service_name,
                    method=func.__name__,
                    status=status
                ).inc()
                
                SERVICE_REQUEST_DURATION.labels(
                    service=service_name,
                    method=func.__name__
                ).observe(duration)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            status = "success"
            
            try:
                result = func(*args, **kwargs)
                return result
                
            except Exception as e:
                status = "error"
                raise e
                
            finally:
                duration = time.time() - start_time
                
                # Registrar métricas
                SERVICE_REQUESTS_TOTAL.labels(
                    service=service_name,
                    method=func.__name__,
                    status=status
                ).inc()
                
                SERVICE_REQUEST_DURATION.labels(
                    service=service_name,
                    method=func.__name__
                ).observe(duration)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator

def register_service_info(service_name: str, version: str, environment: str):
    """Registrar informações do serviço"""
    
    SERVICE_INFO.labels(
        service=service_name,
        version=version,
        environment=environment
    ).info({
        'service': service_name,
        'version': version,
        'environment': environment
    })

def update_service_health(service_name: str, is_healthy: bool):
    """Atualizar status de saúde do serviço"""
    
    SERVICE_HEALTH_STATUS.labels(service=service_name).set(1 if is_healthy else 0)
```

### Health Checks Detalhados

```python
# backend/app/core/health_checks.py
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import asyncio
import aiohttp
from app.core.config import settings

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class HealthCheckResult:
    name: str
    status: HealthStatus
    message: str
    response_time: float
    timestamp: datetime
    metadata: Optional[Dict] = None

@dataclass
class ServiceHealth:
    service_name: str
    overall_status: HealthStatus
    checks: List[HealthCheckResult]
    response_time: float
    timestamp: datetime

class BaseHealthCheck:
    """Base class para health checks"""
    
    def __init__(self, name: str, timeout: int = 10):
        self.name = name
        self.timeout = timeout
    
    async def check(self) -> HealthCheckResult:
        """Executar health check"""
        raise NotImplementedError

class DatabaseHealthCheck(BaseHealthCheck):
    """Health check para banco de dados"""
    
    def __init__(self, db_type: str, connection_string: str):
        super().__init__(f"{db_type}_database")
        self.db_type = db_type
        self.connection_string = connection_string
    
    async def check(self) -> HealthCheckResult:
        start_time = datetime.now()
        
        try:
            # Testar conexão com banco de dados
            if self.db_type == "postgresql":
                await self._check_postgres_connection()
            elif self.db_type == "neo4j":
                await self._check_neo4j_connection()
            elif self.db_type == "redis":
                await self._check_redis_connection()
            
            response_time = (datetime.now() - start_time).total_seconds()
            
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.HEALTHY,
                message=f"{self.db_type} database is responsive",
                response_time=response_time,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds()
            
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"{self.db_type} database connection failed: {str(e)}",
                response_time=response_time,
                timestamp=datetime.now(),
                metadata={"error": str(e)}
            )
    
    async def _check_postgres_connection(self):
        """Verificar conexão PostgreSQL"""
        from app.core.database import get_db_session
        
        async with get_db_session() as session:
            result = await session.execute("SELECT 1")
            await result.scalar()
    
    async def _check_neo4j_connection(self):
        """Verificar conexão Neo4j"""
        from app.core.database import get_neo4j_driver
        
        driver = get_neo4j_driver()
        await driver.verify_connectivity()
    
    async def _check_redis_connection(self):
        """Verificar conexão Redis"""
        from app.core.cache import get_redis_client
        
        redis_client = get_redis_client()
        await redis_client.ping()

class ExternalServiceHealthCheck(BaseHealthCheck):
    """Health check para serviços externos"""
    
    def __init__(self, service_name: str, health_url: str):
        super().__init__(f"external_{service_name}")
        self.service_name = service_name
        self.health_url = health_url
    
    async def check(self) -> HealthCheckResult:
        start_time = datetime.now()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.health_url, timeout=self.timeout) as response:
                    response_time = (datetime.now() - start_time).total_seconds()
                    
                    if response.status == 200:
                        health_data = await response.json()
                        
                        if health_data.get("status") == "healthy":
                            status = HealthStatus.HEALTHY
                            message = f"{self.service_name} is healthy"
                        elif health_data.get("status") == "degraded":
                            status = HealthStatus.DEGRADED
                            message = f"{self.service_name} is degraded"
                        else:
                            status = HealthStatus.UNHEALTHY
                            message = f"{self.service_name} is unhealthy"
                        
                        return HealthCheckResult(
                            name=self.name,
                            status=status,
                            message=message,
                            response_time=response_time,
                            timestamp=datetime.now(),
                            metadata=health_data
                        )
                    else:
                        return HealthCheckResult(
                            name=self.name,
                            status=HealthStatus.UNHEALTHY,
                            message=f"{self.service_name} returned status {response.status}",
                            response_time=response_time,
                            timestamp=datetime.now()
                        )
                        
        except asyncio.TimeoutError:
            response_time = (datetime.now() - start_time).total_seconds()
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"{self.service_name} timed out after {self.timeout}s",
                response_time=response_time,
                timestamp=datetime.now()
            )
        
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds()
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"{self.service_name} health check failed: {str(e)}",
                response_time=response_time,
                timestamp=datetime.now(),
                metadata={"error": str(e)}
            )

class HealthCheckManager:
    """Gerenciador de health checks para todos os serviços"""
    
    def __init__(self):
        self.health_checks: List[BaseHealthCheck] = []
        self.health_status_cache: Optional[ServiceHealth] = None
        self.cache_expiry = 30  # segundos
        self.last_check_time: Optional[datetime] = None
        
    def register_health_check(self, health_check: BaseHealthCheck):
        """Registrar novo health check"""
        self.health_checks.append(health_check)
    
    async def get_health_status(self, force_refresh: bool = False) -> ServiceHealth:
        """Obter status de saúde completo do serviço"""
        
        # Verificar cache
        if (not force_refresh and 
            self.health_status_cache and 
            self.last_check_time and 
            (datetime.now() - self.last_check_time).seconds < self.cache_expiry):
            return self.health_status_cache
        
        # Executar todos os health checks
        start_time = datetime.now()
        
        check_results = await asyncio.gather(
            *[hc.check() for hc in self.health_checks],
            return_exceptions=True
        )
        
        # Filtrar resultados válidos
        valid_results = [r for r in check_results if isinstance(r, HealthCheckResult)]
        
        # Determinar status geral
        overall_status = self._determine_overall_status(valid_results)
        
        response_time = (datetime.now() - start_time).total_seconds()
        
        health_status = ServiceHealth(
            service_name="janus-api",
            overall_status=overall_status,
            checks=valid_results,
            response_time=response_time,
            timestamp=datetime.now()
        )
        
        # Atualizar cache
        self.health_status_cache = health_status
        self.last_check_time = datetime.now()
        
        return health_status
    
    def _determine_overall_status(self, check_results: List[HealthCheckResult]) -> HealthStatus:
        """Determinar status geral baseado nos resultados individuais"""
        
        if not check_results:
            return HealthStatus.UNKNOWN
        
        unhealthy_count = sum(1 for r in check_results if r.status == HealthStatus.UNHEALTHY)
        degraded_count = sum(1 for r in check_results if r.status == HealthStatus.DEGRADED)
        
        total_checks = len(check_results)
        
        # Se mais de 50% dos checks estão unhealthy, sistema está unhealthy
        if unhealthy_count > total_checks * 0.5:
            return HealthStatus.UNHEALTHY
        
        # Se há unhealthy ou degraded, sistema está degraded
        if unhealthy_count > 0 or degraded_count > 0:
            return HealthStatus.DEGRADED
        
        # Se todos são healthy, sistema está healthy
        return HealthStatus.HEALTHY
    
    async def get_detailed_health_report(self) -> Dict:
        """Obter relatório detalhado de saúde"""
        
        health_status = await self.get_health_status()
        
        # Análise adicional
        slow_checks = [c for c in health_status.checks if c.response_time > 5.0]
        failing_checks = [c for c in health_status.checks if c.status != HealthStatus.HEALTHY]
        
        return {
            "service_name": health_status.service_name,
            "overall_status": health_status.overall_status.value,
            "response_time": health_status.response_time,
            "timestamp": health_status.timestamp.isoformat(),
            "summary": {
                "total_checks": len(health_status.checks),
                "healthy_checks": len([c for c in health_status.checks if c.status == HealthStatus.HEALTHY]),
                "degraded_checks": len([c for c in health_status.checks if c.status == HealthStatus.DEGRADED]),
                "unhealthy_checks": len([c for c in health_status.checks if c.status == HealthStatus.UNHEALTHY]),
                "slow_checks": len(slow_checks),
                "failing_checks": len(failing_checks)
            },
            "checks": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "message": c.message,
                    "response_time": c.response_time,
                    "metadata": c.metadata
                }
                for c in health_status.checks
            ],
            "recommendations": self._generate_health_recommendations(health_status)
        }
    
    def _generate_health_recommendations(self, health_status: ServiceHealth) -> List[str]:
        """Gerar recomendações baseadas no status de saúde"""
        
        recommendations = []
        
        # Verificar checks lento
        slow_checks = [c for c in health_status.checks if c.response_time > 5.0]
        if slow_checks:
            recommendations.append(
                f"Consider investigating slow health checks: {', '.join(c.name for c in slow_checks)}"
            )
        
        # Verificar checks falhando
        failing_checks = [c for c in health_status.checks if c.status != HealthStatus.HEALTHY]
        if failing_checks:
            recommendations.append(
                f"Address failing health checks: {', '.join(c.name for c in failing_checks)}"
            )
        
        # Verificar status geral
        if health_status.overall_status == HealthStatus.UNHEALTHY:
            recommendations.append(
                "System is unhealthy. Immediate attention required."
            )
        elif health_status.overall_status == HealthStatus.DEGRADED:
            recommendations.append(
                "System is degraded. Monitor closely and address issues."
            )
        
        return recommendations

# Instância global
health_check_manager = HealthCheckManager()

# Registrar health checks padrão
health_check_manager.register_health_check(DatabaseHealthCheck("postgresql", settings.DATABASE_URL))
health_check_manager.register_health_check(DatabaseHealthCheck("neo4j", settings.NEO4J_URI))
health_check_manager.register_health_check(DatabaseHealthCheck("redis", settings.REDIS_URL))
```

## Deployment e Escalabilidade

### Configuração Kubernetes

```yaml
# k8s/chat-service-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: janus-chat-service
  namespace: janus
  labels:
    app: janus-chat-service
    version: v1.0.0
spec:
  replicas: 3
  selector:
    matchLabels:
      app: janus-chat-service
  template:
    metadata:
      labels:
        app: janus-chat-service
        version: v1.0.0
    spec:
      containers:
      - name: chat-service
        image: janus/chat-service:v1.0.0
        ports:
        - containerPort: 8000
          name: http
        env:
        - name: SERVICE_NAME
          value: "chat-service"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: janus-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: janus-secrets
              key: redis-url
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: 2000m
            memory: 2Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        startupProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 30
---
apiVersion: v1
kind: Service
metadata:
  name: janus-chat-service
  namespace: janus
spec:
  selector:
    app: janus-chat-service
  ports:
  - port: 80
    targetPort: 8000
    name: http
  type: ClusterIP
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: janus-chat-service-hpa
  namespace: janus
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: janus-chat-service
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
```

### Service Mesh (Istio)

```yaml
# k8s/istio-service-mesh.yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: janus-chat-service
  namespace: janus
spec:
  hosts:
  - chat-service.janus.svc.cluster.local
  http:
  - match:
    - headers:
        x-version:
          exact: v2
    route:
    - destination:
        host: chat-service.janus.svc.cluster.local
        subset: v2
      weight: 100
  - route:
    - destination:
        host: chat-service.janus.svc.cluster.local
        subset: v1
      weight: 100
---
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: janus-chat-service
  namespace: janus
spec:
  host: chat-service.janus.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
    loadBalancer:
      simple: LEAST_REQUEST
    outlierDetection:
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
  subsets:
  - name: v1
    labels:
      version: v1.0.0
  - name: v2
    labels:
      version: v2.0.0
---
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: janus-chat-service
  namespace: janus
spec:
  selector:
    matchLabels:
      app: janus-chat-service
  mtls:
    mode: STRICT
---
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: janus-chat-service
  namespace: janus
spec:
  selector:
    matchLabels:
      app: janus-chat-service
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/janus/sa/janus-api"]
  - to:
    - operation:
        methods: ["GET", "POST", "PUT", "DELETE"]
        paths: ["/api/*", "/health", "/metrics"]
```

## Conclusão

Esta arquitetura de microserviços do Janus foi projetada para:

1. **Escalabilidade**: Cada serviço pode escalar independentemente
2. **Resiliência**: Circuit breakers, retries e fallback mechanisms
3. **Observabilidade**: Métricas, tracing e logging centralizados
4. **Manutenibilidade**: Serviços bem definidos e desacoplados
5. **Performance**: Caching, load balancing e otimizações específicas

Os serviços são independentes mas se comunicam de forma eficiente através de APIs bem definidas, garantindo que o sistema como um todo seja robusto e performático.