# Tailscale Serve Setup para Janus

## Configuração Backend (FastAPI)

### 1. Instalar Tailscale no servidor backend
```bash
# Ubuntu/Debian
curl -fsSL https://tailscale.com/install.sh | sh

# Windows (PowerShell Admin)
winget install Tailscale.Tailscale
```

### 2. Configurar Tailscale Serve para FastAPI
```bash
# Autenticar no Tailscale
tailscale up

# Configurar serve para FastAPI (porta 8000)
tailscale serve https:443 / http://localhost:8000

# Verificar status
tailscale serve status
```

### 3. Atualizar configuração do backend
```python
# janus/config.py - Adicionar suporte para Tailscale
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Configurações existentes...
    
    # Tailscale Serve config
    TAILSCALE_SERVE_ENABLED: bool = True
    TAILSCALE_HOST: str = "janus-backend.tailnet-name.ts.net"
    ALLOWED_TAILSCALE_ORIGINS: list = ["*.tailnet-name.ts.net"]
    
    # CORS para Tailscale
    CORS_ORIGINS: list = [
        "https://janus-frontend.tailnet-name.ts.net",
        "http://localhost:4201",
        "http://localhost:4200"
    ]
```

## Configuração Frontend (Angular)

### 1. Configurar Tailscale Serve para Angular
```bash
# No diretório front/
tailscale serve https:443 / http://localhost:4201

# Verificar status
tailscale serve status
```

### 2. Atualizar configuração Angular
```typescript
// front/src/environments/environment.ts
export const environment = {
  production: false,
  apiUrl: 'https://janus-backend.tailnet-name.ts.net/api',
  tailscaleServe: true
};

// front/src/environments/environment.prod.ts
export const environment = {
  production: true,
  apiUrl: 'https://janus-backend.tailnet-name.ts.net/api',
  tailscaleServe: true
};
```

### 3. Atualizar proxy configuration
```json
// front/proxy.conf.json
{
  "/api": {
    "target": "https://janus-backend.tailnet-name.ts.net",
    "secure": true,
    "changeOrigin": true,
    "logLevel": "debug"
  }
}
```

## Scripts de Automação

### Script de setup para backend
```bash
#!/bin/bash
# scripts/setup-tailscale-backend.sh

echo "Configurando Tailscale Serve para Janus Backend..."

# Verificar se Tailscale está instalado
if ! command -v tailscale &> /dev/null; then
    echo "Instalando Tailscale..."
    curl -fsSL https://tailscale.com/install.sh | sh
fi

# Subir Tailscale
tailscale up

# Configurar serve
tailscale serve https:443 / http://localhost:8000

# Verificar status
tailscale serve status

echo "Tailscale Serve configurado!"
echo "URL do backend: https://$(tailscale status | grep -o '^[^ ]*').tailnet-name.ts.net"
```

### Script de setup para frontend
```bash
#!/bin/bash
# scripts/setup-tailscale-frontend.sh

echo "Configurando Tailscale Serve para Janus Frontend..."

# Verificar se Tailscale está instalado
if ! command -v tailscale &> /dev/null; then
    echo "Instalando Tailscale..."
    # Windows
    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        winget install Tailscale.Tailscale
    else
        curl -fsSL https://tailscale.com/install.sh | sh
    fi
fi

# Subir Tailscale
tailscale up

# Configurar serve
tailscale serve https:443 / http://localhost:4201

# Verificar status
tailscale serve status

echo "Tailscale Serve configurado!"
echo "URL do frontend: https://$(tailscale status | grep -o '^[^ ]*').tailnet-name.ts.net"
```

## Comandos Úteis

### Verificar status
```bash
tailscale status
tailscale serve status
```

### Debug
```bash
tailscale serve --verbose
```

### Parar serve
```bash
tailscale serve --remove
```

### Ver logs
```bash
# Linux/macOS
sudo journalctl -u tailscaled -f

# Windows
Get-WinEvent -LogName "Tailscale" | Select-Object -First 20
```

## Segurança

### Configurar ACLs no Tailscale
```json
// Acessar https://login.tailscale.com/admin/acls
{
  "acls": [
    {
      "action": "accept",
      "src": ["*"],
      "dst": ["*:443"]
    }
  ]
}
```

### Verificar certificado SSL
```bash
curl -v https://janus-backend.tailnet-name.ts.net/health
```

## Testes

### Testar conectividade backend
```bash
curl https://janus-backend.tailnet-name.ts.net/api/health
```

### Testar conectividade frontend
```bash
curl https://janus-frontend.tailnet-name.ts.net
```

## Troubleshooting

### Problemas comuns:
1. **Certificado SSL inválido**: Verificar se o domínio está correto
2. **CORS errors**: Atualizar CORS origins no backend
3. **Conexão recusada**: Verificar se os serviços estão rodando nas portas corretas
4. **Tailscale não conecta**: Verificar firewall e conectividade