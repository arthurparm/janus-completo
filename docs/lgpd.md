# Relatório de Conformidade LGPD - Janus

Data de criação: 2026-03-01
Objetivo: Mapear fluxos de dados sensíveis e riscos de privacidade dentro do sistema.

## 1. Inventário de Dados e PII (Informações Pessoais Identificáveis)
Atualmente o sistema processa e interage com as seguintes informações pessoais (PII):
- E-mails (Remetente e Destinatários via Productivity Tools)
- Números de telefone (Redação parcial no backend)
- Identificadores governamentais (CPF, CNPJ, IPs mapeados em `memory/security.py`)
- Dados Biométricos de Áudio (Comandos de voz capturados pela interface Janus Daemon)
- Interações diretas no Chat (Conversas, histórico e "thought streams" guardados em banco de dados).

## 2. Pontos de Risco Atuais (Achados da Auditoria)
- **Vazamento por Logging:** O `ChatEventPublisher`, `CollaborationService` e `ChatCommandHandler` estão gravando partes do conteúdo dos usuários, como prévias (100 caracteres) e meta-dados de e-mail e payloads, de forma não ofuscada nos arquivos de log estáticos da aplicação (`janus.log`).
- **Retenção Descontrolada:** Embora exista o `DataRetentionService`, ele depende de execuções assíncronas falhas acopladas a transações síncronas (`sync_events.py`) e falta um cron job para varrer e aplicar expurgo estruturado. Ademais, os logs gravados em disco (`janus.log`) não contam com política de rotação.
- **Vazamento em In-Memory:** As `ProductivityTools` mantêm globais (_notes, _calendar_events) na memória volátil que constituem risco não-persistente.

## 3. Próximos Passos (Plano de Mitigação)
1. Estender a camada de ofuscação (`app.core.memory.security`) para injetar um redator diretamente nas configurações do `structlog` (`logging_config.py`).
2. Programar limpeza cronológica (Job diário) do `DataRetentionService`.
3. Adicionar política de Log Rotation aos volumes configurados nos containers ou injetados na runtime do sistema operacional.
- **Registros Indevidos de User IDs e E-mails (Logging Tools):** A ferramenta de envio de email `send_email` em `backend/app/core/tools/productivity_tools.py` registra abertamente metadados de correspondência, como remetente (`user_id`), destinatário (`to`) e assunto (`subject`), no logger em modo informativo, consolidando um ponto de vazamento PII não mascarado de forma contínua.
- **Armazenamento Temporal de Memória Global:** A `backend/app/core/tools/productivity_tools.py` continua armazenando notas (`_notes`) e eventos de calendário (`_calendar_events`) em variáveis globais. Na ausência de isolamento, vazamentos cruciais de rotina de diferentes `user_id` podem ser lidos entre sessões se houver exploração de agentes maliciosos no espaço local.

## 4. Recomendações Recentes
1. Introduzir uma política estrita de "Scrubbing/Masking" para metadados de email (Destinatários e Assuntos) passando por uma heurística segura antes de ser jogado nos arquivos `janus.log` ou ser interceptado pelo structlog.
2. Refatorar as listas globais (`_notes` e `_calendar_events`) e mover esse estado transitório para repositórios transacionais atrelados a banco (Postgres/Redis) onde AuthZ e encriptação de disco possam intervir, prevenindo compartilhamentos temporais entre requests.

## Achados do dia (2026-03-08)

### Lacunas e Impacto
- **Captura de Tela Indiscriminada:** O serviço `backend/windows_agent.py` capta a tela do usuário através do endpoint `/screenshot` e disponibiliza sem registros de auditoria ou ofuscação (PII), ferindo princípios de minimização (Coleta Excessiva).
- **Voz Logada sem Minimização:** O `backend/app/interfaces/daemon/daemon.py` arquiva comandos de voz (dados biométricos indiretos e possivelmente sensíveis) nos logs da aplicação em claro.

### Próximos Passos
1. **Adicionar Auditoria e Redação Visual:** No `windows_agent.py`, logar toda requisição com escopo, finalidade e ofuscar ativamente áreas sensíveis do display antes de retorná-lo.
2. **Filtrar Logs do Daemon:** Integrar uma camada de _PII scrubbing_ aos canais do logger em `daemon.py` para os conteúdos textuais transcritos dos comandos vocais.

## Achados do dia (2026-03-10)

### Lacunas e Impacto
- **Metadados de Email Sensíveis não Ofuscados (Logging):** O `backend/app/core/tools/productivity_tools.py` continua registrando e-mails e tópicos no logger (.info) sem qualquer camada de _redaction_, permitindo que dados sensíveis cruciais caiam em dumps de logs estáticos (`janus.log`) para potenciais administradores ou atacantes lerem.
- **Estado Global Compartilhado em Ferramentas de Produtividade (PII Leak Risk):** As listas na `backend/app/core/tools/productivity_tools.py` que armazenam `_notes` e `_calendar_events` ficam no estado global, de modo que os lembretes ou notas de um usuário podem ser acessadas por outras threads e requests em concorrência se a chave/índice não garantir isolamento total (Sessão global exposta).

### Próximos Passos
1. **Mascarar Logs em Tools:** Extender a aplicação das regex e máscaras de PII (`_PII_PATTERNS` em `memory/security.py`) diretamente às chamadas do logger nas tools, filtrando destinatários e assuntos antes da formatação em texto limpo.
2. **Refatorar Estado Global:** Passar a responsabilidade de manter `_notes` e `_calendar_events` das variáves estáticas para uma camada de persistência vinculada ao DB e usuário, aplicando controles severos de ACL (Access Control Lists).

## Achados do dia (2026-03-17)

### Lacunas e Impacto
- **Captura de Áudio Sensível sem Minimização (Logs do Daemon):** O `backend/app/interfaces/daemon/daemon.py` arquiva comandos de voz diretos da interface nos logs de sistema (`janus.log`). Isso se qualifica como dado de natureza indiretamente biométrica/comportamental, sem minimização (PII scrubbing) prévia antes do salvamento em texto plano, quebrando o princípio de minimização da LGPD.
- **Capturas de Tela sem Consentimento ou Ofuscação (Windows Agent):** A API do Windows agent continua expondo via endpoints (como `/screenshot`) imagens capturadas diretamente do SO. Como mencionado no Achado anterior, além de faltar Auth, falta o scrub visual de áreas contendo senhas, e-mails ou conteúdo bancário.

### Próximos Passos
1. **Mascarar Textos do Daemon:** Aplicar a camada de regex `_PII_PATTERNS` em `memory/security.py` antes de encaminhar transcrições de áudio ao logger no `daemon.py`.
2. **Revisar Consentimento Local:** Exigir uma configuração de `OPT_IN` com flag persistente antes de autorizar a primeira chamada a endpoints que realizam captura de input do SO host no `windows_agent.py`.

## Achados do dia (2026-03-18)

### Lacunas e Impacto
- **Captura de Áudio Sensível sem Minimização (Logs do Daemon):** O arquivo `backend/app/interfaces/daemon/daemon.py` (e o loop principal nele) continua realizando o log (`logger.info("log_info", message=f"Command received: {command}")`) de comandos de voz transcritos diretamente. Essa ação grava dados de natureza indiretamente biométrica e comportamental em logs estáticos (`janus.log`), quebrando o princípio de minimização da LGPD por não realizar prévio PII scrubbing antes de gravar em disco ou no fluxo do console.
- **Estado Global Compartilhado em Ferramentas de Produtividade (PII Leak Risk):** As listas na `backend/app/core/tools/productivity_tools.py` que armazenam `_notes` e `_calendar_events` permanecem no estado global como vazamento em In-Memory, de modo que os dados temporários de sessão podem ser lidos entre requests em concorrência se houver comprometimento de agentes ou usuários, sem isolamento claro nem controle de AuthZ.
- **Metadados de Email Sensíveis não Ofuscados (Logging):** Na função `send_email` de `backend/app/core/tools/productivity_tools.py`, metadados essenciais e potencialmente rastreáveis a pessoas (como o remetente `user_id`, destinatário `to` e o `subject`) ainda são passados ao `logger.info()` limpos, falhando no mascaramento preventivo de PII.
- **Captura de Tela Indiscriminada e sem Autorização (Windows Agent):** Os endpoints expostos sem autenticação pelo `backend/windows_agent.py` (`/screenshot`) mantêm os riscos críticos de vazamento LGPD por capturar a tela ativa do usuário (possivelmente abrigando e-mails, acessos bancários, comunicações sigilosas) de forma indiscriminada, sem data minimisation visual (blur/redaction em certas janelas) ou registro de auditoria local (logs no agent não identificam quem/qual request realizou a captura).

### Próximos Passos
1. **Mascarar Textos do Daemon:** Importar e utilizar o helper `redact_pii_text_only` (de `app.core.memory.security`) sobre o `command` no loop do `daemon.py` antes de passá-lo para os métodos de log, garantindo que CPFs, e-mails ou senhas vocalizadas não sejam arquivados.
2. **Refatorar Estado Global:** Passar a responsabilidade de manter `_notes` e `_calendar_events` (`productivity_tools.py`) para uma camada de persistência vinculada ao DB ou cache isolado por usuário (`user_id`), aplicando controles severos de acesso.
3. **Mascarar Logs em Tools:** Aplicar ofuscação (`redact_pii_text_only`) ativamente aos parâmetros sensíveis injetados no logger de envio de e-mail e em criações de calendários e notas.
4. **Adicionar Auditoria, Consentimento e Redação Visual:** Requerer `OPT_IN` local explicíto ou Autenticação na rede via Token no `windows_agent.py`, e adicionar log local para gerar uma trilha de auditoria cada vez que uma foto de tela for gerada, mantendo rastro LGPD.

## Achados do dia (2026-03-26)

### Lacunas e Impacto
- **Shadow IT/Monitoramento sem Ofuscação:** O script `tooling/secure-tailscale-setup.ps1` atua como um componente de monitoramento que gera logs locais (`tailscale-security-monitor.log`) expondo nomes de host e dados de peers em texto plano (clear text). Essa prática contorna a redação padrão de PII (core) do sistema e apresenta um risco direto de conformidade com a LGPD ao reter logs detalhados de rede/identidade não mascarados.

### Próximos Passos
1. **Mascarar Identificadores de Rede:** Aplicar filtragem ou ofuscação (`PII scrubbing/redaction`) no output que vai para `tailscale-security-monitor.log` via script de setup. Substituir IPs externos, usernames, ou hashes de peers por identificadores criptográficos ou mascarados caso o log seja salvo localmente.
