# 🖥️ Tailscale no Windows - Guia Interface Gráfica

## 📋 Passo a Passo Completo para Windows

### 1️⃣ **Instalar Tailscale via Microsoft Store (Recomendado)**

1. **Microsoft Store**:
   - Abra a Microsoft Store
   - Pesquise "Tailscale"
   - Clique em "Instalar"

2. **Ou via Winget (PowerShell Admin)**:
   ```powershell
   winget install Tailscale.Tailscale
   ```

### 2️⃣ **Autenticar pela Interface Gráfica**

1. **Iniciar Tailscale**:
   - Procure "Tailscale" no menu Iniciar
   - Ou encontre o ícone na bandeja do sistema (próximo ao relógio)

2. **Fazer Login**:
   - Clique no ícone do Tailscale na bandeja
   - Clique em "Log in..."
   - Escolha seu método de login (Google, Microsoft, GitHub, etc.)
   
3. **Autorizar Dispositivo**:
   - Uma página vai abrir no navegador
   - Faça login com sua conta
   - Clique em "Authorize this device"
   - Volte para o Tailscale - ele vai mostrar "Connected"

### 3️⃣ **Descobrir seu Tailnet Name**

1. **Via Interface**:
   - Clique com botão direito no ícone do Tailscale
   - Vá em "Preferences" → "General"
   - Veja seu "Tailnet name" (ex: `seu-nome.ts.net`)

2. **Via PowerShell**:
   ```powershell
   tailscale status
   ```

### 4️⃣ **Configurar Tailscale Serve pela Interface**

1. **Abrir Dashboard Web**:
   - Clique com botão direito no ícone Tailscale
   - Vá em "Preferences" → "Debug" → "Web interface"
   - Ou acesse: `http://100.100.100.100:8088`

2. **Configurar Serve**:
   ```powershell
   # PowerShell como Administrador
   tailscale serve https:443 / http://localhost:8000
   ```

### 5️⃣ **Configurar seus Arquivos**

Depois de descobrir seu tailnet name, atualize os arquivos:

**Arquivo: `janus/app/config.py`**
```python
# Linha 294-297, mude para:
TAILSCALE_SERVE_ENABLED: bool = True
TAILSCALE_HOST: str = "seu-pc-name.seu-nome.ts.net"
TAILSCALE_BACKEND_URL: str = "https://seu-pc-name.seu-nome.ts.net"
```

**Arquivo: `front/src/environments/environment.ts`**
```typescript
// Linha 8-12, mude para:
tailscale: {
  enabled: true,
  apiUrl: 'https://seu-pc-name.seu-nome.ts.net/api',
  frontendUrl: 'https://seu-pc-name-frontend.seu-nome.ts.net'
}
```

### 6️⃣ **Scripts Windows Otimizados**

**Novo Script: `scripts/setup-tailscale-windows.bat`**
```batch
@echo off
setlocal enabledelayedexpansion

echo 🚀 Configurando Tailscale Serve para Janus no Windows...

:: Verificar se Tailscale está instalado
tailscale version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Tailscale não encontrado. Instalando...
    winget install Tailscale.Tailscale
    echo ✅ Tailscale instalado! Por favor, reinicie este script após a instalação.
    pause
    exit /b 1
)

echo ✅ Tailscale está instalado

:: Conectar ao Tailscale
echo 🔗 Conectando ao Tailscale...
tailscale up

:: Aguardar conexão
timeout /t 3 /nobreak >nul

:: Obter informações
echo 📡 Obtendo informações da máquina...
for /f "tokens=1" %%i in ('tailscale status ^| findstr /v "^$" ^| findstr /v "Tailscale"') do set HOSTNAME=%%i
for /f "tokens=2" %%i in ('tailscale status ^| findstr "@"') do set TAILNET=%%i
set TAILNET=%TAILNET:@=%

echo 🌐 Hostname: %HOSTNAME%
echo 🌐 Tailnet: %TAILNET%

:: Configurar Tailscale Serve
echo 🔧 Configurando Tailscale Serve...
tailscale serve --remove 2>nul
tailscale serve https:443 / http://localhost:8000

:: Verificar status
echo 📊 Verificando status...
tailscale serve status

:: URL final
set BACKEND_URL=https://%HOSTNAME%.%TAILNET%.ts.net

echo.
echo 🎉 Tailscale Serve configurado com sucesso!
echo.
echo 📋 Resumo da configuracao:
echo    🌐 URL do backend: %BACKEND_URL%
echo    🔗 Porta HTTPS: 443
echo    🔄 Backend local: http://localhost:8000
echo.
echo 🧪 Para testar:
echo    curl %BACKEND_URL%/health
echo.
echo 💡 Dica: Salve esta URL: %BACKEND_URL%

:: Salvar configuração
if not exist .tailscale mkdir .tailscale
echo %BACKEND_URL% > .tailscale\backend-url.txt

:: Criar arquivo de ambiente
echo # Tailscale Serve Configuration > janus\.env.tailscale
echo TAILSCALE_BACKEND_URL=%BACKEND_URL% >> janus\.env.tailscale
echo TAILSCALE_SERVE_ENABLED=true >> janus\.env.tailscale
echo TAILSCALE_HOST=%HOSTNAME%.%TAILNET%.ts.net >> janus\.env.tailscale

echo 📄 Configuracoes salvas em janus\.env.tailscale
pause
```

### 7️⃣ **Interface Gráfica Alternativa**

**Tailscale GUI** (Mais fácil para iniciantes):
1. Baixe em: https://tailscale.com/download/windows
2. Instale normalmente
3. Interface intuitiva para configurar tudo via cliques

### 8️⃣ **Verificar Tudo Funcionando**

1. **Ícone na Bandeja**: Deve mostrar "Connected"
2. **Testar URL**: Abra `https://seu-pc-name.seu-nome.ts.net/health` no navegador
3. **PowerShell**:
   ```powershell
   tailscale status
   tailscale serve status
   ```

### 🚨 **Solução de Problemas Comuns no Windows**

**Problema: Tailscale não conecta**
- Windows Defender pode estar bloqueando
- Solução: Adicione exceção no firewall
- PowerShell Admin:
  ```powershell
  netsh advfirewall firewall add rule name="Tailscale" dir=in action=allow program="%ProgramFiles%\Tailscale\tailscale.exe"
  ```

**Problema: Serve não funciona**
- Execute PowerShell como Administrador
- Verifique se a porta 443 está livre
- Reinicie o serviço: `Restart-Service Tailscale`

**Problema: Não consigo acessar de outros dispositivos**
- Certifique-se que todos estão na mesma conta Tailscale
- Verifique ACLs em: https://login.tailscale.com/admin/acls

### 📱 **Aplicativo Móvel (Opcional)**

Baixe o app Tailscale no celular para acessar seu Janus de qualquer lugar:
- iOS: App Store → "Tailscale"
- Android: Play Store → "Tailscale"

### 🎯 **Resumo Visual**

```
[Seu PC Windows] ←→ [Tailscale Cloud] ←→ [Outros Dispositivos]
       ↓
[Janus Backend:8000] → [Tailscale Serve:443] → https://seu-pc.ts.net
       ↓
[Angular Frontend:4201] → [Tailscale Serve:443] → https://seu-pc-frontend.ts.net
```

**Pronto!** Agora é só clicar nos ícones e seguir o fluxo visual do Windows! 🎉