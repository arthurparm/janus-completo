# Janus Performance Tuning Guide

## Overview

This guide provides comprehensive performance optimization strategies for the Janus multi-agent AI system. It covers database optimization, caching strategies, LLM performance tuning, frontend optimization, and monitoring best practices.

## Table of Contents

1. [Performance Metrics and KPIs](#performance-metrics-and-kpis)
2. [Database Performance Optimization](#database-performance-optimization)
3. [Caching Strategies](#caching-strategies)
4. [LLM Performance Tuning](#llm-performance-tuning)
5. [Frontend Angular Optimization](#frontend-angular-optimization)
6. [Backend FastAPI Optimization](#backend-fastapi-optimization)
7. [Infrastructure Scaling](#infrastructure-scaling)
8. [Monitoring and Alerting](#monitoring-and-alerting)
9. [Performance Testing](#performance-testing)
10. [Troubleshooting Performance Issues](#troubleshooting-performance-issues)

---

## Performance Metrics and KPIs

### Key Performance Indicators

#### Response Time Metrics
- **API Response Time**: < 200ms for simple queries, < 1000ms for complex operations
- **Chat Message Response Time**: < 2s for first token, < 30s for complete response
- **Database Query Time**: < 100ms for simple queries, < 500ms for complex joins
- **Frontend Load Time**: < 3s for initial page load, < 1s for subsequent navigation

#### Throughput Metrics
- **API Requests per Second**: Target 1000+ RPS per instance
- **Concurrent Chat Sessions**: Support 100+ simultaneous conversations
- **Database Transactions**: Handle 500+ TPS sustained load
- **LLM Token Generation**: 50+ tokens per second for streaming responses

#### Resource Utilization
- **CPU Usage**: < 70% average, < 85% peak
- **Memory Usage**: < 80% of available RAM
- **Disk I/O**: < 50% utilization during peak hours
- **Network Bandwidth**: < 70% of available capacity

### Performance Baselines

#### Current Baseline Measurements
```bash
# API Response Time Baseline
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/api/v1/system/status

# Database Performance Baseline
docker exec postgres psql -c "
  SELECT 
    schemaname,
    tablename,
    seq_scan,
    seq_tup_read,
    idx_scan,
    idx_tup_fetch
  FROM pg_stat_user_tables 
  ORDER BY seq_scan DESC
"

# Memory Usage Baseline
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

---

## Database Performance Optimization

### PostgreSQL Configuration

#### Memory Settings
```sql
-- Check current memory settings
SELECT name, setting, unit FROM pg_settings WHERE name LIKE '%memory%';

-- Optimal settings for Janus workload
ALTER SYSTEM SET shared_buffers = '256MB';        -- 25% of RAM
ALTER SYSTEM SET effective_cache_size = '1GB';   -- 50% of RAM
ALTER SYSTEM SET work_mem = '16MB';              -- For complex queries
ALTER SYSTEM SET maintenance_work_mem = '64MB';  -- For maintenance operations
```

#### Connection Pooling
```python
# Optimized connection pool configuration
DATABASE_CONFIG = {
    'pool_size': 20,           # Maximum connections in pool
    'max_overflow': 10,        # Maximum overflow connections
    'pool_timeout': 30,      # Timeout for getting connection
    'pool_recycle': 3600,     # Connection recycle time
    'pool_pre_ping': True,    # Verify connections before use
    'echo': False,            # Disable SQL logging in production
}
```

#### Query Optimization
```sql
-- Create indexes for common queries
CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_created_at ON conversations(created_at DESC);
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_timestamp ON messages(timestamp DESC);

-- Composite indexes for complex queries
CREATE INDEX idx_audit_user_action ON audit_logs(user_id, action_type, timestamp DESC);
CREATE INDEX idx_memory_user_class ON memories(user_id, memory_class, ts_ms DESC);

-- Partial indexes for specific conditions
CREATE INDEX idx_active_users ON users(email) WHERE is_active = true;
CREATE INDEX idx_recent_conversations ON conversations(updated_at) WHERE updated_at > NOW() - INTERVAL '30 days';
```

### Query Performance Analysis

#### Identify Slow Queries
```sql
-- Enable pg_stat_statements
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Find slowest queries
SELECT 
  query,
  calls,
  total_time,
  mean_time,
  rows,
  100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
FROM pg_stat_statements
WHERE mean_time > 100
ORDER BY mean_time DESC
LIMIT 20;
```

#### Query Execution Plan Analysis
```sql
-- Analyze specific query execution
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT c.*, COUNT(m.id) as message_count
FROM conversations c
LEFT JOIN messages m ON c.id = m.conversation_id
WHERE c.user_id = 'user123'
AND c.created_at > NOW() - INTERVAL '7 days'
GROUP BY c.id
ORDER BY c.updated_at DESC
LIMIT 10;
```

#### Automated Query Optimization
```python
class QueryOptimizer:
    def __init__(self, db_session):
        self.db = db_session
        
    async def optimize_conversation_queries(self, user_id: str, limit: int = 10):
        # Use CTE for better performance
        query = """
        WITH recent_conversations AS (
            SELECT id, title, created_at, updated_at
            FROM conversations
            WHERE user_id = :user_id
            AND created_at > NOW() - INTERVAL '30 days'
            ORDER BY updated_at DESC
            LIMIT :limit
        )
        SELECT rc.*, COUNT(m.id) as message_count
        FROM recent_conversations rc
        LEFT JOIN messages m ON rc.id = m.conversation_id
        GROUP BY rc.id, rc.title, rc.created_at, rc.updated_at
        ORDER BY rc.updated_at DESC
        """
        
        result = await self.db.execute(
            text(query),
            {"user_id": user_id, "limit": limit}
        )
        return result.fetchall()
        
    async def optimize_memory_queries(self, user_id: str, query: str):
        # Use vector similarity with proper indexing
        query_sql = """
        SELECT content, metadata, ts_ms, similarity
        FROM memories
        WHERE user_id = :user_id
        AND memory_class = 'semantic'
        ORDER BY embedding <=> query_embedding(:query)
        LIMIT 10
        """
        
        result = await self.db.execute(
            text(query_sql),
            {"user_id": user_id, "query": query}
        )
        return result.fetchall()
```

---

## Caching Strategies

### Multi-Level Caching Architecture

#### Redis Configuration
```python
# Optimized Redis configuration
REDIS_CONFIG = {
    'host': 'redis',
    'port': 6379,
    'db': 0,
    'decode_responses': True,
    'socket_keepalive': True,
    'socket_keepalive_options': {},
    'health_check_interval': 30,
    'retry_on_timeout': True,
    'retry_on_error': [redis.ConnectionError, redis.TimeoutError],
    'max_connections': 50,
}

# Cache TTL settings
CACHE_TTL = {
    'user_session': 3600,      # 1 hour
    'conversation_list': 300,   # 5 minutes
    'user_preferences': 1800,     # 30 minutes
    'api_response': 60,         # 1 minute
    'llm_response': 1800,       # 30 minutes
    'system_status': 30,        # 30 seconds
}
```

#### Cache Warming Strategy
```python
class CacheWarmer:
    def __init__(self, redis_client, db_session):
        self.redis = redis_client
        self.db = db_session
        
    async def warm_user_cache(self, user_id: str):
        # Preload frequently accessed data
        user_data = await self.get_user_data(user_id)
        await self.redis.hset(f"user:{user_id}", mapping=user_data)
        
        # Preload recent conversations
        conversations = await self.get_recent_conversations(user_id)
        await self.redis.setex(
            f"conversations:{user_id}",
            CACHE_TTL['conversation_list'],
            json.dumps(conversations)
        )
        
        # Preload user preferences
        preferences = await self.get_user_preferences(user_id)
        await self.redis.setex(
            f"preferences:{user_id}",
            CACHE_TTL['user_preferences'],
            json.dumps(preferences)
        )
        
    async def warm_system_cache(self):
        # Cache system status
        status = await self.get_system_status()
        await self.redis.setex(
            "system:status",
            CACHE_TTL['system_status'],
            json.dumps(status)
        )
        
        # Cache service health
        health = await self.get_service_health()
        await self.redis.setex(
            "system:health",
            CACHE_TTL['system_status'],
            json.dumps(health)
        )
```

#### Cache Invalidation Patterns
```python
class CacheInvalidator:
    def __init__(self, redis_client):
        self.redis = redis_client
        
    async def invalidate_user_cache(self, user_id: str):
        # Invalidate all user-related caches
        keys_to_delete = [
            f"user:{user_id}",
            f"conversations:{user_id}",
            f"preferences:{user_id}",
            f"session:{user_id}",
        ]
        
        deleted = await self.redis.delete(*keys_to_delete)
        logger.info(f"Invalidated {deleted} cache keys for user {user_id}")
        
    async def invalidate_conversation_cache(self, conversation_id: str):
        # Get conversation participants
        participants = await self.redis.smembers(f"conversation:{conversation_id}:participants")
        
        # Invalidate for all participants
        for user_id in participants:
            await self.redis.delete(f"conversations:{user_id}")
            
        # Invalidate conversation data
        await self.redis.delete(f"conversation:{conversation_id}")
        await self.redis.delete(f"messages:{conversation_id}")
```

### Application-Level Caching

#### Response Caching
```python
from functools import lru_cache
from typing import Optional

class ResponseCache:
    def __init__(self, redis_client):
        self.redis = redis_client
        
    async def cache_llm_response(self, cache_key: str, response: Dict, ttl: int = 1800):
        # Cache successful LLM responses
        if response.get('status') == 'success':
            await self.redis.setex(
                f"llm:response:{cache_key}",
                ttl,
                json.dumps(response)
            )
            
    async def get_cached_llm_response(self, cache_key: str) -> Optional[Dict]:
        cached = await self.redis.get(f"llm:response:{cache_key}")
        if cached:
            return json.loads(cached)
        return None
        
    def generate_cache_key(self, prompt: str, model: str, parameters: Dict) -> str:
        # Generate deterministic cache key
        content = f"{prompt}:{model}:{json.dumps(parameters, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()
```

#### Database Query Result Caching
```python
class QueryCache:
    def __init__(self, redis_client):
        self.redis = redis_client
        
    async def cached_query(self, query: str, params: Dict, ttl: int = 300) -> List[Dict]:
        # Generate cache key
        cache_key = f"query:{hashlib.md5(f'{query}:{json.dumps(params)}'.encode()).hexdigest()}"
        
        # Try to get from cache
        cached_result = await self.redis.get(cache_key)
        if cached_result:
            return json.loads(cached_result)
            
        # Execute query and cache result
        result = await self.execute_query(query, params)
        await self.redis.setex(cache_key, ttl, json.dumps(result))
        
        return result
        
    async def invalidate_query_cache(self, pattern: str):
        # Invalidate cache entries matching pattern
        keys = await self.redis.keys(f"query:{pattern}")
        if keys:
            await self.redis.delete(*keys)
```

---

## LLM Performance Tuning

### Model Selection and Optimization

#### Intelligent Model Routing
```python
class LLMRouter:
    def __init__(self):
        self.models = {
            'fast_and_cheap': {
                'provider': 'openai',
                'model': 'gpt-3.5-turbo',
                'max_tokens': 1000,
                'cost_per_1k_tokens': 0.002,
                'avg_response_time': 0.5,
            },
            'balanced': {
                'provider': 'openai',
                'model': 'gpt-4-turbo',
                'max_tokens': 2000,
                'cost_per_1k_tokens': 0.01,
                'avg_response_time': 1.5,
            },
            'high_quality': {
                'provider': 'openai',
                'model': 'gpt-4',
                'max_tokens': 4000,
                'cost_per_1k_tokens': 0.03,
                'avg_response_time': 3.0,
            },
            'reasoning': {
                'provider': 'openai',
                'model': 'gpt-4-turbo',
                'max_tokens': 4000,
                'cost_per_1k_tokens': 0.01,
                'avg_response_time': 2.0,
            }
        }
        
    def select_model(self, query: str, context: Dict, user_preferences: Dict) -> str:
        # Analyze query complexity
        complexity_score = self.assess_complexity(query)
        
        # Consider user preferences and constraints
        priority = user_preferences.get('priority', 'balanced')
        budget_limit = user_preferences.get('budget_limit')
        time_constraint = user_preferences.get('time_constraint')
        
        # Select appropriate model
        if complexity_score < 0.3 and priority == 'fast_and_cheap':
            return 'fast_and_cheap'
        elif complexity_score > 0.8 or priority == 'high_quality':
            return 'high_quality'
        elif 'reasoning' in query.lower() or priority == 'reasoning':
            return 'reasoning'
        else:
            return 'balanced'
            
    def assess_complexity(self, query: str) -> float:
        # Simple complexity assessment
        factors = {
            'length': min(len(query) / 1000, 1.0),
            'technical_terms': len(re.findall(r'\b(code|algorithm|architecture|optimization)\b', query.lower())) * 0.1,
            'reasoning_indicators': len(re.findall(r'\b(why|how|explain|analyze|compare)\b', query.lower())) * 0.05,
            'multi_step': len(re.findall(r'\b(step|first|then|finally)\b', query.lower())) * 0.1,
        }
        return min(sum(factors.values()), 1.0)
```

#### Token Usage Optimization
```python
class TokenOptimizer:
    def __init__(self):
        self.token_limits = {
            'gpt-3.5-turbo': 4096,
            'gpt-4-turbo': 8192,
            'gpt-4': 8192,
        }
        
    def optimize_prompt(self, prompt: str, context: str, max_tokens: int) -> str:
        # Remove redundant information
        optimized = self.remove_redundancies(prompt)
        
        # Compress context if too long
        if len(context) > max_tokens * 0.3:
            context = self.compress_context(context, int(max_tokens * 0.3))
            
        # Structure prompt efficiently
        optimized_prompt = f"""
Context: {context}

Question: {optimized}

Please provide a concise and focused response.
"""
        
        return optimized_prompt.strip()
        
    def compress_context(self, context: str, max_tokens: int) -> str:
        # Simple compression - remove extra whitespace and redundant phrases
        compressed = re.sub(r'\s+', ' ', context)
        compressed = re.sub(r'\b(in other words|that is to say|to put it simply)\b', '', compressed)
        
        # If still too long, truncate with ellipsis
        if len(compressed.split()) > max_tokens * 0.75:  # Rough token estimation
            words = compressed.split()
            compressed = ' '.join(words[:int(max_tokens * 0.75)]) + '...'
            
        return compressed
        
    def remove_redundancies(self, text: str) -> str:
        # Remove repeated phrases
        sentences = text.split('.')
        unique_sentences = []
        seen = set()
        
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and sentence not in seen:
                seen.add(sentence)
                unique_sentences.append(sentence)
                
        return '. '.join(unique_sentences)
```

### Streaming and Batch Processing

#### Optimized Streaming Implementation
```python
class StreamingLLMService:
    def __init__(self):
        self.chunk_size = 50  # tokens per chunk
        self.max_chunks = 100  # maximum chunks per response
        
    async def stream_response(self, prompt: str, model: str, parameters: Dict) -> AsyncGenerator[str, None]:
        # Pre-process prompt for optimal streaming
        optimized_prompt = self.optimize_for_streaming(prompt)
        
        # Start streaming
        async for chunk in self.llm_client.stream(optimized_prompt, model, parameters):
            # Process chunk for better UX
            processed_chunk = self.process_stream_chunk(chunk)
            yield processed_chunk
            
            # Implement backpressure if needed
            if self.should_slow_down():
                await asyncio.sleep(0.1)
                
    def optimize_for_streaming(self, prompt: str) -> str:
        # Ensure prompt encourages structured response
        if not any(marker in prompt.lower() for marker in ['format', 'structure', 'list']):
            prompt += "\n\nPlease provide your response in a clear, structured format."
            
        return prompt
        
    def process_stream_chunk(self, chunk: str) -> str:
        # Remove awkward mid-word breaks
        chunk = re.sub(r'\w+$', '', chunk)  # Remove incomplete words
        
        # Add appropriate spacing
        if chunk.startswith(('.,;:!?')):
            chunk = ' ' + chunk
            
        return chunk
        
    def should_slow_down(self) -> bool:
        # Simple rate limiting based on current load
        return self.current_rps > 100  # Adjust threshold as needed
```

#### Batch Processing for Non-Real-time Tasks
```python
class BatchLLMProcessor:
    def __init__(self):
        self.batch_size = 10
        self.processing_interval = 30  # seconds
        self.pending_requests = []
        
    async def add_request(self, request: Dict) -> str:
        # Add request to batch queue
        request_id = str(uuid.uuid4())
        self.pending_requests.append({
            'id': request_id,
            'request': request,
            'timestamp': datetime.now()
        })
        
        # Process batch if size reached
        if len(self.pending_requests) >= self.batch_size:
            await self.process_batch()
            
        return request_id
        
    async def process_batch(self):
        if not self.pending_requests:
            return
            
        # Group similar requests
        grouped_requests = self.group_similar_requests(self.pending_requests)
        
        # Process each group
        for group in grouped_requests:
            await self.process_group(group)
            
        # Clear processed requests
        self.pending_requests = []
        
    def group_similar_requests(self, requests: List[Dict]) -> List[List[Dict]]:
        # Simple grouping by request type and model
        groups = defaultdict(list)
        for req in requests:
            key = f"{req['request'].get('type')}:{req['request'].get('model')}"
            groups[key].append(req)
            
        return list(groups.values())
        
    async def process_group(self, group: List[Dict]):
        # Process group efficiently
        if len(group) == 1:
            # Single request - process normally
            await self.process_single(group[0])
        else:
            # Multiple requests - batch process
            await self.process_multiple(group)
```

---

## Frontend Angular Optimization

### Bundle Size Optimization

#### Tree Shaking and Code Splitting
```typescript
// app-routing.module.ts
const routes: Routes = [
  {
    path: 'chat',
    loadChildren: () => import('./chat/chat.module').then(m => m.ChatModule)
  },
  {
    path: 'admin',
    loadChildren: () => import('./admin/admin.module').then(m => m.AdminModule),
    canLoad: [AuthGuard]
  },
  {
    path: 'settings',
    loadChildren: () => import('./settings/settings.module').then(m => m.SettingsModule)
  }
];

// Use standalone components for better tree shaking
@Component({
  selector: 'app-chat-message',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `...`
})
export class ChatMessageComponent {
  // Component logic
}
```

#### Lazy Loading Strategies
```typescript
// Preloading strategy for critical modules
export class PreloadCriticalModules implements PreloadingStrategy {
  preload(route: Route, load: () => Observable<any>): Observable<any> {
    return route.data && route.data['preload'] ? load() : of(null);
  }
}

// On-demand loading for heavy components
@Component({
  selector: 'app-chat-interface',
  template: `
    <div *ngIf="showAdvancedFeatures">
      <ng-container *ngComponentOutlet="advancedFeatures"></ng-container>
    </div>
  `
})
export class ChatInterfaceComponent {
  showAdvancedFeatures = false;
  advancedFeatures: Type<any>;

  async loadAdvancedFeatures() {
    const { AdvancedFeaturesComponent } = await import('./advanced-features.component');
    this.advancedFeatures = AdvancedFeaturesComponent;
    this.showAdvancedFeatures = true;
  }
}
```

#### Bundle Analysis and Optimization
```json
// angular.json optimization settings
{
  "configurations": {
    "production": {
      "optimization": true,
      "outputHashing": "all",
      "sourceMap": false,
      "namedChunks": false,
      "extractLicenses": true,
      "vendorChunk": false,
      "buildOptimizer": true,
      "budgets": [
        {
          "type": "bundle",
          "maximumWarning": "500kb",
          "maximumError": "1mb"
        },
        {
          "type": "initial",
          "maximumWarning": "2mb",
          "maximumError": "5mb"
        }
      ]
    }
  }
}
```

### Runtime Performance

#### Change Detection Optimization
```typescript
// Use OnPush change detection
@Component({
  selector: 'app-chat-message',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="message">
      {{ message.content }}
      <time>{{ message.timestamp | date:'short' }}</time>
    </div>
  `
})
export class ChatMessageComponent {
  @Input() message: Message;
  
  constructor(private cdr: ChangeDetectorRef) {}
  
  updateMessage(newContent: string) {
    this.message.content = newContent;
    this.cdr.markForCheck(); // Manually trigger change detection
  }
}

// Use trackBy for lists
@Component({
  template: `
    <div *ngFor="let message of messages; trackBy: trackByMessageId">
      {{ message.content }}
    </div>
  `
})
export class ChatListComponent {
  trackByMessageId(index: number, message: Message): string {
    return message.id;
  }
}
```

#### Virtual Scrolling for Large Lists
```typescript
// chat-list.component.ts
import { CdkVirtualScrollViewport } from '@angular/cdk/scrolling';

@Component({
  template: `
    <cdk-virtual-scroll-viewport 
      itemSize="60" 
      class="chat-viewport"
      (scrolledIndexChange)="onScroll($event)">
      <div *cdkVirtualFor="let message of messages; trackBy: trackByMessageId" 
           class="message-item">
        <app-chat-message [message]="message"></app-chat-message>
      </div>
    </cdk-virtual-scroll-viewport>
  `,
  styles: [`
    .chat-viewport {
      height: 100vh;
      width: 100%;
    }
    .message-item {
      height: 60px;
      display: flex;
      align-items: center;
    }
  `]
})
export class ChatListComponent {
  @ViewChild(CdkVirtualScrollViewport) viewport: CdkVirtualScrollViewport;
  
  messages: Message[] = [];
  
  onScroll(index: number) {
    // Load more messages when approaching the end
    if (index > this.messages.length - 20) {
      this.loadMoreMessages();
    }
  }
  
  loadMoreMessages() {
    // Implement pagination logic
  }
}
```

#### Web Workers for Heavy Computation
```typescript
// llm-processing.worker.ts
addEventListener('message', ({ data }) => {
  const result = processLLMResponse(data.response);
  postMessage(result);
});

function processLLMResponse(response: string): ProcessedResponse {
  // Heavy processing logic
  return {
    tokens: tokenize(response),
    entities: extractEntities(response),
    sentiment: analyzeSentiment(response),
    keywords: extractKeywords(response)
  };
}

// chat.service.ts
export class ChatService {
  private worker: Worker;
  
  constructor() {
    this.worker = new Worker('./llm-processing.worker.ts', { type: 'module' });
  }
  
  processLLMResponse(response: string): Observable<ProcessedResponse> {
    return new Observable(observer => {
      this.worker.postMessage({ response });
      
      this.worker.onmessage = (event) => {
        observer.next(event.data);
        observer.complete();
      };
    });
  }
}
```

### Network Optimization

#### HTTP Request Optimization
```typescript
// http-cache.interceptor.ts
@Injectable()
export class HttpCacheInterceptor implements HttpInterceptor {
  private cache = new Map<string, HttpResponse<any>>();
  
  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    if (req.method !== 'GET') {
      return next.handle(req);
    }
    
    const cachedResponse = this.cache.get(req.urlWithParams);
    if (cachedResponse) {
      return of(cachedResponse.clone());
    }
    
    return next.handle(req).pipe(
      tap(event => {
        if (event instanceof HttpResponse) {
          this.cache.set(req.urlWithParams, event);
        }
      })
    );
  }
}

// api.service.ts - Request deduplication
export class ApiService {
  private pendingRequests = new Map<string, Observable<any>>();
  
  get<T>(url: string, params?: any): Observable<T> {
    const cacheKey = `${url}${JSON.stringify(params)}`;
    
    if (this.pendingRequests.has(cacheKey)) {
      return this.pendingRequests.get(cacheKey)!;
    }
    
    const request = this.http.get<T>(url, { params }).pipe(
      shareReplay(1),
      finalize(() => this.pendingRequests.delete(cacheKey))
    );
    
    this.pendingRequests.set(cacheKey, request);
    return request;
  }
}
```

#### Progressive Loading
```typescript
// progressive-loader.service.ts
export class ProgressiveLoaderService {
  loadChatHistory(conversationId: string): Observable<Message[]> {
    return this.loadInitialMessages(conversationId).pipe(
      switchMap(initialMessages => {
        // Load initial messages immediately
        const messages$ = of(initialMessages);
        
        // Load older messages progressively
        const olderMessages$ = this.loadOlderMessagesProgressively(
          conversationId, 
          initialMessages[0]?.timestamp
        );
        
        return concat(messages$, olderMessages$);
      })
    );
  }
  
  private loadOlderMessagesProgressively(
    conversationId: string, 
    beforeTimestamp: Date
  ): Observable<Message[]> {
    return interval(2000).pipe(
      take(5), // Load 5 batches
      concatMap(batch => 
        this.api.getMessages(conversationId, { 
          before: beforeTimestamp, 
          limit: 20 
        })
      ),
      filter(messages => messages.length > 0)
    );
  }
}
```

---

## Backend FastAPI Optimization

### Application-Level Optimizations

#### Async Database Operations
```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Optimized database configuration
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
    future=True,
)

async_session = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# Dependency injection with connection pooling
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
```

#### Response Time Optimization
```python
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import time

app = FastAPI(
    title="Janus API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS optimization
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://janus-ai.com", "http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    max_age=86400,  # 24 hours
)

# Gzip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# ETags for caching
@app.middleware("http")
async def add_etag_header(request: Request, call_next):
    response = await call_next(request)
    if request.method == "GET" and response.status_code == 200:
        content = b"".join([chunk async for chunk in response.body_iterator])
        etag = hashlib.md5(content).hexdigest()
        response.headers["ETag"] = f'"{etag}"'
        response.body_iterator = iter([content])
    return response
```

#### Database Query Optimization
```python
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import joinedload, selectinload

class OptimizedChatService:
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def get_conversation_with_messages(self, conversation_id: str) -> Conversation:
        # Optimize query with proper joins and loading
        stmt = (
            select(Conversation)
            .options(
                selectinload(Conversation.messages),
                selectinload(Conversation.participants),
                joinedload(Conversation.created_by)
            )
            .where(Conversation.id == conversation_id)
        )
        
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
        
    async def get_user_conversations_optimized(self, user_id: str, limit: int = 10) -> List[Conversation]:
        # Use window functions for efficient pagination
        stmt = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
        )
        
        result = await self.db.execute(stmt)
        return result.scalars().all()
        
    async def batch_insert_messages(self, messages: List[Dict]) -> None:
        # Batch insert for better performance
        stmt = insert(Message).values(messages)
        await self.db.execute(stmt)
        await self.db.commit()
```

### API Endpoint Optimization

#### Pagination and Filtering
```python
from fastapi import Query, Depends
from typing import Optional, List
from pydantic import BaseModel

class PaginationParams(BaseModel):
    page: int = Query(1, ge=1, description="Page number")
    page_size: int = Query(20, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = Query(None, description="Sort field")
    sort_order: str = Query("desc", regex="^(asc|desc)$")
    
class ConversationFilter(BaseModel):
    user_id: Optional[str] = None
    status: Optional[str] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    search: Optional[str] = None

@app.get("/api/v1/conversations")
async def get_conversations(
    pagination: PaginationParams = Depends(),
    filters: ConversationFilter = Depends(),
    db: AsyncSession = Depends(get_db)
) -> PaginatedResponse[ConversationResponse]:
    # Build optimized query
    stmt = select(Conversation)
    
    # Apply filters efficiently
    if filters.user_id:
        stmt = stmt.where(Conversation.user_id == filters.user_id)
    if filters.status:
        stmt = stmt.where(Conversation.status == filters.status)
    if filters.created_after:
        stmt = stmt.where(Conversation.created_at >= filters.created_after)
    if filters.created_before:
        stmt = stmt.where(Conversation.created_at <= filters.created_before)
    if filters.search:
        stmt = stmt.where(Conversation.title.ilike(f"%{filters.search}%"))
        
    # Apply sorting
    if pagination.sort_by:
        sort_field = getattr(Conversation, pagination.sort_by)
        if pagination.sort_order == "desc":
            stmt = stmt.order_by(sort_field.desc())
        else:
            stmt = stmt.order_by(sort_field.asc())
    else:
        stmt = stmt.order_by(Conversation.updated_at.desc())
        
    # Apply pagination with count optimization
    offset = (pagination.page - 1) * pagination.page_size
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_count = await db.scalar(count_stmt)
    
    stmt = stmt.offset(offset).limit(pagination.page_size)
    result = await db.execute(stmt)
    conversations = result.scalars().all()
    
    return PaginatedResponse(
        items=conversations,
        total=total_count,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=math.ceil(total_count / pagination.page_size)
    )
```

#### Response Caching
```python
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache
from fastapi_cache.backends.redis import RedisBackend

# Configure Redis cache
redis = aioredis.from_url("redis://localhost:6379")
FastAPICache.init(RedisBackend(redis), prefix="janus-cache")

@app.get("/api/v1/system/status")
@cache(expire=30)  # Cache for 30 seconds
async def get_system_status() -> SystemStatusResponse:
    # Expensive operation cached
    return await calculate_system_status()

@app.get("/api/v1/conversations/{conversation_id}")
@cache(expire=300, namespace="conversations")  # Cache for 5 minutes
async def get_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db)
) -> ConversationResponse:
    service = ChatService(db)
    return await service.get_conversation(conversation_id)

# Cache invalidation
@app.post("/api/v1/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    message: MessageRequest,
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    service = ChatService(db)
    response = await service.send_message(conversation_id, message)
    
    # Invalidate conversation cache
    await FastAPICache.clear_namespace(f"conversations:{conversation_id}")
    
    return response
```

---

## Infrastructure Scaling

### Horizontal Scaling

#### Docker Swarm Configuration
```yaml
# docker-compose.scale.yml
version: '3.8'
services:
  janus-api:
    image: janus-api:latest
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
        failure_action: rollback
        order: start-first
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
      placement:
        constraints:
          - node.role == worker
        preferences:
          - spread: node.id
    environment:
      - WORKER_PROCESSES=4
      - WORKER_CONNECTIONS=1024
      - WORKER_TIMEOUT=30
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  postgres:
    image: postgres:13
    deploy:
      replicas: 1
      placement:
        constraints:
          - node.labels.db == true
      resources:
        limits:
          cpus: '4.0'
          memory: 8G
        reservations:
          cpus: '2.0'
          memory: 4G
    environment:
      - POSTGRES_MAX_CONNECTIONS=200
      - POSTGRES_SHARED_BUFFERS=256MB
      - POSTGRES_EFFECTIVE_CACHE_SIZE=1GB
      
  redis:
    image: redis:6-alpine
    deploy:
      replicas: 1
      placement:
        constraints:
          - node.labels.cache == true
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

#### Load Balancing Configuration
```nginx
# nginx.conf
upstream janus_api {
    least_conn;
    server janus-api-1:8000 weight=3 max_fails=3 fail_timeout=30s;
    server janus-api-2:8000 weight=3 max_fails=3 fail_timeout=30s;
    server janus-api-3:8000 weight=3 max_fails=3 fail_timeout=30s;
    
    keepalive 32;
}

server {
    listen 80;
    server_name api.janus-ai.com;
    
    # Enable gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1000;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/javascript
        application/xml+rss
        application/json;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;
    
    location / {
        proxy_pass http://janus_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 5s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
        
        # Keepalive
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }
    
    # Health check endpoint
    location /health {
        access_log off;
        proxy_pass http://janus_api/health;
    }
}
```

### Auto-scaling

#### Kubernetes HPA Configuration
```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: janus-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: janus-api
  minReplicas: 3
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
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "100"
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
      - type: Pods
        value: 2
        periodSeconds: 60
      selectPolicy: Max
```

#### Custom Metrics Scaling
```python
# custom_metrics.py
from prometheus_client import Counter, Histogram, Gauge
import asyncio

# Define custom metrics
request_duration = Histogram('janus_request_duration_seconds', 'Request duration')
active_connections = Gauge('janus_active_connections', 'Active connections')
queue_depth = Gauge('janus_queue_depth', 'Queue depth')
llm_tokens_per_second = Gauge('janus_llm_tokens_per_second', 'LLM tokens per second')

class MetricsCollector:
    def __init__(self):
        self.start_collection()
        
    def start_collection(self):
        asyncio.create_task(self.collect_metrics())
        
    async def collect_metrics(self):
        while True:
            try:
                # Collect queue depth
                queue_depth.set(await self.get_queue_depth())
                
                # Collect active connections
                active_connections.set(await self.get_active_connections())
                
                # Collect LLM performance
                llm_tokens_per_second.set(await self.get_llm_tps())
                
                await asyncio.sleep(15)  # Collect every 15 seconds
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
                
    async def get_queue_depth(self) -> int:
        # Implement queue depth measurement
        return await redis_client.llen("processing_queue")
        
    async def get_active_connections(self) -> int:
        # Implement connection counting
        return len(active_connections)
        
    async def get_llm_tps(self) -> float:
        # Implement tokens per second calculation
        return calculate_tps()
```

---

## Monitoring and Alerting

### Performance Monitoring

#### Key Metrics Collection
```python
# monitoring/performance_metrics.py
from prometheus_client import Counter, Histogram, Gauge, Info
import time

# Define performance metrics
api_request_duration = Histogram(
    'janus_api_request_duration_seconds',
    'API request duration',
    ['method', 'endpoint', 'status']
)

database_query_duration = Histogram(
    'janus_database_query_duration_seconds',
    'Database query duration',
    ['query_type', 'table']
)

llm_response_duration = Histogram(
    'janus_llm_response_duration_seconds',
    'LLM response duration',
    ['model', 'provider']
)

active_sessions = Gauge(
    'janus_active_sessions',
    'Number of active chat sessions'
)

memory_usage = Gauge(
    'janus_memory_usage_bytes',
    'Memory usage in bytes'
)

class PerformanceMonitor:
    def __init__(self):
        self.start_system_monitoring()
        
    def start_system_monitoring(self):
        asyncio.create_task(self.monitor_system_resources())
        
    async def monitor_system_resources(self):
        while True:
            try:
                # Monitor memory usage
                memory_info = psutil.virtual_memory()
                memory_usage.set(memory_info.used)
                
                # Monitor active sessions
                active_sessions.set(await self.count_active_sessions())
                
                await asyncio.sleep(30)  # Monitor every 30 seconds
            except Exception as e:
                logger.error(f"Error monitoring system resources: {e}")
                
    async def count_active_sessions(self) -> int:
        # Implement session counting logic
        return await redis_client.scard("active_sessions")

# Middleware for API monitoring
@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    api_request_duration.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).observe(duration)
    
    return response
```

#### Alerting Rules
```yaml
# alerting_rules.yml
groups:
- name: janus_performance
  rules:
  - alert: HighResponseTime
    expr: janus_api_request_duration_seconds{quantile="0.95"} > 2
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High API response time"
      description: "95th percentile response time is {{ $value }}s for {{ $labels.endpoint }}"
      
  - alert: HighErrorRate
    expr: rate(janus_api_requests_total{status=~"5.."}[5m]) > 0.1
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High error rate"
      description: "Error rate is {{ $value | humanizePercentage }} for {{ $labels.endpoint }}"
      
  - alert: HighMemoryUsage
    expr: janus_memory_usage_bytes / janus_memory_limit_bytes > 0.9
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "High memory usage"
      description: "Memory usage is {{ $value | humanizePercentage }}"
      
  - alert: DatabaseSlowQueries
    expr: janus_database_query_duration_seconds{quantile="0.95"} > 1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Slow database queries"
      description: "95th percentile query time is {{ $value }}s for {{ $labels.query_type }}"
      
  - alert: LLMHighLatency
    expr: janus_llm_response_duration_seconds{quantile="0.95"} > 30
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High LLM latency"
      description: "95th percentile LLM response time is {{ $value }}s for {{ $labels.model }}"
```

### Real-time Performance Dashboard

#### Grafana Dashboard Configuration
```json
{
  "dashboard": {
    "title": "Janus Performance Dashboard",
    "panels": [
      {
        "title": "API Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(janus_api_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          },
          {
            "expr": "histogram_quantile(0.50, rate(janus_api_request_duration_seconds_bucket[5m]))",
            "legendFormat": "50th percentile"
          }
        ]
      },
      {
        "title": "Request Rate",
        "type": "singlestat",
        "targets": [
          {
            "expr": "rate(janus_api_requests_total[5m])",
            "legendFormat": "Requests/sec"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(janus_api_requests_total{status=~\"5..\"}[5m])",
            "legendFormat": "5xx errors"
          },
          {
            "expr": "rate(janus_api_requests_total{status=~\"4..\"}[5m])",
            "legendFormat": "4xx errors"
          }
        ]
      },
      {
        "title": "Database Performance",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, janus_database_query_duration_seconds_bucket)",
            "legendFormat": "95th percentile"
          },
          {
            "expr": "histogram_quantile(0.50, janus_database_query_duration_seconds_bucket)",
            "legendFormat": "50th percentile"
          }
        ]
      },
      {
        "title": "LLM Performance",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, janus_llm_response_duration_seconds_bucket)",
            "legendFormat": "95th percentile"
          },
          {
            "expr": "janus_llm_tokens_per_second",
            "legendFormat": "Tokens/sec"
          }
        ]
      },
      {
        "title": "System Resources",
        "type": "graph",
        "targets": [
          {
            "expr": "janus_memory_usage_bytes",
            "legendFormat": "Memory usage"
          },
          {
            "expr": "rate(janus_cpu_usage_seconds_total[5m])",
            "legendFormat": "CPU usage"
          }
        ]
      }
    ]
  }
}
```

---

## Performance Testing

### Load Testing

#### K6 Test Scripts
```javascript
// load-test.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '2m', target: 100 },  // Ramp up to 100 users
    { duration: '5m', target: 100 },  // Stay at 100 users
    { duration: '2m', target: 200 },  // Ramp up to 200 users
    { duration: '5m', target: 200 },  // Stay at 200 users
    { duration: '2m', target: 0 },    // Ramp down to 0 users
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'], // 95% of requests under 2s
    http_req_failed: ['rate<0.1'],     // Error rate under 10%
  },
};

export default function () {
  // Test API endpoints
  let responses = http.batch([
    ['GET', 'http://localhost:8000/api/v1/system/status'],
    ['GET', 'http://localhost:8000/api/v1/system/health/services'],
  ]);
  
  // Validate responses
  check(responses[0], {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });
  
  sleep(1);
}
```

#### Chat Load Testing
```javascript
// chat-load-test.js
import http from 'k6/http';
import { check, sleep } from 'k6';
import { uuidv4 } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';

export let options = {
  scenarios: {
    chat_simulation: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 50 },
        { duration: '2m', target: 50 },
        { duration: '30s', target: 100 },
        { duration: '2m', target: 100 },
        { duration: '30s', target: 0 },
      ],
    },
  },
};

export default function () {
  const userId = `user_${__VU}`;
  const conversationId = `conv_${uuidv4()}`;
  
  // Start conversation
  let startResponse = http.post(
    'http://localhost:8000/api/v1/chat/start',
    JSON.stringify({
      user_id: userId,
      title: 'Load Test Conversation',
    }),
    { headers: { 'Content-Type': 'application/json' } }
  );
  
  check(startResponse, {
    'conversation started': (r) => r.status === 200,
  });
  
  // Send messages
  for (let i = 0; i < 5; i++) {
    let messageResponse = http.post(
      'http://localhost:8000/api/v1/chat/message',
      JSON.stringify({
        conversation_id: conversationId,
        message: `Test message ${i}`,
        user_id: userId,
      }),
      { headers: { 'Content-Type': 'application/json' } }
    );
    
    check(messageResponse, {
      'message sent': (r) => r.status === 200,
      'response time < 5s': (r) => r.timings.duration < 5000,
    });
    
    sleep(2);
  }
}
```

### Stress Testing

#### Database Stress Test
```python
# stress_test_db.py
import asyncio
import asyncpg
import time
from concurrent.futures import ThreadPoolExecutor

class DatabaseStressTest:
    def __init__(self):
        self.connection_pool = None
        self.results = []
        
    async def setup(self):
        self.connection_pool = await asyncpg.create_pool(
            "postgresql://user:password@localhost/janus",
            min_size=10,
            max_size=50,
        )
        
    async def stress_test_concurrent_reads(self, num_connections: int):
        tasks = []
        for i in range(num_connections):
            task = asyncio.create_task(self.simulate_read_load(i))
            tasks.append(task)
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
        
    async def simulate_read_load(self, worker_id: int):
        start_time = time.time()
        query_count = 0
        
        async with self.connection_pool.acquire() as conn:
            while time.time() - start_time < 60:  # Run for 1 minute
                try:
                    # Simulate realistic queries
                    await conn.fetch("""
                        SELECT c.*, COUNT(m.id) as message_count
                        FROM conversations c
                        LEFT JOIN messages m ON c.id = m.conversation_id
                        WHERE c.created_at > NOW() - INTERVAL '7 days'
                        GROUP BY c.id
                        ORDER BY c.updated_at DESC
                        LIMIT 10
                    """)
                    query_count += 1
                    await asyncio.sleep(0.1)  # Small delay between queries
                except Exception as e:
                    logger.error(f"Worker {worker_id} error: {e}")
                    break
                    
        return {
            'worker_id': worker_id,
            'queries_executed': query_count,
            'duration': time.time() - start_time
        }
        
    async def stress_test_concurrent_writes(self, num_connections: int):
        tasks = []
        for i in range(num_connections):
            task = asyncio.create_task(self.simulate_write_load(i))
            tasks.append(task)
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
        
    async def simulate_write_load(self, worker_id: int):
        start_time = time.time()
        insert_count = 0
        
        async with self.connection_pool.acquire() as conn:
            while time.time() - start_time < 60:  # Run for 1 minute
                try:
                    # Simulate message inserts
                    await conn.execute("""
                        INSERT INTO messages (conversation_id, content, role, timestamp)
                        VALUES ($1, $2, $3, NOW())
                    """, f"conv_{worker_id}", f"Test message from worker {worker_id}", "user")
                    
                    insert_count += 1
                    await asyncio.sleep(0.2)  # Delay between inserts
                except Exception as e:
                    logger.error(f"Worker {worker_id} error: {e}")
                    break
                    
        return {
            'worker_id': worker_id,
            'inserts_executed': insert_count,
            'duration': time.time() - start_time
        }
```

#### LLM Stress Testing
```python
# stress_test_llm.py
import asyncio
import aiohttp
import time
from typing import List, Dict

class LLMStressTest:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.session = None
        
    async def setup(self):
        self.session = aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        
    async def stress_test_concurrent_requests(self, num_requests: int):
        tasks = []
        start_time = time.time()
        
        for i in range(num_requests):
            task = asyncio.create_task(self.send_llm_request(i))
            tasks.append(task)
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        return {
            'total_requests': num_requests,
            'successful_requests': sum(1 for r in results if not isinstance(r, Exception)),
            'failed_requests': sum(1 for r in results if isinstance(r, Exception)),
            'total_time': total_time,
            'requests_per_second': num_requests / total_time,
            'results': results
        }
        
    async def send_llm_request(self, request_id: int) -> Dict:
        start_time = time.time()
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/v1/chat/message",
                json={
                    'conversation_id': f'stress_test_conv_{request_id}',
                    'message': f'Stress test message {request_id}',
                    'priority': 'fast_and_cheap'
                }
            ) as response:
                result = await response.json()
                
                return {
                    'request_id': request_id,
                    'status': response.status,
                    'response_time': time.time() - start_time,
                    'tokens_generated': result.get('tokens_generated', 0),
                    'success': response.status == 200
                }
                
        except Exception as e:
            return {
                'request_id': request_id,
                'error': str(e),
                'response_time': time.time() - start_time,
                'success': False
            }
```

---

## Troubleshooting Performance Issues

### Common Performance Issues

#### High Response Time
```bash
# Check API response times
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/api/v1/system/status

# Check slow database queries
docker exec postgres psql -c "
  SELECT query, mean_time, calls
  FROM pg_stat_statements
  WHERE mean_time > 100
  ORDER BY mean_time DESC
  LIMIT 10
"

# Check Redis performance
docker exec redis redis-cli --latency

# Check system resources
docker stats --no-stream
```

#### Memory Leaks
```bash
# Monitor memory usage over time
watch -n 30 'docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}"'

# Check for Python memory leaks
docker exec janus_api python -c "
import gc
import psutil
print(f'Memory: {psutil.virtual_memory().percent}%')
gc.collect()
print(f'Garbage collected: {gc.get_count()}')
"

# Check for database connection leaks
docker exec postgres psql -c "
SELECT count(*), state
FROM pg_stat_activity
GROUP BY state
"
```

#### Database Performance
```bash
# Check for table locks
docker exec postgres psql -c "
SELECT 
  blocked_locks.pid AS blocked_pid,
  blocked_activity.usename AS blocked_user,
  blocking_locks.pid AS blocking_pid,
  blocking_activity.usename AS blocking_user
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted
"

# Check index usage
docker exec postgres psql -c "
SELECT 
  schemaname,
  tablename,
  seq_scan,
  seq_tup_read,
  idx_scan,
  idx_tup_fetch,
  100.0 * idx_scan / nullif(seq_scan + idx_scan, 0) AS index_usage_ratio
FROM pg_stat_user_tables
WHERE seq_scan + idx_scan > 0
ORDER BY index_usage_ratio ASC
"
```

### Performance Profiling

#### Python Profiling
```python
# profile_api.py
import cProfile
import pstats
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

def profile_endpoint():
    """Profile API endpoint performance"""
    profiler = cProfile.Profile()
    
    # Profile the endpoint
    profiler.enable()
    response = client.get("/api/v1/system/status")
    profiler.disable()
    
    # Save stats
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # Top 20 functions
    stats.dump_stats('api_profile.prof')
    
    return response

# Run profiling
if __name__ == "__main__":
    profile_endpoint()
```

#### Database Profiling
```python
# profile_database.py
import asyncio
import asyncpg
import time
from typing import List

class DatabaseProfiler:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        
    async def profile_query(self, query: str, params: dict = None, iterations: int = 100):
        conn = await asyncpg.connect(self.connection_string)
        
        times = []
        for i in range(iterations):
            start = time.time()
            await conn.fetch(query, *params.values() if params else [])
            duration = time.time() - start
            times.append(duration)
            
        await conn.close()
        
        return {
            'query': query,
            'iterations': iterations,
            'avg_time': sum(times) / len(times),
            'min_time': min(times),
            'max_time': max(times),
            'p95_time': sorted(times)[int(len(times) * 0.95)],
            'total_time': sum(times)
        }
        
    async def profile_all_queries(self):
        queries = [
            ("SELECT * FROM conversations WHERE user_id = $1 LIMIT 10", {"user_id": "test_user"}),
            ("SELECT * FROM messages WHERE conversation_id = $1 ORDER BY timestamp DESC LIMIT 20", {"conversation_id": "test_conv"}),
            ("SELECT COUNT(*) FROM conversations WHERE created_at > $1", {"created_at": "2024-01-01"}),
        ]
        
        results = []
        for query, params in queries:
            result = await self.profile_query(query, params)
            results.append(result)
            
        return results
```

### Performance Optimization Checklist

#### Application Level
- [ ] Enable response caching
- [ ] Optimize database queries with proper indexing
- [ ] Implement connection pooling
- [ ] Use async operations where possible
- [ ] Enable gzip compression
- [ ] Implement rate limiting
- [ ] Optimize JSON serialization
- [ ] Use efficient data structures

#### Database Level
- [ ] Create appropriate indexes
- [ ] Optimize query execution plans
- [ ] Configure connection pooling
- [ ] Set optimal memory parameters
- [ ] Enable query result caching
- [ ] Partition large tables if needed
- [ ] Update table statistics regularly
- [ ] Monitor for slow queries

#### Infrastructure Level
- [ ] Configure auto-scaling
- [ ] Set up load balancing
- [ ] Optimize container resources
- [ ] Configure health checks
- [ ] Set up monitoring and alerting
- [ ] Implement circuit breakers
- [ ] Configure proper logging
- [ ] Set up backup strategies

---

*This performance tuning guide is maintained by the Janus Operations Team. Last updated: [DATE]*

*For questions or updates, contact: operations@janus-ai.com*