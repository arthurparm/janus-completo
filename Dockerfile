# --- Estágio 1: Builder ---
# Usando uma tag de imagem específica e estável para reprodutibilidade.
FROM python:3.11-slim-bookworm AS builder

WORKDIR /app

# Mantemos a atualização do pip como uma boa prática.
RUN pip install --upgrade pip

# Copia o arquivo de dependências
COPY requirements.txt .

# Instala as dependências.
RUN pip install --no-cache-dir -r requirements.txt


# --- Estágio 2: Final ---
# Usando a mesma tag de imagem específica e estável.
FROM python:3.11-slim-bookworm

WORKDIR /app

# Copia apenas as dependências instaladas do estágio anterior
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copia o código da aplicação para a imagem final
COPY ./app ./app

# Expõe a porta que a aplicação irá rodar
EXPOSE 8000

# CORREÇÃO: Removida a flag inválida "-u".
# O comando para iniciar a aplicação deve estar no estágio final.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]