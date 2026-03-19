# Guia de Onboarding - Janus Completo

## Objetivo
Este guia fornece instruções passo-a-passo para configurar o ambiente de desenvolvimento Janus pela primeira vez, desde o clone do repositório até o primeiro deploy local funcionando.

## Escopo
- **Inclui**: Setup completo para Windows, macOS e Linux
- **Exclui**: Configurações avançadas de produção
- **Público-alvo**: Novos desenvolvedores na equipe Janus

## Pré-requisitos

### Sistema Operacional
- **Windows**: Windows 10/11 com WSL2 recomendado
- **macOS**: macOS 12 (Monterey) ou superior
- **Linux**: Ubuntu 20.04+, Debian 11+, ou equivalente

### Softwares Necessários
1. **Node.js 20+** ([Download](https://nodejs.org/))
2. **Python 3.11+** ([Download](https://www.python.org/))
3. **Docker & Docker Compose** ([Download](https://www.docker.com/))
4. **Git** ([Download](https://git-scm.com/))

### Verificação de Instalação
```bash
# Verificar versões (mínimo necessário)
node --version    # v20.0.0+
python3 --version # 3.11+
docker --version  # 20.10+
git --version     # 2.30+
```

## Setup Passo-a-Passo

### 1. Clone do Repositório
```bash
git clone https://github.com/seu-org/janus-completo.git
cd janus-completo
```

### 2. Bootstrap com Um Comando (Recomendado)
```bash
python tooling/dev.py up
```
Este comando irá:
- Verificar todos os pré-requisitos
- Configurar variáveis de ambiente
- Subir todos os serviços Docker
- Realizar health checks

### 3. Verificação do Setup
Abra seu navegador e acesse:
- **Frontend**: http://localhost:4300
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### 4. Desenvolvimento Local Alternativo

#### Frontend (Angular)
```bash
cd frontend
npm install
npm start
# Acesse: http://localhost:4200
```

#### Backend (FastAPI)
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# Acesse: http://localhost:8000/docs
```

## Verificação de Instalação Completa

### Testes Básicos
```bash
# Testar API
curl -sf http://localhost:8000/health

# Testar frontend (deve abrir página inicial)
open http://localhost:4300

# Testar Docker Compose
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 ps
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 ps
```

### Logs e Diagnóstico
```bash
# Ver logs da API
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 logs -f janus-api

# Ver logs do frontend
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 logs -f janus-frontend

# Diagnóstico completo
python tooling/dev.py doctor --host localhost --backend-port 8000 --frontend-port 4300
```

## Configuração do IDE Recomendada

### VS Code (Recomendado)
1. Instalar extensões:
   - Python
   - Angular Language Service
   - Docker
   - Thunder Client (para testes de API)

2. Configurar settings.json:
```json
{
  "python.defaultInterpreterPath": "./backend/.venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "typescript.preferences.importModuleSpecifier": "relative"
}
```

### PyCharm/IntelliJ
- Importar backend como projeto Python
- Configurar interpreter para `./backend/.venv`
- Habilitar Docker plugin

## Primeiros Passos no Desenvolvimento

### 1. Explore o Código
```bash
# Frontend
cd frontend/src/app
ls -la

# Backend
cd backend/app
ls -la
```

### 2. Execute os Testes
```bash
# Frontend
cd frontend && npm test

# Backend
cd backend && pytest
```

### 3. Faça sua Primeira Mudança
1. Edite um arquivo simples (ex: `frontend/src/app/app.component.html`)
2. Veja a hot-reload funcionando
3. Commit suas mudanças

## Recursos Adicionais

### Comandos Úteis
```bash
# Subir apenas serviços essenciais
python tooling/dev.py setup

# Verificar health completo
python tooling/dev.py doctor

# Parar tudo
python tooling/dev.py down

# Rodar QA checks
python tooling/dev.py qa
```

### Documentação Específica
- [Development Guide - Frontend](../development-guide-frontend.md)
- [Development Guide - Backend](../development-guide-backend.md)
- [API Test Playbook](../qa/api-test-playbook.md)

## Última Atualização
2026-03-11 - Documentação criada para novo onboarding consolidado