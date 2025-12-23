# --- Estágio 1: Builder ---
# Usa uma imagem Python completa para instalar dependências, incluindo as que podem precisar de compilação.
FROM python:3.11-slim as builder

# Define o diretório de trabalho
WORKDIR /app

# Define variáveis de ambiente para otimizar a instalação do pip
ENV PIP_NO_CACHE_DIR=on \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

# Instala libs essenciais e virtualenv de forma confiável
RUN apt-get update && apt-get install -y --no-install-recommends build-essential git curl libstdc++6 libgomp1 portaudio19-dev && rm -rf /var/lib/apt/lists/* && \
    python3 -m pip install --no-cache-dir --upgrade pip setuptools wheel && \
    python3 -m pip install --no-cache-dir virtualenv

# Cria ambiente virtual isolado com virtualenv
RUN python3 -m virtualenv /opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Instala o Poetry
ENV POETRY_HOME=/opt/poetry
ENV PATH="$POETRY_HOME/bin:$PATH"
RUN curl -sSL https://install.python-poetry.org | python3 -

# Copia os arquivos de definição de dependências (Poetry)
COPY pyproject.toml poetry.lock* ./

# Instala as dependências (sem instalar o pacote raiz por enquanto, apenas libs)
# --no-root: não instala o projeto janus como pacote (será copiado depois)
# --only main: apenas dependências de produção
RUN poetry config virtualenvs.create false \
    && poetry install --no-root

# Se quiser usar venv criado pelo poetry, precisaríamos ajustar o PATH ou config.
# Mas aqui, como estamos em container, instalamos no sistema ou desativamos virtualenv.
# O padrão 'virtualenvs.create false' instala no python do sistema /opt/venv se estiver ativo ou global.
# Como já estamos num venv (/opt/venv) ativado no PATH, o poetry instalará nele.

# --- Estágio 2: Final ---
# Usa uma imagem base mínima para a imagem final, reduzindo o tamanho e a superfície de ataque.
FROM python:3.11-slim as final

WORKDIR /app

# Copia o ambiente virtual com as dependências instaladas do estágio 'builder'
COPY --from=builder /opt/venv /opt/venv

# Instala bibliotecas de runtime necessárias e Docker CLI para controle de containers
RUN apt-get update && apt-get install -y --no-install-recommends \
    libstdc++6 libgomp1 libasound2 libportaudio2 \
    curl gnupg lsb-release \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list \
    && apt-get update && apt-get install -y --no-install-recommends docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copia o código da aplicação
COPY ./app ./app

# Expõe a porta que a aplicação vai usar
EXPOSE 8000

# O comando para iniciar a aplicação será fornecido pelo docker-compose.yml