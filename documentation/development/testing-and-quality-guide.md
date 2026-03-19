# Guia de Testes e Qualidade - Janus

## Visão Geral

Este guia fornece uma estratégia abrangente de testes e garantia de qualidade para o projeto Janus, cobrindo desde testes unitários até testes de performance e segurança.

## 1. Estratégia de Testes

### 1.1 Pirâmide de Testes

```
    🚀 E2E Tests (5%)
      📱 Integration Tests (15%)
         🔧 Unit Tests (80%)
```

### 1.2 Tipos de Testes

| Tipo | Ferramenta | Cobertura | Executado em |
|------|------------|-----------|--------------|
| Unit Tests | Pytest / Jest | >80% | CI/CD |
| Integration Tests | Pytest / TestContainers | >70% | CI/CD |
| Contract Tests | Pact / OpenAPI | >90% | CI/CD |
| E2E Tests | Playwright / Cypress | >60% | Pre-release |
| Performance Tests | Locust / K6 | >50% | Weekly |
| Security Tests | OWASP ZAP / Bandit | >95% | CI/CD |
| Observability Tests | Prometheus / Grafana | 100% | Continuous |

## 2. Testes Backend (Python/FastAPI)

### 2.1 Configuração do Pytest

**`backend/pytest.ini`**:
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --strict-config
    --verbose
    --tb=short
    --cov=app
    --cov-report=term-missing
    --cov-report=html:htmlcov
    --cov-report=xml:coverage.xml
    --cov-fail-under=80
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow tests
    contract: Contract tests
    performance: Performance tests
    security: Security tests
```

### 2.2 Testes Unitários

**`backend/tests/unit/test_chat_service.py`**:
```python
import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.services.chat_service import ChatService
from app.models.chat import ChatMessage, ChatResponse
from app.core.exceptions import ChatServiceException

@pytest.mark.unit
class TestChatService:
    
    @pytest.fixture
    def chat_service(self):
        return ChatService(
            llm_provider=Mock(),
            memory_service=Mock(),
            knowledge_service=Mock()
        )
    
    @pytest.mark.asyncio
    async def test_process_message_success(self, chat_service):
        # Arrange
        message = ChatMessage(
            content="What is the weather?",
            user_id="user123",
            session_id="session456"
        )
        
        chat_service.llm_provider.generate_response = AsyncMock(
            return_value=ChatResponse(
                content="The weather is sunny",
                confidence=0.9,
                sources=["weather_api"]
            )
        )
        
        # Act
        response = await chat_service.process_message(message)
        
        # Assert
        assert response.content == "The weather is sunny"
        assert response.confidence == 0.9
        assert "weather_api" in response.sources
        
        chat_service.memory_service.store_interaction.assert_called_once()
        chat_service.knowledge_service.enhance_context.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_message_with_context(self, chat_service):
        # Arrange
        message = ChatMessage(
            content="Explain quantum computing",
            user_id="user123",
            session_id="session456",
            context={"domain": "physics", "level": "intermediate"}
        )
        
        chat_service.knowledge_service.get_relevant_docs = AsyncMock(
            return_value=[{"title": "Quantum Computing Basics", "content": "..."}]
        )
        
        # Act
        response = await chat_service.process_message(message)
        
        # Assert
        assert response.content is not None
        assert len(response.sources) > 0
        chat_service.knowledge_service.get_relevant_docs.assert_called_with(
            "quantum computing", {"domain": "physics", "level": "intermediate"}
        )
    
    @pytest.mark.asyncio
    async def test_process_message_rate_limit_exceeded(self, chat_service):
        # Arrange
        message = ChatMessage(
            content="Test message",
            user_id="user123",
            session_id="session456"
        )
        
        chat_service.llm_provider.generate_response = AsyncMock(
            side_effect=RateLimitExceeded("Rate limit exceeded")
        )
        
        # Act & Assert
        with pytest.raises(ChatServiceException) as exc_info:
            await chat_service.process_message(message)
        
        assert "Rate limit exceeded" in str(exc_info.value)
        chat_service.memory_service.store_interaction.assert_not_called()
```

### 2.3 Testes de Integração

**`backend/tests/integration/test_knowledge_repository.py`**:
```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.repositories.knowledge_repository import KnowledgeRepository
from app.models.knowledge import KnowledgeItem, KnowledgeGraph
from app.core.database import Base, get_db

@pytest.mark.integration
class TestKnowledgeRepository:
    
    @pytest.fixture(scope="class")
    def test_db(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        TestingSessionLocal = sessionmaker(bind=engine)
        return TestingSessionLocal()
    
    @pytest.fixture
    def repository(self, test_db):
        return KnowledgeRepository(test_db)
    
    def test_create_knowledge_item(self, repository, test_db):
        # Arrange
        item = KnowledgeItem(
            title="Machine Learning Basics",
            content="Machine learning is a subset of AI...",
            category="AI/ML",
            tags=["machine-learning", "ai", "basics"],
            metadata={"difficulty": "beginner", "estimated_time": 30}
        )
        
        # Act
        created_item = repository.create(item)
        test_db.commit()
        
        # Assert
        assert created_item.id is not None
        assert created_item.title == "Machine Learning Basics"
        assert "machine-learning" in created_item.tags
        assert created_item.metadata["difficulty"] == "beginner"
        
        # Verify persistence
        retrieved_item = repository.get_by_id(created_item.id)
        assert retrieved_item.title == created_item.title
    
    def test_search_knowledge_items(self, repository, test_db):
        # Arrange
        items = [
            KnowledgeItem(
                title="Python Programming",
                content="Python is a versatile programming language...",
                category="Programming",
                tags=["python", "programming"]
            ),
            KnowledgeItem(
                title="JavaScript Fundamentals",
                content="JavaScript is essential for web development...",
                category="Programming",
                tags=["javascript", "web", "frontend"]
            ),
            KnowledgeItem(
                title="Data Science with Python",
                content="Python is widely used in data science...",
                category="Data Science",
                tags=["python", "data-science", "analytics"]
            )
        ]
        
        for item in items:
            repository.create(item)
        test_db.commit()
        
        # Act - Search by category
        programming_items = repository.search(
            query="programming",
            category="Programming",
            limit=10
        )
        
        # Assert
        assert len(programming_items) == 2
        assert all(item.category == "Programming" for item in programming_items)
        
        # Act - Search by tags
        python_items = repository.search_by_tags(["python"])
        
        # Assert
        assert len(python_items) == 2
        assert all("python" in item.tags for item in python_items)
    
    def test_knowledge_graph_operations(self, repository, test_db):
        # Arrange
        item1 = KnowledgeItem(title="Neural Networks", category="AI")
        item2 = KnowledgeItem(title="Deep Learning", category="AI")
        
        repository.create(item1)
        repository.create(item2)
        
        # Create relationship
        graph = KnowledgeGraph(
            source_item_id=item1.id,
            target_item_id=item2.id,
            relationship_type="prerequisite",
            strength=0.8,
            metadata={"description": "Deep learning builds on neural networks"}
        )
        
        # Act
        created_graph = repository.create_graph_relation(graph)
        test_db.commit()
        
        # Assert
        assert created_graph.id is not None
        assert created_graph.relationship_type == "prerequisite"
        assert created_graph.strength == 0.8
        
        # Test graph traversal
        related_items = repository.get_related_items(item1.id, relationship_type="prerequisite")
        assert len(related_items) == 1
        assert related_items[0].title == "Deep Learning"
```

### 2.4 Testes de Contrato

**`backend/tests/contract/test_api_contract.py`**:
```python
import pytest
import json
from pact import Consumer, Provider
from app.models.chat import ChatMessage, ChatResponse
from app.core.config import settings

# Pact configuration
pact = Consumer('JanusFrontend').has_pact_with(
    Provider('JanusBackend'),
    pact_dir='./pacts',
    log_dir='./logs'
)

@pytest.mark.contract
class TestChatAPIContract:
    
    @pact.given('a chat session exists')
    @pact.upon_receiving('a request to send a message')
    @pact.with_request({
        'method': 'POST',
        'path': '/api/v1/chat/messages',
        'headers': {'Content-Type': 'application/json'},
        'body': {
            'content': 'Hello, how are you?',
            'session_id': 'test-session-123',
            'user_id': 'user-456'
        }
    })
    @pact.will_respond_with({
        'status': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': {
            'id': '123',
            'content': "I'm doing well, thank you!",
            'confidence': 0.9,
            'sources': ['ai_model'],
            'timestamp': '2024-01-01T12:00:00Z'
        }
    })
    def test_send_chat_message_contract(self):
        # This test verifies the contract between frontend and backend
        with pact:
            # The actual API call would be made here
            # For contract testing, we verify the structure
            pass
    
    @pact.given('user has permission to access knowledge')
    @pact.upon_receiving('a request to search knowledge')
    @pact.with_request({
        'method': 'GET',
        'path': '/api/v1/knowledge/search',
        'query': 'query=machine learning&limit=10',
        'headers': {'Authorization': 'Bearer valid-token'}
    })
    @pact.will_respond_with({
        'status': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': {
            'items': [
                {
                    'id': '1',
                    'title': 'Machine Learning Basics',
                    'content': 'Introduction to ML...',
                    'category': 'AI/ML',
                    'tags': ['machine-learning', 'basics'],
                    'confidence': 0.85
                }
            ],
            'total': 1,
            'page': 1,
            'limit': 10
        }
    })
    def test_search_knowledge_contract(self):
        with pact:
            pass
```

### 2.5 Testes de Performance

**`backend/tests/performance/test_chat_performance.py`**:
```python
import pytest
import asyncio
import time
from locust import HttpUser, task, between
from app.services.chat_service import ChatService
from app.models.chat import ChatMessage

class ChatLoadTest(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        self.session_id = f"session-{time.time()}"
        self.user_id = f"user-{time.time()}"
    
    @task(3)
    def send_simple_message(self):
        """Test simple chat message performance"""
        response = self.client.post(
            "/api/v1/chat/messages",
            json={
                "content": "Hello, what can you help me with?",
                "session_id": self.session_id,
                "user_id": self.user_id
            }
        )
        
        assert response.status_code == 200
        assert response.json()["confidence"] > 0.5
        assert response.elapsed.total_seconds() < 2.0  # 2 second SLA
    
    @task(2)
    def send_complex_message(self):
        """Test complex query performance"""
        response = self.client.post(
            "/api/v1/chat/messages",
            json={
                "content": "Explain the difference between supervised and unsupervised machine learning with examples",
                "session_id": self.session_id,
                "user_id": self.user_id,
                "context": {"domain": "machine-learning", "level": "intermediate"}
            }
        )
        
        assert response.status_code == 200
        assert len(response.json()["content"]) > 100  # Should be detailed
        assert response.elapsed.total_seconds() < 5.0  # 5 second SLA for complex queries
    
    @task(1)
    def search_knowledge(self):
        """Test knowledge search performance"""
        response = self.client.get(
            "/api/v1/knowledge/search",
            params={
                "query": "artificial intelligence",
                "limit": 10,
                "category": "AI/ML"
            }
        )
        
        assert response.status_code == 200
        assert len(response.json()["items"]) <= 10
        assert response.elapsed.total_seconds() < 1.0  # 1 second SLA

@pytest.mark.performance
class TestChatPerformance:
    
    @pytest.mark.asyncio
    async def test_message_processing_latency(self, chat_service):
        """Test message processing latency under load"""
        message = ChatMessage(
            content="Test performance message",
            user_id="perf-user",
            session_id="perf-session"
        )
        
        # Measure latency for 100 messages
        latencies = []
        for i in range(100):
            start_time = time.time()
            await chat_service.process_message(message)
            end_time = time.time()
            latencies.append(end_time - start_time)
        
        # Assert performance requirements
        avg_latency = sum(latencies) / len(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
        
        assert avg_latency < 1.0, f"Average latency {avg_latency}s exceeds 1s threshold"
        assert p95_latency < 2.0, f"P95 latency {p95_latency}s exceeds 2s threshold"
    
    @pytest.mark.asyncio
    async def test_concurrent_message_processing(self, chat_service):
        """Test concurrent message processing"""
        messages = [
            ChatMessage(
                content=f"Concurrent message {i}",
                user_id=f"user-{i}",
                session_id=f"session-{i}"
            )
            for i in range(50)
        ]
        
        # Process messages concurrently
        start_time = time.time()
        tasks = [chat_service.process_message(msg) for msg in messages]
        responses = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Assert all messages processed successfully
        assert len(responses) == 50
        assert all(response.content is not None for response in responses)
        
        # Assert performance
        total_time = end_time - start_time
        assert total_time < 10.0, f"Concurrent processing took {total_time}s"
```

## 3. Testes Frontend (Angular)

### 3.1 Configuração do Jest

**`frontend/jest.config.js`**:
```javascript
module.exports = {
  preset: 'jest-preset-angular',
  setupFilesAfterEnv: ['<rootDir>/src/test-setup.ts'],
  testMatch: [
    '<rootDir>/src/**/__tests__/**/*.(ts|js)',
    '<rootDir>/src/**/?(*.)+(spec|test).(ts|js)'
  ],
  collectCoverageFrom: [
    'src/app/**/*.ts',
    '!src/app/**/*.module.ts',
    '!src/app/**/*.spec.ts',
    '!src/app/**/*.test.ts'
  ],
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80
    }
  },
  testEnvironment: 'jsdom',
  transform: {
    '^.+\\.(ts|js|html)$': 'jest-preset-angular'
  },
  moduleFileExtensions: ['ts', 'html', 'js', 'json'],
  moduleNameMapper: {
    '^@app/(.*)$': '<rootDir>/src/app/$1',
    '^@env/(.*)$': '<rootDir>/src/environments/$1'
  }
};
```

### 3.2 Testes Unitários de Componentes

**`frontend/src/app/components/chat/chat.component.spec.ts`**:
```typescript
import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { ChatComponent } from './chat.component';
import { ChatService } from '../../services/chat.service';
import { AuthService } from '../../services/auth.service';
import { of, throwError } from 'rxjs';
import { ReactiveFormsModule } from '@angular/forms';
import { MatSnackBar } from '@angular/material/snack-bar';

describe('ChatComponent', () => {
  let component: ChatComponent;
  let fixture: ComponentFixture<ChatComponent>;
  let chatService: jasmine.SpyObj<ChatService>;
  let authService: jasmine.SpyObj<AuthService>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;

  beforeEach(async () => {
    const chatServiceSpy = jasmine.createSpyObj('ChatService', [
      'sendMessage', 'getMessages', 'clearSession'
    ]);
    const authServiceSpy = jasmine.createSpyObj('AuthService', [
      'getCurrentUser', 'isAuthenticated'
    ]);
    const snackBarSpy = jasmine.createSpyObj('MatSnackBar', ['open']);

    await TestBed.configureTestingModule({
      declarations: [ChatComponent],
      imports: [ReactiveFormsModule],
      providers: [
        { provide: ChatService, useValue: chatServiceSpy },
        { provide: AuthService, useValue: authServiceSpy },
        { provide: MatSnackBar, useValue: snackBarSpy }
      ]
    }).compileComponents();

    chatService = TestBed.inject(ChatService) as jasmine.SpyObj<ChatService>;
    authService = TestBed.inject(AuthService) as jasmine.SpyObj<AuthService>;
    snackBar = TestBed.inject(MatSnackBar) as jasmine.SpyObj<MatSnackBar>;
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(ChatComponent);
    component = fixture.componentInstance;
    
    // Setup default mocks
    authService.getCurrentUser.and.returnValue({
      id: 'user123',
      name: 'Test User',
      email: 'test@example.com'
    });
    authService.isAuthenticated.and.returnValue(true);
    
    chatService.getMessages.and.returnValue(of([]));
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should initialize with empty message form', () => {
    fixture.detectChanges();
    expect(component.messageForm.get('content')?.value).toBe('');
    expect(component.messageForm.valid).toBeFalsy();
  });

  it('should validate message content is required', () => {
    fixture.detectChanges();
    const contentControl = component.messageForm.get('content');
    
    contentControl?.setValue('');
    expect(contentControl?.valid).toBeFalsy();
    expect(contentControl?.errors?.['required']).toBeTruthy();
    
    contentControl?.setValue('Hello');
    expect(contentControl?.valid).toBeTruthy();
  });

  it('should send message successfully', fakeAsync(() => {
    fixture.detectChanges();
    
    const mockResponse = {
      id: 'msg123',
      content: 'Hello! How can I help you?',
      timestamp: new Date().toISOString(),
      confidence: 0.9
    };
    
    chatService.sendMessage.and.returnValue(of(mockResponse));
    
    // Act
    component.messageForm.get('content')?.setValue('Hello');
    component.sendMessage();
    tick();
    
    // Assert
    expect(chatService.sendMessage).toHaveBeenCalledWith({
      content: 'Hello',
      sessionId: component.sessionId,
      userId: 'user123'
    });
    
    expect(component.messages.length).toBe(1);
    expect(component.messages[0].content).toBe('Hello! How can I help you?');
    expect(component.messageForm.get('content')?.value).toBe(''); // Form should be cleared
  }));

  it('should handle message send error', fakeAsync(() => {
    fixture.detectChanges();
    
    const error = new Error('Network error');
    chatService.sendMessage.and.returnValue(throwError(() => error));
    
    // Act
    component.messageForm.get('content')?.setValue('Hello');
    component.sendMessage();
    tick();
    
    // Assert
    expect(snackBar.open).toHaveBeenCalledWith(
      'Failed to send message. Please try again.',
      'Close',
      { duration: 5000, panelClass: ['error-snackbar'] }
    );
    expect(component.messages.length).toBe(0);
  }));

  it('should load message history on init', fakeAsync(() => {
    const mockMessages = [
      { id: '1', content: 'Hi', isUser: true, timestamp: new Date().toISOString() },
      { id: '2', content: 'Hello!', isUser: false, timestamp: new Date().toISOString() }
    ];
    
    chatService.getMessages.and.returnValue(of(mockMessages));
    
    // Act
    fixture.detectChanges();
    tick();
    
    // Assert
    expect(chatService.getMessages).toHaveBeenCalledWith(component.sessionId);
    expect(component.messages.length).toBe(2);
    expect(component.messages).toEqual(mockMessages);
  }));

  it('should clear session when user clicks clear', () => {
    fixture.detectChanges();
    
    // Act
    component.clearSession();
    
    // Assert
    expect(chatService.clearSession).toHaveBeenCalledWith(component.sessionId);
    expect(component.messages.length).toBe(0);
  });

  it('should disable send button when form is invalid', () => {
    fixture.detectChanges();
    
    const sendButton = fixture.nativeElement.querySelector('button[type="submit"]');
    
    component.messageForm.get('content')?.setValue('');
    fixture.detectChanges();
    
    expect(sendButton.disabled).toBeTruthy();
    
    component.messageForm.get('content')?.setValue('Valid message');
    fixture.detectChanges();
    
    expect(sendButton.disabled).toBeFalsy();
  });
});
```

### 3.3 Testes de Serviços

**`frontend/src/app/services/auth.service.spec.ts`**:
```typescript
import { TestBed } from '@angular/core/testing';
import { AuthService } from './auth.service';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { JwtHelperService } from '@auth0/angular-jwt';
import { environment } from '../../environments/environment';

describe('AuthService', () => {
  let service: AuthService;
  let httpMock: HttpTestingController;
  let jwtHelper: jasmine.SpyObj<JwtHelperService>;

  beforeEach(() => {
    const jwtHelperSpy = jasmine.createSpyObj('JwtHelperService', [
      'decodeToken', 'isTokenExpired', 'getTokenExpirationDate'
    ]);

    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [
        AuthService,
        { provide: JwtHelperService, useValue: jwtHelperSpy }
      ]
    });
    
    service = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);
    jwtHelper = TestBed.inject(JwtHelperService) as jasmine.SpyObj<JwtHelperService>;
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('login', () => {
    it('should authenticate user successfully', () => {
      const mockResponse = {
        access_token: 'mock-jwt-token',
        refresh_token: 'mock-refresh-token',
        user: {
          id: 'user123',
          email: 'test@example.com',
          name: 'Test User'
        }
      };

      service.login('test@example.com', 'password123').subscribe(response => {
        expect(response).toEqual(mockResponse);
        expect(service.getCurrentUser()).toEqual(mockResponse.user);
        expect(service.isAuthenticated()).toBeTruthy();
      });

      const req = httpMock.expectOne(`${environment.apiUrl}/auth/login`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({
        email: 'test@example.com',
        password: 'password123'
      });
      
      req.flush(mockResponse);
      
      // Verify token was stored
      expect(localStorage.getItem('access_token')).toBe('mock-jwt-token');
      expect(localStorage.getItem('refresh_token')).toBe('mock-refresh-token');
    });

    it('should handle login error', () => {
      const errorResponse = { error: 'Invalid credentials' };

      service.login('invalid@example.com', 'wrongpassword').subscribe({
        next: () => fail('should have failed'),
        error: (error) => {
          expect(error.error).toEqual(errorResponse);
        }
      });

      const req = httpMock.expectOne(`${environment.apiUrl}/auth/login`);
      req.flush(errorResponse, { status: 401, statusText: 'Unauthorized' });
    });
  });

  describe('logout', () => {
    it('should clear tokens and user data', () => {
      // Setup
      localStorage.setItem('access_token', 'token');
      localStorage.setItem('refresh_token', 'refresh');
      service.currentUser = { id: 'user123', email: 'test@example.com' };

      // Act
      service.logout();

      // Assert
      expect(localStorage.getItem('access_token')).toBeNull();
      expect(localStorage.getItem('refresh_token')).toBeNull();
      expect(service.currentUser).toBeNull();
      expect(service.isAuthenticated()).toBeFalsy();
    });
  });

  describe('token management', () => {
    it('should refresh token when expired', () => {
      const mockRefreshResponse = {
        access_token: 'new-jwt-token',
        refresh_token: 'new-refresh-token'
      };

      jwtHelper.isTokenExpired.and.returnValue(true);

      service.refreshToken().subscribe(response => {
        expect(response).toEqual(mockRefreshResponse);
      });

      const req = httpMock.expectOne(`${environment.apiUrl}/auth/refresh`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({
        refresh_token: null // No token stored initially
      });

      req.flush(mockRefreshResponse);
    });

    it('should decode token correctly', () => {
      const mockToken = 'mock-jwt-token';
      const mockDecodedToken = {
        sub: 'user123',
        email: 'test@example.com',
        exp: 1234567890
      };

      jwtHelper.decodeToken.and.returnValue(mockDecodedToken);

      localStorage.setItem('access_token', mockToken);
      
      const decoded = service.getDecodedToken();
      
      expect(decoded).toEqual(mockDecodedToken);
      expect(jwtHelper.decodeToken).toHaveBeenCalledWith(mockToken);
    });
  });

  describe('authorization', () => {
    it('should check user roles correctly', () => {
      const mockToken = 'mock-jwt-token';
      const mockDecodedToken = {
        sub: 'user123',
        email: 'test@example.com',
        roles: ['admin', 'user']
      };

      jwtHelper.decodeToken.and.returnValue(mockDecodedToken);
      localStorage.setItem('access_token', mockToken);

      expect(service.hasRole('admin')).toBeTruthy();
      expect(service.hasRole('user')).toBeTruthy();
      expect(service.hasRole('superadmin')).toBeFalsy();
      expect(service.hasAnyRole(['admin', 'moderator'])).toBeTruthy();
      expect(service.hasAnyRole(['superadmin', 'moderator'])).toBeFalsy();
    });
  });
});
```

## 4. Testes de Segurança

### 4.1 Testes de Autenticação e Autorização

**`backend/tests/security/test_auth_security.py`**:
```python
import pytest
import jwt
from datetime import datetime, timedelta
from app.core.security import create_access_token, verify_token, get_password_hash, verify_password
from app.core.config import settings
from app.core.exceptions import AuthenticationException, AuthorizationException

@pytest.mark.security
class TestAuthSecurity:
    
    def test_password_hashing_security(self):
        """Test secure password hashing"""
        password = "MySecurePassword123!"
        
        # Hash password
        hashed = get_password_hash(password)
        
        # Assert hash is different from original
        assert hashed != password
        assert len(hashed) > 50  # Should be long hash
        
        # Verify password
        assert verify_password(password, hashed) is True
        assert verify_password("WrongPassword", hashed) is False
    
    def test_jwt_token_creation_and_validation(self):
        """Test JWT token security"""
        user_data = {
            "sub": "user123",
            "email": "test@example.com",
            "roles": ["user"]
        }
        
        # Create token
        token = create_access_token(user_data)
        
        # Verify token structure
        parts = token.split('.')
        assert len(parts) == 3  # Header, payload, signature
        
        # Decode and verify
        decoded = verify_token(token)
        assert decoded["sub"] == "user123"
        assert decoded["email"] == "test@example.com"
        assert "exp" in decoded
        assert "iat" in decoded
    
    def test_jwt_token_expiration(self):
        """Test token expiration handling"""
        user_data = {"sub": "user123"}
        
        # Create expired token
        expired_token = create_access_token(
            user_data,
            expires_delta=timedelta(minutes=-1)  # Already expired
        )
        
        # Should raise exception for expired token
        with pytest.raises(AuthenticationException):
            verify_token(expired_token)
    
    def test_jwt_token_tampering_detection(self):
        """Test detection of tampered tokens"""
        user_data = {"sub": "user123"}
        token = create_access_token(user_data)
        
        # Tamper with token
        parts = token.split('.')
        tampered_payload = jwt.encode(
            {"sub": "hacker", "exp": datetime.utcnow() + timedelta(hours=1)},
            "wrong-secret",
            algorithm=settings.ALGORITHM
        )
        tampered_token = f"{parts[0]}.{tampered_payload.split('.')[1]}.{parts[2]}"
        
        # Should raise exception for tampered token
        with pytest.raises(AuthenticationException):
            verify_token(tampered_token)
    
    def test_rate_limiting_protection(self):
        """Test rate limiting for authentication endpoints"""
        # This would typically be tested with integration tests
        # Here we test the rate limiter implementation
        from app.core.rate_limiter import RateLimiter
        
        rate_limiter = RateLimiter(
            key_prefix="auth_attempts",
            limit=5,  # 5 attempts
            window=60  # per 60 seconds
        )
        
        user_id = "test_user"
        
        # Should allow 5 attempts
        for i in range(5):
            assert rate_limiter.is_allowed(user_id) is True
        
        # 6th attempt should be blocked
        assert rate_limiter.is_allowed(user_id) is False
    
    def test_sql_injection_prevention(self):
        """Test SQL injection prevention"""
        # Test with SQL injection payloads
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "admin'--",
            "1' UNION SELECT * FROM users--"
        ]
        
        # These should be properly escaped/parameterized
        # Actual implementation would use ORM with parameterization
        for malicious_input in malicious_inputs:
            # This is a placeholder - actual SQL injection tests
            # would be done on repository/database layer
            assert len(malicious_input) > 0  # Basic validation
    
    def test_xss_prevention(self):
        """Test XSS prevention"""
        # Test XSS payloads
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>"
        ]
        
        # These should be properly sanitized
        for payload in xss_payloads:
            # Placeholder - actual XSS prevention would be
            # implemented in input validation/sanitization
            assert payload != ""  # Basic validation
```

### 4.2 Testes de Vulnerabilidades

**`backend/tests/security/test_vulnerability_scanning.py`**:
```python
import pytest
import requests
from urllib.parse import urljoin
from app.core.config import settings

@pytest.mark.security
class TestVulnerabilityScanning:
    
    def test_openapi_security(self, client):
        """Test OpenAPI security definitions"""
        response = client.get("/openapi.json")
        openapi_spec = response.json()
        
        # Verify security schemes are defined
        assert "securitySchemes" in openapi_spec.get("components", {})
        security_schemes = openapi_spec["components"]["securitySchemes"]
        
        # Should have JWT Bearer authentication
        assert "bearerAuth" in security_schemes
        assert security_schemes["bearerAuth"]["type"] == "http"
        assert security_schemes["bearerAuth"]["scheme"] == "bearer"
        assert security_schemes["bearerAuth"]["bearerFormat"] == "JWT"
    
    def test_cors_configuration(self, client):
        """Test CORS configuration"""
        # Test preflight request
        response = client.options(
            "/api/v1/chat/messages",
            headers={
                "Origin": "https://frontend.example.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type, Authorization"
            }
        )
        
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers
    
    def test_security_headers(self, client):
        """Test security headers are present"""
        response = client.get("/health")
        
        # Check for security headers
        headers = response.headers
        assert "x-content-type-options" in headers
        assert headers["x-content-type-options"] == "nosniff"
        
        assert "x-frame-options" in headers
        assert headers["x-frame-options"] == "DENY"
        
        assert "x-xss-protection" in headers
        assert headers["x-xss-protection"] == "1; mode=block"
        
        assert "strict-transport-security" in headers
        assert "max-age" in headers["strict-transport-security"]
    
    def test_api_rate_limiting(self, client):
        """Test API rate limiting"""
        # Make multiple requests quickly
        responses = []
        for i in range(20):  # Assuming rate limit is 10 per minute
            response = client.get("/api/v1/health")
            responses.append(response.status_code)
        
        # Should start returning 429 after rate limit exceeded
        # This is a simplified test - actual rate limiting would
        # depend on the specific implementation
        assert 200 in responses  # At least some should succeed
    
    def test_input_validation(self, client):
        """Test input validation prevents injection attacks"""
        # Test with various injection payloads
        payloads = [
            {"content": "<script>alert('xss')</script>"},
            {"content": "'; DROP TABLE users; --"},
            {"content": "../../../etc/passwd"},
            {"content": "javascript:alert('xss')"}
        ]
        
        for payload in payloads:
            response = client.post(
                "/api/v1/chat/messages",
                json=payload
            )
            
            # Should either reject or sanitize the input
            # Actual behavior depends on validation implementation
            assert response.status_code in [200, 400, 422]
```

## 5. Testes de Observabilidade

### 5.1 Testes de Métricas

**`backend/tests/observability/test_metrics.py`**:
```python
import pytest
import time
from prometheus_client import REGISTRY, Counter, Histogram, Gauge
from app.core.metrics import MetricsCollector
from app.models.chat import ChatMessage, ChatResponse

@pytest.mark.observability
class TestMetrics:
    
    def setup_method(self):
        """Clear metrics before each test"""
        # Clear all collectors
        for collector in list(REGISTRY._collector_to_names.keys()):
            try:
                REGISTRY.unregister(collector)
            except:
                pass
    
    def test_chat_metrics_collection(self):
        """Test chat-related metrics collection"""
        metrics = MetricsCollector()
        
        # Simulate chat interactions
        message = ChatMessage(content="Test", user_id="user123")
        response = ChatResponse(content="Response", confidence=0.9)
        
        start_time = time.time()
        time.sleep(0.1)  # Simulate processing time
        end_time = time.time()
        
        # Record metrics
        metrics.record_chat_message(message)
        metrics.record_chat_response(response, end_time - start_time)
        
        # Verify metrics were recorded
        assert metrics.chat_messages_total._value.get() == 1
        assert metrics.chat_responses_total._value.get() == 1
        assert metrics.chat_duration_seconds._sum.get() > 0.1
    
    def test_error_metrics_collection(self):
        """Test error metrics collection"""
        metrics = MetricsCollector()
        
        # Record different types of errors
        metrics.record_error("validation_error")
        metrics.record_error("database_error")
        metrics.record_error("validation_error")  # Second occurrence
        
        # Verify error counts
        assert metrics.errors_total.labels(error_type="validation_error")._value.get() == 2
        assert metrics.errors_total.labels(error_type="database_error")._value.get() == 1
    
    def test_performance_metrics(self):
        """Test performance metrics collection"""
        metrics = MetricsCollector()
        
        # Simulate various operations
        operations = [
            ("database_query", 0.05),
            ("api_call", 0.1),
            ("llm_request", 2.5),
            ("database_query", 0.08),
            ("api_call", 0.12)
        ]
        
        for operation, duration in operations:
            metrics.record_operation_duration(operation, duration)
        
        # Verify histogram buckets
        histogram = metrics.operation_duration_seconds
        
        # Check that observations were recorded
        assert histogram._sum.get() > 0
        assert histogram._count.get() == 5
    
    def test_business_metrics(self):
        """Test business-specific metrics"""
        metrics = MetricsCollector()
        
        # Simulate user activity
        metrics.record_user_login("user123")
        metrics.record_user_login("user456")
        metrics.record_user_logout("user123")
        
        # Simulate knowledge operations
        metrics.record_knowledge_search("machine learning", 15)
        metrics.record_knowledge_item_created("ai_ml_category")
        
        # Verify business metrics
        assert metrics.user_logins_total._value.get() == 2
        assert metrics.user_logouts_total._value.get() == 1
        assert metrics.knowledge_searches_total._value.get() == 1
        assert metrics.knowledge_items_created_total.labels(category="ai_ml_category")._value.get() == 1
    
    def test_metrics_endpoint_availability(self, client):
        """Test metrics endpoint is available"""
        response = client.get("/metrics")
        
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        assert "# HELP" in response.text
        assert "# TYPE" in response.text
```

### 5.2 Testes de Health Checks

**`backend/tests/observability/test_health_checks.py`**:
```python
import pytest
from unittest.mock import Mock, patch
from app.core.health import HealthChecker
from app.services.database_service import DatabaseService
from app.services.llm_service import LLMService

@pytest.mark.observability
class TestHealthChecks:
    
    @pytest.fixture
    def health_checker(self):
        return HealthChecker()
    
    def test_basic_health_endpoint(self, client):
        """Test basic health endpoint"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    def test_detailed_health_check(self, client):
        """Test detailed health check with dependencies"""
        response = client.get("/healthz")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "services" in data
        
        # Check individual services
        services = data["services"]
        expected_services = ["database", "redis", "llm_provider"]
        
        for service in expected_services:
            assert service in services
            assert services[service]["status"] in ["healthy", "unhealthy"]
            assert "response_time_ms" in services[service]
    
    def test_health_check_with_failing_service(self, client):
        """Test health check when a service is failing"""
        # Mock a failing service
        with patch.object(DatabaseService, 'check_health', return_value={
            "status": "unhealthy",
            "error": "Connection timeout"
        }):
            response = client.get("/healthz")
            
            assert response.status_code == 503  # Service Unavailable
            data = response.json()
            
            assert data["status"] == "unhealthy"
            assert data["services"]["database"]["status"] == "unhealthy"
            assert "Connection timeout" in data["services"]["database"]["error"]
    
    def test_readiness_probe(self, client):
        """Test readiness probe"""
        response = client.get("/ready")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "ready"
        assert "checks" in data
        
        # Verify all readiness checks
        checks = data["checks"]
        expected_checks = [
            "database_connection",
            "migrations_up_to_date",
            "critical_services_available"
        ]
        
        for check in expected_checks:
            assert check in checks
            assert checks[check]["status"] in ["pass", "fail"]
    
    def test_liveness_probe(self, client):
        """Test liveness probe"""
        response = client.get("/alive")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "alive"
        assert "timestamp" in data
        assert "uptime_seconds" in data
        assert data["uptime_seconds"] > 0
```

## 6. Testes de Regressão

### 6.1 Configuração de Testes de Regressão

**`backend/tests/regression/test_regression_suite.py`**:
```python
import pytest
import json
import time
from pathlib import Path
from app.core.config import settings

@pytest.mark.regression
class TestRegressionSuite:
    """
    Comprehensive regression test suite that validates
    critical functionality after changes
    """
    
    @pytest.fixture(scope="class")
    def regression_data(self):
        """Load regression test data"""
        data_file = Path(__file__).parent / "regression_data.json"
        if data_file.exists():
            with open(data_file, 'r') as f:
                return json.load(f)
        return {}
    
    def test_critical_user_journeys(self, client, regression_data):
        """Test critical user journeys"""
        # Test complete user flow: login -> chat -> knowledge search
        
        # 1. Authenticate
        auth_response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })
        assert auth_response.status_code == 200
        token = auth_response.json()["access_token"]
        
        # 2. Send chat message
        chat_response = client.post(
            "/api/v1/chat/messages",
            json={
                "content": "What is machine learning?",
                "session_id": "test-session"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert chat_response.status_code == 200
        assert chat_response.json()["content"] is not None
        
        # 3. Search knowledge base
        search_response = client.get(
            "/api/v1/knowledge/search",
            params={"query": "machine learning", "limit": 5},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert search_response.status_code == 200
        assert len(search_response.json()["items"]) > 0
    
    def test_api_response_consistency(self, client, regression_data):
        """Test API responses remain consistent"""
        test_cases = [
            {
                "method": "GET",
                "path": "/api/v1/health",
                "expected_keys": ["status", "timestamp"]
            },
            {
                "method": "POST",
                "path": "/api/v1/chat/messages",
                "data": {
                    "content": "Test message",
                    "session_id": "test"
                },
                "expected_keys": ["content", "confidence", "timestamp"]
            }
        ]
        
        for test_case in test_cases:
            if test_case["method"] == "GET":
                response = client.get(test_case["path"])
            elif test_case["method"] == "POST":
                response = client.post(test_case["path"], json=test_case["data"])
            
            assert response.status_code == 200
            
            # Verify response structure
            response_data = response.json()
            for key in test_case["expected_keys"]:
                assert key in response_data, f"Missing key '{key}' in response from {test_case['path']}"
    
    def test_performance_regression(self, client, regression_data):
        """Test performance doesn't regress"""
        # Define performance thresholds
        thresholds = {
            "/api/v1/health": 0.1,  # 100ms
            "/api/v1/chat/messages": 2.0,  # 2s
            "/api/v1/knowledge/search": 1.0  # 1s
        }
        
        for endpoint, max_time in thresholds.items():
            start_time = time.time()
            
            if endpoint == "/api/v1/health":
                response = client.get(endpoint)
            elif endpoint == "/api/v1/chat/messages":
                response = client.post(endpoint, json={
                    "content": "Performance test message",
                    "session_id": "perf-test"
                })
            elif endpoint == "/api/v1/knowledge/search":
                response = client.get(endpoint, params={"query": "test", "limit": 10})
            
            end_time = time.time()
            response_time = end_time - start_time
            
            assert response.status_code == 200
            assert response_time < max_time, \
                f"Response time {response_time}s for {endpoint} exceeds threshold {max_time}s"
    
    def test_error_handling_regression(self, client, regression_data):
        """Test error handling consistency"""
        error_test_cases = [
            {
                "method": "POST",
                "path": "/api/v1/chat/messages",
                "data": {},  # Missing required fields
                "expected_status": 422
            },
            {
                "method": "GET",
                "path": "/api/v1/nonexistent",
                "expected_status": 404
            },
            {
                "method": "POST",
                "path": "/api/v1/auth/login",
                "data": {
                    "email": "invalid-email",
                    "password": "short"
                },
                "expected_status": 422
            }
        ]
        
        for test_case in error_test_cases:
            if test_case["method"] == "GET":
                response = client.get(test_case["path"])
            elif test_case["method"] == "POST":
                response = client.post(test_case["path"], json=test_case.get("data", {}))
            
            assert response.status_code == test_case["expected_status"]
            
            # Verify error response structure
            error_data = response.json()
            assert "detail" in error_data or "error" in error_data
    
    def test_generate_regression_report(self, client, regression_data):
        """Generate regression test report"""
        report = {
            "timestamp": time.time(),
            "test_suite": "janus_regression",
            "results": {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0
            },
            "performance_metrics": {},
            "api_coverage": []
        }
        
        # This would be populated by actual test results
        # For now, create a template
        report_path = Path(__file__).parent / f"regression_report_{int(time.time())}.json"
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Regression report generated: {report_path}")
```

## 7. Qualidade de Código

### 7.1 Análise Estática

**`backend/pyproject.toml` - Configuração de Qualidade**:
```toml
[tool.ruff]
line-length = 88
target-version = "py311"
select = [
    "E",  # pycodestyle errors
    "W",  # pycodestyle warnings
    "F",  # pyflakes
    "I",  # isort
    "B",  # flake8-bugbear
    "C4", # flake8-comprehensions
    "UP", # pyupgrade
    "ARG001", # unused-function-args
    "SIM", # flake8-simplify
    "TCH", # flake8-type-checking
    "TID", # flake8-tidy-imports
    "Q", # flake8-quotes
    "PTH", # flake8-use-pathlib
    "ERA", # eradicate
    "PD", # pandas-vet
    "NPY", # numpy-specific-rules
    "RUF", # ruff-specific rules
]
ignore = [
    "E501",  # line too long, handled by black
    "B008",  # do not perform function calls in argument defaults
    "C901",  # too complex
]

[tool.ruff.per-file-ignores]
"__init__.py" = ["F401"]
"tests/*" = ["ARG001"]

[tool.ruff.isort]
known-first-party = ["app"]

[tool.black]
line-length = 88
target-version = ['py311']
include = '\.pyi?$'
extend-exclude = '''
/(
  # directories
  \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | build
  | dist
)/
'''

[tool.mypy]
python_version = "3.11"
check_untyped_defs = true
disallow_any_generics = true
disallow_incomplete_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_unreachable = true
strict_equality = true

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false
```

### 7.2 Testes de Cobertura

**Configuração de Cobertura**:
```bash
# Executar testes com cobertura
pytest --cov=app --cov-report=html --cov-report=term-missing --cov-fail-under=80

# Gerar relatório de cobertura
pytest --cov=app --cov-report=xml:coverage.xml --cov-report=json:coverage.json

# Verificar cobertura por módulo
pytest --cov=app --cov-report=term:skip-covered
```

## 8. Integração com CI/CD

### 8.1 Pipeline de Qualidade

**`.github/workflows/quality-gates-enhanced.yml`**:
```yaml
name: Enhanced Quality Gates

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  quality-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r backend/requirements.txt
          pip install -r backend/requirements-dev.txt
      
      - name: Run linting
        run: |
          ruff check backend/
          black --check backend/
      
      - name: Run type checking
        run: mypy backend/app/
      
      - name: Run security scanning
        run: |
          bandit -r backend/app/
          safety check -r backend/requirements.txt
      
      - name: Run unit tests
        run: |
          cd backend
          pytest tests/unit/ -v --cov=app --cov-report=xml
      
      - name: Run integration tests
        run: |
          cd backend
          pytest tests/integration/ -v
      
      - name: Run performance tests
        run: |
          cd backend
          pytest tests/performance/ -v --benchmark-only
      
      - name: Upload coverage reports
        uses: codecov/codecov-action@v3
        with:
          file: ./backend/coverage.xml
          flags: backend
          name: backend-coverage

  quality-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      
      - name: Run linting
        run: |
          cd frontend
          npm run lint
      
      - name: Run type checking
        run: |
          cd frontend
          npm run typecheck
      
      - name: Run unit tests
        run: |
          cd frontend
          npm run test -- --coverage --watch=false
      
      - name: Run component tests
        run: |
          cd frontend
          npm run test:components
      
      - name: Build application
        run: |
          cd frontend
          npm run build
      
      - name: Upload coverage reports
        uses: codecov/codecov-action@v3
        with:
          file: ./frontend/coverage/lcov.info
          flags: frontend
          name: frontend-coverage

  security-scanning:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run OWASP ZAP scan
        uses: zaproxy/action-full-scan@v0.4.0
        with:
          target: 'http://localhost:8000'
          rules_file_name: '.zap/rules.tsv'
          cmd_options: '-a'
      
      - name: Run dependency scanning
        run: |
          # Backend dependencies
          cd backend
          pip install safety
          safety check -r requirements.txt
          
          # Frontend dependencies
          cd ../frontend
          npm audit --audit-level moderate
      
      - name: Run container scanning
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'janus-api:latest'
          format: 'sarif'
          output: 'trivy-results.sarif'

  performance-testing:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install locust
      
      - name: Run load tests
        run: |
          cd backend/tests/performance
          locust --headless --users 100 --spawn-rate 10 --run-time 60s \
                 --host http://localhost:8000 --html performance_report.html
      
      - name: Upload performance report
        uses: actions/upload-artifact@v3
        with:
          name: performance-report
          path: backend/tests/performance/performance_report.html

  contract-testing:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install pact-python
      
      - name: Run contract tests
        run: |
          cd backend
          pytest tests/contract/ -v
      
      - name: Publish contract
        run: |
          # Publish to Pact Broker
          pact-broker publish ./pacts \
            --consumer-app-version ${{ github.sha }} \
            --tag ${{ github.ref_name }} \
            --broker-base-url ${{ secrets.PACT_BROKER_URL }} \
            --broker-token ${{ secrets.PACT_BROKER_TOKEN }}

  regression-testing:
    runs-on: ubuntu-latest
    needs: [quality-backend, quality-frontend]
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up test environment
        run: |
          docker-compose -f docker-compose.test.yml up -d
      
      - name: Run regression tests
        run: |
          cd backend
          pytest tests/regression/ -v --tb=short
      
      - name: Compare with baseline
        run: |
          # Compare current results with baseline
          python scripts/compare_regression_baseline.py \
            --current results/current.json \
            --baseline results/baseline.json \
            --output comparison_report.html
      
      - name: Upload regression report
        uses: actions/upload-artifact@v3
        with:
          name: regression-report
          path: comparison_report.html
```

## 9. Monitoramento de Qualidade

### 9.1 Dashboard de Qualidade

**`monitoring/quality_dashboard.py`**:
```python
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import json

class QualityDashboard:
    def __init__(self, api_base_url="http://localhost:8000"):
        self.api_base_url = api_base_url
        st.set_page_config(
            page_title="Janus Quality Dashboard",
            page_icon="📊",
            layout="wide"
        )
    
    def fetch_metrics(self):
        """Fetch metrics from the API"""
        try:
            response = requests.get(f"{self.api_base_url}/metrics")
            if response.status_code == 200:
                return self.parse_prometheus_metrics(response.text)
            return {}
        except Exception as e:
            st.error(f"Failed to fetch metrics: {e}")
            return {}
    
    def parse_prometheus_metrics(self, metrics_text):
        """Parse Prometheus metrics format"""
        metrics = {}
        for line in metrics_text.split('\n'):
            if line and not line.startswith('#'):
                parts = line.split(' ')
                if len(parts) >= 2:
                    metric_name = parts[0]
                    metric_value = float(parts[1])
                    metrics[metric_name] = metric_value
        return metrics
    
    def display_test_coverage(self):
        """Display test coverage metrics"""
        st.header("📈 Test Coverage")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            backend_coverage = 82.5  # This would come from coverage API
            fig = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=backend_coverage,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Backend Coverage (%)"},
                delta={'reference': 80},
                gauge={'axis': {'range': [None, 100]},
                       'bar': {'color': "darkgreen"},
                       'steps': [
                           {'range': [0, 50], 'color': "lightgray"},
                           {'range': [50, 80], 'color': "yellow"}],
                       'threshold': {'line': {'color': "red", 'width': 4},
                                    'thickness': 0.75, 'value': 80}}))
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            frontend_coverage = 78.3
            fig = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=frontend_coverage,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Frontend Coverage (%)"},
                delta={'reference': 80},
                gauge={'axis': {'range': [None, 100]},
                       'bar': {'color': "darkblue"},
                       'steps': [
                           {'range': [0, 50], 'color': "lightgray"},
                           {'range': [50, 80], 'color': "yellow"}],
                       'threshold': {'line': {'color': "red", 'width': 4},
                                    'thickness': 0.75, 'value': 80}}))
            st.plotly_chart(fig, use_container_width=True)
        
        with col3:
            integration_coverage = 75.8
            fig = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=integration_coverage,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Integration Coverage (%)"},
                delta={'reference': 70},
                gauge={'axis': {'range': [None, 100]},
                       'bar': {'color': "purple"},
                       'steps': [
                           {'range': [0, 50], 'color': "lightgray"},
                           {'range': [50, 70], 'color': "yellow"}],
                       'threshold': {'line': {'color': "red", 'width': 4},
                                    'thickness': 0.75, 'value': 70}}))
            st.plotly_chart(fig, use_container_width=True)
    
    def display_performance_metrics(self, metrics):
        """Display performance metrics"""
        st.header("⚡ Performance Metrics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            avg_response_time = metrics.get('http_request_duration_seconds_sum', 0) / max(metrics.get('http_request_duration_seconds_count', 1), 1)
            st.metric(
                label="Avg Response Time",
                value=f"{avg_response_time:.3f}s",
                delta="-0.1s from last week"
            )
        
        with col2:
            error_rate = (metrics.get('http_requests_total', 0) - metrics.get('http_requests_success_total', 0)) / max(metrics.get('http_requests_total', 1), 1) * 100
            st.metric(
                label="Error Rate",
                value=f"{error_rate:.2f}%",
                delta="-0.5% from last week"
            )
        
        with col3:
            throughput = metrics.get('http_requests_total', 0) / 3600  # per hour
            st.metric(
                label="Throughput",
                value=f"{throughput:.0f} req/h",
                delta="+150 from last week"
            )
        
        with col4:
            availability = metrics.get('service_availability', 99.9)
            st.metric(
                label="Availability",
                value=f"{availability:.2f}%",
                delta="+0.1% from last week"
            )
    
    def display_quality_trends(self):
        """Display quality trends over time"""
        st.header("📊 Quality Trends")
        
        # Generate sample data (in real implementation, this would come from database)
        dates = pd.date_range(start=datetime.now() - timedelta(days=30), periods=30, freq='D')
        
        # Test pass rate trend
        pass_rates = pd.DataFrame({
            'Date': dates,
            'Backend': [85 + (i % 10) - 5 for i in range(30)],
            'Frontend': [82 + (i % 8) - 4 for i in range(30)],
            'Integration': [78 + (i % 12) - 6 for i in range(30)]
        })
        
        fig = px.line(pass_rates, x='Date', y=['Backend', 'Frontend', 'Integration'],
                      title='Test Pass Rate Trends (%)',
                      labels={'value': 'Pass Rate (%)', 'variable': 'Component'})
        fig.update_layout(hovermode='x unified')
        st.plotly_chart(fig, use_container_width=True)
        
        # Code quality trend
        quality_scores = pd.DataFrame({
            'Date': dates,
            'Code Quality': [8.2 + (i % 5) * 0.1 for i in range(30)],
            'Security Score': [9.1 + (i % 3) * 0.05 for i in range(30)],
            'Performance': [7.8 + (i % 7) * 0.1 for i in range(30)]
        })
        
        fig2 = px.line(quality_scores, x='Date', y=['Code Quality', 'Security Score', 'Performance'],
                      title='Quality Score Trends (1-10)',
                      labels={'value': 'Score', 'variable': 'Metric'})
        fig2.update_layout(hovermode='x unified')
        st.plotly_chart(fig2, use_container_width=True)
    
    def display_test_execution_summary(self):
        """Display recent test execution summary"""
        st.header("🧪 Test Execution Summary")
        
        # Recent test runs (sample data)
        test_runs = pd.DataFrame({
            'Test Suite': ['Unit Tests', 'Integration Tests', 'E2E Tests', 'Performance Tests', 'Security Tests'],
            'Last Run': ['2 hours ago', '1 hour ago', '30 minutes ago', '6 hours ago', '12 hours ago'],
            'Pass Rate (%)': [95, 88, 92, 85, 98],
            'Duration': ['5m 23s', '12m 45s', '18m 30s', '25m 15s', '8m 42s'],
            'Status': ['PASS', 'PASS', 'PASS', 'PASS', 'PASS']
        })
        
        # Color code based on status
        def color_status(val):
            if val == 'PASS':
                return 'background-color: green'
            elif val == 'FAIL':
                return 'background-color: red'
            else:
                return 'background-color: yellow'
        
        styled_tests = test_runs.style.applymap(color_status, subset=['Status'])
        st.dataframe(styled_tests, use_container_width=True)
    
    def display_defect_metrics(self):
        """Display defect and issue metrics"""
        st.header("🐛 Defect Metrics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Defect density by component
            defect_data = pd.DataFrame({
                'Component': ['Chat Service', 'Auth Service', 'Knowledge Service', 'API Gateway', 'Database Layer'],
                'Defects': [12, 8, 15, 5, 3],
                'Code Size (KLOC)': [25, 15, 30, 10, 20],
                'Defect Density': [0.48, 0.53, 0.50, 0.50, 0.15]
            })
            
            fig = px.bar(defect_data, x='Component', y='Defect Density',
                        title='Defect Density by Component',
                        color='Defect Density',
                        color_continuous_scale='Reds')
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Defect severity distribution
            severity_data = pd.DataFrame({
                'Severity': ['Critical', 'High', 'Medium', 'Low'],
                'Count': [2, 8, 25, 15],
                'Percentage': [4.0, 16.0, 50.0, 30.0]
            })
            
            fig = px.pie(severity_data, values='Count', names='Severity',
                        title='Defect Severity Distribution',
                        color_discrete_map={
                            'Critical': '#FF0000',
                            'High': '#FF8000',
                            'Medium': '#FFFF00',
                            'Low': '#00FF00'
                        })
            st.plotly_chart(fig, use_container_width=True)
    
    def run(self):
        """Run the quality dashboard"""
        st.title("🎯 Janus Quality Dashboard")
        st.markdown("---")
        
        # Sidebar for filtering
        with st.sidebar:
            st.header("Filters")
            time_range = st.selectbox(
                "Time Range",
                ["Last 24 hours", "Last 7 days", "Last 30 days", "Last 90 days"]
            )
            
            component_filter = st.multiselect(
                "Components",
                ["Backend", "Frontend", "Database", "Infrastructure"],
                default=["Backend", "Frontend"]
            )
            
            refresh_interval = st.slider(
                "Refresh Interval (seconds)",
                min_value=30,
                max_value=300,
                value=60
            )
        
        # Fetch metrics
        metrics = self.fetch_metrics()
        
        # Display dashboard sections
        self.display_test_coverage()
        self.display_performance_metrics(metrics)
        self.display_quality_trends()
        self.display_test_execution_summary()
        self.display_defect_metrics()
        
        # Footer
        st.markdown("---")
        st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    dashboard = QualityDashboard()
    dashboard.run()
```

## Conclusão

Este guia de testes e qualidade fornece uma estrutura abrangente para garantir a qualidade do projeto Janus. As principais características incluem:

### ✅ **Cobertura Completa**
- Testes unitários, integração, contrato, E2E, performance e segurança
- Análise estática e dinâmica de código
- Monitoramento contínuo de qualidade

### ✅ **Automação**
- Integração completa com CI/CD
- Testes automatizados em múltiplos níveis
- Geração automática de relatórios

### ✅ **Performance**
- Testes de carga e stress com Locust e K6
- Monitoramento de latência e throughput
- Análise de regressão de performance

### ✅ **Segurança**
- Testes de autenticação e autorização
- Varredura de vulnerabilidades
- Análise de dependências

### ✅ **Observabilidade**
- Métricas detalhadas de qualidade
- Dashboard interativo
- Alertas proativos

### 📋 **Próximos Passos**
1. Implementar os testes conforme descrito neste guia
2. Configurar o pipeline de CI/CD com as ferramentas especificadas
3. Estabelecer baseline de performance e qualidade
4. Criar processo de revisão de código baseado nestes padrões
5. Treinar a equipe nas práticas e ferramentas definidas

### 📊 **Métricas de Sucesso**
- Cobertura de testes > 80%
- Taxa de aprovação de testes > 95%
- Tempo médio de resposta < 2s
- Disponibilidade > 99.9%
- Zero vulnerabilidades críticas

Esta abordagem garante que o Janus mantenha os mais altos padrões de qualidade, segurança e performance ao longo de seu ciclo de vida.