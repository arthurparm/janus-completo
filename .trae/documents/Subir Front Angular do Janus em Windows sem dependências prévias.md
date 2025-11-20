## Requisitos
- Node.js 20 LTS (inclui `npm`) — necessário para instalar deps e rodar `ng serve`
- O projeto já inclui `@angular/cli` como devDependency; `npm start` usa o CLI local (não precisa instalar global)
- Proxy do frontend aponta para `http://localhost:8000` (`front/proxy.conf.json`); se o backend não estiver rodando, o front sobe, mas chamadas à API falham

## Passos para Instalar e Rodar
1) Instalar Node.js (Windows)
- Via Winget (recomendado): `winget install OpenJS.NodeJS.LTS`
- Alternativa (se Winget indisponível): baixar em `https://nodejs.org/en/download` (Windows x64 .msi), instalar e reiniciar o PowerShell

2) Instalar dependências do frontend
- Abra o terminal em `c:\repos\janus-completo\front`
- Execute: `npm install`

3) Rodar o servidor de desenvolvimento
- No mesmo diretório: `npm start`
- Acesse: `http://localhost:4200/`
- Observação: o comando já abre o navegador (`-o`), usa dev-server padrão e proxy para o backend

## Observações e Troubleshooting
- Se `npm start` reclamar de `ng` não encontrado, confirme que `node_modules/.bin` foi criado (reinstale com `npm install`)
- Em ambientes corporativos com proxy de rede, configure `npm config set proxy http://...` se necessário
- Sem backend rodando, áreas que chamam `/api/v1/*` e `/healthz` mostrarão erro; isto é esperado

## Próximo
- Após sua aprovação, executo os comandos no terminal, valido o servidor e te entrego a URL de preview (`http://localhost:4200/`)