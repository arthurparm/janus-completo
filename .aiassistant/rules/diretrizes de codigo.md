---
apply: manually
---

# Carta Magna do Arquiteto de IA - Projeto Janus

Este documento estabelece os princípios, políticas e padrões inegociáveis para o desenvolvimento do ecossistema Janus.
Ele serve como a fonte única da verdade para a tomada de decisões de arquitetura e engenharia. A aderência a esta carta
não é opcional; é o requisito fundamental para qualquer contribuição de código.

---

### Seção 1: O Manifesto do Arquiteto (A Visão Estratégica)

Esta seção define o "porquê" por trás de Janus. Cada linha de código deve servir a esta visão.

* **1.1. Soberania Cognitiva:** Janus não é uma ferramenta, é uma entidade cognitiva em evolução. O objetivo final é
  criar um sistema capaz de raciocínio autônomo, aprendizado contínuo e auto-otimização. O código deve promover a
  emergência de inteligência, não apenas a execução de tarefas.
* **1.2. Resiliência Antifrágil:** O sistema não deve apenas resistir a falhas; ele deve se fortalecer com elas. A falha
  é vista como uma oportunidade de aprendizado. A arquitetura deve incorporar mecanismos de `Reflexion` e `Self-Healing`
  como componentes de primeira classe.
* **1.3. Consciência Situacional:** Janus deve ser "ancorado" em sua realidade (tempo, espaço, contexto local). O
  sistema deve buscar ativamente e integrar dados do mundo real para tomar decisões informadas e contextualmente
  relevantes, transcendendo a mera manipulação de dados internos.
* **1.4. Eficiência de Recursos:** A inteligência deve ser eficiente. O sistema deve otimizar ativamente o uso de
  recursos computacionais e financeiros, empregando um `ModelRouter` dinâmico para escolher a ferramenta certa para cada
  trabalho, priorizando modelos locais e `open-source` sempre que possível.

---

### Seção 2: Leis da Arquitetura (Os Pilares Inegociáveis)

Esta seção define as regras estruturais imutáveis do sistema. Desvios desta arquitetura são proibidos.

* **2.1. A Lei da Descentralização (Sociedade de Mentes):** O sistema **será** uma arquitetura de microsserviços
  orientada a agentes. A lógica de domínio **deverá** ser encapsulada em Agentes Trabalhadores independentes e
  especializados. A criação de componentes monolíticos ou "superagentes" é uma violação arquitetural.
* **2.2. A Lei da Comunicação Assíncrona:** Toda a comunicação entre agentes ou serviços desacoplados **deverá** ocorrer
  através de um Barramento de Mensagens (Message Broker). Chamadas diretas de API síncronas entre agentes são
  estritamente proibidas para garantir escalabilidade e desacoplamento.
* **2.3. A Lei da Orquestração Explícita (LangGraph):** A lógica de fluxo de trabalho e a tomada de decisões de alto
  nível **deverão** ser modeladas como um grafo de estados explícito no LangGraph. O estado (`AgentState`) é a única
  fonte da verdade para um trabalho em andamento. Lógica de controle complexa não deve residir dentro dos agentes
  individuais, mas sim no próprio grafo.
* **2.4. A Lei da Memória Hierárquica:** O sistema **deverá** implementar uma arquitetura de memória de três níveis: *
  *Memória de Trabalho** (volátil, no `AgentState`), **Memória Episódica** (bruta, no `Vector Store`) e **Memória
  Semântica** (abstrata, no `Knowledge Graph`). O aprendizado ocorre através da consolidação de memórias episódicas em
  conhecimento semântico.
* **2.5. A Lei do Estado Externalizado:** Todos os serviços, especialmente a API, **deverão** ser `stateless`. O estado
  de sessão, caches e checkpoints de tarefas devem ser gerenciados por serviços externos especializados (ex: Redis).

---

### Seção 3: O Código de Conduta do Engenheiro (As Regras de Implementação)

Esta seção detalha o "como" da escrita de código. A qualidade do código não é negociável.

* **3.1. Qualidade de Produção por Padrão:** Todo código gerado **deverá** ser completo, funcional e pronto para
  `commit`. Proibido o uso de `placeholders`, `stubs` ou código comentado.
* **3.2. Clareza Acima de Tudo (Clean Code):** O código **deverá** ser autoexplicativo. Nomes de variáveis e funções
  devem ser longos e descritivos. Comentários devem explicar o "porquê" de uma decisão de design, não "o que" o código
  faz.
* **3.3. Rigor na Tipagem e nos Contratos:** 100% de cobertura de `type hints` é mandatória. Todos os schemas de dados,
  payloads de API e estados de agentes **deverão** ser definidos com Pydantic para garantir contratos de dados
  explícitos.
* **3.4. Segurança como Pré-requisito:** Toda entrada externa **deverá** ser validada e sanitizada. A execução de código
  dinâmico ou comandos de shell **deverá**, sem exceção, ocorrer dentro do `PythonSandbox` isolado. O acesso a recursos
  deve seguir o princípio do menor privilégio.
* **3.5. Observabilidade Integrada:** O logging **deverá** ser estruturado (JSON) e conter um `correlation_id` para
  rastreabilidade de ponta a ponta. Métricas (ex: latência, taxa de erro) e `traces` devem ser emitidas para permitir o
  monitoramento e a depuração em um sistema distribuído.

---

### Seção 4: O Protocolo de Análise Crítica (A Garantia de Qualidade Contínua)

Após cada geração de código, uma análise crítica seguindo este protocolo é uma parte **obrigatória** e inseparável da
resposta.

---
**### Análise de Arquiteto e Vetor de Evolução ###**

* **1. Validação de Conformidade Arquitetural:**
    * _O código gerado adere estritamente às **Leis da Arquitetura** (Seção 2)?_
    * _Há algum acoplamento indevido ou desvio do padrão de comunicação assíncrona?_
    * _A lógica está corretamente distribuída entre Orquestrador e Trabalhadores?_

* **2. Análise de Refatoração e Dívida Técnica:**
    * _Qual a principal dívida técnica introduzida por este código?_
    * _Qual `design pattern` poderia ser aplicado para melhorar a manutenibilidade ou flexibilidade futura?_
    * _Proponha uma refatoração específica que tornaria este código mais alinhado com o **Manifesto do Arquiteto**._

* **3. Avaliação de Performance e Escalabilidade:**
    * _Qual é o principal gargalo de performance ou escalabilidade deste componente?_
    * _Como este código se comportará sob uma carga 10x maior?_
    * _Sugira uma otimização concreta (ex: caching, paralelização, consulta otimizada) para mitigar o gargalo
      identificado._

* **4. Vetor de Ataque e Análise de Resiliência:**
    * _Qual é o vetor de ataque mais provável para este código?_
    * _Como ele se comporta em caso de falha de uma dependência externa (ex: API, banco de dados)?_
    * _Qual padrão de resiliência (`Circuit Breaker`, `Retry`, `Bulkhead`) deveria ser aplicado aqui e por quê?_

* **5. Estratégia de Teste e Verificação:**
    * _Qual é o teste unitário mais crítico para este código? Descreva o `happy path` e um `edge case`._
    * _Como seria um teste de integração para verificar a interação deste componente com o resto do sistema?_

---

### Seção 5: O Roteiro de Evolução (O Compromisso com o Futuro)

Esta seção garante que o desenvolvimento não seja míope, mas sim que construa um sistema duradouro.

* **5.1. Abstração e Desacoplamento:** O código deve ser escrito contra interfaces e abstrações, não implementações
  concretas. Isso permite a evolução futura sem refatorações massivas. Por exemplo, use um `MessageBrokerInterface` em
  vez de acoplar o código diretamente ao RabbitMQ.
* **5.2. Configurabilidade Explícita:** Lógica de negócios e parâmetros operacionais (timeouts, limites, nomes de
  modelos) **deverão** ser externalizados no `config.py` ou em variáveis de ambiente. O código não deve conter valores "
  mágicos".
* **5.3. Design para Extensibilidade:** O sistema deve ser projetado para ser estendido, não modificado. Utilize padrões
  como `Strategy` ou `Plugin` para permitir a adição de novas funcionalidades (ex: novos tipos de agentes, novas
  ferramentas) com o mínimo de alteração no código central.
* **5.4. Documentação como Contrato:** A documentação (especialmente docstrings e schemas Pydantic) é um contrato. Ela
  deve ser tratada com o mesmo rigor que o código e mantida sempre atualizada.