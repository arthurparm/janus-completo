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
RUN apt-get update && apt-get install -y --no-install-recommends build-essential git curl libstdc++6 libgomp1 && rm -rf /var/lib/apt/lists/* && \
    python3 -m pip install --no-cache-dir --upgrade pip setuptools wheel && \
    python3 -m pip install --no-cache-dir virtualenv

# Cria ambiente virtual isolado com virtualenv
RUN python3 -m virtualenv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Preinstala PyTorch CPU para evitar downloads pesados e falhas
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.3.1

# Copia os arquivos de definição de dependências (pip)
COPY requirements.txt ./

# Instala apenas as dependências de produção
RUN pip install --no-cache-dir -r requirements.txt

# --- Estágio 2: Final ---
# Usa uma imagem base mínima para a imagem final, reduzindo o tamanho e a superfície de ataque.
FROM python:3.11-slim as final

WORKDIR /app

# Copia o ambiente virtual com as dependências instaladas do estágio 'builder'
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copia o código da aplicação
COPY ./app ./app

# Expõe a porta que a aplicação vai usar
EXPOSE 8000

# O comando para iniciar a aplicação será fornecido pelo docker-compose.yml