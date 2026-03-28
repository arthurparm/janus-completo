# Janus - Melhorias Possiveis

Data de criacao: 2026-02-12
Objetivo: centralizar ideias de evolucao do Janus em um unico backlog vivo, para manter organizacao nas conversas futuras.

## Como usar este documento

1. Cada item deve ter dono, prioridade e status.
2. Priorizar por impacto em usuario + reducao de risco tecnico.
3. Quebrar itens grandes em historias pequenas e testaveis.
4. Revisar semanalmente e mover itens para roadmap ativo.

## Escala sugerida

- Prioridade: P0 (urgente), P1 (alta), P2 (media), P3 (baixa)
- Esforco: S (1-2 dias), M (3-7 dias), L (2+ semanas)
- Status: ideia, planejado, em andamento, concluido, descartado

---

## 1) Estudo do proprio codigo (Code Intelligence)

| ID | Melhoria | Prioridade | Esforco | Status |
|---|---|---|---|---|
| CI-001 | Corrigir modelagem de entidades de codigo no grafo (File/Function/Class com chaves consistentes) | P0 | M | feito (2026-02-12) |
| CI-002 | Corrigir resolucao de `CALLS` para usar nome qualificado e evitar links quebrados | P0 | M | feito (2026-02-12) |
| CI-003 | Indexacao incremental por `git diff` (alem de reindex full) | P1 | M | ideia |
| CI-004 | ExtraÃ§Ã£o AST de imports, decorators, assinatura, linhas inicio/fim | P1 | M | ideia |
| CI-005 | Suporte a multiplas linguagens (TS/JS/Python/SQL) no parser | P1 | L | ideia |
| CI-006 | Endpoint de pergunta sobre codigo com citacao (`arquivo` + `linha`) | P0 | M | feito (2026-02-12) |
| CI-007 | Busca hibrida para codigo (lexical + vetorial + grafo) | P1 | L | ideia |
| CI-008 | Mapa de impacto de mudanca (o que quebra se alterar X) | P1 | M | ideia |
| CI-009 | Hotspots de complexidade e debt automaticamente rankeados | P2 | M | ideia |
| CI-010 | Detecao de ciclos de dependencia e camadas violadas | P2 | M | ideia |
| CI-011 | Identificacao de codigo morto e endpoint sem uso | P2 | M | ideia |
| CI-012 | Grafo temporal de mudancas por commit e autor | P2 | L | ideia |
| CI-013 | Explainability: por que o Janus respondeu isso sobre o codigo | P1 | M | ideia |
| CI-014 | Modo "pair reviewer" para PR com checklist automatico | P1 | M | ideia |
| CI-015 | Dataset de avaliacao de perguntas tecnicas com baseline versionado | P0 | M | feito (2026-02-12) |

---

## 2) Memoria, RAG e Conhecimento

| ID | Melhoria | Prioridade | Esforco | Status |
|---|---|---|---|---|
| MR-001 | Telemetria obrigatoria por etapa (`source`, `db`, `latency_ms`, `confidence`, `error_code`) | P0 | M | feito (2026-02-13) |
| MR-002 | Politica de roteamento explicita entre Postgres, vetor e grafo | P0 | M | concluido (2026-03-03) |
| MR-003 | Threshold de confianca com fluxo de confirmacao do usuario | P0 | S | feito (2026-02-13) |
| MR-004 | CitaÃ§Ãµes obrigatorias em respostas baseadas em documento/codigo | P0 | M | feito (2026-02-13) |
| MR-005 | Reranking semantico com features de qualidade por tipo de consulta | P1 | M | ideia |
| MR-006 | Chunking adaptativo por tipo de arquivo (codigo, doc, conversa) | P1 | M | ideia |
| MR-007 | Eviccao inteligente de memoria curta com politicas por origem | P1 | S | parcial |
| MR-008 | Memoria de longo prazo com consolidacao transacional no grafo | P1 | M | ideia |
| MR-009 | Compactacao e resumo hierarquico de conversas longas | P2 | M | ideia |
| MR-010 | Detecao de contradicao entre memorias antigas e novas | P2 | M | ideia |
| MR-011 | Protecao de PII em `pending confirmations` e logs de ferramentas | P0 | S | feito (2026-02-13) |
| MR-012 | Explainable retrieval (mostrar por que cada contexto entrou) | P1 | M | ideia |
| MR-013 | Avaliacao offline recorrente (score.json + comparacao de baseline) | P0 | S | feito (2026-02-21, gate pre-merge offline) |
| MR-014 | Cache de consulta semantica com invalidacao por mudanca de fonte | P2 | M | ideia |
| MR-015 | RAG multimodal (imagem + texto + PDF) | P3 | L | ideia |

---

## 3) Agentes, Planejamento e Execucao

| ID | Melhoria | Prioridade | Esforco | Status |
|---|---|---|---|---|
| AG-001 | Planejamento hierarquico com decomposicao de metas em tarefas verificaveis | P1 | M | ideia |
| AG-002 | Politica de ferramenta por perfil de risco e escopo | P0 | M | parcial |
| AG-003 | Simulacao antes de execucao de acoes destrutivas | P0 | S | concluido (2026-03-03) |
| AG-004 | Auto-critica por rodada com memoria de erros recorrentes | P1 | M | ideia |
| AG-005 | Detecao de loop e escape automatico com estrategia alternativa | P1 | S | ideia |
| AG-006 | Multi-agente com papeis fixos (executor, reviewer, auditor) | P2 | M | ideia |
| AG-007 | Checklist de saida por tipo de tarefa (codigo, docs, deploy) | P1 | S | ideia |
| AG-008 | Modo "aprender com feedback humano" por acao aprovada/rejeitada | P1 | M | ideia |
| AG-009 | Controle de custo por objetivo e abort por budget | P1 | S | parcial |
| AG-010 | Recomendador de proxima melhor acao com score esperado | P2 | M | ideia |
| AG-011 | Refatorar ChatService (Backend) para modularidade e SRP | P1 | M | ideia |

---

## 4) Ferramentas, SeguranÃ§a e Governanca

| ID | Melhoria | Prioridade | Esforco | Status |
|---|---|---|---|---|
| SG-001 | Substituir parser fragil de tool call por envelope JSON estrito | P0 | M | feito (2026-02-13) |
| SG-002 | Validacao de args por schema por ferramenta (pydantic) | P0 | M | feito (2026-02-13) |
| SG-003 | Redaction de secrets/PII antes de persistir args e auditoria | P0 | S | feito (2026-02-13) |
| SG-004 | Sandboxing por capability e allowlist de comandos | P0 | M | feito (2026-02-13) |
| SG-005 | Approvals com explicacao de risco e escopo claro | P1 | S | parcial |
| SG-006 | Quotas por usuario/projeto/ferramenta com janela deslizante | P1 | M | parcial |
| SG-007 | Politica de retencao e expurgo de dados sensiveis | P1 | M | ideia |
| SG-008 | Trilha de auditoria assinada para acoes criticas | P2 | M | ideia |
| SG-009 | Simulador de politicas para validar mudancas antes de ativar | P2 | M | ideia |
| SG-010 | Modo compliance (LGPD/GDPR) com controles pre-configurados | P2 | M | ideia |
| SG-011 | Eliminar segredos default (config.py) e restringir CORS | P0 | S | feito (2026-02-20) |
| SG-012 | Proteger endpoint de reset de senha contra vazamento de token | P1 | S | feito (2026-02-20) |
| SG-013 | Implementar politica de rotacao de logs e expurgo automatico de auditoria | P1 | S | ideia |
| SG-018 | Remover senhas/credenciais default do config.py | P0 | S | ideia |
| SG-019 | Corrigir vazamento de estado global e risco de PII no productivity_tools.py | P1 | M | ideia |
| SG-020 | Corrigir vulnerabilidade de SQL Injection no dedupe_service.py (f-strings) | P0 | M | aberto |
| SG-021 | Implementar autenticacao nos endpoints FastAPI expostos em windows_agent.py | P0 | S | aberto |
| SG-022 | LGPD: Adicionar minimizacao e auditoria nas capturas de tela do windows_agent.py | P1 | M | aberto |
| SG-023 | LGPD: Ofuscar comandos de voz capturados e logados em daemon.py | P1 | S | aberto |
| SG-024 | Atualizar @hono/node-server no frontend para mitigar vulnerabilidade de alta severidade | P1 | S | aberto |
| SG-025 | Substituir geradores pseudo-aleatorios padrao por secrets no auto_analysis.py | P2 | S | aberto |
| SG-026 | Mitigar Command Injection (shell=True) e Code Injection em launcher_tools.py, python_sandbox.py e faulty_tools.py | P0 | S | aberto |
| SG-027 | Corrigir criacao insegura de arquivos temporarios em log_aware_reflector.py (/tmp hardcoded) | P1 | S | aberto |
| SG-028 | Mitigar abertura insegura de URL com arbitrary schemes (file://) em message_broker.py e agent_tools.py | P1 | S | aberto |
| SG-029 | Remover ou ofuscar credenciais e segredos hardcoded em scripts de tooling/testes e benchmarks | P1 | S | aberto |
---

## 5) Observabilidade, Qualidade e Confiabilidade

| ID | Melhoria | Prioridade | Esforco | Status |
|---|---|---|---|---|
| OQ-001 | Dashboard unico por request_id (pipeline completo) | P0 | M | feito (2026-02-13) |
| OQ-002 | SLOs por dominio (chat, rag, tools, workers) com alertas | P0 | M | feito (2026-02-21) |
| OQ-003 | Tracing distribuido fim-a-fim com correlacao frontend/back/worker | P1 | M | concluido (2026-03-03) |
| OQ-004 | Error taxonomy padronizada para suporte e produto | P1 | S | feito (2026-02-13) |
| OQ-005 | Chaos tests para Redis, Neo4j, vetor e broker | P2 | M | ideia |
| OQ-006 | Contract tests para endpoints criticos e SSE | P0 | M | feito (2026-02-13) |
| OQ-007 | Scorecards automaticos de qualidade de resposta | P1 | M | ideia |
| OQ-008 | Canary release para mudancas de prompt/roteador | P2 | M | ideia |
| OQ-009 | Regressao semantica automatica antes de deploy | P1 | M | ideia |
| OQ-010 | Postmortem template e playbook de incidentes | P1 | S | ideia |
| OQ-011 | Cobertura automatizada das 231 APIs com relatorio JSON e evidencias Docker | P0 | M | feito (2026-02-21, automacao entregue; inventario atual 230/231) |
| OQ-012 | Corrigir execucao assincrona fragil no DataRetentionService (SQLAlchemy events) | P1 | M | feito (2026-02-20) |
| OQ-015 | Padronizar uso do Settings/Config no ChatAgentLoop (remover os.getenv) | P2 | S | ideia |
| OQ-016 | Corrigir fragilidade e mocking HTTP no frontend auth.service.spec.ts | P1 | S | ideia |

---

## 6) Produto e Experiencia (Front + API)

| ID | Melhoria | Prioridade | Esforco | Status |
|---|---|---|---|---|
| PX-001 | Tela de explicacao de resposta (fontes, confianca, latencia) | P1 | M | ideia |
| PX-002 | UI de citacao clicavel para codigo e documentos | P0 | M | feito (2026-02-13) |
| PX-003 | Timeline de memoria por conversa e por usuario | P1 | M | parcial |
| PX-004 | Centro de aprovacoes pendentes com comparacao de risco | P1 | M | feito (2026-02-13) |
| PX-005 | Modo operador com visao de workers e filas em tempo real | P1 | M | parcial |
| PX-006 | Busca global no workspace (docs, codigo, conversas, tarefas) | P1 | M | ideia |
| PX-007 | Acoes rapidas de rotina (criar tarefa, lembrete, resumo) | P2 | M | ideia |
| PX-008 | Onboarding guiado para novos usuarios | P2 | M | ideia |
| PX-009 | Perfis de usuario (dev, pm, qa) com defaults de comportamento | P2 | S | ideia |
| PX-010 | Internacionalizacao completa e consistencia terminologica | P3 | M | ideia |
| PX-011 | Simplificar UX do chat para modo usuario (modo simples padrao + painel avancado opcional) | P0 | S | em andamento (2026-02-13) |
| PX-012 | Mensagens de erro de auth mais claras (401/422) + fluxo de reset guiado | P1 | S | planejado |
| PX-013 | Reforcar identidade Janus-first no chat (prompts + sanitizacao + /about) | P0 | S | concluido (2026-02-28) |

---

## 7) Plataforma, Dados e Integracoes

| ID | Melhoria | Prioridade | Esforco | Status |
|---|---|---|---|---|
| PL-001 | Alinhamento definitivo de schema SQL (evitar drift MySQL vs Postgres) | P0 | M | feito (2026-02-13) |
| PL-002 | Migracoes idempotentes e auditadas | P1 | M | ideia |
| PL-003 | Backup/restore automatizado de banco, grafo e vetor | P0 | M | ideia |
| PL-004 | Multi-tenant com isolamento forte por organizacao | P2 | L | ideia |
| PL-005 | Feature flags por ambiente e por cliente | P1 | M | ideia |
| PL-006 | Provisionamento declarativo de infraestrutura local e cloud | P2 | M | ideia |
| PL-007 | API versioning formal com politica de deprecacao | P1 | M | ideia |
| PL-008 | Conectores nativos (GitHub, Notion, Jira, Slack, GDrive) | P2 | L | ideia |
| PL-009 | Pipeline de ingestao em lote com dedupe e retry robusto | P1 | M | ideia |
| PL-010 | Data catalog interno para fontes de conhecimento | P2 | M | ideia |
| PL-011 | Fixar dependências do Backend (lockfile) e versionamento de pacotes críticos (asyncpg) | P1 | M | ideia |

---

## 8) DevEx e Fluxo de Entrega

| ID | Melhoria | Prioridade | Esforco | Status |
|---|---|---|---|---|
| DX-001 | Comando unico de setup local (devcontainer/script cross-platform) | P1 | S | concluido (2026-03-03) |
| DX-002 | Seed de dados e cenarios de teste reproduziveis | P1 | M | feito (2026-02-13) |
| DX-003 | Lint/type/test gates padronizados em CI | P0 | S | feito (2026-02-13) |
| DX-004 | Templates de PR orientados a risco e evidencia | P1 | S | ideia |
| DX-005 | Testes de carga para chat e retrieval | P1 | M | ideia |
| DX-006 | Snapshot tests para prompts criticos | P2 | M | ideia |
| DX-007 | CLI de diagnostico rapido (health + deps + config) | P1 | M | ideia |
| DX-008 | Reprodutibilidade de bugs via captura de trace minima | P1 | M | ideia |
| DX-009 | Ferramenta interna para gerar datasets de avaliacao | P2 | M | ideia |
| DX-010 | Bot de release notes tecnicas por commit semantico | P3 | S | ideia |
| DX-011 | Matriz viva de endpoints + playbook de execucao dos testes de API (local/CI) | P1 | S | feito (2026-02-21) |
| DX-012 | Remover código duplicado e morto (ex: tool_service_improved) | P1 | S | concluido (2026-03-03) |

---

## 9) IA aplicada ao produto (futuro)

| ID | Melhoria | Prioridade | Esforco | Status |
|---|---|---|---|---|
| AI-001 | Roteamento dinamico de modelos por tipo de pergunta e custo | P1 | M | parcial |
| AI-002 | Distilacao de respostas validadas para modelos menores | P2 | L | ideia |
| AI-003 | Avaliador automatico de factualidade com juiz externo | P2 | M | ideia |
| AI-004 | Aprendizado continuo com feedback implicito (uso real) | P2 | L | ideia |
| AI-005 | Geracao de plano de acao com verificacao automatica de consistencia | P1 | M | ideia |
| AI-006 | Assistente de arquitetura que compara opcoes e trade-offs | P2 | M | ideia |
| AI-007 | Suporte a memoria episodica com janela temporal semantica | P2 | M | ideia |
| AI-008 | Deteccao de alucinacao com fallback para modo conservador | P1 | M | ideia |
| AI-009 | Fine-tuning supervisionado para dominio Janus | P3 | L | ideia |
| AI-010 | Modo tutor para explicar decisoes tecnicas passo a passo | P3 | M | ideia |
| AI-011 | Classificador de intencao e risco no chat para roteamento automatico de agentes e guardrails | P1 | M | feito (2026-02-21, refinado v2) |
| AI-012 | Reranker semantico no RAG com cross-encoder para priorizar evidencias relevantes | P1 | M | feito (2026-02-21, refinado v2) |
| AI-013 | Politica de decisao para orquestracao autonoma baseada em historico de sucesso | P1 | M | ideia |
| AI-014 | Deteccao preditiva de anomalias operacionais em latencia, erro e filas | P1 | M | feito (2026-02-21) |
| AI-015 | Predicao de satisfacao e risco de abandono de conversa com acao automatica | P2 | M | ideia |
| AI-016 | Classificacao e extracao semantica na ingestao de documentos (tipo, entidades, resumo) | P1 | M | feito (2026-02-21, refinado v2) |
| AI-017 | Camada multimodal de visao e audio para enriquecer contexto dos agentes | P2 | L | ideia |

---

### [AI-011] Classificador de intencao e risco no chat para roteamento automatico de agentes e guardrails
- Problema atual: o roteamento de mensagens do chat depende principalmente de regras e contexto bruto, gerando escolhas subotimas de agente em parte das conversas.
- Solucao proposta: treinar e integrar um classificador leve (intencao + risco + urgencia) no fluxo de entrada do chat para decidir agente, politicas e nivel de verificacao antes da resposta.
- Impacto esperado: melhora de qualidade de resposta, menos retries, menor custo de tokens e maior previsibilidade operacional.
- Riscos: drift de dados, vies de classificacao e latencia adicional se o modelo for pesado.
- Dependencias: telemetria confiavel por request, dataset rotulado inicial e fallback deterministico quando a confianca for baixa.
- Prioridade: P1
- Esforco: M
- Dono: a definir
- Status: feito (2026-02-21)

---

### [AI-012] Reranker semantico no RAG com cross-encoder para priorizar evidencias relevantes
- Problema atual: o retrieval vetorial puro ainda traz chunks parcialmente relevantes, elevando ruido no contexto final do LLM.
- Solucao proposta: inserir etapa de reranking com cross-encoder apos recuperacao inicial para reordenar candidatos por relevancia contextual.
- Impacto esperado: maior precisao factual, menos alucinacao e reducao de tokens por prompt com contexto mais enxuto.
- Riscos: aumento de latencia por inferencia extra e custo computacional adicional.
- Dependencias: benchmark de retrieval, conjunto de queries de avaliacao e limite de candidatos por rodada.
- Prioridade: P1
- Esforco: M
- Dono: a definir
- Status: feito (2026-02-21, refinado v2)

---

### [AI-013] Politica de decisao para orquestracao autonoma baseada em historico de sucesso
- Problema atual: escolha de proximas acoes autonomas ainda depende muito de heuristicas estaticas e pode repetir caminhos ineficientes.
- Solucao proposta: treinar modelo de ranking/politica com historico de execucoes (sucesso, custo, tempo, falha) para priorizar a melhor proxima acao.
- Impacto esperado: menos loops, maior taxa de conclusao e melhor uso de budget por objetivo.
- Riscos: exploracao insuficiente de estrategias novas e vies para cenarios mais frequentes.
- Dependencias: telemetria historica confiavel, schema de feedback por acao e fallback deterministico.
- Prioridade: P1
- Esforco: M
- Dono: a definir
- Status: ideia

### [SG-020] Potencial SQL Injection em queries dinâmicas (Bandit B608)
- Problema atual: `backend/app/services/dedupe_service.py` constrói nomes de tabelas dinamicamente com f-strings nas queries SQL, apresentando um risco de injeção mapeado (Bandit B608).
- Solucao proposta: Substituir a construção dinâmica de queries por parametrização adequada e validação estrita dos nomes de tabelas permitidos.
- Impacto esperado: Mitigação de risco crítico de SQL Injection.
- Riscos: Quebra do fluxo de deduplicação se a validação dos nomes das tabelas não for precisa.
- Dependencias: Nenhuma.
- Prioridade: P1
- Esforco: S
- Dono: a definir
- Status: ideia

### [SG-021] Endpoint Windows Agent sem Autenticação
- Problema atual: `backend/windows_agent.py` expõe endpoints críticos do sistema operacional hospedeiro (screenshot, notify, speak) na porta 5001 sem mecanismo de autenticação (AuthN/AuthZ).
- Solucao proposta: Implementar uma camada de autenticação leve no FastAPI (como um token em um cabeçalho ou query param), garantindo que apenas requisições originárias do container do Janus sejam autorizadas.
- Impacto esperado: Bloqueio de acessos não autorizados e execução remota não autenticada no host Windows.
- Riscos: Nenhuma falha esperada desde que o docker-compose passe a credencial correta.
- Dependencias: Passagem de um secret compartilhado entre Janus container e Windows Agent.
- Prioridade: P0
- Esforco: S
- Dono: a definir
- Status: ideia

### [SG-022] Risco LGPD em Screenshots Full Screen no Windows Agent
- Problema atual: O endpoint de captura de tela no `backend/windows_agent.py` pode capturar todo o ambiente de trabalho (quando o fallback para a captura full screen ocorre ou modo "full" é invocado), sem log de auditoria, caracterizando um risco em termos de minimização de dados e LGPD.
- Solucao proposta: Adicionar um mecanismo de consentimento, auditar cada captura via log central e restringir por padrão a captura para apenas a janela ativa ou mascarar áreas sensíveis.
- Impacto esperado: Cumprimento dos princípios da LGPD de necessidade, minimização de dados e responsabilidade (trilha de auditoria).
- Riscos: Desafios técnicos no processamento ou mascaramento em tempo real se a performance for afetada.
- Dependencias: Mecanismo de logging centralizado ou local seguro.
- Prioridade: P0
- Esforco: M
- Dono: a definir
- Status: ideia

### [SG-024] Vulnerabilidades em dependências do frontend (npm audit)
- Problema atual: Múltiplas dependências do frontend (`@hono/node-server`, `dompurify`, e `express-rate-limit`) possuem vulnerabilidades ativas mapeadas através do `npm audit`.
- Solucao proposta: Atualizar as versões destas dependências para suas correções seguras e realizar regressão nos testes do frontend.
- Impacto esperado: Resolução imediata de vulnerabilidades introduzidas pelas bibliotecas no ecossistema do frontend.
- Riscos: Breaking changes causadas por atualizações major/minor das libs listadas.
- Dependencias: Ajuste de dependências no `package.json`.
- Prioridade: P1
- Esforco: M
- Dono: a definir
- Status: ideia

### [SG-025] Geração pseudo-aleatória insegura (Bandit B311)
- Problema atual: A rotina no arquivo `backend/app/api/v1/endpoints/auto_analysis.py` usa funções de geração pseudo-aleatórias (do módulo padrão `random`), as quais são inseguras para propósitos criptográficos ou tokens.
- Solucao proposta: Substituir o uso do módulo `random` pelo módulo `secrets` integrado no Python para gerações críticas ou aleatoriedades seguras.
- Impacto esperado: Remoção de um alerta do analisador de segurança (Bandit B311) e blindagem contra ataques à aleatoriedade do sistema.
- Riscos: Pequena chance de problema caso as rotinas exijam um seed determinístico estrito, embora indesejável para segurança.
- Dependencias: Nenhuma.
- Prioridade: P1
- Esforco: S
- Dono: a definir
- Status: ideia

---

### [AI-014] Deteccao preditiva de anomalias operacionais em latencia, erro e filas
- Problema atual: muitos desvios operacionais sao percebidos apenas apos impacto no usuario.
- Solucao proposta: adicionar deteccao de anomalias em series temporais de metricas criticas (latencia, taxa de erro, backlog de fila) com alertas automaticos.
- Impacto esperado: deteccao precoce de incidentes, menor MTTR e aumento de confiabilidade do sistema.
- Riscos: falsos positivos/negativos em periodos de carga irregular.
- Dependencias: pipeline de metricas consistente, janela historica minima e calibracao de thresholds.
- Prioridade: P1
- Esforco: M
- Dono: a definir
- Status: feito (2026-02-21)

---

### [AI-015] Predicao de satisfacao e risco de abandono de conversa com acao automatica
- Problema atual: sinais de conversa mal resolvida nem sempre sao capturados em tempo de evitar churn na sessao.
- Solucao proposta: treinar modelo de classificacao/regressao com sinais de UX (tempo, retries, interrupcoes, feedback) para estimar satisfacao e risco de abandono.
- Impacto esperado: acionamento proativo de fallback, escalonamento para agente especialista e melhoria de experiencia.
- Riscos: interpretacao errada de sinais comportamentais e vies por perfil de usuario.
- Dependencias: coleta de eventos de UX, definicao de labels de sucesso e estrategia de intervencao.
- Prioridade: P2
- Esforco: M
- Dono: a definir
- Status: ideia

---

### [AI-016] Classificacao e extracao semantica na ingestao de documentos (tipo, entidades, resumo)
- Problema atual: ingestao trata documentos de forma quase uniforme, com perda de estrutura e sem priorizacao inteligente.
- Solucao proposta: aplicar classificacao de tipo de documento, extracao de entidades (NER) e resumo estruturado antes da indexacao.
- Impacto esperado: base de conhecimento mais consistente, melhor recuperacao no RAG e menor trabalho manual de curadoria.
- Riscos: erro de classificacao em documentos ambiguos e ruido em entidades extraidas.
- Dependencias: pipeline de parser robusto, taxonomia de documentos e avaliacao de qualidade de extracao.
- Prioridade: P1
- Esforco: M
- Dono: a definir
- Status: feito (2026-02-21, refinado v2)

---

### [AI-017] Camada multimodal de visao e audio para enriquecer contexto dos agentes
- Problema atual: agentes ainda exploram pouco sinais de tela e audio para compreender contexto real do usuario.
- Solucao proposta: integrar modelos de visao/audio para classificacao de contexto, deteccao de eventos e enriquecimento de memoria de sessao.
- Impacto esperado: respostas mais contextuais em fluxos multimodais e nova classe de automacoes orientadas por percepcao.
- Riscos: custo computacional, privacidade de dados sensiveis e maior complexidade operacional.
- Dependencias: politica de consentimento/LGPD, pipeline multimodal observavel e avaliacao de latencia fim a fim.
- Prioridade: P2
- Esforco: L
- Dono: a definir
- Status: ideia

---

## 10) Frontend V1 - Complete UI Coverage (Baseado em 228 APIs)

**Contexto:** Atualmente temos 228 endpoints documentados no OpenAPI, mas apenas ~18% têm interfaces visuais completas. Esta seção organiza o desenvolvimento do frontend em **3 cenários estratégicos** alinhados com perfis de usuário e valor de negócio.

**Inventário API por Módulo (Top 10):**
- Observability: 22 endpoints
- Knowledge: 21 endpoints
- Productivity: 13 endpoints
- LLM: 12 endpoints
- Learning: 12 endpoints
- Chat: 11 endpoints
- Collaboration: 11 endpoints
- Autonomy: 11 endpoints
- Feedback: 7 endpoints
- Meta-Agent: 6 endpoints

---

### Cenário 1: Observability Dashboard (Gestor de Sistema)

**Persona:** Desenvolvedor/DevOps que precisa diagnosticar problemas, monitorar saúde do sistema e entender performance.

**Valor:** Visibilidade completa do sistema operacional sem depender de logs ou ferramentas externas.

|   ID    | Funcionalidade | APIs Cobertos | Prioridade | Esforço | Status |
|---------|--------------------------------------------------------|---|---|---|---|
| FE1-001 | Dashboard de sistema único (status, health, services)             | `/system/status`, `/system/health/services`, `/system/overview` | P0 | M | ideia |
| FE1-002 | Visualização de traces distribuídos por request_id                | `/observability/traces/*`, `/observability/spans/*`             | P0 | M | ideia |
| FE1-003 | Painel de métricas em tempo real (latência, throughput, errors)   | `/observability/metrics/*`                                      | P0 | M | ideia |
| FE1-004 | Explorador de logs com filtros avançados                          | `/observability/logs/*`                                         | P1 | M | ideia |
| FE1-005 | Drill-down de pipeline completo por request (front→API→worker→DB) | Composição de múltiplos endpoints                               | P0 | L | ideia |
| FE1-006 | Alertas configuráveis e SLO tracking visual                       | `/observability/alerts/*` (futuro)                              | P1 | M | ideia |
| FE1-007 | Database validation e migration UI                                | `/system/db/validate`, `/system/db/migrate`                     | P1 | S | ideia |
| FE1-008 | Health check detalhado com circuit breaker controls               | `/knowledge/health/*`                                           | P1 | S | ideia |

**Arquitetura sugerida:**
- Dashboard tipo Grafana/Datadog simplificado
- WebSocket/SSE para métricas real-time
- Layout responsivo com foco em desktop
- Exportação para JSON/CSV para análise offline

---

### Cenário 2: Knowledge Graph Explorer (Cientista Curioso)

**Persona:** Desenvolvedor que quer entender a base de código, explorar relações entre componentes e fazer perguntas sobre arquitetura.

**Valor:** Transformar o grafo de conhecimento invisível em ferramenta visual de navegação e descoberta.

| ID | Funcionalidade | APIs Cobertos | Prioridade | Esforço | Status |
|---|---|---|---|---|---|
| FE2-001 | Visualização interativa do grafo (nós + relacionamentos)                    | `/knowledge/stats`, `/knowledge/node-types`, `/knowledge/entities` | P0 | L | ideia |
| FE2-002 | Navegação drill-down de entidades (click → expand relationships)            | `/knowledge/entity/{name}/relationships` | P0 | M | ideia |
| FE2-003 | Interface de consulta com NLQ (Natural Language Query)                      | `/knowledge/query`, `/knowledge/query/code` | P0 | M | ideia |
| FE2-004 | Busca de conceitos relacionados com visualização de clusters                | `/knowledge/concepts/related` | P1 | M | ideia |
| FE2-005 | Explorador de code analysis (funções que chamam X, arquivos que importam Y) | `/knowledge/functions/calling`, `/knowledge/files/importing` | P1 | M | ideia |
| FE2-006 | Quarantine management com promoção visual de sugestões | `/knowledge/quarantine/*` | P1 | S | parcial |
| FE2-007 | Indexação manual com progresso visual | `/knowledge/index`, `/knowledge/concepts/reindex` | P1 | S | ideia |
| FE2-008 | Exportação de subgrafos para análise externa (GraphML, JSON) | API customizada necessária | P2 | M | ideia |
| FE2-009 | Timeline de consolidação de conhecimento | `/knowledge/consolidate` | P2 | M | ideia |

**Arquitetura sugerida:**
- Biblioteca de visualização: D3.js, Cytoscape.js ou Vis.js
- Layout força-dirigida com zoom/pan
- Painel lateral para detalhes de nó
- Filtros por tipo de nó e relacionamento
- Modo "mapa de impacto" para mudanças

---

### Cenário 3: Orchestration Center (Desenvolvedor Produtivo)

**Persona:** Usuário que interage com o Janus para realizar tarefas, gerenciar autonomia, e acompanhar execuções.

**Valor:** Centralizar controle de agentes, tarefas, ferramentas e feedback em uma interface coesa.

| ID | Funcionalidade | APIs Cobertos | Prioridade | Esforço | Status |
|---|---|---|---|---|---|
| FE3-001 | Chat melhorado com stream de eventos de agente (thought stream) | `/chat/*`, SSE events | P0 | M | parcial |
| FE3-002 | Painel de autonomia com gestão de strategic goals e tools | `/autonomy/*`, `/tools/*` | P0 | M | parcial |
| FE3-003 | Centro de aprovações pendentes com diff visual | `/pending-actions/*` | P0 | S | feito |
| FE3-004 | Gerenciamento de tasks e subtasks com Kanban/Timeline | `/tasks/*` | P1 | M | ideia |
| FE3-005 | Productivity dashboard (summary, metrics, templates) | `/productivity/*` | P1 | M | ideia |
| FE3-006 | Learning center com insights e flashcards | `/learning/*` | P1 | M | ideia |
| FE3-007 | Feedback loop UI (thumbs up/down, corrections, reports) | `/feedback/*` | P1 | S | ideia |
| FE3-008 | Meta-agent control panel (ciclos, configs, histórico) | `/meta-agent/*` | P1 | M | ideia |
| FE3-009 | Workers monitoring (status, queues, health) | `/workers/*` | P1 | S | ideia |
| FE3-010 | Evaluation dashboard com comparação de modelos | `/evaluation/*` | P1 | M | ideia |
| FE3-011 | RAG document management (upload, status, embedding quality) | `/rag/*`, `/documents/*` | P1 | M | ideia |
| FE3-012 | Context manager visual (memória curta/longa, evictions) | `/context/*` | P2 | M | ideia |
| FE3-013 | Reflexion viewer (self-critique, improvements) | `/reflexion/*` | P2 | S | ideia |
| FE3-014 | Sandbox playground para testar ferramentas | `/sandbox/*` | P2 | S | ideia |
| FE3-015 | Refatorar JanusApiService para micro-serviços (SRP) | N/A | P1 | M | ideia |

**Arquitetura sugerida:**
- Layout tipo "plataforma unificada" (sidebar + múltiplas views)
- Real-time updates via SSE/WebSocket
- Componentização forte (reuso entre módulos)
- Design system consistente (já existe framework Magicpunk)
- PWA para acesso offline e notificações

---

### Roadmap de Implementação Sugerido

**Sprint 1-3 (Fundação):**
- ✅ PX-011: Simplificar UX do chat (já em andamento)
- FE3-001: Chat melhorado com thought stream
- FE1-001: Dashboard de sistema básico
- Design system refinement

**Sprint 4-6 (Observability):**
- FE1-002 a FE1-005: Pipeline completo de observability
- FE1-007 a FE1-008: Admin tools

**Sprint 7-9 (Knowledge):**
- FE2-001 a FE2-003: Core do Knowledge Graph Explorer
- FE2-006: Quarantine management
- FE2-007: Indexing controls

**Sprint 10-12 (Orchestration):**
- FE3-002 a FE3-010: Módulos de produtividade e controle
- FE2-004 a FE2-005: Análise de código avançada
- FE3-011 a FE3-014: Features secundárias

**Total estimado:** ~36 sprints (9 meses com time de 2 devs)
**Cobertura final:** 100% dos 228 endpoints com UI funcional

---

## 11) Itens imediatos recomendados (Top 12)

1. CI-001 (feito em 2026-02-12)
2. CI-002 (feito em 2026-02-12)
3. CI-006 (feito em 2026-02-12)
4. CI-015 (feito em 2026-02-12)
5. MR-001 (feito em 2026-02-13)
6. MR-004 (feito em 2026-02-13)
7. SG-001 (feito em 2026-02-13)
8. SG-002 (feito em 2026-02-13)
9. OQ-001 (feito em 2026-02-13)
10. OQ-006 (feito em 2026-02-13)
11. PL-001 (feito em 2026-02-13)
12. DX-003 (feito em 2026-02-13)

---

## 12) Sprint atual (prioridades)

### [SPR-001] Sprint de prioridades - Fundacao ML + Confiabilidade
- Janela: 2026-02-23 a 2026-03-06
- Objetivo: executar o menor conjunto de alto impacto para destravar ML no produto sem perder seguranca/estabilidade.
- Status: concluido (2026-02-21)

**Backlog priorizado (ordem de execucao):**

| Ordem | ID | Tema | Prioridade | Esforco | Resultado esperado na sprint |
|---|---|---|---|---|---|
| 1 | SG-011 | Seguranca de configuracao | P0 | S | concluido (2026-02-20): segredos default removidos e CORS restrito por ambiente |
| 2 | SG-012 | Seguranca de auth | P1 | S | concluido (2026-02-20): reset de senha sem vazamento de token/sinal sensivel |
| 3 | OQ-012 | Confiabilidade de retention | P1 | M | concluido (2026-02-20): execucao assincrona robusta no DataRetentionService sem falhas intermitentes |
| 4 | AI-011 | Roteamento inteligente de chat | P1 | M | concluido (2026-02-21): classificador refinado (v2) com urgencia, reducao de falso positivo e fallback deterministico |
| 5 | AI-012 | Qualidade de retrieval no RAG | P1 | M | concluido (2026-02-21): reranker refinado (v2) com sinais de metadata/recencia e telemetria expandida |
| 6 | DX-011 | Governanca de testes de API | P1 | S | concluido (2026-02-21): matriz viva de endpoints e playbook local/CI atualizado |

**Criticos da sprint (nao-negociavel):**
- SG-011, SG-012 e OQ-012 concluidos.
- AI-011 concluido em modo MVP + refinamento v2 (heuristica de urgencia e risco defensivo).

**Stretch goals (se houver capacidade):**
- AI-016 (classificacao e extracao semantica na ingestao de documentos) - concluido (2026-02-21, refinado v2).
- AI-014 (deteccao preditiva de anomalias operacionais) - concluido (2026-02-21).

**Definicao de pronto da SPR-001:**
- PRs vinculadas as issues com evidencias (testes, logs e metricas antes/depois).
- Feature flags para AI-011 e AI-012 com rollback simples.
- Sem regressao em CI principal.
- Atualizacao de documentacao operacional minima (runbook/README tecnico).

**Evidencias de fechamento (2026-02-21):**
- Backlog priorizado 1 a 6 concluido (SG-011, SG-012, OQ-012, AI-011, AI-012, DX-011).
- Testes unitarios da sprint executados sem falhas (22 passed): `test_sg011_security_config.py`, `test_oq012_data_retention.py`, `test_ai011_intent_routing.py`, `test_ai012_semantic_reranker.py`.
- Feature flags ativas e com rollback simples por configuracao em `backend/app/config.py`:
  `AI_INTENT_ROUTING_ENABLED`, `AI_INTENT_RISK_ESCALATION_ENABLED`, `RAG_RERANK_ENABLED`, `RAG_RERANK_BACKEND`, `RAG_RERANK_TOP_K`.
- Documentacao operacional atualizada via DX-011 em `documentation/qa/api-endpoint-matrix.md` e `documentation/qa/api-test-playbook.md`.

### [SPR-002] Sprint de prioridades - Operacao previsivel + Qualidade mensuravel
- Janela: 2026-03-09 a 2026-03-20
- Objetivo: elevar previsibilidade operacional, cobertura de contrato e qualidade de resposta com gates objetivos antes de novas frentes de ML de alto risco.
- Status: em andamento (adiantado em 2026-02-21)

**Backlog priorizado (ordem de execucao):**

| Ordem | ID | Tema | Prioridade | Esforco | Resultado esperado na sprint |
|---|---|---|---|---|---|
| 1 | OQ-011 | Cobertura automatizada das APIs | P0 | M | concluido (2026-02-21): geracao automatica de matriz + cobertura JSON/MD + evidencias Docker (ops-validation), inventario observado 230/231 |
| 2 | OQ-002 | SLOs por dominio com alertas | P0 | M | concluido (2026-02-21): metricas por dominio, endpoint de SLO com alertas, regras Prometheus e dashboard Grafana |
| 3 | MR-013 | Avaliacao offline recorrente | P0 | S | concluido (2026-02-21): baseline versionado + comparacao automatica pre-merge no quality-gates |
| 4 | MR-002 | Politica explicita de roteamento | P0 | M | regras de decisao documentadas e telemetria por source/latency/confidence |
| 5 | PX-011 | UX do chat simplificada | P0 | S | modo simples como padrao e painel avancado opcional sem regressao funcional |
| 6 | SG-013 | Rotacao de logs e expurgo | P1 | S | politica de rotacao/retencao aplicada a logs de auditoria com verificacao automatica |

**Criticos da sprint (nao-negociavel):**
- OQ-011 e OQ-002 concluidos com evidencias versionadas.
- MR-013 concluido com evidencias versionadas.
- Sem aumento de taxa de erro em endpoints criticos apos ativacao dos novos gates.

**Stretch goals (se houver capacidade):**
- OQ-009 (regressao semantica automatica antes de deploy).
- DX-005 (testes de carga para chat e retrieval).

**Definicao de pronto da SPR-002:**
- Cobertura de APIs executada em CI com artefato de resultado por execucao.
- SLOs publicados com alertas ativos e ownership definido por dominio.
- Gate de qualidade (baseline offline) bloqueando merge quando houver regressao acima do limite.
- Politica de roteamento MR-002 com regras, fallback e observabilidade documentados.
- Evidencia de validacao com 0 erros criticos em log nos cenarios da sprint.

**Evidencias parciais (2026-02-28):**
- PX-013 concluido: prompts `system_identity` e `system_identity_enforcement` atualizados, sanitizacao refinada para contexto de autoidentificacao e comando `/about` alinhado a narrativa Janus-first.
- Testes focados da rodada executados com sucesso (8 passed):
  `qa/test_chat_agent_loop_content_safety.py`,
  `backend/tests/unit/test_identity_sanitizer.py`,
  `backend/tests/unit/test_chat_about_identity.py`.
- Execucao isolada de `qa/test_chat_endpoint_contract.py` com falhas preexistentes no dublê de servico (3 failed) sem relacao direta com PX-013:
  `test_chat_message_low_confidence_requires_confirmation`,
  `test_chat_stream_contract_headers_events_and_actor_fallback_user`,
  `test_chat_events_contract_headers_event_and_actor_fallback_user`.

---

## Template para novas ideias

Copiar e preencher:

```md
### [ID] Titulo da melhoria
- Problema atual:
- Solucao proposta:
- Impacto esperado:
- Riscos:
- Dependencias:
- Prioridade:
- Esforco:
- Dono:
- Status:
```

### [SG-014] Vazamento de PII em logs de Chat e Collaboration
- Problema atual: Os serviços `ChatCommandHandler` (argumentos do usuário), `ChatEventPublisher` (conteúdo da mensagem) e `CollaborationService` (artefatos e mensagens) loggam conteúdo sensível que constitui risco de PII/LGPD.
- Solucao proposta: Aplicar redação (PII redaction) antes de loggar, ou usar logs estruturados com restrição de acesso e ofuscação de dados textuais.
- Impacto esperado: Conformidade com LGPD e prevenção de vazamento de dados sensíveis em logs plain text.
- Riscos: Perda parcial de contexto para debugging se ofuscação for agressiva.
- Dependencias: Módulo `app.core.memory.security` para usar regex de PII já existentes.
- Prioridade: P0
- Esforco: S
- Dono: a definir
- Status: ideia

### [OQ-013] Rate Limiting Fail-Closed
- Problema atual: O middleware `rate_limit_middleware.py` bloqueia requisições (503) se o Redis estiver indisponível em produção (fail-closed) invés de fail-open.
- Solucao proposta: Configurar a política do Rate Limit para modo `fail-open`, permitindo a requisição prosseguir com degradação graciosa caso o Redis caia.
- Impacto esperado: Maior disponibilidade do sistema (Availability > 99.9%) caso o serviço de cache fique indisponível temporariamente.
- Riscos: Possível sobrecarga da API durante interrupção do Redis.
- Dependencias: Ajuste na injeção do rate limiter.
- Prioridade: P1
- Esforco: S
- Dono: a definir
- Status: ideia

### [SG-015] Fuga de Autenticação em Workspaces API
- Problema atual: Endpoints em `backend/app/api/v1/endpoints/workspace.py` usam `Depends(get_collaboration_service)` sem aplicar verificação de AuthN/AuthZ.
- Solucao proposta: Adicionar dependência de autenticação (ex: `Depends(get_current_user)`) aos endpoints do workspace.
- Impacto esperado: Prevenir que usuários anônimos manipulem workspaces e desliguem o sistema.
- Riscos: Nenhum.
- Dependencias: Nenhuma.
- Prioridade: P0
- Esforco: S
- Dono: a definir
- Status: ideia

### [SG-016] Vulnerabilidade do Header X-User-Id
- Problema atual: `backend/app/core/infrastructure/auth.py` confia no header `X-User-Id` por padrão, possibilitando Bypass/Impersonation.
- Solucao proposta: Desabilitar o `AUTH_TRUST_X_USER_ID_HEADER` em produção e validar JWT/Token robusto.
- Impacto esperado: Correção de vulnerabilidade crítica de spoofing de usuário.
- Riscos: Quebra de compatibilidade em ambientes internos que confiam no header sem token.
- Dependencias: Ajuste de configuração em `config.py`.
- Prioridade: P0
- Esforco: S
- Dono: a definir
- Status: ideia

### [PX-013] Refatoração de God Objects e Componentes Complexos
- Problema atual: `observability_service.py` (~1200 linhas) e `frontend/src/app/services/backend-api.service.ts` (~1638 linhas) e `conversations.ts` (~1700 linhas) concentram lógica excessiva.
- Solucao proposta: Quebrar o serviço de observabilidade em (Health, Metrics, Audit, Anomaly) e particionar os componentes Frontend aplicando SRP e NgRx/Store.
- Impacto esperado: Menor complexidade ciclomática, testes mais simples e manutenção sustentável.
- Riscos: Regressões durante o processo de split de classes.
- Dependencias: Nenhuma.
- Prioridade: P2
- Esforco: L
- Dono: a definir
- Status: ideia

### [SG-017] Endpoint de Auth exposto a brute-force
- Problema atual: `backend/app/api/v1/endpoints/auth.py` (login/refresh) não possuem rate limiter.
- Solucao proposta: Decorar a rota de login com `@limiter.limit("5/minute")` para prevenir ataques de dicionário e brute-force.
- Impacto esperado: Maior resiliência contra ataques de força bruta.
- Riscos: Bloqueio acidental de IPs em caso de NAT/Proxy (necessário extrair IP real).
- Dependencias: O Rate Limit com Redis.
- Prioridade: P1
- Esforco: S
- Dono: a definir
- Status: ideia

### [OQ-014] Hardcoded Paths e Criação Precoce de Diretórios
- Problema atual: Trabalhadores assíncronos e testes quebram por `PermissionError` em caminhos como `/app/workspace` e `.mkdir()` fora de contexto em `NeuralTrainer`.
- Solucao proposta: Usar sempre `app.core.infrastructure.filesystem_manager.WORKSPACE_DIR` e garantir que o `mkdir` ocorre apenas na hora da execução (e.g. `_save_model`).
- Impacto esperado: Compatibilidade cross-environment (Docker/Local/CI) robusta.
- Riscos: Quebra momentânea de caminhos estáticos assumidos.
- Dependencias: filesystem_manager.
- Prioridade: P1
- Esforco: S
- Dono: a definir
- Status: ideia

### [SG-018] Vulnerabilidade OS Command Injection
- Problema atual: `backend/app/core/tools/launcher_tools.py` permite RCE e injeção de comandos devido ao uso inseguro de `subprocess.Popen` com o argumento `shell=True`.
- Solucao proposta: Substituir por um array de argumentos em formato de lista (ex: `subprocess.Popen(["start", '""', app_name])`) ou outra alternativa da stdlib sem shell string execution.
- Impacto esperado: Remoção imediata de risco crítico mapeado por linter (Bandit B602).
- Riscos: Quebra de compatibilidade em certos Windows App execution paths.
- Dependencias: Nenhuma
- Prioridade: P0
- Esforco: S
- Dono: a definir
- Status: ideia

### [SG-019] Vazamento contínuo de PII e estado global inseguro (Produtividade)
- Problema atual: `backend/app/core/tools/productivity_tools.py` possui listas de notas/calendário armazenadas globalmente em memória (`_notes`, `_calendar_events`) vazando contexto através de requests. Além disso, o logger grava emails e ids abertos.
- Solucao proposta: Remover as globais para um repositório restrito por sessão/DB e ofuscar IDs, e-mails, e assuntos no logger do `send_email`.
- Impacto esperado: Conformidade com LGPD e eliminação de falhas de isolamento no state application.
- Riscos: Redução de velocidade na execução destas ferramentas caso banco/cache esteja lento.
- Dependencias: Camada de mascaramento em `logging_config.py`.
- Prioridade: P1
- Esforco: M
- Dono: a definir
- Status: ideia

### [SG-026] Vulnerabilidade de Code Injection e Execução Arbitrária
- Problema atual: Uso de `subprocess.Popen` com `shell=True` (OS Command Injection) e também chamadas como `exec`/`eval` estão presentes em `backend/app/core/tools/launcher_tools.py`, `backend/app/core/infrastructure/python_sandbox.py` e `backend/app/core/tools/faulty_tools.py`.
- Solucao proposta: Refatorar subprocess para usar listas de parâmetros removendo `shell=True`. Aplicar mecanismos de sandbox restrito para as camadas de interpretação de Python local e remover `exec`/`eval` não sanitizados.
- Impacto esperado: Remoção da possibilidade de escalonamento de privilégio e execução indevida no host/container da API.
- Riscos: Falhas de funcionalidade em ferramentas que dependam do Shell global ou de injeção dinâmica intencional.
- Dependencias: Nenhuma.
- Prioridade: P0
- Esforco: S
- Dono: a definir
- Status: aberto

### [SG-041] Vazamento LGPD em Monitoramento Shadow (Tailscale)
- Problema atual: O script PowerShell `tooling/secure-tailscale-setup.ps1` atua como um monitor de segurança independente que registra eventos e metadados de hostnames em logs de texto sem a redação de PII padrão do sistema.
- Solucao proposta: Interromper a geração local desse arquivo de log, delegar a telemetria do Tailscale à API principal do Janus para processamento (via pipeline de ofuscação) ou eliminar o log no disco do usuário.
- Impacto esperado: Restauração da conformidade LGPD e centralização da proteção de dados em logs.
- Riscos: Queda de observabilidade nativa na máquina local caso o agente apresente falha de comunicação com o backend.
- Dependencias: Modificar script de tooling.
- Prioridade: P1
- Esforco: S
- Dono: a definir
- Status: aberto

### [DX-013] Scripts de QA sem timeout e isolados do Pytest (Testes/Arquitetura)
- Problema atual: O script `tooling/test_debate_system.py` atua como teste E2E do grafo sem utilizar runners de validação (`pytest`), enquanto carece de mecanismos de timeout assíncrono durante iterações do grafo LangGraph (`astream`).
- Solucao proposta: Refatorar e mover esses testes para o diretório de Quality Assurance (`qa/`) integrando-os na pipeline Pytest (usando os hooks e markers corretos como `asyncio.wait_for`).
- Impacto esperado: Aumento da segurança de regressão com relatórios integrados, evitando hangs não monitorados em esteiras de Continuous Integration.
- Riscos: Falhas por limite temporal no QA se as queries das ferramentas no grafo excederem o threshold estabelecido.
- Dependencias: Pytest no pipeline `qa`.
- Prioridade: P1
- Esforco: S
- Dono: a definir
- Status: aberto

### [SG-027] Criação Insegura de Arquivos Temporários
- Problema atual: Caminhos temporários hardcoded (`/tmp`) no arquivo `backend/app/core/memory/log_aware_reflector.py` podem causar vazamento ou serem explorados via Time-of-check to time-of-use (TOCTOU).
- Solucao proposta: Utilizar o módulo `tempfile` da biblioteca padrão com flags apropriadas (ou delegar ao `filesystem_manager`).
- Impacto esperado: Arquivos temporários serão restritos e protegidos a nível de SO.
- Riscos: Nenhum.
- Dependencias: Nenhuma.
- Prioridade: P1
- Esforco: S
- Dono: a definir
- Status: aberto

### [SG-028] Abertura de URL com Esquemas Arbitrários (SSRF / File Read)
- Problema atual: Uso de `urllib.urlopen` em `backend/app/core/infrastructure/message_broker.py` e `backend/app/core/tools/agent_tools.py` permitindo esquemas não HTTP (como `file://`), possibilitando Server-Side Request Forgery ou leitura arbitrária.
- Solucao proposta: Forçar restrição e checagem de url explícita (`startswith('http://')` ou `'https://'`) antes de invocar a chamada ou delegar ao `httpx` / `requests` estritos.
- Impacto esperado: Bloqueio de leitura de arquivos locais via API.
- Riscos: Ferramentas de desenvolvimento podem parar se usarem esquemas locais intencionalmente.
- Dependencias: Nenhuma.
- Prioridade: P1
- Esforco: S
- Dono: a definir
- Status: aberto

### [SG-029] Exposição de Credenciais Hardcoded em Scripts
- Problema atual: Scripts como `tooling/run_api_e2e_all.py`, `benchmark_complex_process.py` e `chaos_harness.py` efetuam log e print explícitos de secrets e senhas no stdout do processo.
- Solucao proposta: Substituir prints dessas informações por ofuscações `***` ou variáveis de ambiente/mock (`SecretStr`).
- Impacto esperado: Menor risco de exposição de credenciais em logs de sistema e ambientes de CI/CD.
- Riscos: Nenhum.
- Dependencias: Nenhuma.
- Prioridade: P1
- Esforco: S
- Dono: a definir
- Status: aberto
### [SG-023] Vazamento Biométrico em logs do Daemon
- Problema atual: O `backend/app/interfaces/daemon/daemon.py` arquiva comandos de voz (dados possivelmente sensíveis) nos logs do sistema sem minimização.
- Solucao proposta: Aplicar a camada de _PII scrubbing_ da aplicação antes do dump para texto ou remover esse log em produção.
- Impacto esperado: Conformidade com LGPD / minimização de dados.
- Riscos: Redução de utilidade em debugging de áudio local.
- Dependencias: `app.core.memory.security`.
- Prioridade: P1
- Esforco: S
- Dono: a definir
- Status: aberto

### [SG-030] Fuga de observabilidade em falha do RabbitMQ
- Problema atual: `backend/app/core/infrastructure/message_broker.py` apresenta falha silenciosa (Silent fail-open) ao falhar a conexão com RabbitMQ, omitindo o problema para ferramentas de alerta e deixando a aplicação em estado degradado escondido.
- Solucao proposta: Implementar uma camada de Circuit Breaker com alertas imediatos nos logs/métricas antes do fallback para offline.
- Impacto esperado: Melhor tempo de resposta em incidentes de rede e broker down.
- Riscos: Overhead temporário na tentativa de reconexão.
- Dependencias: Modificação do message broker.
- Prioridade: P1
- Esforco: S
- Dono: a definir
- Status: aberto

### [SG-031] Vulnerabilidade de XML Parsing em DOCX (Bandit B314)
- Problema atual: `backend/app/services/document_parser_service.py` utiliza `xml.etree.ElementTree.fromstring` que é vulnerável a ataques de XML External Entity (XXE) / Billion Laughs.
- Solucao proposta: Migrar para `defusedxml.ElementTree` ou garantir a chamada de `defusedxml.defuse_stdlib()` global.
- Impacto esperado: Proteção ativa contra injeções no parsers de documentos.
- Riscos: Quebra do parse de alguns documentos caso o pacote `defusedxml` não esteja na venv.
- Dependencias: Instalação do pacote `defusedxml`.
- Prioridade: P0
- Esforco: S
- Dono: a definir
- Status: aberto

### [SG-032] Agente Windows binding a 0.0.0.0 (Bandit B104)
- Problema atual: O `backend/windows_agent.py` sobe seu servidor no host configurando binding global `0.0.0.0` sem autenticação.
- Solucao proposta: Restringir o host inicial para `127.0.0.1` ou exigir tokens fortes se exposição for esperada.
- Impacto esperado: Prevenção de acesso indevido da rede local aos comandos OS.
- Riscos: Quebra de acesso caso existam clientes locais em outros IPs conectando via LAN.
- Dependencias: Ajuste de flags da cli do Uvicorn no script.
- Prioridade: P0
- Esforco: S
- Dono: a definir
- Status: aberto

### [SG-033] Requisição sem timeout em scripts de evolução (Bandit B113)
- Problema atual: Em `backend/scripts/test_tool_evolution_chat.py`, `requests` é usado sem o parâmetro opcional `timeout`.
- Solucao proposta: Definir `timeout=10` ou equivalente nas chamadas web para evitar resource starvation (Hanging requests).
- Impacto esperado: Prevenção contra stalls na execução de CI ou evolução.
- Riscos: Timeout errors para redes muito lentas, que antes apenas paravam esperando eternamente.
- Dependencias: Nenhuma.
- Prioridade: P2
- Esforco: S
- Dono: a definir
- Status: aberto

### [SG-034] Atualizar vulnerabilidades do Frontend via `npm audit`
- Problema atual: Diversas dependências do frontend possuem vulnerabilidades de segurança severas (ex: `@angular/core`, `@hono/node-server`, `dompurify`, `tar`).
- Solucao proposta: Executar `npm audit fix` ou atualizar as dependências manualmente `package.json` para as versões corrigidas mais recentes e recompilar.
- Impacto esperado: Prevenção contra vulnerabilidades XSS, Prototype Pollution e Hardlink Path Traversal.
- Riscos: Quebras em build caso ocorram atualizações majoritárias.
- Dependencias: Testes da pipeline de frontend `npm run test`.
- Prioridade: P1
- Esforco: M
- Dono: a definir
- Status: aberto

### [SG-035] Uso do exec() Inseguro no Sandbox (Bandit B102)
- Problema atual: A função `backend/app/core/infrastructure/python_sandbox.py` utiliza o comando built-in `exec()` que possibilita execução de código arbitrário e pode escapar facilmente se a validação/sanitização não for robusta.
- Solucao proposta: Substituir por um modelo de containerização/isolamento estrito (como gVisor ou seccomp) em vez de executar `exec()` com strings do usuário nativamente.
- Impacto esperado: Evitar bypass do sandbox nativo que leve a RCE crítico no backend.
- Riscos: Redução de flexibilidade para o desenvolvedor ou agente usando a ferramenta e sobrecarga caso opte por virtualização.
- Dependencias: Nenhuma.
- Prioridade: P0
- Esforco: L
- Dono: a definir
- Status: aberto

### [SG-036] Criação Insegura de Arquivos Temporários (Bandit B108)
- Problema atual: Criação manual ou com caminhos previsíveis hardcoded (ex: `/tmp/`) na classe `backend/app/core/memory/log_aware_reflector.py`, possibilitando vulnerabilidades como TOCTOU.
- Solucao proposta: Usar sempre a biblioteca segura `tempfile` (como `tempfile.NamedTemporaryFile`) ou o serviço local unificado do sistema.
- Impacto esperado: Prevenção de ataques de Symlink/Colisão locais.
- Riscos: Nenhum risco funcional grave; refatoração simples.
- Dependencias: Nenhuma.
- Prioridade: P2
- Esforco: S
- Dono: a definir
- Status: aberto
