# Plano de Limpeza de APIs Pagas e Consolidação OpenRouter

Este plano visa remover as dependências hardcoded de APIs pagas (OpenAI, Gemini, xAI) e garantir que o sistema opere exclusivamente via OpenRouter e Ollama (Local), prevenindo custos acidentais e erros de log.

## 1. Núcleo de LLM (`router.py`)
- **Objetivo**: Impedir que o roteador tente instanciar clientes diretos da OpenAI ou Google.
- **Ações**:
    1. Remover "Google Gemini", "xAI" e "OpenAI" da lista `provider_order`.
    2. Ajustar a lógica de criação de provedores para focar em `OpenRouter` e `Ollama`.
    3. Garantir que a seleção de modelos respeite estritamente o `config.py` atualizado.

## 2. Agendador (`scheduler_service.py`)
- **Objetivo**: Parar de tentar verificar cotas de serviços desativados.
- **Ações**:
    1. Comentar ou remover o registro do job `update_gemini_quotas`.
    2. Remover a importação de `GeminiQuotaFetcher` para evitar erros de dependência.

## 3. Agentes (`leaf_worker.py`)
- **Objetivo**: Corrigir defaults perigosos que apontam para modelos pagos.
- **Ações**:
    1. Alterar `default_model="openai:gpt-4o"` para `default_model="openrouter:deepseek/deepseek-r1-0528:free"`.

## 4. Frontend (`ops.ts`)
- **Objetivo**: Alinhar a interface com o backend.
- **Ações**:
    1. Atualizar `activeModelId` padrão.
    2. Atualizar a lista de modelos disponíveis no dropdown para mostrar as opções do OpenRouter.
