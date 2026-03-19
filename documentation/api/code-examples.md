# Janus API Code Examples

## Visão Geral

Este documento fornece exemplos práticos de código para integrar com a API Janus em diferentes linguagens de programação. Inclui exemplos de autenticação, chat, gerenciamento de memória e operações administrativas.

## 1. Configuração e Autenticação

### 1.1 JavaScript/TypeScript (Node.js + Express)

```typescript
// janus-client.ts
import axios, { AxiosInstance } from 'axios';

class JanusClient {
  private api: AxiosInstance;
  private token: string | null = null;

  constructor(baseURL: string = 'http://localhost:8000/api/v1') {
    this.api = axios.create({
      baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor for auth
    this.api.interceptors.request.use((config) => {
      if (this.token) {
        config.headers.Authorization = `Bearer ${this.token}`;
      }
      return config;
    });

    // Response interceptor for error handling
    this.api.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          this.token = null;
          // Redirect to login or refresh token
        }
        return Promise.reject(error);
      }
    );
  }

  async login(email: string, password: string): Promise<string> {
    try {
      const response = await this.api.post('/auth/local/login', {
        email,
        password,
      });
      
      this.token = response.data.access_token;
      return this.token;
    } catch (error) {
      throw new Error(`Login failed: ${error.response?.data?.detail || error.message}`);
    }
  }

  async refreshToken(refreshToken: string): Promise<string> {
    const response = await this.api.post('/auth/refresh', {
      refresh_token: refreshToken,
    });
    
    this.token = response.data.access_token;
    return this.token;
  }

  logout(): void {
    this.token = null;
  }

  get isAuthenticated(): boolean {
    return !!this.token;
  }
}

// Usage
const client = new JanusClient();
await client.login('user@example.com', 'password123');
```

### 1.2 Python (Requests)

```python
# janus_client.py
import requests
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

class JanusClient:
    def __init__(self, base_url: str = "http://localhost:8000/api/v1"):
        self.base_url = base_url
        self.session = requests.Session()
        self.token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expires: Optional[datetime] = None
        
        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'JanusPythonClient/1.0'
        })
    
    def _update_auth_header(self):
        """Update Authorization header if token exists"""
        if self.token:
            self.session.headers['Authorization'] = f'Bearer {self.token}'
        else:
            self.session.headers.pop('Authorization', None)
    
    def login(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate user and store tokens"""
        try:
            response = self.session.post(
                f"{self.base_url}/auth/local/login",
                json={"email": email, "password": password}
            )
            response.raise_for_status()
            
            data = response.json()
            self.token = data['access_token']
            self.refresh_token = data.get('refresh_token')
            
            # Set token expiration (assuming 24h)
            if 'expires_in' in data:
                self.token_expires = datetime.now() + timedelta(seconds=data['expires_in'])
            else:
                self.token_expires = datetime.now() + timedelta(hours=24)
            
            self._update_auth_header()
            return data
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Login failed: {str(e)}")
    
    def refresh_access_token(self) -> str:
        """Refresh access token using refresh token"""
        if not self.refresh_token:
            raise Exception("No refresh token available")
        
        try:
            response = self.session.post(
                f"{self.base_url}/auth/refresh",
                json={"refresh_token": self.refresh_token}
            )
            response.raise_for_status()
            
            data = response.json()
            self.token = data['access_token']
            self.token_expires = datetime.now() + timedelta(hours=24)
            self._update_auth_header()
            
            return self.token
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Token refresh failed: {str(e)}")
    
    def ensure_valid_token(self):
        """Check if token is valid and refresh if needed"""
        if not self.token:
            raise Exception("No access token available")
        
        if self.token_expires and datetime.now() >= self.token_expires:
            self.refresh_access_token()
    
    def api_call(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make authenticated API call"""
        self.ensure_valid_token()
        
        try:
            response = self.session.request(
                method=method,
                url=f"{self.base_url}{endpoint}",
                **kwargs
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"API call failed: {str(e)}")

# Usage
client = JanusClient()
client.login("user@example.com", "password123")
```

### 1.3 cURL Examples

```bash
# Basic authentication
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/local/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }' | jq -r '.access_token')

# Use token for authenticated requests
curl -X GET "http://localhost:8000/api/v1/chat/conversations" \
  -H "Authorization: Bearer $TOKEN"

# Refresh token
REFRESH_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/auth/refresh" \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"$REFRESH_TOKEN\"}")
```

## 2. Chat and Conversations

### 2.1 Real-time Chat with SSE (Server-Sent Events)

```typescript
// chat-service.ts
class ChatService {
  private eventSource: EventSource | null = null;
  private conversationId: string | null = null;

  async startConversation(): Promise<string> {
    const response = await this.api.post('/chat/start', {
      title: 'New Conversation',
      system_prompt: 'You are a helpful AI assistant.'
    });
    
    this.conversationId = response.data.conversation_id;
    return this.conversationId;
  }

  connectToConversation(conversationId: string): void {
    if (this.eventSource) {
      this.eventSource.close();
    }

    this.eventSource = new EventSource(
      `/api/v1/chat/stream?conversation_id=${conversationId}`,
      {
        headers: {
          'Authorization': `Bearer ${this.token}`,
        },
      }
    );

    this.eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case 'message':
          this.handleNewMessage(data);
          break;
        case 'typing':
          this.handleTypingIndicator(data);
          break;
        case 'error':
          this.handleError(data);
          break;
        case 'complete':
          this.handleCompletion(data);
          break;
      }
    };

    this.eventSource.onerror = (error) => {
      console.error('SSE Error:', error);
      this.reconnectWithBackoff();
    };
  }

  async sendMessage(content: string, conversationId?: string): Promise<void> {
    const convId = conversationId || this.conversationId;
    
    if (!convId) {
      throw new Error('No conversation ID available');
    }

    try {
      await this.api.post('/chat/message', {
        conversation_id: convId,
        content,
        message_type: 'user'
      });
    } catch (error) {
      console.error('Failed to send message:', error);
      throw error;
    }
  }

  private reconnectWithBackoff(): void {
    let attempts = 0;
    const maxAttempts = 5;
    
    const tryReconnect = () => {
      if (attempts >= maxAttempts) {
        console.error('Max reconnection attempts reached');
        return;
      }

      const delay = Math.min(1000 * Math.pow(2, attempts), 30000);
      attempts++;

      setTimeout(() => {
        if (this.conversationId) {
          this.connectToConversation(this.conversationId);
        }
      }, delay);
    };

    tryReconnect();
  }

  disconnect(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }
}

// Usage
const chatService = new ChatService();
await chatService.startConversation();
chatService.connectToConversation(conversationId);
chatService.sendMessage("Hello, how can you help me today?");
```

### 2.2 Python Chat Client with WebSocket

```python
# chat_client.py
import asyncio
import json
import websockets
from typing import Optional, Callable, Dict, Any

class ChatClient:
    def __init__(self, base_url: str = "ws://localhost:8000"):
        self.base_url = base_url
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.conversation_id: Optional[str] = None
        self.message_handlers: Dict[str, Callable] = {}
        self.running = False
    
    def on_message(self, func: Callable):
        """Decorator to register message handlers"""
        self.message_handlers['message'] = func
        return func
    
    def on_typing(self, func: Callable):
        """Decorator to register typing handlers"""
        self.message_handlers['typing'] = func
        return func
    
    def on_error(self, func: Callable):
        """Decorator to register error handlers"""
        self.message_handlers['error'] = func
        return func
    
    def on_complete(self, func: Callable):
        """Decorator to register completion handlers"""
        self.message_handlers['complete'] = func
        return func
    
    async def start_conversation(self, title: str = "New Conversation") -> str:
        """Start a new conversation"""
        # This would be a REST call to get conversation_id
        # For this example, we'll generate one
        import uuid
        self.conversation_id = str(uuid.uuid4())
        return self.conversation_id
    
    async def connect(self, conversation_id: str, token: str):
        """Connect to WebSocket for real-time chat"""
        self.conversation_id = conversation_id
        
        uri = f"{self.base_url}/api/v1/chat/ws/{conversation_id}"
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            self.websocket = await websockets.connect(uri, extra_headers=headers)
            self.running = True
            
            # Start listening for messages
            await self._listen()
            
        except Exception as e:
            print(f"Failed to connect: {e}")
            raise
    
    async def _listen(self):
        """Listen for incoming messages"""
        try:
            while self.running and self.websocket:
                try:
                    message = await self.websocket.recv()
                    data = json.loads(message)
                    
                    # Handle different message types
                    msg_type = data.get('type', 'message')
                    handler = self.message_handlers.get(msg_type)
                    
                    if handler:
                        await handler(data)
                    else:
                        print(f"Unknown message type: {msg_type}")
                        
                except websockets.exceptions.ConnectionClosed:
                    print("WebSocket connection closed")
                    break
                except json.JSONDecodeError as e:
                    print(f"Failed to parse message: {e}")
                    
        except Exception as e:
            print(f"Error in listen loop: {e}")
    
    async def send_message(self, content: str, message_type: str = "user"):
        """Send a message through WebSocket"""
        if not self.websocket:
            raise Exception("Not connected to WebSocket")
        
        message = {
            "type": "message",
            "content": content,
            "message_type": message_type,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        await self.websocket.send(json.dumps(message))
    
    async def send_typing_indicator(self, is_typing: bool = True):
        """Send typing indicator"""
        if not self.websocket:
            return
        
        message = {
            "type": "typing",
            "is_typing": is_typing
        }
        
        await self.websocket.send(json.dumps(message))
    
    async def disconnect(self):
        """Disconnect from WebSocket"""
        self.running = False
        if self.websocket:
            await self.websocket.close()
            self.websocket = None

# Usage example
async def main():
    client = ChatClient()
    
    # Register handlers
    @client.on_message
    async def handle_message(data):
        print(f"Message: {data['content']}")
    
    @client.on_typing
    async def handle_typing(data):
        print(f"User is typing: {data['is_typing']}")
    
    @client.on_error
    async def handle_error(data):
        print(f"Error: {data['message']}")
    
    # Connect and chat
    conversation_id = await client.start_conversation()
    await client.connect(conversation_id, "your-jwt-token")
    
    await client.send_message("Hello, how can you help me today?")
    
    # Keep connection alive for demo
    await asyncio.sleep(30)
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

### 2.3 Conversation Management

```typescript
// conversation-manager.ts
interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  last_message?: string;
}

interface Message {
  id: string;
  conversation_id: string;
  content: string;
  message_type: 'user' | 'assistant' | 'system';
  created_at: string;
  citations?: Citation[];
}

interface Citation {
  source: string;
  content: string;
  relevance: number;
}

class ConversationManager {
  private conversations: Map<string, Conversation> = new Map();
  private messages: Map<string, Message[]> = new Map();

  async createConversation(title: string, systemPrompt?: string): Promise<Conversation> {
    const response = await this.api.post('/chat/start', {
      title,
      system_prompt: systemPrompt
    });

    const conversation: Conversation = response.data;
    this.conversations.set(conversation.id, conversation);
    this.messages.set(conversation.id, []);

    return conversation;
  }

  async getConversations(limit: number = 50, offset: number = 0): Promise<Conversation[]> {
    const response = await this.api.get('/chat/conversations', {
      params: { limit, offset }
    });

    const conversations = response.data.conversations;
    conversations.forEach(conv => {
      this.conversations.set(conv.id, conv);
    });

    return conversations;
  }

  async getConversationHistory(
    conversationId: string, 
    limit: number = 100, 
    before?: string
  ): Promise<Message[]> {
    const params: any = { limit };
    if (before) params.before = before;

    const response = await this.api.get(`/chat/conversations/${conversationId}/messages`, {
      params
    });

    const messages = response.data.messages;
    this.messages.set(conversationId, messages);

    return messages;
  }

  async updateConversationTitle(conversationId: string, title: string): Promise<void> {
    await this.api.put(`/chat/conversations/${conversationId}`, {
      title
    });

    const conversation = this.conversations.get(conversationId);
    if (conversation) {
      conversation.title = title;
    }
  }

  async deleteConversation(conversationId: string): Promise<void> {
    await this.api.delete(`/chat/conversations/${conversationId}`);
    
    this.conversations.delete(conversationId);
    this.messages.delete(conversationId);
  }

  async exportConversation(conversationId: string, format: 'json' | 'csv' | 'txt' = 'json'): Promise<Blob> {
    const response = await this.api.get(`/chat/conversations/${conversationId}/export`, {
      params: { format },
      responseType: 'blob'
    });

    return response.data;
  }

  getCachedConversation(conversationId: string): Conversation | undefined {
    return this.conversations.get(conversationId);
  }

  getCachedMessages(conversationId: string): Message[] {
    return this.messages.get(conversationId) || [];
  }

  clearCache(): void {
    this.conversations.clear();
    this.messages.clear();
  }
}

// Usage
const conversationManager = new ConversationManager();

// Create new conversation
const conversation = await conversationManager.createConversation(
  "AI Assistant Chat",
  "You are a helpful AI assistant specialized in technology."
);

// Get recent conversations
const recentConversations = await conversationManager.getConversations(10);

// Get conversation history
const messages = await conversationManager.getConversationHistory(conversation.id);

// Export conversation
const exportData = await conversationManager.exportConversation(conversation.id, 'json');
```

## 3. Memory and Knowledge Management

### 3.1 Memory Operations

```python
# memory_client.py
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime

class MemoryClient:
    def __init__(self, base_client):
        self.client = base_client
    
    def store_memory(self, content: str, memory_type: str = "general", 
                    metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Store a new memory"""
        data = {
            "content": content,
            "memory_type": memory_type,
            "metadata": metadata or {}
        }
        
        return self.client.api_call("POST", "/memory/store", json=data)
    
    def search_memories(self, query: str, limit: int = 10, 
                       memory_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search stored memories"""
        params = {"query": query, "limit": limit}
        if memory_type:
            params["memory_type"] = memory_type
        
        response = self.client.api_call("GET", "/memory/search", params=params)
        return response.get("memories", [])
    
    def get_timeline(self, start_date: Optional[datetime] = None,
                    end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get memory timeline"""
        params = {}
        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()
        
        response = self.client.api_call("GET", "/memory/timeline", params=params)
        return response.get("events", [])
    
    def update_memory(self, memory_id: str, content: str,
                     metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Update existing memory"""
        data = {"content": content}
        if metadata:
            data["metadata"] = metadata
        
        return self.client.api_call("PUT", f"/memory/{memory_id}", json=data)
    
    def delete_memory(self, memory_id: str) -> Dict[str, Any]:
        """Delete a memory"""
        return self.client.api_call("DELETE", f"/memory/{memory_id}")
    
    def get_preferences(self) -> Dict[str, Any]:
        """Get user preferences"""
        return self.client.api_call("GET", "/memory/preferences")
    
    def update_preferences(self, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Update user preferences"""
        return self.client.api_call("PUT", "/memory/preferences", json=preferences)

# Usage
memory_client = MemoryClient(janus_client)

# Store memory
memory = memory_client.store_memory(
    content="User prefers Python over JavaScript for backend development",
    memory_type="preference",
    metadata={"category": "technology", "confidence": 0.9}
)

# Search memories
results = memory_client.search_memories("Python", limit=5, memory_type="preference")

# Get timeline
from datetime import datetime, timedelta
last_week = datetime.now() - timedelta(days=7)
timeline = memory_client.get_timeline(start_date=last_week)
```

### 3.2 Knowledge Graph Operations

```typescript
// knowledge-graph-client.ts
interface KnowledgeNode {
  id: string;
  label: string;
  type: string;
  properties: Record<string, any>;
  created_at: string;
  updated_at: string;
}

interface KnowledgeRelationship {
  id: string;
  source_id: string;
  target_id: string;
  relationship_type: string;
  properties: Record<string, any>;
  strength: number;
}

interface KnowledgeQuery {
  query: string;
  limit?: number;
  min_confidence?: number;
  node_types?: string[];
}

class KnowledgeGraphClient {
  async createNode(
    label: string, 
    type: string, 
    properties: Record<string, any> = {}
  ): Promise<KnowledgeNode> {
    const response = await this.api.post('/knowledge/nodes', {
      label,
      type,
      properties
    });

    return response.data;
  }

  async createRelationship(
    sourceId: string,
    targetId: string,
    relationshipType: string,
    properties: Record<string, any> = {},
    strength: number = 1.0
  ): Promise<KnowledgeRelationship> {
    const response = await this.api.post('/knowledge/relationships', {
      source_id: sourceId,
      target_id: targetId,
      relationship_type: relationshipType,
      properties,
      strength
    });

    return response.data;
  }

  async queryKnowledge(query: KnowledgeQuery): Promise<{
    nodes: KnowledgeNode[];
    relationships: KnowledgeRelationship[];
  }> {
    const response = await this.api.post('/knowledge/query', query);

    return {
      nodes: response.data.nodes,
      relationships: response.data.relationships
    };
  }

  async getNodeConnections(
    nodeId: string,
    relationshipTypes?: string[],
    maxDepth: number = 2
  ): Promise<{
    nodes: KnowledgeNode[];
    relationships: KnowledgeRelationship[];
  }> {
    const params: any = { max_depth: maxDepth };
    if (relationshipTypes) {
      params.relationship_types = relationshipTypes;
    }

    const response = await this.api.get(`/knowledge/nodes/${nodeId}/connections`, {
      params
    });

    return {
      nodes: response.data.nodes,
      relationships: response.data.relationships
    };
  }

  async updateNode(
    nodeId: string,
    updates: {
      label?: string;
      properties?: Record<string, any>;
    }
  ): Promise<KnowledgeNode> {
    const response = await this.api.put(`/knowledge/nodes/${nodeId}`, updates);
    return response.data;
  }

  async deleteNode(nodeId: string): Promise<void> {
    await this.api.delete(`/knowledge/nodes/${nodeId}`);
  }

  async indexDocument(
    documentId: string,
    content: string,
    metadata: Record<string, any> = {}
  ): Promise<{
    nodes_created: number;
    relationships_created: number;
  }> {
    const response = await this.api.post('/knowledge/index-document', {
      document_id: documentId,
      content,
      metadata
    });

    return response.data;
  }

  async semanticSearch(
    query: string,
    limit: number = 10,
    threshold: number = 0.7
  ): Promise<{
    results: Array<{
      node: KnowledgeNode;
      score: number;
      relevant_content: string;
    }>;
  }> {
    const response = await this.api.post('/knowledge/semantic-search', {
      query,
      limit,
      threshold
    });

    return response.data;
  }
}

// Usage
const kgClient = new KnowledgeGraphClient();

// Create knowledge nodes
const pythonNode = await kgClient.createNode("Python", "programming_language", {
  paradigm: "multi-paradigm",
  typing: "dynamic",
  created_year: 1991
});

const aiNode = await kgClient.createNode("Artificial Intelligence", "technology", {
  category: "computer_science",
  applications: ["machine_learning", "nlp", "computer_vision"]
});

// Create relationship
await kgClient.createRelationship(
  pythonNode.id,
  aiNode.id,
  "used_for",
  { common_frameworks: ["TensorFlow", "PyTorch", "scikit-learn"] },
  0.9
);

// Query knowledge graph
const results = await kgClient.queryKnowledge({
  query: "programming languages for AI",
  node_types: ["programming_language", "technology"],
  min_confidence: 0.8
});

// Semantic search
const searchResults = await kgClient.semanticSearch(
  "machine learning frameworks",
  limit=5,
  threshold=0.8
);
```

## 4. Observability and Monitoring

### 4.1 Health Checks and Status

```python
# monitoring_client.py
class MonitoringClient:
    def __init__(self, base_client):
        self.client = base_client
    
    def health_check(self) -> Dict[str, Any]:
        """Basic health check"""
        return self.client.api_call("GET", "/health")
    
    def system_status(self) -> Dict[str, Any]:
        """Get detailed system status"""
        return self.client.api_call("GET", "/api/v1/system/status")
    
    def worker_status(self) -> Dict[str, Any]:
        """Get worker status"""
        return self.client.api_call("GET", "/api/v1/workers/status")
    
    def database_health(self) -> Dict[str, Any]:
        """Check database health"""
        return self.client.api_call("GET", "/api/v1/system/health/db")
    
    def cache_health(self) -> Dict[str, Any]:
        """Check cache health"""
        return self.client.api_call("GET", "/api/v1/system/health/cache")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get system metrics"""
        return self.client.api_call("GET", "/api/v1/observability/metrics")
    
    def get_slo_status(self, window_minutes: int = 60) -> Dict[str, Any]:
        """Get SLO status"""
        params = {"window_minutes": window_minutes}
        return self.client.api_call("GET", "/api/v1/observability/slo/domains", params=params)

# Usage
monitoring_client = MonitoringClient(janus_client)

# Health checks
health = monitoring_client.health_check()
system_status = monitoring_client.system_status()
worker_status = monitoring_client.worker_status()

# Get metrics
metrics = monitoring_client.get_metrics()
slo_status = monitoring_client.get_slo_status(window_minutes=120)
```

### 4.2 Performance Monitoring

```typescript
// performance-monitor.ts
interface PerformanceMetrics {
  response_time: number;
  status_code: number;
  endpoint: string;
  timestamp: number;
  error?: string;
}

interface LatencyMetrics {
  p50: number;
  p95: number;
  p99: number;
  mean: number;
  samples: number;
}

class PerformanceMonitor {
  private metrics: PerformanceMetrics[] = [];
  private maxMetrics: number = 1000;

  async measureApiCall<T>(
    call: () => Promise<T>,
    endpoint: string
  ): Promise<{ result: T; metrics: PerformanceMetrics }> {
    const start = performance.now();
    
    try {
      const result = await call();
      const end = performance.now();
      
      const metrics: PerformanceMetrics = {
        response_time: end - start,
        status_code: 200,
        endpoint,
        timestamp: Date.now()
      };
      
      this.addMetric(metrics);
      
      return { result, metrics };
      
    } catch (error) {
      const end = performance.now();
      
      const metrics: PerformanceMetrics = {
        response_time: end - start,
        status_code: error.response?.status || 500,
        endpoint,
        timestamp: Date.now(),
        error: error.message
      };
      
      this.addMetric(metrics);
      throw error;
    }
  }

  addMetric(metric: PerformanceMetrics): void {
    this.metrics.push(metric);
    
    // Keep only recent metrics
    if (this.metrics.length > this.maxMetrics) {
      this.metrics = this.metrics.slice(-this.maxMetrics);
    }
  }

  getLatencyMetrics(endpoint?: string, timeWindow: number = 3600000): LatencyMetrics {
    const now = Date.now();
    const windowStart = now - timeWindow;
    
    let relevantMetrics = this.metrics.filter(m => 
      m.timestamp >= windowStart && 
      (endpoint ? m.endpoint === endpoint : true) &&
      m.status_code < 400
    );

    if (relevantMetrics.length === 0) {
      return {
        p50: 0,
        p95: 0,
        p99: 0,
        mean: 0,
        samples: 0
      };
    }

    const responseTimes = relevantMetrics.map(m => m.response_time).sort((a, b) => a - b);
    
    return {
      p50: this.percentile(responseTimes, 0.5),
      p95: this.percentile(responseTimes, 0.95),
      p99: this.percentile(responseTimes, 0.99),
      mean: responseTimes.reduce((sum, time) => sum + time, 0) / responseTimes.length,
      samples: responseTimes.length
    };
  }

  private percentile(sortedArray: number[], p: number): number {
    if (sortedArray.length === 0) return 0;
    
    const index = Math.ceil(sortedArray.length * p) - 1;
    return sortedArray[Math.max(0, index)];
  }

  getErrorRate(endpoint?: string, timeWindow: number = 3600000): number {
    const now = Date.now();
    const windowStart = now - timeWindow;
    
    const relevantMetrics = this.metrics.filter(m => 
      m.timestamp >= windowStart && 
      (endpoint ? m.endpoint === endpoint : true)
    );

    if (relevantMetrics.length === 0) return 0;

    const errorCount = relevantMetrics.filter(m => m.status_code >= 400).length;
    return errorCount / relevantMetrics.length;
  }

  exportMetrics(): PerformanceMetrics[] {
    return [...this.metrics];
  }

  clearMetrics(): void {
    this.metrics = [];
  }
}

// Usage
const performanceMonitor = new PerformanceMonitor();

// Wrap API calls with performance monitoring
const { result, metrics } = await performanceMonitor.measureApiCall(
  () => client.get('/api/v1/chat/conversations'),
  'GET /chat/conversations'
);

// Get latency metrics
const latencyMetrics = performanceMonitor.getLatencyMetrics();
const endpointLatency = performanceMonitor.getLatencyMetrics('/chat/conversations');

// Get error rates
const overallErrorRate = performanceMonitor.getErrorRate();
const endpointErrorRate = performanceMonitor.getErrorRate('/chat/conversations');
```

## 5. Error Handling and Retry Logic

### 5.1 Comprehensive Error Handling

```typescript
// error-handler.ts
export class JanusError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public errorCode?: string,
    public details?: any
  ) {
    super(message);
    this.name = 'JanusError';
  }
}

export class AuthenticationError extends JanusError {
  constructor(message: string = 'Authentication failed') {
    super(message, 401, 'AUTH_FAILED');
  }
}

export class RateLimitError extends JanusError {
  constructor(
    message: string = 'Rate limit exceeded',
    public retryAfter?: number
  ) {
    super(message, 429, 'RATE_LIMIT_EXCEEDED');
  }
}

export class ValidationError extends JanusError {
  constructor(message: string, public validationErrors: any[]) {
    super(message, 400, 'VALIDATION_ERROR', validationErrors);
  }
}

// Retry configuration
interface RetryConfig {
  maxAttempts: number;
  initialDelay: number;
  maxDelay: number;
  backoffFactor: number;
  retryableStatusCodes: number[];
}

const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxAttempts: 3,
  initialDelay: 1000,
  maxDelay: 30000,
  backoffFactor: 2,
  retryableStatusCodes: [408, 429, 500, 502, 503, 504]
};

class RetryHandler {
  private config: RetryConfig;

  constructor(config: Partial<RetryConfig> = {}) {
    this.config = { ...DEFAULT_RETRY_CONFIG, ...config };
  }

  async executeWithRetry<T>(
    operation: () => Promise<T>,
    onRetry?: (error: Error, attempt: number) => void
  ): Promise<T> {
    let lastError: Error;
    
    for (let attempt = 1; attempt <= this.config.maxAttempts; attempt++) {
      try {
        return await operation();
      } catch (error) {
        lastError = error as Error;
        
        // Check if error is retryable
        if (!this.isRetryableError(error)) {
          throw error;
        }
        
        // Don't retry on last attempt
        if (attempt === this.config.maxAttempts) {
          break;
        }
        
        // Calculate delay with exponential backoff
        const delay = this.calculateDelay(attempt);
        
        // Call retry callback if provided
        if (onRetry) {
          onRetry(error, attempt);
        }
        
        // Wait before retrying
        await this.sleep(delay);
      }
    }
    
    throw lastError!;
  }

  private isRetryableError(error: Error): boolean {
    if (error instanceof JanusError) {
      return this.config.retryableStatusCodes.includes(error.statusCode);
    }
    
    // Network errors are retryable
    if (error.message.includes('network') || 
        error.message.includes('timeout') ||
        error.message.includes('ECONNREFUSED')) {
      return true;
    }
    
    return false;
  }

  private calculateDelay(attempt: number): number {
    const exponentialDelay = this.config.initialDelay * Math.pow(this.config.backoffFactor, attempt - 1);
    const jitteredDelay = exponentialDelay * (0.5 + Math.random() * 0.5); // Add jitter
    return Math.min(jitteredDelay, this.config.maxDelay);
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// Usage with retry logic
const retryHandler = new RetryHandler({
  maxAttempts: 5,
  initialDelay: 2000
});

try {
  const result = await retryHandler.executeWithRetry(
    () => client.get('/api/v1/chat/conversations'),
    (error, attempt) => {
      console.log(`Retry attempt ${attempt} after error: ${error.message}`);
    }
  );
  
  console.log('Success:', result);
} catch (error) {
  console.error('Failed after all retries:', error);
}
```

### 5.2 Circuit Breaker Pattern

```typescript
// circuit-breaker.ts
enum CircuitState {
  CLOSED = 'CLOSED',
  OPEN = 'OPEN',
  HALF_OPEN = 'HALF_OPEN'
}

interface CircuitBreakerConfig {
  failureThreshold: number;
  resetTimeout: number;
  monitoringPeriod: number;
  minimumRequests: number;
}

class CircuitBreaker {
  private state: CircuitState = CircuitState.CLOSED;
  private failures: number = 0;
  private successes: number = 0;
  private lastFailureTime: number = 0;
  private totalRequests: number = 0;

  constructor(
    private name: string,
    private config: CircuitBreakerConfig = {
      failureThreshold: 5,
      resetTimeout: 60000, // 1 minute
      monitoringPeriod: 10000, // 10 seconds
      minimumRequests: 10
    }
  ) {}

  async execute<T>(operation: () => Promise<T>): Promise<T> {
    if (this.state === CircuitState.OPEN) {
      if (this.shouldAttemptReset()) {
        this.state = CircuitState.HALF_OPEN;
        console.log(`Circuit breaker ${this.name}: attempting reset`);
      } else {
        throw new Error(`Circuit breaker ${this.name} is OPEN`);
      }
    }

    this.totalRequests++;

    try {
      const result = await operation();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  private onSuccess(): void {
    this.successes++;
    
    if (this.state === CircuitState.HALF_OPEN) {
      this.reset();
      console.log(`Circuit breaker ${this.name}: reset successful`);
    }
  }

  private onFailure(): void {
    this.failures++;
    this.lastFailureTime = Date.now();

    if (this.state === CircuitState.HALF_OPEN) {
      this.trip();
      console.log(`Circuit breaker ${this.name}: tripped again`);
      return;
    }

    if (this.shouldTrip()) {
      this.trip();
    }
  }

  private shouldTrip(): boolean {
    if (this.totalRequests < this.config.minimumRequests) {
      return false;
    }

    const failureRate = this.failures / this.totalRequests;
    return failureRate >= 0.5 && this.failures >= this.config.failureThreshold;
  }

  private shouldAttemptReset(): boolean {
    return Date.now() - this.lastFailureTime >= this.config.resetTimeout;
  }

  private trip(): void {
    this.state = CircuitState.OPEN;
    console.log(`Circuit breaker ${this.name}: tripped`);
  }

  private reset(): void {
    this.state = CircuitState.CLOSED;
    this.failures = 0;
    this.successes = 0;
    this.totalRequests = 0;
    console.log(`Circuit breaker ${this.name}: reset`);
  }

  getState(): CircuitState {
    return this.state;
  }

  getMetrics(): {
    state: CircuitState;
    failures: number;
    successes: number;
    totalRequests: number;
    failureRate: number;
  } {
    return {
      state: this.state,
      failures: this.failures,
      successes: this.successes,
      totalRequests: this.totalRequests,
      failureRate: this.totalRequests > 0 ? this.failures / this.totalRequests : 0
    };
  }
}

// Usage
const circuitBreaker = new CircuitBreaker('JanusAPI', {
  failureThreshold: 3,
  resetTimeout: 30000,
  monitoringPeriod: 5000,
  minimumRequests: 5
});

try {
  const result = await circuitBreaker.execute(() => 
    client.get('/api/v1/chat/conversations')
  );
  
  console.log('Success:', result);
} catch (error) {
  console.error('Circuit breaker error:', error);
}
```

## 6. Complete Integration Examples

### 6.1 Full Chat Application

```typescript
// complete-chat-app.ts
import { JanusClient } from './janus-client';
import { ChatService } from './chat-service';
import { ConversationManager } from './conversation-manager';
import { PerformanceMonitor } from './performance-monitor';
import { RetryHandler, JanusError } from './error-handler';

class JanusChatApp {
  private client: JanusClient;
  private chatService: ChatService;
  private conversationManager: ConversationManager;
  private performanceMonitor: PerformanceMonitor;
  private retryHandler: RetryHandler;

  constructor() {
    this.client = new JanusClient();
    this.chatService = new ChatService(this.client);
    this.conversationManager = new ConversationManager(this.client);
    this.performanceMonitor = new PerformanceMonitor();
    this.retryHandler = new RetryHandler({
      maxAttempts: 3,
      initialDelay: 1000
    });

    this.setupEventListeners();
  }

  private setupEventListeners(): void {
    // Handle connection events
    this.chatService.on('connected', () => {
      console.log('Connected to chat service');
      this.updateUI('connected');
    });

    this.chatService.on('disconnected', () => {
      console.log('Disconnected from chat service');
      this.updateUI('disconnected');
    });

    this.chatService.on('message', (message) => {
      this.displayMessage(message);
      this.performanceMonitor.addMetric({
        endpoint: 'chat/message',
        response_time: Date.now() - message.timestamp,
        status_code: 200
      });
    });

    this.chatService.on('error', (error) => {
      console.error('Chat service error:', error);
      this.displayError(error.message);
    });
  }

  async initialize(): Promise<void> {
    try {
      // Authenticate user
      await this.client.login('user@example.com', 'password123');
      
      // Load existing conversations
      const conversations = await this.loadConversations();
      this.displayConversations(conversations);
      
      console.log('Chat application initialized successfully');
    } catch (error) {
      console.error('Failed to initialize chat app:', error);
      throw error;
    }
  }

  async startNewConversation(title: string, systemPrompt?: string): Promise<string> {
    return await this.retryHandler.executeWithRetry(async () => {
      const conversation = await this.conversationManager.createConversation(
        title,
        systemPrompt
      );
      
      // Connect to real-time updates
      this.chatService.connectToConversation(conversation.id);
      
      return conversation.id;
    });
  }

  async sendMessage(content: string, conversationId?: string): Promise<void> {
    if (!conversationId && !this.chatService.currentConversationId) {
      throw new Error('No conversation selected');
    }

    try {
      // Add user message to UI immediately
      this.displayUserMessage(content);
      
      // Send message with retry logic
      await this.retryHandler.executeWithRetry(() =>
        this.chatService.sendMessage(content, conversationId)
      );
      
      // Show typing indicator
      this.showTypingIndicator(true);
      
    } catch (error) {
      console.error('Failed to send message:', error);
      this.displayError('Failed to send message. Please try again.');
      this.removeLastUserMessage();
    }
  }

  private async loadConversations(): Promise<any[]> {
    return await this.performanceMonitor.measureApiCall(
      () => this.conversationManager.getConversations(20),
      'load_conversations'
    );
  }

  private displayMessage(message: any): void {
    // Update UI with new message
    const messageElement = this.createMessageElement(message);
    this.chatContainer.appendChild(messageElement);
    
    // Scroll to bottom
    this.scrollToBottom();
    
    // Hide typing indicator for assistant messages
    if (message.message_type === 'assistant') {
      this.showTypingIndicator(false);
    }
  }

  private displayUserMessage(content: string): void {
    const userMessage = {
      id: Date.now().toString(),
      content,
      message_type: 'user',
      timestamp: new Date().toISOString()
    };
    
    this.displayMessage(userMessage);
  }

  private showTypingIndicator(show: boolean): void {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) {
      indicator.style.display = show ? 'block' : 'none';
    }
  }

  private createMessageElement(message: any): HTMLElement {
    const element = document.createElement('div');
    element.className = `message ${message.message_type}`;
    element.innerHTML = `
      <div class="message-content">${this.escapeHtml(message.content)}</div>
      <div class="message-timestamp">${this.formatTimestamp(message.timestamp)}</div>
    `;
    
    // Add citations if present
    if (message.citations && message.citations.length > 0) {
      const citationsElement = this.createCitationsElement(message.citations);
      element.appendChild(citationsElement);
    }
    
    return element;
  }

  private createCitationsElement(citations: any[]): HTMLElement {
    const element = document.createElement('div');
    element.className = 'message-citations';
    element.innerHTML = '<strong>Sources:</strong><ul>' +
      citations.map(citation => 
        `<li>${citation.source}: ${citation.content.substring(0, 100)}...</li>`
      ).join('') +
      '</ul>';
    
    return element;
  }

  private escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  private formatTimestamp(timestamp: string): string {
    const date = new Date(timestamp);
    return date.toLocaleTimeString();
  }

  private scrollToBottom(): void {
    this.chatContainer.scrollTop = this.chatContainer.scrollHeight;
  }

  private displayError(message: string): void {
    const errorElement = document.createElement('div');
    errorElement.className = 'error-message';
    errorElement.textContent = message;
    this.chatContainer.appendChild(errorElement);
  }

  private removeLastUserMessage(): void {
    const messages = this.chatContainer.querySelectorAll('.message.user');
    if (messages.length > 0) {
      messages[messages.length - 1].remove();
    }
  }

  private updateUI(state: string): void {
    const statusElement = document.getElementById('connection-status');
    if (statusElement) {
      statusElement.textContent = state;
      statusElement.className = `status-${state}`;
    }
  }

  // Performance monitoring methods
  getPerformanceMetrics() {
    return {
      latency: this.performanceMonitor.getLatencyMetrics(),
      errorRate: this.performanceMonitor.getErrorRate(),
      totalMessages: this.chatService.getMessageCount()
    };
  }

  exportChatHistory(conversationId: string, format: string = 'json'): Promise<Blob> {
    return this.conversationManager.exportConversation(conversationId, format as any);
  }

  disconnect(): void {
    this.chatService.disconnect();
    this.client.logout();
  }
}

// Usage
const chatApp = new JanusChatApp();

// Initialize the application
await chatApp.initialize();

// Start a new conversation
const conversationId = await chatApp.startNewConversation(
  "AI Assistant Chat",
  "You are a helpful AI assistant."
);

// Send messages
await chatApp.sendMessage("Hello, how can you help me today?");
await chatApp.sendMessage("What are the best practices for API design?");

// Get performance metrics
const metrics = chatApp.getPerformanceMetrics();
console.log('Performance metrics:', metrics);

// Export conversation
const exportData = await chatApp.exportChatHistory(conversationId, 'json');

// Cleanup
chatApp.disconnect();
```

---

*Estes exemplos fornecem uma base sólida para integrar com a API Janus. Para mais exemplos e casos de uso avançados, consulte a documentação completa da API.*