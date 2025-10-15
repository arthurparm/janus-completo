Relatório de Projeto Arquitetural: Evoluindo o Assistente Pessoal Janus para um Sistema Cognitivo Distribuído e
Escalável

Data: 14 de agosto de 2025
Localização: Itanhaém, SP, Brasil
Documento ID: JANUS-ARC-1.0-20250814
Status: Proposta Arquitetural Final

Sumário Executivo

Este documento apresenta uma proposta arquitetural abrangente para o reprojeto do assistente pessoal Janus. A
arquitetura atual, baseada em dois computadores pessoais, impõe limitações intrínsecas de escalabilidade, resiliência e
capacidade computacional. A evolução proposta visa transformar Janus de um sistema de nó duplo para uma arquitetura
cognitiva distribuída, fundamentalmente escalável e capaz de incorporar um número arbitrário de nós computacionais.
A nova arquitetura é fundamentada no paradigma de multiagentes, utilizando o padrão Orquestrador-Trabalhador para
decompor tarefas complexas e distribuir a carga de trabalho entre nós especializados. O framework LangGraph servirá como
a espinha dorsal da orquestração, permitindo a criação de fluxos de trabalho agenticos cíclicos, stateful e
controláveis. A comunicação entre os nós será desacoplada e assíncrona, mediada por um barramento de mensagens para
máxima resiliência e escalabilidade.
As capacidades cognitivas de Janus serão significativamente aprimoradas através de uma arquitetura de memória
hierárquica inspirada na cognição humana, compreendendo memórias de trabalho, episódica e semântica. O aprendizado
contínuo e a auto-otimização serão alcançados pela implementação do framework Reflexion, que habilita os agentes a
aprenderem com falhas através de um processo de autorreflexão verbal.
A autonomia de Janus será expandida para incluir a geração dinâmica de ferramentas e a automação de interfaces gráficas
de usuário (GUI), permitindo a interação com sistemas que não possuem APIs. A segurança é um pilar central deste
projeto, com um framework de defesa multicamadas que inclui a execução de código em ambientes sandbox rigorosamente
isolados, criptografia de ponta a ponta e controle de acesso granular.
Finalmente, o sistema integrará uma consciência contextual baseada na data e localização atuais (14 de agosto de 2025,
Itanhaém, SP), permitindo que Janus forneça interações mais relevantes e proativas. Este relatório detalha a pilha
tecnológica, os padrões de implementação e um roteiro de implantação em fases para guiar a transformação de Janus em um
assistente de IA de próxima geração, preparado para o futuro.

### Índice

* **Parte I: Arquitetura Fundamental**
* **Parte II: O Núcleo Cognitivo**
* **Parte III: Interação Ambiental e Ancoragem Contextual**
* **Parte IV: Escalabilidade, Segurança e Blueprint de Implantação**
* **Parte V: Conclusão e Roteiro de Implementação**
    * [Visão Arquitetural Sintetizada](#visão-arquitetural-sintetizada-janus-10)
    * [Roteiro de Implementação em Fases (Mapeado para Sprints)](#roteiro-de-implementação-em-fases-mapeado-para-sprints)
* **Apêndice A: Catálogo de APIs e Serviços de IA**
* **Apêndice B: Referências**

Parte I: Arquitetura Fundamental - De um Sistema de Dois Nós para um Coletivo Multiagente

Esta seção estabelece a mudança arquitetural fundamental necessária para atender aos objetivos de escalabilidade. A
transição vai além da simples adição de mais computadores, propondo uma reestruturação para um sistema distribuído
robusto, projetado para crescimento e especialização funcional.

A Mudança de Paradigma para a Cognição Distribuída: Do Monolito ao Coletivo

A arquitetura atual de Janus, limitada a dois PCs, representa um modelo que, embora funcional para prototipagem, é
inerentemente restrito em sua capacidade de evoluir. A tentativa de escalar tal sistema simplesmente aumentando o poder
de seus componentes individuais (escalabilidade vertical) inevitavelmente encontrará um teto de desempenho e custo. A
solução proposta é uma mudança de paradigma fundamental: a transição de uma arquitetura monolítica ou fortemente
acoplada para uma arquitetura de cognição distribuída e multiagente.1
Este novo modelo não visa criar um "cérebro maior", mas sim uma "sociedade de mentes", onde a inteligência e o
comportamento complexo emergem da colaboração de múltiplos agentes de software mais simples e especializados. Cada
agente, ou grupo de agentes, pode residir em um nó computacional distinto, permitindo que o sistema cresça
horizontalmente. A adição de novas capacidades ou o aumento da carga de trabalho não exigirá a substituição de uma
máquina central, mas sim a adição de novos nós especializados à rede, tornando o sistema fundamentalmente mais
resiliente, extensível e economicamente viável a longo prazo.3
A pesquisa atual no campo de agentes de IA demonstra uma clara convergência para este modelo de redes colaborativas em
detrimento de "superagentes" monolíticos. Diferentes tarefas de IA possuem perfis computacionais drasticamente
distintos: a Recuperação Aumentada por Geração (RAG) é intensiva em I/O e CPU, o raciocínio complexo é intensivo em GPU,
e a execução de ferramentas externas é sensível à segurança. Operar essas cargas de trabalho díspares em um cluster
homogêneo é ineficiente. Uma arquitetura escalável e eficiente deve, portanto, separar física e logicamente essas
funções em nós especializados. Esta não é apenas uma escolha de design, mas uma evolução necessária para gerenciar a
complexidade e o custo de forma eficaz. A reengenharia de Janus deve, portanto, adotar uma arquitetura semelhante a
microserviços, onde cada agente ou nó possui uma única responsabilidade bem definida, garantindo a modularidade que é a
chave para a escalabilidade e manutenibilidade futuras.

O Padrão Orquestrador-Trabalhador: Um Blueprint para as Operações de Janus

Para estruturar a colaboração entre os múltiplos agentes de Janus, a arquitetura proposta adota formalmente o padrão de
design Orquestrador-Trabalhador (Orchestrator-Worker). Este padrão estabelece uma clara separação de responsabilidades
que é ideal para sistemas distribuídos complexos.
Um nó central, denominado Janus-Core, atuará como o orquestrador. Este componente funcionará como o "cérebro"
estratégico do sistema, responsável por receber as solicitações do usuário, realizar a decomposição de tarefas de alto
nível, planejar a sequência de execução e, finalmente, sintetizar os resultados parciais dos trabalhadores em uma
resposta final coesa.1 É crucial notar que o orquestrador não executa as tarefas operacionais em si; em vez disso, ele
delega essas subtarefas a um pool dinâmico de agentes "Trabalhadores" especializados.
A implementação deste padrão será realizada utilizando o framework LangGraph. A natureza de LangGraph, que permite a
construção de grafos de estado cíclicos e controláveis, é perfeitamente adequada para a lógica de um orquestrador que
precisa gerenciar fluxos de trabalho complexos e multi-etapas, coordenando múltiplos trabalhadores e lidando com estados
intermediários. O orquestrador, em essência, se torna um grafo LangGraph que roteia tarefas para diferentes nós
trabalhadores com base no plano de execução.
Para garantir o máximo desacoplamento e resiliência, a comunicação entre o orquestrador e os trabalhadores adotará um
modelo orientado a eventos. Em vez de chamadas de API diretas e síncronas, o orquestrador publicará tarefas em tópicos
específicos de um barramento de mensagens, como Apache Kafka ou RabbitMQ. Os agentes trabalhadores, por sua vez, se
inscreverão nos tópicos relevantes às suas especialidades. Esta abordagem assíncrona impede que o orquestrador se torne
um gargalo, permite que novos trabalhadores sejam adicionados ou removidos da rede sem a necessidade de reconfigurar o
sistema central e garante que, se um trabalhador falhar, a tarefa possa ser reatribuída sem interromper todo o fluxo de
trabalho.3

Especialização de Nós e Alocação de Recursos

A eficiência da arquitetura distribuída depende da especialização funcional de seus nós. Cada nó será configurado com o
hardware e o software otimizados para sua função específica, garantindo que os recursos computacionais sejam alocados de
forma inteligente. A seguir, define-se um conjunto inicial de papéis para os agentes trabalhadores:
Nó Orquestrador Cognitivo (Janus-Core): Este é o nó central que gerencia o ciclo de interação primário com o usuário.
Suas responsabilidades incluem a decomposição de objetivos, o planejamento estratégico e a manutenção do estado global
da tarefa. Requer um Modelo de Linguagem Grande (LLM) de propósito geral e de alta capacidade de raciocínio (por
exemplo, modelos da série GPT-5 da OpenAI ou Claude 4 Opus da Anthropic) e recursos moderados de CPU e RAM para
gerenciar o grafo de estado.
Nó de RAG e Memória: Este nó é o guardião do conhecimento de Janus. Ele gerencia o banco de dados vetorial e o grafo de
conhecimento. Suas funções principais são a ingestão de dados, a fragmentação de documentos (chunking), a geração de
embeddings e a recuperação de informações. Este nó é intensivo em I/O e CPU durante a ingestão e se beneficia de um
banco de dados vetorial rápido e leve, como o Qdrant, que suporta persistência em disco.5
Nó de Raciocínio Complexo e Autorreflexão: Dedicado a tarefas que exigem pensamento profundo e iterativo, como o
planejamento detalhado de subtarefas e a auto-correção através do framework Reflexion. Este nó se beneficiaria de um LLM
focado em raciocínio (por exemplo, o modelo o3 da OpenAI ou o DeepSeek-R1) e, potencialmente, de uma GPU dedicada com
alta VRAM para acelerar os ciclos de inferência complexos.8
Nó de Execução e Criação de Ferramentas: Um nó altamente seguro, responsável por executar ferramentas externas (chamadas
de API, scripts locais) e, criticamente, por executar código gerado dinamicamente em um ambiente sandbox. Este nó requer
a instalação do Docker e um endurecimento de segurança específico para isolar a execução de código não confiável.
Nó de Consciência Contextual: Um nó especializado em interagir com APIs externas para obter dados baseados em
localização e tempo. Ele fornecerá ao orquestrador o contexto em tempo real sobre Itanhaém, SP, na data de 14 de agosto
de 2025, como condições meteorológicas, notícias locais e eventos.
Nó de Gateway de Interface do Usuário: Um nó leve executando uma aplicação FastAPI.10 Ele expõe uma API RESTful segura
para a interação do usuário, traduzindo as entradas do usuário em tarefas para o orquestrador e formatando as saídas
finais para apresentação.
A tabela a seguir resume a pilha tecnológica recomendada para a arquitetura fundamental de Janus. A seleção de cada
tecnologia foi baseada em critérios de desempenho, escalabilidade, maturidade e adequação ao padrão arquitetural
proposto.

Componente
Escolha Recomendada
Alternativas
Justificativa Chave
Orquestração de Agentes
LangGraph
CrewAI, AutoGen
Gerenciamento de estado, fluxos de trabalho cíclicos, depuração com LangSmith.
Comunicação Inter-Nós
Fila de Mensagens (Kafka/RabbitMQ)
APIs REST Diretas (FastAPI)
Assíncrono, desacoplado, escalável, resiliente a falhas de nó.3
Gateway de API
FastAPI
Flask
Alto desempenho, suporte assíncrono, documentação automática.10
Banco de Dados Vetorial
Qdrant
ChromaDB, FAISS, Milvus
Desempenho, persistência em disco, filtragem avançada, escalabilidade.14
Sandbox de Código
Docker + epicbox
Kernel Jupyter em Docker
Isolamento forte, limites de recursos, comprovado para código não confiável.

Parte II: O Núcleo Cognitivo - Engenharia de Aprendizado e Autonomia

Esta seção detalha os padrões de software e as arquiteturas cognitivas que conferirão inteligência a Janus, movendo o
sistema de uma simples execução de tarefas para um aprendizado e adaptação genuínos.

O Núcleo Agentico: Implementando um Loop ReAct com LangGraph

O comportamento de cada agente trabalhador, bem como do próprio orquestrador, será construído em torno de um ciclo
fundamental conhecido como ReAct (Reason + Act).16 Este padrão é um pilar da arquitetura de agentes modernos, permitindo
que o sistema interaja de forma inteligente com seu ambiente através de um ciclo iterativo:
Pensamento (Reason): O LLM analisa o objetivo atual, o estado da tarefa e o histórico de ações anteriores para
raciocinar sobre o próximo passo lógico.
Ação (Act): Com base em seu raciocínio, o LLM decide qual ferramenta externa chamar e com quais argumentos. A "ação" é a
formulação desta chamada de ferramenta em um formato estruturado.
Observação (Observation): A ferramenta selecionada é executada no ambiente (por exemplo, uma busca na web é realizada,
um cálculo é feito). O resultado ou saída dessa execução é então retornado ao agente como uma "observação".
Este ciclo se repete, com a nova observação alimentando o próximo passo de "Pensamento", permitindo que o agente refine
sua abordagem, corrija erros e se aproxime progressivamente da solução do objetivo.
A implementação deste loop será feita utilizando LangGraph para construir uma máquina de estados robusta e depurável. O
AgentState do grafo, uma estrutura de dados definida, conterá a lista de mensagens que compõem a trajetória do agente (
pensamentos, chamadas de ação, observações).19 Uma aresta condicional no grafo avaliará a saída do LLM a cada passo: se
o LLM emitir uma nova chamada de ferramenta, o fluxo será direcionado para o nó de execução de ferramentas; se o LLM
determinar que a tarefa foi concluída, o fluxo será direcionado para o nó final, encerrando o ciclo. Esta abordagem
estruturada é superior a um simples loop
while(true), pois oferece maior controle, persistência de estado e visibilidade para depuração através de ferramentas
como o LangSmith.

Uma Arquitetura de Memória Hierárquica para Aprendizagem Contínua

Para que Janus transcenda as limitações de um assistente reativo e desenvolva uma capacidade de aprendizado contínuo (
lifelong learning), é essencial projetar um sistema de memória sofisticado. Inspirado em modelos da ciência cognitiva, a
arquitetura de memória de Janus será organizada hierarquicamente em três camadas distintas, cada uma com uma função e
tecnologia específicas. Esta estrutura é projetada para gerenciar a complexidade da informação e evitar a "esquecimento
catastrófico" que aflige sistemas baseados apenas em janelas de contexto finitas.
Camada 1: Memória de Trabalho (Curto Prazo): Esta é a camada mais imediata e volátil da memória. Corresponde diretamente
ao AgentState dentro de uma execução de grafo no LangGraph. Ela armazena o contexto, as variáveis e o histórico de
mensagens exclusivamente para a tarefa atual. É a "consciência" do agente no momento da execução, sendo descartada após
a conclusão da tarefa.
Camada 2: Memória Episódica (Buffer de Experiência de Longo Prazo):
Função: Esta camada serve como um registro persistente de todas as experiências passadas de Janus. Cada trajetória
completa de um agente (a sequência de pensamentos, ações e observações), seja ela bem-sucedida ou não, é arquivada aqui
como um "episódio" bruto.
Tecnologia: Um banco de dados vetorial Qdrant é a escolha ideal para esta camada. Qdrant oferece recuperação semântica
de alta performance e, crucialmente, suporta persistência em disco (on_disk=True). Esta funcionalidade é vital para
gerenciar grandes volumes de memória episódica ao longo do tempo, especialmente em nós com recursos de RAM limitados,
sem comprometer o desempenho.5 Cada episódio será convertido em um
embedding vetorial e armazenado juntamente com seus metadados para recuperação futura.
Camada 3: Memória Semântica (Conhecimento e Habilidades Consolidadas):
Função: Esta é a camada onde a informação bruta da memória episódica é transformada em conhecimento estruturado e
generalizável. Representa o que Janus aprendeu de fato. Este conhecimento inclui fatos validados, planos de ação
bem-sucedidos (fluxos de trabalho), e habilidades recém-adquiridas (como uma nova função Python que o próprio agente
escreveu e validou).
Pipeline de Consolidação: Um processo em segundo plano executará periodicamente uma tarefa de sumarização do tipo
Map-Reduce sobre a Memória Episódica.21 Este processo identificará padrões recorrentes, extrairá insights chave e gerará
resumos de estratégias bem-sucedidas. Esses insights consolidados serão então armazenados em um formato mais
estruturado, como um grafo de conhecimento ou um banco de dados relacional, formando a Memória Semântica. Este mecanismo
impede que o agente tenha que rederivar soluções a partir de experiências brutas a cada vez, acelerando o raciocínio e a
tomada de decisão.

Auto-otimização Através do Framework Reflexion

Para que a aprendizagem seja verdadeiramente autônoma, Janus deve ser capaz de melhorar a partir de seus próprios erros.
Para isso, será implementado o padrão Reflexion, uma forma de "reforço de aprendizado verbal" onde o agente critica seu
próprio desempenho para informar ações futuras.
O fluxo de trabalho da auto-otimização será o seguinte:
Execução: Um agente tenta executar uma tarefa, gerando uma trajetória que é armazenada na Memória de Trabalho.
Avaliação: Um componente Avaliador (que pode ser outra chamada de LLM com um prompt de avaliação ou uma verificação
determinística, como um teste de unidade para código gerado) analisa o resultado da trajetória e determina se foi
bem-sucedida.
Autorreflexão: Se o resultado for subótimo, um agente de Autorreflexão é invocado. Este agente recebe a trajetória falha
e é instruído a analisar o processo, gerar uma crítica textual explicando por que a falha ocorreu e sugerir uma
estratégia alternativa ou uma correção para o futuro.
Armazenamento na Memória: Esta "reflexão" gerada é armazenada na Memória Episódica, vinculada à trajetória falha.
Recuperação Futura: Quando o orquestrador encontrar uma tarefa semelhante no futuro, o nó de RAG não recuperará apenas
tentativas bem-sucedidas, mas também essas reflexões explícitas sobre falhas. Isso fornecerá ao agente um contexto
crucial para evitar a repetição dos mesmos erros, funcionando como um mecanismo de aprendizado por experiência.25
A capacidade de Janus de aprender não reside apenas em sua habilidade de lembrar, mas em sua capacidade de abstrair. O
simples armazenamento de todas as interações passadas em um banco de dados vetorial cria um espaço de busca ruidoso e
ineficiente. A verdadeira aquisição de habilidades emerge de um pipeline cognitivo que transforma experiências brutas em
conhecimento generalizável. O padrão Reflexion 26 gera críticas explícitas e de alto nível ("A chamada de API falhou
porque o parâmetro
user_id estava incorreto"). O processo de sumarização Map-Reduce 21, quando aplicado a essas reflexões, pode
consolidá-las de instâncias específicas para princípios gerais ("Sempre verifique os nomes dos parâmetros da API na
documentação antes de fazer uma chamada"). Este princípio generalizado é o que constitui uma "habilidade" ou "
conhecimento". Armazenar essa heurística em uma Memória Semântica separada e estruturada permite uma recuperação mais
rápida e confiável de lições aprendidas, em vez de esperar que o agente redescubra a solução a partir de dados brutos.
Esta arquitetura transforma Janus de um agente que meramente repete sucessos passados para um que aprende habilidades
generalizáveis a partir de todo o seu histórico de sucessos e fracassos.

Parte III: Interação Ambiental e Ancoragem Contextual

Esta seção detalha como Janus irá perceber e atuar em seu ambiente, que abrange o mundo digital de APIs, a área de
trabalho do usuário e seu contexto físico em Itanhaém.

Geração Dinâmica de Ferramentas e Execução Segura

Uma capacidade fundamental para a autonomia de um agente é a habilidade de criar novas ferramentas em tempo real quando
as existentes se mostram insuficientes para uma determinada tarefa. O fluxo de trabalho para esta capacidade avançada
será:
Identificação da Necessidade: Durante a fase de planejamento, o agente Orquestrador determina que nenhuma ferramenta em
seu arsenal atual pode cumprir uma subtarefa necessária.
Geração de Código: O Orquestrador invoca um agente "Codificador" especializado, fornecendo-lhe um prompt detalhado para
escrever uma função Python que realize a tarefa desejada. Este prompt incluirá especificações rigorosas sobre entradas,
saídas, dependências e tratamento de erros.
Execução e Validação em Sandbox: O código Python gerado nunca é executado diretamente no sistema hospedeiro. Ele é
passado para o Nó de Execução de Ferramentas, que utiliza a biblioteca epicbox para executar o código dentro de um
contêiner Docker seguro, isolado e com recursos limitados (CPU, memória, sem acesso à rede). O Orquestrador fornecerá
casos de teste para validar a correção e a segurança do código. A falha em qualquer teste resultará no descarte do
código e em uma nova tentativa de geração com feedback de erro.
Registro da Ferramenta: Se o código passar em todos os testes de validação, ele será registrado dinamicamente como uma
nova ferramenta disponível para o sistema. Isso pode ser feito usando o decorador @tool do LangChain ou a função
StructuredTool.from_function. A descrição e o esquema da nova ferramenta são adicionados à lista de ferramentas
disponíveis para futuras tarefas, e esta nova "habilidade" é registrada na Memória Semântica de Janus.

O Módulo de Contexto de Itanhaém: Ancorando Janus na Realidade

Para cumprir o requisito de consciência contextual, Janus será equipado com um módulo dedicado que o ancora em sua
localização e tempo específicos. Este módulo consiste em um conjunto de ferramentas pré-definidas que são acionadas
automaticamente no início de cada interação para fornecer um contexto base para o agente Orquestrador.
Função: O módulo coletará informações em tempo real relevantes para Itanhaém, SP, em 14 de agosto de 2025, e as injetará
no prompt inicial do Orquestrador.
Pontos de Dados Contextuais:
Data e Hora: Obtenção do timestamp atual via datetime.now().
Localização: Configuração estática: "Itanhaém, São Paulo, Brasil".
Integração com Busca na Web: O módulo utilizará uma ferramenta de busca otimizada para LLMs, como a Tavily Search API.
Esta API é ideal para desenvolvimento, pois oferece um nível gratuito generoso de 1.000 solicitações por mês e é
projetada para fornecer resultados concisos e relevantes para RAG. O módulo formulará automaticamente consultas como:
"Previsão do tempo para Itanhaém, SP hoje"
"Notícias locais de Itanhaém, 14 de agosto de 2025"
"Tábua de marés Itanhaém hoje"
"Eventos públicos em Itanhaém esta semana"
Impacto no Sistema: Esta informação contextual será fornecida ao Orquestrador no início de cada ciclo de planejamento.
Isso permitirá que Janus ofereça respostas e sugestões proativas e altamente relevantes (por exemplo, "A previsão do
tempo para hoje em Itanhaém indica chuva à tarde, talvez seja melhor adiar a caminhada na praia") sem que o usuário
precise fornecer explicitamente esses detalhes.

Automação de GUI: Interagindo com o Inautomatizável

Muitas aplicações, especialmente softwares legados de desktop, não oferecem APIs para automação. Para alcançar uma
verdadeira autonomia, Janus deve ser capaz de interagir com esses sistemas como um humano faria: olhando para a tela e
usando o mouse e o teclado.
Solução Proposta: Será desenvolvida uma ferramenta de agente multimodal que combina visão computacional com bibliotecas
de automação de GUI.
Percepção (Visão): O agente captura uma imagem da tela atual usando a função pyautogui.screenshot().
Raciocínio (LLM Multimodal): A captura de tela, juntamente com um objetivo de alto nível (por exemplo, "Clique no
botão 'Enviar' que está próximo ao campo de texto 'Assunto'"), é enviada para um LLM com capacidade de visão, como
GPT-4o ou Gemini. A tarefa do LLM é analisar a imagem e retornar as coordenadas exatas do elemento de interface alvo.
Ação (Controle de GUI): Com as coordenadas retornadas pelo LLM, a ferramenta utiliza as funções pyautogui.moveTo() e
pyautogui.click() para mover o cursor e interagir com o elemento de interface identificado.
Considerações de Segurança: Esta ferramenta é extremamente poderosa e apresenta um risco de segurança significativo. Sua
execução será restrita a um nó de trabalho específico e altamente isolado. Além disso, a ferramenta exigirá permissão
explícita do usuário para cada sessão de uso. Para interações que envolvam dados sensíveis (como senhas ou informações
de pagamento), será implementado um "modo de tomada de controle" (takeover mode), onde o agente pausa sua execução e
solicita que o usuário humano insira as informações diretamente, garantindo que o agente nunca "veja" ou processe esses
dados.

Parte IV: Escalabilidade, Segurança e Blueprint de Implantação

Esta seção aborda os aspectos práticos da implantação, manutenção e proteção do sistema Janus distribuído, fornecendo um
caminho claro do desenvolvimento à produção.

Estratégia de Modelos: APIs Proprietárias vs. Open Source Auto-hospedado

A escolha dos LLMs que alimentarão os agentes de Janus é uma decisão arquitetural crítica com implicações diretas em
custo, desempenho, privacidade e flexibilidade. Uma análise cuidadosa revela que uma estratégia híbrida é a mais
vantajosa.
APIs Proprietárias (OpenAI, Anthropic, Google, Cohere): Esses serviços oferecem acesso aos modelos mais avançados do
mercado com zero sobrecarga de configuração e manutenção.28 São ideais para prototipagem rápida e para as tarefas que
exigem o mais alto nível de raciocínio, como as executadas pelos agentes Orquestrador e de Autorreflexão. No entanto,
eles incorrem em custos por token, podem ter limites de taxa (
rate limits) e levantam questões de privacidade de dados, já que os dados são enviados para servidores de terceiros.
Modelos Open Source Auto-hospedados (Llama 3, Falcon, Mistral): Esta abordagem oferece controle total sobre os dados,
eliminando preocupações com privacidade, e não possui custos por chamada de API. Permite personalização e ajuste fino
ilimitados. Contudo, exige um investimento inicial significativo em hardware (especialmente GPUs com alta VRAM) e uma
sobrecarga contínua de manutenção e gerenciamento da infraestrutura.37 Frameworks como
Ollama e vLLM simplificam consideravelmente a implantação desses modelos, fornecendo endpoints de API compatíveis com o
padrão da OpenAI, o que facilita a alternância entre modelos locais e remotos.45
A tensão econômica entre a simplicidade das APIs e a liberdade do open-source é um fator central. A fase inicial de
desenvolvimento pode ser acelerada e barateada utilizando os generosos níveis gratuitos oferecidos por provedores de
API (ver **Apêndice A**), evitando gastos iniciais com hardware. No entanto, à medida que o uso de Janus aumenta, o
custo por token das APIs proprietárias se tornará uma despesa operacional significativa. A estratégia ótima a longo
prazo não é uma escolha binária, mas um modelo híbrido e dinâmico. A arquitetura de Janus deve ser agnóstica em relação
ao modelo, utilizando interfaces padronizadas. Propõe-se a implementação de um componente "Roteador de Modelos". Este
roteador, com base na complexidade da tarefa, sensibilidade ao custo e requisitos de privacidade, poderá decidir
dinamicamente se envia uma solicitação para uma API proprietária remota ou para um modelo open-source auto-hospedado
localmente. Esta abordagem oferece a máxima flexibilidade para equilibrar custo, desempenho e segurança à medida que o
sistema e o mercado de IA evoluem.

Roteiro de Hardware e Implantação em Nuvem

A decisão entre uma infraestrutura local (on-premises) e em nuvem (cloud) envolve um balanço entre controle e
flexibilidade. A infraestrutura local oferece controle máximo sobre segurança e hardware, mas acarreta um alto dispêndio
de capital inicial e custos de manutenção. A nuvem (AWS, Azure, GCP) oferece um modelo de pagamento conforme o uso (
pay-as-you-go), escalabilidade elástica e serviços gerenciados, tornando-a a escolha ideal para um sistema como Janus,
cuja carga de trabalho pode variar significativamente.54
Para a auto-hospedagem de modelos open-source, a VRAM da GPU é o principal gargalo. A análise de hardware deve ser
precisa:
Um modelo como Llama-2 7B requer entre 15 GB e 28 GB de VRAM para inferência em precisão total (FP16), mas esse
requisito pode ser drasticamente reduzido com técnicas de quantização (INT4/INT8).63
Uma GPU como a NVIDIA RTX 4060 Ti com 16 GB de VRAM representa uma opção de excelente custo-benefício. Ela é capaz de
executar modelos poderosos como Llama 3.1 8B e até mesmo Mixtral 8x7B com quantização adequada e algum descarregamento
para a CPU (CPU offloading), tornando-a uma escolha viável para os nós trabalhadores especializados.68
A estratégia de implantação recomendada é containerizar cada nó de agente usando Docker. Isso garante portabilidade,
consistência de ambiente e isolamento. Esses contêineres devem ser gerenciados por uma plataforma de orquestração como
Kubernetes, implantada em um provedor de nuvem. Isso permitirá o escalonamento automático dos nós trabalhadores com base
na demanda, garantirá a alta disponibilidade e simplificará o gerenciamento do ciclo de vida da aplicação.62

Um Framework de Segurança Multicamadas

Dada a autonomia de Janus, sua capacidade de interagir com sistemas externos e de gerar e executar código, a segurança
deve ser a prioridade máxima. Uma abordagem de confiança zero (zero-trust) é mandatória.
Camada 1: Segurança na Execução de Código: Todo código gerado dinamicamente deve ser executado em um ambiente sandbox
isolado. O uso da biblioteca epicbox com Docker fornece isolamento de processo, rede e sistema de arquivos, além de
impor limites estritos de recursos (CPU, memória). Isso previne ataques de negação de serviço, acesso malicioso a
arquivos e tentativas de fuga do contêiner (container escape). Os contêineres devem sempre ser executados com usuários
não-root, e as capacidades desnecessárias do kernel do Linux devem ser descartadas (dropped).
Camada 2: Segurança de Rede: Toda a comunicação entre os nós de Janus deve ser criptografada usando TLS. Os nós
trabalhadores devem ser implantados em sub-redes privadas, com regras de firewall rigorosas que permitam apenas o
tráfego proveniente do orquestrador e de APIs externas explicitamente autorizadas. O nó de Gateway de API será o único
componente com exposição à rede externa, atuando como um ponto de entrada seguro e controlado.
Camada 3: Controle de Acesso e Permissões: Deve ser implementado um controle de acesso baseado em função (RBAC) seguindo
o princípio do menor privilégio. Cada agente deve possuir credenciais apenas para as ferramentas e os armazenamentos de
dados estritamente necessários para sua função. Ferramentas de alto risco, como a de automação de GUI, exigirão
consentimento explícito do usuário para cada sessão de uso.
Camada 4: Segurança de Dados: Todos os dados em repouso, especialmente nas Memórias Episódica e Semântica, devem ser
criptografados. Um processo de sanitização deve ser implementado para identificar e anonimizar ou redigir informações
pessoalmente identificáveis (PII) ou outros dados sensíveis das interações do usuário antes de serem armazenados na
memória de longo prazo.

Parte V: Conclusão e Roteiro de Implementação em Fases

Esta seção final sintetiza a visão arquitetural e fornece um plano de ação prático e incremental para a implementação do
novo sistema Janus.

### Visão Arquitetural Sintetizada: Janus 1.0

A arquitetura proposta transforma Janus em um sistema multiagente seguro, escalável e com capacidade de auto-otimização.
Este design aborda diretamente todos os requisitos da solicitação inicial:
Escalabilidade: Através de uma arquitetura distribuída de nós especializados que pode crescer horizontalmente.
Aprendizado: Habilitado por uma memória hierárquica e pelo framework Reflexion, que permite o aprendizado a partir da
experiência e da correção de erros.
Autonomia: Realizada através do ciclo de raciocínio e ação (ReAct) e da capacidade de gerar dinamicamente novas
ferramentas para resolver problemas inéditos.
Segurança: Garantida por um framework de defesa multicamadas, com ênfase na execução segura de código em ambientes
sandbox.
Consciência Contextual: Integrada através de um módulo dedicado que ancora o agente em seu tempo e espaço (Itanhaém, 14
de agosto de 2025), proporcionando interações mais ricas e relevantes.

### Roteiro de Implementação em Fases (Mapeado para Sprints)

Para gerenciar a complexidade e entregar valor incrementalmente, a implementação é dividida em fases. Cada fase agrupa
um conjunto de sprints de desenvolvimento, conforme detalhado no documento `SPRINTS JANUS.md`.

| Fase       | Título                        | Foco Principal                                                                                                      | Sprints Correspondentes |
|:-----------|:------------------------------|:--------------------------------------------------------------------------------------------------------------------|:------------------------|
| **Fase 1** | **A Espinha Dorsal**          | Estabelecer a fundação da comunicação distribuída e da memória de longo prazo.                                      | **Sprints 1-3**         |
| **Fase 2** | **O Núcleo Cognitivo**        | Implementar a capacidade de raciocínio (ReAct), execução segura (Sandbox) e aprendizado com erros (Reflexion).      | **Sprints 4-7**         |
| **Fase 3** | **Inteligência e Expansão**   | Transformar experiências em sabedoria (Memória Semântica), coletar dados e hibridizar a inteligência (LLMs).        | **Sprints 8-10**        |
| **Fase 4** | **Maturidade e Proatividade** | Habilitar a colaboração entre agentes, garantir a resiliência do sistema e lançar o Meta-Agente de auto-otimização. | **Sprints 11-13**       |

---

### Apêndice A: Catálogo de APIs e Serviços de IA

Este apêndice centraliza todas as APIs e serviços externos que alimentam as capacidades de Janus.

1. Provedores de Modelos de Linguagem (LLMs)
   Estes são os cérebros do Janus, responsáveis pelo raciocínio, geração de texto e tomada de decisão. A estratégia,
   como planeado, é usar um roteador inteligente (LLMManager) para priorizar os níveis gratuitos.Confira os provedores
   de modelos de IA e seus usos no projeto Janus:
   Provedor
   Família de Modelos
   Limite do Nível Gratuito / Crédito Inicial
   Uso Principal no Janus
   Google AI
   Gemini 1.5 Pro / Flash
   Gemini 1.5 Flash: 1.500 requisições diárias (RPD). Crédito Total (Google Cloud): $300 para uso em 90 dias.
   Flash: Tarefas de rotina (Camada 2/3), como extração de JSON e sumarização. Pro: Raciocínio de ponta e geração de hipóteses (Camada 1).
   OpenAI
   Séries GPT-4o
   Crédito inicial para contas novas (geralmente $5 a $100).
   Raciocínio complexo (Camada 1), competindo com o Gemini Pro, especialmente durante o uso dos créditos iniciais.
   Cohere
   Séries Command R
   1.000 chamadas por mês (para uso não comercial/avaliação).
   Uma das primeiras opções para tarefas de Camada 2/3, como geração de texto e sumarização, aproveitando seu nível gratuito mensal.
   Anthropic
   Séries Claude
   Créditos iniciais para contas novas.
   Alternativa para tarefas de Camada 1 que exigem raciocínio complexo e geração de texto de alta qualidade.
   Ollama
   Llama 3, etc.
   Ilimitado (auto-hospedado). O limite é o seu hardware.
   Fallback Crítico: Garante que o Janus nunca fique inoperacional. Se todas as APIs de nuvem falharem, o LLMManager aciona o modelo local.
   Hugging Face
   Vários Modelos
   Nível gratuito para inferência com limites de taxa por hora.
   Acesso a uma vasta gama de modelos de código aberto especializados sem a necessidade de hospedagem.
   Together AI
   Vários Modelos
   $25 em créditos gratuitos na inscrição.
   Excelente opção para acessar modelos de código aberto com alto desempenho e custos baixos após o término dos
   créditos.

2. Ferramentas e APIs Especializadas
   Estas APIs fornecem ao Janus "sentidos" e "habilidades" específicas para interagir com o mundo digital e físico.
   Categoria
   API/Serviço
   Limite do Nível Gratuito
   Uso Principal no Janus
   Busca na Web
   Tavily Search API
   1.000 créditos por mês.
   Consciência Contextual: Integrada no core/context_core.py para obter informações em tempo real (notícias, tempo,
   etc.) para Itanhaém, SP.
   Visão Computacional
   Google Cloud Vision AI
   Nível gratuito generoso (ex: 1.000 unidades por mês para detecção de etiquetas).
   "Olhos" do Janus (Sprint 10): Essencial para analisar o ecrã, ler texto de imagens (OCR) e detectar objetos,
   capacitando o gui_automator.
   Processamento de Linguagem
   Google Cloud Natural Language API
   Nível gratuito (ex: 5.000 unidades por mês para análise de sentimento).
   Aprimoramento do knowledge_consolidator: Ajuda a extrair entidades, sentimentos e sintaxe de textos para enriquecer a
   Memória Semântica (Neo4j).
   Dados Estruturados
   APIs da HG Brasil
   Nível gratuito com limites diários.
   Obter dados estruturados e específicos do Brasil (tempo, finanças) com maior precisão do que uma busca genérica,
   aprimorando o módulo de contexto.
   Multimodalidade
   APIs Cloudmersive
   Nível gratuito com um número fixo de chamadas por mês.
   Fornecer um conjunto de ferramentas de utilidade geral prontas a usar, como conversão de documentos, manipulação de
   imagens e verificação de segurança.

---

### Apêndice B: Referências

AI Agent Architectures: Patterns, Applications, and Guide - DZone, acessado em agosto 13,
2025, https://dzone.com/articles/ai-agent-architectures-patterns-applications-guide
Centralized vs Distributed Multi-Agent AI Coordination Strategies - Galileo AI, acessado em agosto 13,
2025, https://galileo.ai/blog/multi-agent-coordination-strategies
Four Design Patterns for Event-Driven, Multi-Agent Systems - Confluent, acessado em agosto 13,
2025, https://www.confluent.io/blog/event-driven-multi-agent-systems/
What Is Agentic Architecture? | IBM, acessado em agosto 13, 2025, https://www.ibm.com/think/topics/agentic-architecture
Langchain - Qdrant, acessado em agosto 13, 2025, https://qdrant.tech/documentation/frameworks/langchain/
Qdrant - ️ LangChain, acessado em agosto 13, 2025, https://python.langchain.com/docs/integrations/vectorstores/qdrant/
qdrant/qdrant: Qdrant - High-performance, massive-scale Vector Database and Vector Search Engine for the next generation
of AI. Also available in the cloud https://cloud.qdrant.io - GitHub, acessado em agosto 13,
2025, https://github.com/qdrant/qdrant
Open LLM Leaderboard 2025 - Vellum AI, acessado em agosto 13, 2025, https://www.vellum.ai/open-llm-leaderboard
Aider LLM Leaderboards, acessado em agosto 13, 2025, https://aider.chat/docs/leaderboards/
Boost Your AI Model with FastAPI: A Quick Start Guide, acessado em agosto 13,
2025, https://pub.aimind.so/boost-your-ai-model-with-fastapi-a-quick-start-guide-dccf345698c3
FastAPI, acessado em agosto 13, 2025, https://fastapi.tiangolo.com/
Deploying Machine Learning models using FastAPI | by Kevinnjagi - Medium, acessado em agosto 13,
2025, https://medium.com/@kevinnjagi83/deploying-machine-learning-models-using-fastapi-0389c576d8f1
How to Use FastAPI for Machine Learning | The PyCharm Blog, acessado em agosto 13,
2025, https://blog.jetbrains.com/pycharm/2024/09/how-to-use-fastapi-for-machine-learning/
Best Vector Database for RAG : r/vectordatabase - Reddit, acessado em agosto 13,
2025, https://www.reddit.com/r/vectordatabase/comments/1hzovpy/best_vector_database_for_rag/
Chroma vs Qdrant: Cost and Performance Comparison - MyScale, acessado em agosto 13,
2025, https://myscale.com/blog/chroma-vs-qdrant-cost-performance-comparison/
Using LangChain ReAct Agents to Answer Complex Questions - Airbyte, acessado em agosto 13,
2025, https://airbyte.com/data-engineering-resources/using-langchain-react-agents
Build LLM Agent combining Reasoning and Action (ReAct) framework using LangChain | by Ashish Kumar Jain | Medium,
acessado em agosto 13,
2025, https://medium.com/@jainashish.079/build-llm-agent-combining-reasoning-and-action-react-framework-using-langchain-379a89a7e881
langchain.agents.react.agent.create_react_agent, acessado em agosto 13,
2025, https://api.python.langchain.com/en/latest/agents/langchain.agents.react.agent.create_react_agent.html
How to create a ReAct agent from scratch - GitHub Pages, acessado em agosto 13,
2025, https://langchain-ai.github.io/langgraph/how-tos/react-agent-from-scratch/
Storage - Qdrant, acessado em agosto 13, 2025, https://qdrant.tech/documentation/concepts/storage/
Summarize Text | 🦜️ LangChain, acessado em agosto 13, 2025, https://python.langchain.com/docs/tutorials/summarization/
Summarize Text - LangChain.js, acessado em agosto 13, 2025, https://js.langchain.com/docs/tutorials/summarization/
Migrating from MapReduceDocumentsChain - ️ LangChain, acessado em agosto 13,
2025, https://python.langchain.com/docs/versions/migrating_chains/map_reduce_chain/
I've been exploring the best way to summarize documents with LLMs. LangChain's MapReduce is good, but way too
expensive... - Reddit, acessado em agosto 13,
2025, https://www.reddit.com/r/LangChain/comments/165xmzx/ive_been_exploring_the_best_way_to_summarize/
MetaReflection: Learning Instructions for Language Agents using Past Reflections - arXiv, acessado em agosto 13,
2025, https://arxiv.org/html/2405.13009v2
Reflexion: Language Agents with Verbal Reinforcement ... - arXiv, acessado em agosto 13,
2025, https://arxiv.org/abs/2303.11366
[NeurIPS 2023] Reflexion: Language Agents with Verbal Reinforcement Learning - GitHub, acessado em agosto 13,
2025, https://github.com/noahshinn/reflexion
Pricing - OpenAI API, acessado em agosto 13, 2025, https://platform.openai.com/docs/pricing
Different Types of API Keys and Rate Limits | Cohere, acessado em agosto 13,
2025, https://docs.cohere.com/docs/rate-limits
Calculate Real ChatGPT API Cost for GPT-4o, o3-mini, and More - Themeisle, acessado em agosto 13,
2025, https://themeisle.com/blog/chatgpt-api-cost/
Rate limits - OpenAI API, acessado em agosto 13, 2025, https://platform.openai.com/docs/guides/rate-limits
Pricing | Secure and Scalable Enterprise AI - Cohere, acessado em agosto 13, 2025, https://cohere.com/pricing
Overview - Anthropic, acessado em agosto 13, 2025, https://docs.anthropic.com/en/api/overview
API Reference - OpenAI Platform, acessado em agosto 13,
2025, https://platform.openai.com/docs/api-reference/introduction
Preços do Serviço OpenAI Azure, acessado em agosto 13,
2025, https://azure.microsoft.com/pt-br/pricing/details/cognitive-services/openai-service/
OpenAI's API Pricing: Cost Breakdown for GPT-3.5, GPT-4 and GPT-4o | dida Insights, acessado em agosto 13,
2025, https://dida.do/openai-s-api-pricing-cost-breakdown-for-gpt-3-5-gpt-4-and-gpt-4o
Best Open Source LLMs of 2025 — Klu, acessado em agosto 13, 2025, https://klu.ai/blog/open-source-llm-models
9 Top Open-Source LLMs for 2024 and Their Uses - DataCamp, acessado em agosto 13,
2025, https://www.datacamp.com/blog/top-open-source-llms
The 11 best open-source LLMs for 2025 - n8n Blog, acessado em agosto 13, 2025, https://blog.n8n.io/open-source-llm/
Top 5 Open Source LLMs You need to know [2024] - Creole Studios, acessado em agosto 13,
2025, https://www.creolestudios.com/top-5-open-source-llm/
IA de código aberto - Google Cloud, acessado em agosto 13,
2025, https://cloud.google.com/use-cases/open-source-ai?hl=pt-BR
10 LLMs (Large Language Models) Open-Source Para Uso Comercial, acessado em agosto 13,
2025, https://blog.dsacademy.com.br/10-llms-large-language-models-open-source-para-uso-comercial/
Your guide to choosing an open source LLM - KNIME, acessado em agosto 13,
2025, https://www.knime.com/blog/a-guide-to-open-source-llms
Guide Of All Open Sourced Large Language Models(LLMs) | by Luv Bansal | Medium, acessado em agosto 13,
2025, https://luv-bansal.medium.com/list-of-all-open-sourced-large-language-models-llms-a9e3927e8da8
Using Ollama with Python: A Simple Guide | by Jonathan Gastón Löwenstern - Medium, acessado em agosto 13,
2025, https://medium.com/@jonigl/using-ollama-with-python-a-simple-guide-0752369e1e55
Python & JavaScript Libraries · Ollama Blog, acessado em agosto 13,
2025, https://ollama.com/blog/python-javascript-libraries
vLLM (LLM inference and serving) - Guides - Vast.ai, acessado em agosto 13,
2025, https://docs.vast.ai/vllm-llm-inference-and-serving
Ollama REST API | Documentation | Postman API Network, acessado em agosto 13,
2025, https://www.postman.com/postman-student-programs/ollama-api/documentation/suc47x8/ollama-rest-api
Ollama Python library - GitHub, acessado em agosto 13, 2025, https://github.com/ollama/ollama-python
How To Use Ollama's API With Python - YouTube, acessado em agosto 13, 2025, https://www.youtube.com/watch?v=pLNqaTxvx3M
Learn Ollama in 15 Minutes - Run LLM Models Locally for FREE - YouTube, acessado em agosto 13,
2025, https://www.youtube.com/watch?v=UtSSMs6ObqY
Vllm documentation is garbage : r/LocalLLaMA - Reddit, acessado em agosto 13,
2025, https://www.reddit.com/r/LocalLLaMA/comments/1mn98w0/vllm_documentation_is_garbage/
vLLM - Qwen docs, acessado em agosto 13, 2025, https://qwen.readthedocs.io/en/latest/deployment/vllm.html
Criar aplicações de IA generativa para sua startup - AWS Startups, acessado em agosto 13,
2025, https://aws.amazon.com/startups/learn/building-generative-ai-applications-for-your-startup?lang=pt-BR
Tipos de instâncias do Amazon EC2 - AWS, acessado em agosto 13, 2025, https://aws.amazon.com/pt/ec2/instance-types/
Série da Máquina Virtual | Microsoft Azure, acessado em agosto 13,
2025, https://azure.microsoft.com/pt-br/pricing/details/virtual-machines/series/
Preço – Instâncias de Contêiner - Microsoft Azure, acessado em agosto 13,
2025, https://azure.microsoft.com/pt-br/pricing/details/container-instances/
AWS Pricing Calculator, acessado em agosto 13, 2025, https://calculator.aws/
Quanto Custa Adicionar GPU na Nuvem | AZURE | AWS | GOOGLE CLOUD - YouTube, acessado em agosto 13,
2025, https://www.youtube.com/watch?v=80tdQPjDkD4
Calculadora de Preços | Azure da Microsoft, acessado em agosto 13,
2025, https://azure.microsoft.com/pt-br/pricing/calculator/
GPU pricing | Google Cloud, acessado em agosto 13, 2025, https://cloud.google.com/compute/gpus-pricing
Disponibilizar um LLM com várias GPUs no GKE | Kubernetes Engine - Google Cloud, acessado em agosto 13,
2025, https://cloud.google.com/kubernetes-engine/docs/tutorials/serve-multiple-gpu?hl=pt-br
Hardware requirements for Llama 2 · Issue #425 - GitHub, acessado em agosto 13,
2025, https://github.com/meta-llama/llama/issues/425
LLaMA 7B GPU Memory Requirement - Transformers - Hugging Face Forums, acessado em agosto 13,
2025, https://discuss.huggingface.co/t/llama-7b-gpu-memory-requirement/34323
Support Matrix — NVIDIA Generative AI Examples 0.5.0 documentation, acessado em agosto 13,
2025, https://nvidia.github.io/GenerativeAIExamples/0.5.0/support-matrix.html
Memory requirements for fine-tuning Llama 2 | by Sri Ranganathan Palaniappan | Polo Club of Data Science | Georgia
Tech | Medium, acessado em agosto 13,
2025, https://medium.com/polo-club-of-data-science/memory-requirements-for-fine-tuning-llama-2-80f366cba7f5
Llama 2 chat with vLLM (7B, 13B & multi-gpu 70B) - Getting started, acessado em agosto 13,
2025, https://docs.mystic.ai/docs/llama-2-with-vllm-7b-13b-multi-gpu-70b
Best Local LLMs for Every NVIDIA RTX 40 Series GPU, acessado em agosto 13,
2025, https://apxml.com/posts/best-local-llm-rtx-40-gpu
The scoop on 4060 ti 16gb cards : r/LocalLLaMA - Reddit, acessado em agosto 13,
2025, https://www.reddit.com/r/LocalLLaMA/comments/1ir08pp/the_scoop_on_4060_ti_16gb_cards/
Can You Run This LLM? VRAM Calculator (Nvidia GPU and Apple Silicon), acessado em agosto 13,
2025, https://apxml.com/tools/vram-calculator
Running LLMs on your computer locally — focus on the hardware! | by Michael McAnally, acessado em agosto 13,
2025, https://michael-mcanally.medium.com/running-llms-on-your-computer-locally-75717bd38d5e
Nvidia RTX 4060 Ollama Benchmark: LLM Inference Performance & Analysis, acessado em agosto 13,
2025, https://www.databasemart.com/blog/ollama-gpu-benchmark-rtx4060
Think twice about getting the RTX 4060 ti : r/LocalLLaMA - Reddit, acessado em agosto 13,
2025, https://www.reddit.com/r/LocalLLaMA/comments/14gnkfw/think_twice_about_getting_the_rtx_4060_ti/
LocalAI LLM Single vs Multi GPU Testing scaling to 6x 4060TI 16GB GPUS - YouTube, acessado em agosto 13,
2025, https://www.youtube.com/watch?v=Zu29LHKXEjs
GeForce RTX 4060 Ti 16GB benchmarks showcase massive performance improvement in some games - TweakTown, acessado em
agosto 13,
2025, https://www.tweaktown.com/news/92752/geforce-rtx-4060-ti-16gb-benchmarks-showcase-massive-performance-improvement-in-some-games/index.html
Code Llama 13B - NVIDIA NGC, acessado em agosto 13, 2025, https://catalog.ngc.nvidia.com/orgs/nvidia/models/code_llama
