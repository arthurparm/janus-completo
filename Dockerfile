# --- Estágio 1: Builder ---
# Usa uma imagem Python completa para instalar dependências, incluindo as que podem precisar de compilação.
FROM python:3.11-slim as builder

# Define o diretório de trabalho
WORKDIR /app

# Define variáveis de ambiente para otimizar a instalação do pip
ENV PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true

# Instala o Poetry (gerenciador de dependências)
RUN apt-get update && apt-get install -y curl && \
    curl -sSL https://install.python-poetry.org | python3 -

# Adiciona o Poetry ao PATH
ENV PATH="$POETRY_HOME/bin:$PATH"

# Copia os arquivos de definição de dependências
COPY pyproject.toml ./

# Instala apenas as dependências de produção, sem criar um venv separado no builder
RUN poetry install --no-root

# --- Estágio 2: Final ---
# Usa uma imagem base mínima para a imagem final, reduzindo o tamanho e a superfície de ataque.
FROM python:3.11-slim as final

WORKDIR /app

# Copia o ambiente virtual com as dependências instaladas do estágio 'builder'
COPY --from=builder /app/.venv ./.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copia o código da aplicação
COPY ./app ./app

# Expõe a porta que a aplicação vai usar
EXPOSE 8000

# O comando para iniciar a aplicação será fornecido pelo docker-compose.yml