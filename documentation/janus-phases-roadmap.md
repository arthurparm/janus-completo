# Janus - Roadmap por Fases (Diagnostico -> Features)

## Objetivo
Definir uma execucao em duas fases para reduzir risco tecnico e acelerar validacao de valor:

1. Fase A: diagnostico do nucleo Janus.
2. Fase B: features de uso diario (lembretes, leitura de documentos, consulta com citacao).

---

## Fase A - Diagnostico do Janus (3-4 dias)

### Meta
Estabelecer baseline tecnico e observabilidade antes de ampliar funcionalidades.

### Escopo
1. Mapear pipeline completo: ingestao -> memoria -> recuperacao -> resposta.
2. Instrumentar telemetria minima por resposta.
3. Criar conjunto fixo de avaliacao com perguntas reais.
4. Definir politica de roteamento entre bancos.

### Entregaveis
1. Mapa do fluxo atual documentado.
2. Logs estruturados por resposta com:
   - fonte(s) utilizadas;
   - banco(s) consultado(s);
   - latencia total e por etapa;
   - nivel de confianca;
   - erros/fallbacks.
3. Comando/script de avaliacao para rodar dataset fixo.
4. Relatorio baseline com metricas iniciais.

### Criterios de Aceite (AC)
1. `AC-DIAG-01`: Cada resposta registra `source`, `db`, `latency_ms`, `confidence`, `error_code` (quando houver).
2. `AC-DIAG-02`: Existe comando unico para rodar avaliacao em dataset fixo e gerar score.
3. `AC-DIAG-03`: Roteamento inicial definido:
   - `Postgres`: estado transacional (lembretes, preferencias, tarefas).
   - `ChromaDB`: busca semantica de documentos.
   - `Neo4j`: relacoes/entidades complexas, inicialmente opcional.
4. `AC-DIAG-04`: Baseline publicado e versionado para comparacao futura.

### Detalhamento Operacional

#### Frente 1 - Observabilidade do Pipeline
1. Instrumentar etapas: `ingestion`, `retrieval`, `context_build`, `response_generation`.
2. Adicionar correlacao por `request_id`.
3. Definir payload minimo de log:
   - `timestamp`
   - `request_id`
   - `stage`
   - `latency_ms`
   - `db_hits`
   - `sources`
   - `confidence`
   - `fallback_used`
   - `error_code`

#### Frente 2 - Harness de Avaliacao
1. Criar dataset fixo com 15-20 perguntas reais do produto.
2. Criar runner unico (`eval`) para executar todas as perguntas.
3. Gerar artefatos:
   - `score.json`
   - resumo em markdown com acertos/erros por categoria
   - latencia por caso

#### Frente 3 - Politica de Roteamento
1. Definir matriz de decisao por tipo de consulta.
2. Aplicar regras iniciais:
   - `Postgres`: estado transacional.
   - `ChromaDB`: busca semantica em documentos.
   - `Neo4j`: consultas de relacao multi-entidade (por feature flag no inicio).
3. Registrar motivo da decisao de roteamento no log.

#### Frente 4 - Operacao Segura
1. Definir limite de confianca (`confidence_threshold`) para acionar confirmacao com usuario.
2. Implementar timeout por etapa e fallback para resposta degradada.
3. Garantir que erro em um backend nao derrube a resposta inteira.

### Metricas-Alvo Iniciais (Ajustaveis)
1. `p95_latency_consulta <= 3500ms`
2. `citation_coverage >= 90%` em respostas baseadas em documentos.
3. `fallback_correctness >= 95%` quando confianca baixa.
4. `eval_pass_rate >= 80%` no dataset inicial.

### Plano Sugerido (3-4 dias)
1. Dia 1: instrumentacao + schema de log + correlacao por `request_id`.
2. Dia 2: dataset de avaliacao + comando `eval` + primeiro `score.json`.
3. Dia 3: roteador por regras + fallback/timeout + telemetria completa.
4. Dia 4 (opcional): ajustes finos para bater metricas-alvo e publicar baseline.

### Stories Tecnicas da Fase A

#### Story A.1 - Telemetria Estruturada por Requisicao
**Objetivo:** Garantir visibilidade ponta a ponta do pipeline.

**Tarefas:**
1. Criar middleware/hook de `request_id`.
2. Instrumentar latencia por etapa.
3. Persistir logs estruturados com schema padrao.

**Given/When/Then:**
1. **Given** uma pergunta enviada ao Janus, **When** a resposta e processada, **Then** existe log com `request_id` e etapas executadas.
2. **Given** falha em uma etapa, **When** o erro ocorre, **Then** `error_code` e `fallback_used` sao registrados.

#### Story A.2 - Harness de Avaliacao Repetivel
**Objetivo:** Medir qualidade por comparacao de baseline.

**Tarefas:**
1. Montar dataset inicial com perguntas reais.
2. Implementar comando unico `eval`.
3. Gerar `score.json` e resumo markdown.

**Given/When/Then:**
1. **Given** o dataset fixo, **When** o comando `eval` roda, **Then** gera score consolidado sem intervencao manual.
2. **Given** duas execucoes em momentos diferentes, **When** comparadas, **Then** e possivel identificar regressao/evolucao.

#### Story A.3 - Roteador Inicial de Bancos
**Objetivo:** Evitar acoplamento precoce e tornar decisao previsivel.

**Tarefas:**
1. Criar matriz de decisao por tipo de consulta.
2. Implementar roteador com regras explicitas.
3. Logar banco escolhido e justificativa.

**Given/When/Then:**
1. **Given** uma consulta de estado transacional, **When** o roteador classifica, **Then** seleciona `Postgres`.
2. **Given** uma pergunta sobre conteudo documental, **When** classifica, **Then** seleciona `ChromaDB`.
3. **Given** consulta de relacao complexa e flag ativa, **When** classifica, **Then** pode selecionar `Neo4j`.

#### Story A.4 - Fallback por Baixa Confianca
**Objetivo:** Reduzir respostas incorretas com alta confianca aparente.

**Tarefas:**
1. Definir `confidence_threshold`.
2. Implementar fluxo de confirmacao com usuario em baixa confianca.
3. Registrar eventos de fallback para auditoria.

**Given/When/Then:**
1. **Given** `confidence` abaixo do threshold, **When** Janus termina a analise, **Then** ele pede confirmacao antes de afirmar.
2. **Given** fallback acionado, **When** o fluxo conclui, **Then** evento fica registrado no log.

#### Story A.5 - Baseline Versionado
**Objetivo:** Ter referencia estavel antes de iniciar features da Fase B.

**Tarefas:**
1. Rodar avaliacao completa apos instrumentacao e roteamento.
2. Publicar baseline com metricas de qualidade e latencia.
3. Versionar artefatos para comparacoes futuras.

**Given/When/Then:**
1. **Given** historias A.1-A.4 concluidas, **When** o baseline e publicado, **Then** existe pacote versionado de metricas e evidencias.
2. **Given** uma mudanca futura no Janus, **When** nova avaliacao for executada, **Then** comparacao com baseline e direta.

### Definition of Done (Fase A)
1. ACs `AC-DIAG-01` a `AC-DIAG-04` atendidos.
2. Stories A.1 a A.5 concluida com evidencias.
3. Metricas baseline publicadas e versionadas.
4. Decisao de roteamento documentada e ativa no sistema.

### Riscos mitigados
1. Evoluir features sem saber por que respostas pioraram.
2. Acoplamento prematuro entre bancos.
3. Dificuldade de depurar erros de recuperacao/contexto.

---

## Fase B - Features Core (5-7 dias)

### Meta
Entregar valor diario com um kit funcional para operacao real.

### Escopo
1. Lembretes de contas via chat com confirmacao explicita.
2. Lista de contas por status: a vencer, vencidas, pagas.
3. Notificacoes no chat (D-1 e no dia).
4. Ingestao de documentos (PDF/TXT/MD).
5. Consulta de documentacao com citacao de origem.

### Entregaveis
1. Fluxo E2E de lembretes funcionando em `Postgres`.
2. Processo de ingestao e indexacao de documentos no `ChromaDB`.
3. Consulta com resposta curta + referencias de arquivo/trecho.
4. Acao de marcar conta como paga no chat.

### Criterios de Aceite (AC)
1. `AC-FEAT-01`: Janus detecta intencao de lembrete no chat e pede confirmacao antes de salvar.
2. `AC-FEAT-02`: Lembrete persistido aparece na lista correta por status.
3. `AC-FEAT-03`: Notificacao dispara em D-1 e no dia do vencimento.
4. `AC-FEAT-04`: Documentos sao ingeridos com metadados minimos (origem, data, tipo).
5. `AC-FEAT-05`: Consulta retorna resposta com pelo menos uma citacao rastreavel.

### Fora do escopo desta fase
1. Billing.
2. Multi-tenant.
3. OCR avancado.
4. Permissoes complexas.
5. Raciocinio de grafo obrigatorio para toda consulta.

---

## Dependencias e Ordem Recomendada
1. Fechar Fase A primeiro para fixar baseline e telemetria.
2. Iniciar Fase B com lembretes (`Postgres`), depois documentos/consulta (`ChromaDB`).
3. Ativar uso do `Neo4j` por feature flag quando houver caso claro de relacoes complexas.

---

## Indicadores de Sucesso
1. Confiabilidade: taxa de sucesso do fluxo de lembretes.
2. Qualidade de resposta: score de avaliacao comparado ao baseline.
3. Tempo de resposta: latencia mediana dentro da meta definida.
4. Utilidade: frequencia de uso diario dos fluxos principais.
