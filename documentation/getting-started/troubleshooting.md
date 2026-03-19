# Troubleshooting - Janus Completo

## Objetivo
Guia para resolver problemas comuns durante desenvolvimento, build, testes e deploy do Janus.

## Escopo
- **Inclui**: Problemas de setup, build, testes, Docker, rede e performance
- **Exclui**: Problemas de produção (ver operations/incident-response.md)
- **Público-alvo**: Desenvolvedores durante desenvolvimento local

## Problemas de Instalação

### Node.js / NPM

**Erro: "npm install falha com EACCES"**
```bash
# Solução: Limpar cache e usar sudo se necessário
npm cache clean --force
sudo npm install -g npm@latest
# Ou usar nvm (recomendado)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 20
nvm use 20
```

**Erro: "node-gyp rebuild falha"**
```bash
# Instalar build tools
# Ubuntu/Debian:
sudo apt-get install build-essential python3-dev
# macOS:
xcode-select --install
# Windows (como admin):
npm install --global windows-build-tools
```

### Python / pip

**Erro: "pip install falha com SSL"**
```bash
# Atualizar pip e certificados
python -m pip install --upgrade pip setuptools wheel
python -m pip install --upgrade certifi
```

**Erro: "No module named '_sqlite3'"**
```bash
# Ubuntu/Debian:
sudo apt-get install libsqlite3-dev python3-dev
# Reinstalar Python após instalar dependências
```

### Docker

**Erro: "Cannot connect to Docker daemon"**
```bash
# Verificar se Docker está rodando
docker version
# Se não estiver:
# Ubuntu/Debian:
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
# Reboot necessário após adicionar ao grupo

# macOS/Windows: Verificar se Docker Desktop está aberto
```

**Erro: "no space left on device"**
```bash
# Limpar containers e imagens antigas
docker system prune -a
# Ou limpar apenas containers parados:
docker container prune
```

## Problemas de Build

### Frontend Build Falhando

**Erro: "Module not found" durante build**
```bash
# Limpar node_modules e reinstalar
cd frontend
rm -rf node_modules package-lock.json
npm install
```

**Erro: "Out of memory" durante build Angular**
```bash
# Aumentar memória do Node.js
export NODE_OPTIONS="--max-old-space-size=4096"
npm run build
```

### Backend Build Falhando

**Erro: "ImportError: cannot import name"**
```bash
# Reinstalar dependências em ambiente limpo
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Problemas de Testes

### Frontend Tests

**Erro: "ChromeHeadless não inicia"**
```bash
# Instalar Chrome/Chromium
# Ubuntu:
sudo apt-get install chromium-browser
# macOS:
brew install chromium
# Verificar permissões
docker run --rm -it --cap-add=SYS_ADMIN node:20 npm test
```

**Erro: "Timeout em testes"**
```bash
# Aumentar timeout nos testes
# Em frontend/package.json, adicionar:
"test": "ng test --code-coverage --watch=false --browsers=ChromeHeadless --timeout=10000"
```

### Backend Tests

**Erro: "Database connection failed"**
```bash
# Verificar se PostgreSQL está rodando
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 ps
# Se não estiver:
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 up -d postgres
```

**Erro: "Redis connection refused"**
```bash
# Verificar Redis
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 ps | grep redis
# Logs se necessário:
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 logs redis
```

## Problemas de Docker/Compose

### Serviços Não Iniciam

**Erro: "Port already in use"**
```bash
# Encontrar processo usando a porta
sudo lsof -i :8000  # ou :4300, :5432, etc
# Matar processo
kill -9 <PID>
# Ou mudar portas nos arquivos .env.pc1/.env.pc2
```

**Erro: "Service 'postgres' failed to build"**
```bash
# Verificar logs específicos
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 logs postgres
# Limpar volumes se necessário
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 down -v
# Rebuildar
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 build --no-cache
```

### Problemas de Rede

**Erro: "Connection refused between services"**
```bash
# Verificar networks
docker network ls
docker network inspect janus-pc1-net
# Verificar se containers estão na mesma rede
docker inspect <container_name> | grep -A 10 NetworkSettings
```

## Problemas de Performance

### Frontend Lento

**Build muito lento**
```bash
# Usar build incremental
npm run build -- --watch
# Desabilitar source maps para builds rápidos
npm run build -- --source-map=false
```

**Hot reload não funciona**
```bash
# Verificar poll interval
npm start -- --poll=2000
# Verificar firewall/antivirus
```

### Backend Lento

**API requests timeout**
```bash
# Verificar logs do container
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 logs -f janus-api
# Verificar resource usage
docker stats
# Aumentar timeout no cliente
export REQUESTS_TIMEOUT=60
```

**Database queries lentas**
```bash
# Verificar indexes
# Verificar connection pool
# Verificar logs de query lenta em postgres
```

## Problemas de Lint/Type Check

### Frontend Lint

**Erro: "Cannot find module" em imports**
```bash
# Verificar tsconfig.json
# Reiniciar TS server no VS Code
# Cmd/Ctrl + Shift + P -> "TypeScript: Restart TS Server"
```

**Erro: "ESLint configuration error"**
```bash
# Reinstalar ESLint
npm install --save-dev eslint @typescript-eslint/parser @typescript-eslint/eslint-plugin
# Verificar .eslintrc.json
```

### Backend Lint

**Erro: "ruff check falha"**
```bash
# Atualizar ruff
pip install --upgrade ruff
# Verificar configuração em backend/pyproject.toml
```

**Erro: "mypy type errors"**
```bash
# Verificar imports cíclicos
# Adicionar type hints
# Usar --ignore-missing-imports se necessário
mypy --ignore-missing-imports app/
```

## Problemas de Ambiente

### Variáveis de Ambiente

**Erro: "Missing environment variable"**
```bash
# Verificar arquivos .env.pc1 e .env.pc2
cp .env.pc1.example .env.pc1
cp .env.pc2.example .env.pc2
# Preencher variáveis obrigatórias
```

### Permissões

**Erro: "Permission denied" em scripts**
```bash
# Tornar scripts executáveis
chmod +x tooling/*.sh
chmod +x backend/scripts/*.py
```

**Erro: "Cannot write to directory"**
```bash
# Verificar ownership
sudo chown -R $USER:$USER .
# Verificar permissões
chmod -R u+rwX .
```

## Diagnóstico Geral

### Comando de Diagnóstico Completo
```bash
# Rodar diagnóstico automatizado
python tooling/dev.py doctor --host localhost --backend-port 8000 --frontend-port 4300

# Verificar todos os serviços
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 ps
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 ps

# Logs de todos os serviços
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 logs --tail=50
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 logs --tail=50
```

### Informações para Debug

Sempre inclua ao reportar problemas:
1. **Sistema Operacional**: `uname -a` ou `systeminfo`
2. **Versões**: `node --version`, `python3 --version`, `docker --version`
3. **Logs relevantes**: Últimas 50 linhas do serviço com problema
4. **Comando executado**: Exatamente o que foi rodado
5. **Mensagem de erro completa**: Copiar toda a stack trace

## Recursos Adicionais

- [Docker Troubleshooting](https://docs.docker.com/config/daemon/#troubleshoot-the-daemon)
- [Angular CLI Issues](https://angular.io/cli)
- [FastAPI Issues](https://github.com/tiangolo/fastapi/issues)
- [Postgres Docker Issues](https://hub.docker.com/_/postgres)

## Última Atualização
2026-03-11 - Guia criado com problemas comuns identificados na comunidade