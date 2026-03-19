# Guia de Integração com LLMs

## Visão Geral

O Janus suporta múltiplos provedores de LLM (Large Language Models) através de uma arquitetura unificada que permite fácil troca entre diferentes modelos e provedores.

## Provedores Suportados

### OpenAI
- **Modelos**: GPT-4, GPT-3.5-turbo, GPT-4-turbo
- **Uso**: Chat, análise de código, geração de conteúdo
- **Configuração**: `OPENAI_API_KEY` no arquivo `.env`

### Anthropic Claude
- **Modelos**: Claude-3.5-Sonnet, Claude-3-Opus, Claude-3-Haiku
- **Uso**: Análise técnica, revisão de código, documentação
- **Configuração**: `ANTHROPIC_API_KEY` no arquivo `.env`

### Google Gemini
- **Modelos**: Gemini Pro, Gemini Flash
- **Uso**: Processamento de texto, análise multimodal
- **Configuração**: `GOOGLE_API_KEY` no arquivo `.env`

### Ollama (Local)
- **Modelos**: Llama 2, Code Llama, Mistral, entre outros
- **Uso**: Desenvolvimento local, privacidade de dados
- **Configuração**: Serviço rodando localmente na porta 11434

### OpenRouter
- **Modelos**: Acesso a múltiplos modelos através de uma única API
- **Uso**: Comparação de modelos, fallback entre provedores
- **Configuração**: `OPEN_ROUTER_API_KEY` no arquivo `.env`

## Configuração

### 1. Variáveis de Ambiente

Configure as chaves de API no arquivo `.env`:

```bash
# OpenAI
OPENAI_API_KEY=sk-your-openai-key
OPENAI_ORG_ID=org-your-org-id

# Anthropic
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key

# Google Gemini
GOOGLE_API_KEY=your-google-api-key

# OpenRouter
OPEN_ROUTER_API_KEY=sk-or-your-openrouter-key

# Ollama (local - não requer chave)
OLLAMA_HOST=http://localhost:11434
```

### 2. Configuração de Modelos

O arquivo `backend/app/config/llm_config.py` contém as configurações padrão para cada modelo:

```python
LLM_CONFIGS = {
    "openai": {
        "default_model": "gpt-4-turbo-preview",
        "max_tokens": 4096,
        "temperature": 0.7,
        "timeout": 30
    },
    "anthropic": {
        "default_model": "claude-3.5-sonnet-20241022",
        "max_tokens": 4096,
        "temperature": 0.7,
        "timeout": 30
    },
    "google": {
        "default_model": "gemini-pro",
        "max_tokens": 4096,
        "temperature": 0.7,
        "timeout": 30
    },
    "ollama": {
        "default_model": "llama2",
        "max_tokens": 4096,
        "temperature": 0.7,
        "timeout": 60
    }
}
```

## Uso na API

### Selecionando um Provedor

```python
from app.services.llm_service import LLMService

# Inicializar serviço com provedor específico
llm_service = LLMService(provider="openai")

# Ou usar o provedor padrão (configurado no .env)
llm_service = LLMService()
```

### Chat com LLM

```python
# Chat simples
response = llm_service.chat(
    messages=[
        {"role": "user", "content": "Explique o conceito de recursão em programação"}
    ],
    model="gpt-4-turbo-preview"
)

# Chat com contexto de sistema
response = llm_service.chat(
    messages=[
        {"role": "system", "content": "Você é um assistente técnico especializado em Python."},
        {"role": "user", "content": "Como implemento um decorator?"}
    ],
    temperature=0.3,
    max_tokens=2000
)
```

### Análise de Código

```python
# Análise de código com contexto
analysis = llm_service.analyze_code(
    code="""
    def fibonacci(n):
        if n <= 1:
            return n
        return fibonacci(n-1) + fibonacci(n-2)
    """,
    language="python",
    analysis_type="performance"
)

# Revisão de código
review = llm_service.review_code(
    code="""
    async function fetchData() {
        const response = await fetch('/api/data');
        return response.json();
    }
    """,
    language="javascript"
)
```

### Geração de Conteúdo

```python
# Gerar documentação
docs = llm_service.generate_documentation(
    code=python_code,
    doc_type="api_reference"
)

# Gerar testes
tests = llm_service.generate_tests(
    code=python_code,
    test_framework="pytest"
)
```

## Integração com Frontend

### Configuração do Serviço Angular

```typescript
// src/app/services/llm.service.ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class LLMService {
  private apiUrl = '/api/v1/llm';

  constructor(private http: HttpClient) {}

  chat(provider: string, messages: any[], options?: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/chat`, {
      provider,
      messages,
      options
    });
  }

  analyzeCode(provider: string, code: string, language: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/analyze-code`, {
      provider,
      code,
      language
    });
  }
}
```

### Componente de Chat

```typescript
// src/app/components/chat/chat.component.ts
import { Component } from '@angular/core';
import { LLMService } from '../../services/llm.service';

@Component({
  selector: 'app-chat',
  templateUrl: './chat.component.html'
})
export class ChatComponent {
  messages = [];
  currentMessage = '';
  selectedProvider = 'openai';

  constructor(private llmService: LLMService) {}

  sendMessage() {
    if (!this.currentMessage.trim()) return;

    // Adicionar mensagem do usuário
    this.messages.push({
      role: 'user',
      content: this.currentMessage
    });

    // Enviar para API
    this.llmService.chat(
      this.selectedProvider,
      this.messages
    ).subscribe(response => {
      // Adicionar resposta do assistente
      this.messages.push({
        role: 'assistant',
        content: response.content
      });
      this.currentMessage = '';
    });
  }
}
```

## Boas Práticas

### 1. Tratamento de Erros

```python
try:
    response = llm_service.chat(messages)
    return response.content
except RateLimitError:
    # Implementar retry com backoff exponencial
    return handle_rate_limit()
except AuthenticationError:
    # Logar erro e notificar administrador
    logger.error("Erro de autenticação com LLM")
    raise
except Exception as e:
    # Fallback para outro provedor
    return fallback_to_alternative_provider(messages)
```

### 2. Caching de Respostas

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def cached_llm_call(messages_hash, provider):
    """Cache respostas frequentes para melhorar performance"""
    messages = json.loads(messages_hash)
    return llm_service.chat(messages, provider=provider)
```

### 3. Rate Limiting

```python
import asyncio
from asyncio import Semaphore

class RateLimitedLLMService:
    def __init__(self, max_concurrent=5):
        self.semaphore = Semaphore(max_concurrent)
    
    async def chat(self, messages):
        async with self.semaphore:
            return await llm_service.chat_async(messages)
```

### 4. Logging e Monitoramento

```python
import logging
import time

logger = logging.getLogger(__name__)

def logged_llm_call(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        logger.info(f"Chamando LLM: {func.__name__}")
        
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            logger.info(f"LLM respondeu em {duration:.2f}s")
            return result
        except Exception as e:
            logger.error(f"Erro na chamada LLM: {str(e)}")
            raise
    
    return wrapper
```

## Segurança

### 1. Validação de Entrada

```python
def validate_llm_input(messages):
    """Validar e sanitizar entrada antes de enviar para LLM"""
    for message in messages:
        # Remover caracteres potencialmente perigosos
        message['content'] = sanitize_input(message['content'])
        
        # Limitar tamanho da mensagem
        if len(message['content']) > 10000:
            raise ValueError("Mensagem muito longa")
    
    return messages
```

### 2. Filtragem de Conteúdo

```python
import re

def filter_sensitive_content(text):
    """Remover informações sensíveis do texto"""
    # Remover padrões de API keys
    text = re.sub(r'sk-[a-zA-Z0-9]{48}', '[API_KEY_REMOVED]', text)
    
    # Remover emails
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REMOVED]', text)
    
    # Remover números de cartão de crédito
    text = re.sub(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', '[CREDIT_CARD_REMOVED]', text)
    
    return text
```

### 3. Controle de Acesso

```python
from functools import wraps

def require_llm_permission(permission):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if not user.has_permission(permission):
                raise PermissionError("Usuário não tem permissão para usar LLM")
            return func(*args, **kwargs)
        return wrapper
    return decorator

@require_llm_permission('llm.chat')
def chat_with_llm(messages):
    return llm_service.chat(messages)
```

## Testes

### Testes Unitários

```python
import pytest
from unittest.mock import Mock, patch

def test_llm_chat_success():
    # Mock do serviço LLM
    mock_llm = Mock()
    mock_llm.chat.return_value = {"content": "Resposta do LLM"}
    
    # Testar serviço
    service = LLMService(provider="openai")
    service.llm_service = mock_llm
    
    response = service.chat([{"role": "user", "content": "Olá"}])
    assert response["content"] == "Resposta do LLM"

def test_llm_chat_rate_limit():
    # Mock para simular rate limit
    mock_llm = Mock()
    mock_llm.chat.side_effect = RateLimitError("Rate limit exceeded")
    
    service = LLMService(provider="openai")
    service.llm_service = mock_llm
    
    with pytest.raises(RateLimitError):
        service.chat([{"role": "user", "content": "Olá"}])
```

### Testes de Integração

```python
def test_llm_integration_openai():
    # Testar integração real com OpenAI (usar chave de teste)
    service = LLMService(provider="openai")
    response = service.chat([
        {"role": "user", "content": "Diga 'teste' em inglês"}
    ])
    
    assert "test" in response["content"].lower()
```

## Troubleshooting

### Problemas Comuns

#### 1. Timeout de Conexão
```python
# Aumentar timeout para modelos lentos
response = llm_service.chat(
    messages=messages,
    timeout=60  # segundos
)
```

#### 2. Erros de Autenticação
```bash
# Verificar se a chave de API está configurada corretamente
echo $OPENAI_API_KEY

# Testar conexão com o provedor
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     https://api.openai.com/v1/models
```

#### 3. Rate Limiting
```python
# Implementar retry com backoff exponencial
import time
import random

def retry_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except RateLimitError:
            if attempt == max_retries - 1:
                raise
            
            # Backoff exponencial com jitter
            delay = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(delay)
```

#### 4. Problemas com Ollama Local
```bash
# Verificar se Ollama está rodando
ollama list

# Verificar logs do serviço
journalctl -u ollama -f

# Testar modelo específico
ollama run llama2 "Olá, como você está?"
```

## Performance e Otimização

### 1. Batch Processing

```python
def batch_process_messages(messages_list, batch_size=10):
    """Processar múltiplas mensagens em lotes"""
    results = []
    
    for i in range(0, len(messages_list), batch_size):
        batch = messages_list[i:i + batch_size]
        batch_results = []
        
        # Processar em paralelo
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(llm_service.chat, messages)
                for messages in batch
            ]
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    batch_results.append(result)
                except Exception as e:
                    logger.error(f"Erro no batch: {str(e)}")
        
        results.extend(batch_results)
    
    return results
```

### 2. Streaming de Respostas

```python
def stream_llm_response(messages):
    """Obter resposta em streaming para melhor UX"""
    response = llm_service.chat_stream(messages)
    
    for chunk in response:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
```

### 3. Cache Inteligente

```python
import hashlib

class SmartLLMCache:
    def __init__(self, ttl=3600):
        self.cache = {}
        self.ttl = ttl
    
    def get_key(self, messages, provider):
        """Gerar chave única para cache"""
        content = json.dumps(messages, sort_keys=True) + provider
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, messages, provider):
        key = self.get_key(messages, provider)
        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry['timestamp'] < self.ttl:
                return entry['response']
        return None
    
    def set(self, messages, provider, response):
        key = self.get_key(messages, provider)
        self.cache[key] = {
            'response': response,
            'timestamp': time.time()
        }
```

## Monitoramento e Métricas

### 1. Métricas de Uso

```python
class LLMMetrics:
    def __init__(self):
        self.requests_total = Counter('llm_requests_total', 'Total LLM requests', ['provider', 'model'])
        self.request_duration = Histogram('llm_request_duration_seconds', 'LLM request duration', ['provider', 'model'])
        self.tokens_used = Counter('llm_tokens_used_total', 'Total tokens used', ['provider', 'model'])
        self.errors_total = Counter('llm_errors_total', 'Total LLM errors', ['provider', 'error_type'])
    
    def record_request(self, provider, model, duration, tokens, error=None):
        self.requests_total.labels(provider=provider, model=model).inc()
        self.request_duration.labels(provider=provider, model=model).observe(duration)
        self.tokens_used.labels(provider=provider, model=model).inc(tokens)
        
        if error:
            error_type = type(error).__name__
            self.errors_total.labels(provider=provider, error_type=error_type).inc()
```

### 2. Dashboard de Monitoramento

Configure alertas para:
- Taxa de erro > 5%
- Tempo de resposta médio > 10s
- Uso de tokens > 80% do limite
- Falhas de autenticação > 3 em 1 hora

## Exemplos de Uso Avançado

### 1. Chain de LLMs

```python
def multi_step_analysis(code):
    """Análise em múltiplos passos usando diferentes LLMs"""
    
    # Passo 1: Análise inicial com GPT-4
    gpt4_service = LLMService(provider="openai")
    initial_analysis = gpt4_service.analyze_code(code, analysis_type="overview")
    
    # Passo 2: Revisão de segurança com Claude
    claude_service = LLMService(provider="anthropic")
    security_review = claude_service.analyze_code(code, analysis_type="security")
    
    # Passo 3: Otimização de performance com Gemini
    gemini_service = LLMService(provider="google")
    performance_analysis = gemini_service.analyze_code(code, analysis_type="performance")
    
    # Combinar resultados
    return {
        "overview": initial_analysis,
        "security": security_review,
        "performance": performance_analysis
    }
```

### 2. Fallback entre Provedores

```python
class FallbackLLMService:
    def __init__(self, primary_provider="openai", fallback_providers=["anthropic", "google"]):
        self.primary = LLMService(provider=primary_provider)
        self.fallbacks = [LLMService(provider=p) for p in fallback_providers]
    
    def chat_with_fallback(self, messages):
        """Tentar provedores em sequência até obter sucesso"""
        
        # Tentar provedor primário
        try:
            return self.primary.chat(messages)
        except Exception as e:
            logger.warning(f"Primary LLM failed: {str(e)}")
        
        # Tentar provedores de fallback
        for fallback in self.fallbacks:
            try:
                return fallback.chat(messages)
            except Exception as e:
                logger.warning(f"Fallback LLM failed: {str(e)}")
                continue
        
        # Todos falharam
        raise Exception("All LLM providers failed")
```

## Conclusão

Esta documentação cobre os principais aspectos da integração com LLMs no Janus. Para mais informações:

- Consulte a [documentação de segurança](security-guidelines.md) para práticas de segurança
- Veja os [exemplos de código](code-examples.md) para mais casos de uso
- Reporte problemas no [repositório GitHub](https://github.com/janus-completo/janus-completo)

Para suporte técnico, entre em contato com a equipe de desenvolvimento.