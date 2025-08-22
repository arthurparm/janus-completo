# --- Estágio 1: Builder ---
# Instala as dependências em um ambiente temporário
FROM python:3.11 AS builder

WORKDIR /app

# CORREÇÃO: Atualiza o pip para a versão mais recente antes de usá-lo.
# Isso resolve o bug interno (`TypeError`) do pip.
RUN pip install --upgrade pip

# Copia o arquivo de dependências
COPY requirements.txt .

# Instala as dependências. Usar --no-cache-dir reduz o tamanho da camada.
RUN pip install --no-cache-dir -r requirements.txt


# --- Estágio 2: Final ---
# Constrói a imagem final e leve a partir de uma base limpa
FROM python:3.11

WORKDIR /app

# MELHORIA: Copia apenas as dependências instaladas do estágio anterior
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# MELHORIA: Copia o código da aplicação para a imagem final
COPY ./app ./app

# Expõe a porta que a aplicação irá rodar
EXPOSE 8000

# CORREÇÃO: O comando para iniciar a aplicação deve estar no estágio final.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]