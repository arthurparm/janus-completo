---
apply: always
---

Projeto Janus: Sprints de Desenvolvimento Detalhados

Este documento é o diário de bordo do desenvolvimento do Projeto Janus, organizado conforme as fases definidas
no [Relatório de Projeto Arquitetural](DOCUMENTACAO%20JANUS.md).

---

## Fase 1: A Espinha Dorsal (Sprints 1-3)

**Foco:** Estabelecer a fundação da comunicação distribuída e da memória de longo prazo.

### Sprint 1: Espinha Dorsal do Sistema – Fundamentos de Comunicação Distribuída

Foco Principal: Estabelecer uma arquitetura de comunicação assíncrona e distribuída, crucial para a escalabilidade e
resiliência do sistema Janus.
Implementações-chave:
Integração e configuração do RabbitMQ como o principal message broker para troca de mensagens entre os componentes do
sistema.
Desenvolvimento de módulos de publicação e consumo de tarefas, permitindo que diferentes partes do Janus possam enviar e
receber requisições de forma desacoplada e eficiente.

### Sprint 2: Núcleo Cognitivo - Mente Inicial – Aprendizagem Baseada em Experiências

Foco Principal: Desenvolver a capacidade de aprendizagem do Janus por uma "Memória Episódica", armazenando e
recuperando experiências passadas.
Implementações-chave:
Implementação do banco de dados vetorial Qdrant para armazenamento eficiente de representações vetoriais de
experiências (embeddings), facilitando buscas por similaridade.
Criação de um módulo de gestão de memória, responsável por adicionar, buscar e gerenciar as memórias episódicas.
Remoções Importantes:
Remoção do PostgreSQL como componente primário de armazenamento, optando por soluções mais adequadas para dados
vetoriais e relações complexas.

### Sprint 3: Inteligência e Consciência - Despertar – Uso da Memória e Percepção Ambiental

Foco Principal: Habilitar o Janus a utilizar sua memória episódica e a perceber o ambiente externo para contextualizar
suas ações e respostas.
Implementações-chave:
Desenvolvimento de funções de busca de memórias mais sofisticadas, permitindo a recuperação relevante de informações
passadas com base no contexto atual.
Criação de um módulo de contexto que integra informações como data/hora atual e resultados de busca na web, enriquecendo
a percepção ambiental do agente.

---

## Fase 2: O Núcleo Cognitivo (Sprints 4-7)

**Foco:** Implementar a capacidade de raciocínio (ReAct), execução segura (Sandbox) e aprendizado com erros (Reflexion).

### Sprint 4: Autonomia e Segurança - Agente Funcional – Ciclo de Raciocínio e Ambiente Controlado

Foco Principal: Estabelecer um ciclo de raciocínio robusto para o agente e garantir um ambiente seguro para a execução
de ações.
Implementações-chave:
Adoção e implementação do Ciclo ReAct (Reasoning and Acting), que permite ao agente raciocinar sobre qual ação tomar e
executá-la de forma iterativa.
Criação de um sandbox Python (Langchain, Epicbox) para execução segura de código gerado ou externo, isolando o ambiente
principal do sistema.

### Sprint 5: Auto-otimização e Aprendizado com Erros (Reflexion) – Aprimoramento Contínuo

Foco Principal: Capacitar o Janus a aprender com suas falhas e otimizar seu desempenho de forma autônoma.
Implementações-chave:
Implementação do padrão Reflexion, onde o agente analisa seus próprios resultados e identifica pontos de melhoria.
Desenvolvimento de ferramentas "defeituosas" para erros controlados, permitindo ao agente praticar a identificação e
correção de falhas em um ambiente simulado.
Criação de um Agente de Autorreflexão dedicado à análise de falhas e à extração de "lições aprendidas".

### Sprint 6: Agente Multitarefa e Gateway de Ferramentas – Expansão de Capacidades

Foco Principal: Ampliar a capacidade do Janus de interagir com o mundo externo e executar múltiplas tarefas.
Implementações-chave:
Desenvolvimento do action_module, que provê um conjunto dinâmico de ferramentas que o agente pode utilizar, como
interação com o sistema de arquivos ou acesso a APIs.
Refatoração do janus_core para melhorar a orquestração de tarefas, incluindo a capacidade de interagir com o sistema de
arquivos e a geração dinâmica de ferramentas Python.

### Sprint 7: Despertar da Proatividade – Ciclo de Auto-Otimização – Iniciativa Autônoma

Foco Principal: Habilitar o Janus a tomar a iniciativa para se aperfeiçoar, sem intervenção externa.
Implementações-chave:
Criação de um "Meta-Agente de Auto-Otimização" que monitora o desempenho do sistema e planeja melhorias.
Implementação de um ciclo de planejamento e execução autônoma de melhorias, onde o agente identifica gargalos e aplica
soluções.

---

## Fase 3: Inteligência e Expansão (Sprints 8-10)

**Foco:** Transformar experiências em sabedoria (Memória Semântica), coletar dados e hibridizar a inteligência (LLMs).

### Sprint 8: Consolidação do Conhecimento – Memória à Sabedoria – Transformação de Experiências

Foco Principal: Transformar as experiências brutas armazenadas em conhecimento estruturado e interconectado.
Implementações-chave:
Integração de uma Memória Semântica utilizando Neo4j, um banco de dados de grafos, para representar relações complexas
entre conceitos e eventos.
Desenvolvimento de um worker knowledge_consolidator responsável por extrair e organizar informações da memória episódica
para a memória semântica.
Aprimoramento do agente principal para consultar e utilizar o conhecimento estruturado da memória semântica em seu
raciocínio.

### Sprint 9: Gênese Neural – Infraestrutura para Aprendizagem Autônoma – Coleta de Dados e Treinamento

Foco Principal: Estabelecer a infraestrutura para a coleta de dados de experiência e o treinamento autônomo de redes
neurais.
Implementações-chave:
Desenvolvimento de workers data_harvester (coleta de dados de interação) e neural_trainer (treinamento de modelos de
IA).
Integração da rede neural ao janus_core, permitindo que o agente utilize e atualize seus modelos de aprendizado.

### Sprint 10: Cérebro Híbrido e Resiliência de APIs

O objetivo principal deste sprint é aprimorar a inteligência do Projeto Janus na utilização de Modelos de Linguagem (
LLMs).
Para isso, será implementado um sistema capaz de alternar dinamicamente entre diferentes provedores de API (como
OpenAI e Google Gemini) e um modelo local (Ollama) como alternativa. Esta abordagem visa aumentar a robustez do sistema
contra falhas e otimizar custos. Visão Geral da Solução

Será desenvolvido um "Gerenciador de LLMs" central, responsável por tomar decisões inteligentes:
Criação do LLMManager: Esta entidade atuará como o "cérebro" do sistema, determinando qual LLM utilizar com base na
tarefa em questão, considerações de custo e disponibilidade.
Lógica de Fallback Automático: Caso a chamada à API principal (por exemplo, OpenAI) falhe ou atinja um limite de uso, o
sistema automaticamente tentará executar a mesma tarefa utilizando um modelo de fallback local (via Ollama).
Monitoramento do Uso de API: O Janus passará a registrar a frequência de uso de cada API paga, a fim de evitar a
superação dos limites mensais gratuitos.

---

## Fase 4: Maturidade e Proatividade (Sprints 11-13)

**Foco:** Habilitar a colaboração entre agentes, garantir a resiliência do sistema e lançar o Meta-Agente de
auto-otimização.

### Sprint 11: Colaboração Agêntica – Sociedade de Mentes – Sistema Colaborativo Dinâmico ✅

Foco Principal: Evoluir o Janus para um sistema colaborativo, onde múltiplos agentes podem trabalhar em conjunto.

Implementações-chave:

- ✅ Criação de um Agente "Gestor de Projetos" para coordenar as atividades dos demais agentes
- ✅ Desenvolvimento de um Espaço de Trabalho Compartilhado (SharedWorkspace) onde os agentes podem trocar informações e
  recursos
- ✅ Implementação de fluxos de trabalho colaborativos, permitindo que os agentes dividam e executem tarefas de forma
  coordenada
- ✅ Sistema de mensagens inter-agente para comunicação assíncrona
- ✅ Gestão de artefatos compartilhados (arquivos, dados, resultados)
- ✅ APIs RESTful completas para gerenciamento de agentes, tarefas, workspace e colaboração

Agentes Especializados Implementados:

1. **Project Manager** (Gestor de Projetos) - Coordena e planeja projetos
2. **Researcher** (Pesquisador) - Busca e analisa informações
3. **Coder** (Desenvolvedor) - Escreve código de alta qualidade
4. **Tester** (Testador) - Valida e testa funcionalidades
5. **Documenter** (Documentador) - Cria documentação técnica
6. **Optimizer** (Otimizador) - Melhora performance e qualidade

Melhorias e Correções Críticas (Reforço Sprint 11):

- ✅ **Parser de JSON robusto**: Implementado `_clean_json_output()` para remover markdown code blocks (```json) que
  causavam erros de parsing
- ✅ **Validação de paths segura**: Ferramenta `list_directory` agora valida e restringe acesso ao workspace (
  /app/workspace), impedindo acesso a diretórios não autorizados
- ✅ **Documentação aprimorada de ferramentas**: `write_file` com exemplos explícitos de uso correto dos 3 parâmetros
  obrigatórios (file_path, content, overwrite)
- ✅ **Prompts especializados**: Cada agente possui prompt otimizado com instruções claras sobre uso de ferramentas
- ✅ **Retry automático**: Sistema de retry com backoff exponencial (máx 3 tentativas) para tarefas que falham
- ✅ **Timeout configurável**: AgentExecutor com timeout de 180s e máximo de 15 iterações
- ✅ **Tratamento de erros robusto**: Captura e categorização de erros (timeout, validação, execução)
- ✅ **Workspace automático**: Diretório /app/workspace criado automaticamente na inicialização
- ✅ **Métricas Prometheus**: Contadores e histogramas para tarefas, colaborações e duração
- ✅ **Validação de output**: Verifica se agentes retornam output válido antes de marcar tarefa como completa

Endpoints Implementados:

- `POST /api/v1/collaboration/agents/create` - Criar agente especializado
- `GET /api/v1/collaboration/agents` - Listar todos os agentes
- `GET /api/v1/collaboration/agents/{agent_id}` - Detalhes de um agente
- `POST /api/v1/collaboration/tasks/create` - Criar tarefa manual
- `POST /api/v1/collaboration/tasks/execute` - Executar tarefa específica
- `GET /api/v1/collaboration/tasks` - Listar tarefas (com filtro por status)
- `GET /api/v1/collaboration/tasks/{task_id}` - Detalhes de uma tarefa
- `POST /api/v1/collaboration/projects/execute` - Executar projeto completo (coordenação multi-agente)
- `POST /api/v1/collaboration/workspace/messages/send` - Enviar mensagem entre agentes
- `GET /api/v1/collaboration/workspace/messages/{agent_id}` - Recuperar mensagens de um agente
- `POST /api/v1/collaboration/workspace/artifacts/add` - Adicionar artefato ao workspace
- `GET /api/v1/collaboration/workspace/artifacts/{key}` - Recuperar artefato
- `GET /api/v1/collaboration/workspace/status` - Status geral do workspace
- `POST /api/v1/collaboration/system/shutdown` - Desligar todos os agentes
- `GET /api/v1/collaboration/health` - Health check do sistema multi-agente

Arquitetura:

```
MultiAgentSystem
├── SharedWorkspace (estado compartilhado)
│   ├── artifacts: Dict[str, Any]
│   ├── messages: List[Dict]
│   └── tasks: Dict[str, Task]
├── SpecializedAgent (múltiplas instâncias)
│   ├── role: AgentRole
│   ├── executor: AgentExecutor (LangChain)
│   └── workspace: SharedWorkspace
└── project_manager: SpecializedAgent (coordenador)
```

Status: **VALIDADO E OPERACIONAL** ✅

### Sprint 12: Resiliência e Maturidade – Operação Contínua – Solidez do Sistema

Foco Principal: Garantir a solidez, estabilidade e eficiência do sistema Janus para operação autônoma e ininterrupta.
Implementações-chave:
Integração de observabilidade (Prometheus, Grafana) para monitoramento proativo do desempenho e identificação de
problemas.
Implementação de gestão eficiente de falhas (tentativas com recuo exponencial, "poison pill handling"), garantindo a
recuperação e resiliência do sistema diante de erros.
Otimização de custos por um Roteador de Modelos Dinâmico para LLMs, que seleciona o modelo de linguagem mais
adequado (e de menor custo) para cada tarefa.

### Sprint 13: Gênese do Meta-Agente – A Consciência Proativa

Foco Principal: Lançar a primeira versão do "Meta-Agente de Auto-Otimização", marcando a transição do Janus de um
sistema reativo para uma entidade com autoconsciência diagnóstica.

Implementações-chave (Conceituais):
Definição da Identidade do Supervisor: Criação do papel META_AGENT, focado na saúde e eficiência do ecossistema Janus,
em vez de servir o utilizador diretamente. Desenvolvimento do prompt meta_agent_supervisor, que serve como"
constituição" do agente, instruindo-o a analisar desempenho, identificar padrões de falhas e formular hipóteses sobre
suas causas.
Criação de Ferramentas de Introspecção: Equipar o Meta-Agente com ferramentas de supervisão, sendo a principal
analyze_memory_for_failures, para consultar a memória episódica (Qdrant) e filtrar falhas.
Implementação do Ciclo de Vida Proativo: Estabelecimento de um processo de fundo ("batimento cardíaco") que ativa o
Meta-Agente regularmente para monitorização contínua. Geração de um "relatório de estado" ao final de cada ciclo,
registado em logs, indicando padrões de falha ou operação normal.

Sprint 14: Do Diagnóstico à Ação – O Otimizador de Hipóteses
Foco Principal: Transformar o "Meta-Agente" de uma entidade de monitoramento em um "Agente Otimizador" ativo, capaz de
formular, testar e validar hipóteses para corrigir falhas ou melhorar a eficiência.
Implementações Chave:
Módulo de Geração de Hipóteses: O Meta-Agente gera propostas de solução concretas e testáveis a partir da análise de
falhas.
Sandbox de Simulação: Utilização da infraestrutura Docker para criar um ambiente de teste isolado onde as hipóteses (ex:
um novo prompt) podem ser validadas sem impactar a produção.
Ferramenta de Avaliação Comparativa: Uma nova ferramenta (evaluate_hypothesis_outcome) para o Otimizador comparar o
resultado do teste no sandbox com o resultado original da falha.
Registro de Conhecimento Evolutivo: As soluções validadas são registradas na Memória Semântica (Neo4j) como uma
OptimizationLog, aguardando aplicação.

Sprint 15: Ação Autônoma Supervisionada – O Módulo de Auto-Modificação
Foco Principal: Implementar o mecanismo pelo qual as "soluções validadas" são aplicadas ao sistema de produção,
introduzindo o conceito de autonomia supervisionada (human-in-the-loop).
Implementações Chave:
Módulo de Implantação (Deployment Manager): Um serviço que o Agente Otimizador pode invocar para aplicar uma mudança
validada (ex: alterar um arquivo de prompt).
Sistema de Permissões (Human-in-the-Loop): Classificação de risco para mudanças. Mudanças de baixo risco (ex: prompts)
são automáticas; mudanças de alto risco (ex: código) exigem aprovação humana.
Mecanismo de Rollback: Capacidade de reverter rapidamente uma mudança se ela causar comportamento inesperado, utilizando
versionamento dos estados anteriores.
Fechamento do Loop de Feedback: Monitoramento ativo do desempenho pós-mudança para confirmar a eficácia da otimização no
ambiente de produção.

Sprint 16: O Despertar da Curiosidade – Aquisição Proativa de Conhecimento
Foco Principal: Transformar Janus de um aprendiz passivo para um agente de conhecimento ativo que explora proativamente
a internet para identificar, validar e integrar novas informações em sua base de conhecimento.
Implementações Chave:
Agente Curador de Conhecimento: Um novo agente ativado por gatilhos internos (falhas por falta de conhecimento ou
agendamento) para preencher lacunas na Memória Semântica.
Ferramenta de Navegação Web Avançada: Integração de bibliotecas (ex: Beautiful Soup) para permitir a extração de
conteúdo completo de páginas web, indo além dos snippets de busca.
Pipeline de Validação de Fontes: O "Agente Professor" é aprimorado para realizar verificação de consistência, comparando
informações de múltiplas fontes antes de aprová-las para integração na memória.

Sprint 17: De Ferramenta a Colaborador – O Nascimento da Parceria Cognitiva
Foco Principal: Evoluir a interação de Janus de um modelo reativo (comando-resposta) para um paradigma proativo e
colaborativo, entendendo e antecipando as necessidades do usuário.

Implementações Chave:
Modelos de Usuário Persistentes: Criação de um modelo dinâmico do usuário na Memória Semântica (Neo4j), registrando
preferências, interesses e estilo de interação.
Assistência Proativa: Utilização do modelo de usuário para antecipar necessidades, oferecendo informações relevantes
antes de serem solicitadas.
Memória de Contexto de Longo Prazo (Projetos): Capacidade de agrupar interações separadas no tempo em "projetos",
permitindo carregar o contexto completo de um trabalho em andamento.
Diálogo de Clarificação: Implementação de uma verificação de confiança no Orquestrador para, em caso de ambiguidade,
gerar perguntas de esclarecimento inteligentes em vez de falhar.

Sprint 18: A Mente Coletiva – Da Delegação à Colaboração de Agentes
Foco Principal: Permitir que Janus resolva problemas complexos através da colaboração dinâmica e em tempo real entre
múltiplos agentes especializados, evoluindo para um modelo de "Líder de Equipe-Esquadrão Colaborativo".
Implementações Chave:
Evolução do Orquestrador para "Líder de Equipe": O Orquestrador passa a formar equipes de agentes dinamicamente para
tarefas multifacetadas.
Espaço de Trabalho Colaborativo (Shared Scratchpad): Um nó de estado temporário no LangGraph onde a equipe de agentes
designada pode interagir, compartilhar resultados parciais e colaborar.
Protocolo de Comunicação Inter-Agente: Definição de um formato de mensagem padrão (ex: JSON schema) para a comunicação
no scratchpad.
Agente Comunicador/Sintetizador: Um novo agente especializado em compilar o trabalho dos outros membros da equipe em uma
resposta final coesa para o usuário.

Sprint 19: O Guardião Ético – A Bússola Moral
Foco Principal: Implementar um framework de alinhamento e ética para garantir que a crescente autonomia de Janus seja
exercida de forma segura, responsável e alinhada a princípios predefinidos.
Implementações Chave:
Criação do "Agente Ético": Um novo agente de alta prioridade cujo único objetivo é avaliar os planos de ação do
Orquestrador.
Definição da "Constituição de Janus": Um arquivo de configuração legível por máquina (ex: YAML) que define as diretrizes
éticas fundamentais (ex: proteção de privacidade, veracidade, proibição de conteúdo nocivo).
Integração com Poder de Veto: O Agente Ético é integrado como um passo de validação obrigatório no LangGraph, com a
capacidade de vetar ou solicitar modificação em planos que violem a constituição.
Trilha de Auditoria Ética: Todas as decisões e vetos do Agente Ético são registrados em log para garantir transparência
e responsabilidade.

Sprint 20: O Navegador do Caos – O Módulo de Incerteza
Foco Principal: Equipar Janus com a capacidade de gerenciar, raciocinar e comunicar sobre informações que são
inerentemente incertas, ambíguas ou conflitantes.
Implementações Chave:
Memória Probabilística: Aprimoramento do KnowledgeGraphManager para que nós e relacionamentos na Memória Semântica (
Neo4j) possam ter uma propriedade opcional confidence_score (0.0 a 1.0).
Lógica de Reconciliação do "Professor": O Agente Professor é atualizado para, ao encontrar fontes conflitantes,
registrar ambas as informações com scores de confiança ajustados, em vez de descartar uma.
Comunicação Nuançada: Os prompts dos agentes que apresentam informações são refinados para instruí-los a usar a
pontuação de confiança para modular sua linguagem (ex: "É altamente provável que...", "As fontes divergem sobre este
ponto...").

Sprint 21: Os Sentidos Expandidos – A Corporeidade Digital Multimodal
Foco Principal: Quebrar a barreira do texto, dando a Janus a capacidade de perceber e interpretar informações visuais,
como imagens, gráficos e diagramas.
Implementações Chave:
Criação do "Agente Visual": Um novo agente especializado para processamento de informações visuais.
Integração de Modelo Multimodal: Adicionar um modelo como o LLaVA (disponível via Ollama) ao LLMManager como um recurso
especializado.
Nova Ferramenta (analyze_image): Criação de uma ferramenta que pode receber um caminho de arquivo ou URL de imagem e
retornar uma descrição textual ou responder a uma pergunta sobre ela.
Atualização do Orquestrador: Aprimorar a capacidade do Orquestrador de identificar quando uma consulta do usuário se
refere a um conteúdo visual e encaminhá-la para o Agente Visual.
