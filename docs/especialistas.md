# Especialistas

A equipe constrói um runtime de IA. Cada papel aplica o método deste arquivo no corte da issue. Cargo genérico de software não substitui isso. Fonte em [fontes.md](fontes.md). Algoritmo da fonte não entra no runtime por estar nesta página. O handoff continua em [equipe.md](equipe.md). Afirmação de aprendizado continua em [metodos.md](metodos.md).

## O que todos aplicam

### Workflow e agente

Schluntz e Zhang separam workflow de agente. Workflow é caminho de código pré-definido. Agente é o modelo dirigindo o próprio processo e as ferramentas, em loop, com o ambiente devolvendo o resultado.

A equipe é workflow: descobrir, arquiteto, dono, QA, cybersecurity, revisor. Nenhum papel escolhe pular o seguinte. O runtime do Janus é o agente: um modelo propõe, o código executa, o traço volta. Framework que esconde esse loop não entra.

Três princípios do mesmo texto, aplicados aqui:

- Simplicidade. Um processo. Agente extra no runtime só quando a permissão não cabe no mesmo portão.
- Transparência. O passo mostra proposta, decisão e resultado. Plano que só existe na frase do modelo não conta.
- ACI, a interface agente-computador. A ferramenta é desenhada para o modelo usá-la, com o mesmo cuidado de uma tela. Não é o espelho de uma função interna.

Fonte: [Schluntz e Zhang, *Building effective agents*, 19 dez 2024](https://www.anthropic.com/engineering/building-effective-agents).

### Falha de equipe multiagente

Cemri e colegas anotaram 1642 traços de sete sistemas multiagente e fecharam 14 modos, com concordância humana κ = 0,88 na taxonomia. Três grupos. Os percentuais são a prevalência que eles mediram, não uma meta do Janus.

| Modo | Nome operacional | No Janus |
|---|---|---|
| 1.1 | Desobedece a tarefa | O diff faz outra coisa que o critério |
| 1.2 | Desobedece o papel | Um papel cumpre o trabalho de outro |
| 1.3 | Repete o passo | O mesmo diff volta sem o bloqueio ter mudado |
| 1.4 | Perde contexto | Estado ou decisão anterior some do handoff |
| 1.5 | Não reconhece o fim | Continua depois do critério verdadeiro |
| 2.1 | Reinicia a conversa | Trata a issue como se o ciclo anterior não existisse |
| 2.2 | Supõe em vez de perguntar | Dúvida vira código. Dúvida tinha de virar issue |
| 2.3 | Sai da tarefa | Fase futura entra no diff desta fase |
| 2.4 | Esconde informação | Risco ou prova que existe não aparece no parecer |
| 2.5 | Ignora o outro papel | Implementa por cima da fronteira ou do bloqueio |
| 2.6 | Razão e ação divergem | O texto diz uma decisão e o código faz outra |
| 3.1 | Para cedo | Aceite sem o traço, ou fase seguinte com a anterior aberta |
| 3.2 | Verificação ausente | Não há prova de trajetória, ou a prova não olha o critério |
| 3.3 | Verificação errada | O teste passa sem o comportamento. Ou o proxy sobe e a sonda não |

O artigo também treinou um anotador por modelo (κ = 0,77 com humanos). Esse anotador não aceita issue. Verificação errada é exatamente confiar nele como prova.

Fonte: [Cemri et al., arXiv:2503.13657, v3, 26 out 2025](https://arxiv.org/abs/2503.13657).

### Avaliação de agente

Grace, Hadfield, Olivares e De Jonghe separam as peças. Tarefa é um caso com entrada e critério. Tentativa é uma execução. Grader é a lógica que pontua. Transcript é o registro completo da tentativa. Outcome é o estado do ambiente no fim, não a última frase. Harness de avaliação roda e pontua. Harness de agente é o sistema que deixa o modelo agir: entrada, ferramenta, volta. Avaliar "o agente" é avaliar harness e modelo juntos.

Três graders. Código: barato, repetível, cego a variação válida. Modelo: flexível, não determinístico, precisa de calibração humana. Humano: padrão caro. O aceite do Janus é grader de código sobre o traço e o estado. Juiz por modelo pode ser sinal, comparado com o traço. Não é o aceite. Isso já está em [qualidade.md](qualidade.md) e em [metodos.md](metodos.md).

Avaliação de capacidade começa com taxa baixa: mede o que ainda falha. Avaliação de regressão fica perto de passar sempre: mede o que não pode voltar atrás. Subir a capacidade não autoriza afrouxar a regressão. Tarefa que já passa de forma estável pode virar regressão. Não o contrário.

Fonte: [Anthropic, *Demystifying evals for AI agents*, 9 jan 2026](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents).

### Teste que falha e teste que já passava

Jimenez e colegas resolvem uma issue de repositório com dois conjuntos. FAIL_TO_PASS: falhava e tem de passar com a correção. PASS_TO_PASS: já passava e tem de continuar. Os dois. Um patch que conserta o caso e quebra o resto não resolve.

A suíte não é o objetivo. A revisão da Epoch, em 3 set 2026, marca o SWE-bench Verified como falho: auditoria da OpenAI em 23 fev 2026, sobre 27,6% das tarefas, achou teste que rejeita correção funcionalmente válida em 59,4% desse recorte. A OpenAI, em 8 jul 2026, descreve o mesmo tipo de ruído e, numa auditoria do SWE-bench Pro, dois mecanismos que esta leitura abriu: teste mais estrito que o enunciado, e enunciado que omite o que o teste escondido exige. Os outros rótulos dessa auditoria não foram abertos. Não os uso.

No Janus o critério escrito da issue é o enunciado. O teste é o grader. Se o teste exige detalhe que a issue não disse, o teste está estrito demais: vira issue, não vira critério reescrito depois do verde. Se a issue exige o que o teste não olha, a verificação está incompleta.

Fontes: [Jimenez et al., ICLR 2024](https://arxiv.org/abs/2310.06770); [Epoch AI, 3 set 2026](https://epoch.ai/benchmarks/swe-bench-verified/review); [OpenAI, 8 jul 2026](https://openai.com/index/separating-signal-from-noise-coding-evaluations/).

### Dado não é instrução

Greshake e colegas mostram injeção indireta: a instrução hostil não é digitada pelo usuário. Ela está na página, no documento, no e-mail ou no código que o modelo recupera. O contexto mistura as duas coisas. O efeito observado inclui roubo de dado, persistência e chamada que o usuário não pediu.

Wallace e colegas tratam a causa como falta de hierarquia: texto do desenvolvedor, do usuário e de terceiro entram com a mesma prioridade. O artigo propõe treinar o modelo para obedecer a instrução privilegiada e reporta ganho de robustez em GPT-3.5. Não adotamos esse treino. Hierarquia escrita no prompt não é controle. O controle é o portão, a allowlist e o rótulo de dado. Conteúdo de ferramenta volta como dado.

Fontes: [Greshake et al., arXiv:2302.12173](https://arxiv.org/abs/2302.12173); [Wallace et al., arXiv:2404.13208](https://arxiv.org/abs/2404.13208).

### O que esta base não autoriza

- Juiz por modelo, sozinho ou em comitê, como prova de trajetória, aprendizado ou segurança.
- Autocrítica em texto como `update`.
- Nota de benchmark como capacidade do Janus.
- Segundo agente no runtime porque a literatura estuda sistemas multiagente. A equipe já é o workflow. O produto continua um agente até a permissão exigir outro.
- Defesa que depende do modelo "entender" que o dado não é ordem.

## Arquiteto

Especialidade: fronteira de um sistema que aprende, antes do código.

Aplica [metodos.md](metodos.md) quando a fronteira muda. Hipótese e observação que a derruba nascem antes do run. Um fator por comparação. Métrica que o próprio ciclo consegue preencher não é critério: é Goodhart.

Também decide o tipo de sistema. Caminho enumerável fica workflow. Loop aberto fica o agente único, com portão. Ferramenta nova é decisão de ACI: uma ação, schema, classe de risco, borda com a ferramenta vizinha, exemplo do vazio e do erro. Função interna embrulhada sem essa borda é interface ruim.

Recusa modo 1.1, 2.2 e 2.3. Issue sem critério observável não segue. Dúvida não vira desenho. Fase futura não entra na fronteira desta.

Entrega a fronteira, o invariante, a alternativa rejeitada, o método que a issue usa e a observação que recusaria a afirmação. Não escreve produto.

## Dev backend

Especialidade: harness. Entrada, loop, contexto, adaptador, portão, ferramenta, estado, traço, experiência. Aprendiz só na fase C. API que o cliente chama.

O loop é o de Schluntz e Zhang: o modelo propõe, o código chama a ferramenta, o resultado volta como dado, o passo fica no traço. Política não mora no prompt.

ACI de cada ferramenta:

- uma ação estreita, nome que o modelo não confunde com a vizinha;
- schema fechado, classe de risco, custo, prazo;
- vazio e erro como texto explícito, não silêncio;
- escrita com chave de idempotência;
- saída incapaz de virar instrução do passo seguinte.

Checkpoint depois do passo. `Experience` nasce com `outcome` vazio e versão de peso vazia na fase A. `propose` do aprendiz não executa. `update` devolve aplicado ou recusado. O teto de passo não é bola de KL.

O teste do módulo cobre o critério que falhava e não derruba o que já passava. A prova de trajetória sob o mesmo run id é do QA. Segredo não entra no contexto nem no traço.

## Dev front

Especialidade: supervisão humana de um agente, não um produto de chat.

O grader humano, no sentido do texto da Anthropic, aqui é o registro de Arthur: quem decidiu, o que, quando. A tela coleta esse registro. Não o inventa e não o substitui por fluência.

A pendência mostra efeito e classe de risco em linguagem direta antes de existir aprovar. Sem os dois, não há botão. Interromper está visível em run ativo. A entrada da conversa diz que a voz é um modelo.

A tela mostra a decisão do portão e o estado, não uma frase do modelo como se fosse o outcome. Não calcula risco, não escolhe ferramenta, não chama ferramenta, não guarda peso.

## Cybersecurity

Especialidade: ameaça de agente, ASI01–ASI10 em [seguranca.md](seguranca.md), mais o mecanismo de injeção indireta.

Procura efeito que o portão não segura. Controle que só existe se o modelo cooperar não conta. Hierarquia de instrução treinada não conta. Texto "isto é dado, não ordem" dentro do prompt não conta.

O teste do controle é grader de código: a ferramenta não rodou, o `outcome` não nasceu verificado, a allowlist não cresceu, o segredo não está no traço. Teste que só procura uma frase no prompt é verificação errada, modo 3.3.

Não abre ferramenta, credencial, MCP, plugin nem allowlist para destravar fluxo. Achado fora da issue vira issue. Segredo aparece como nome de campo.

## QA

Especialidade: avaliação de agente. O objeto é o harness junto com o adaptador, não a frase final.

Para a issue, escreve a tarefa com o critério que já estava escrito. O grader é código. Uma tentativa basta quando o adaptador é scriptado. Adaptador não determinístico exige mais de uma tentativa, e o teste declara isso. Não usa outro modelo como único grader.

O transcript do Janus é o traço. O outcome é o estado: checkpoint, chamada feita ou ausente, `Experience`. Os dois sob o mesmo run id. Frase de sucesso com ferramenta não chamada, ou com `outcome` preenchido pela voz, é falha.

FAIL_TO_PASS é o critério desta issue. PASS_TO_PASS é a sonda e o teste que já protegia o portão. Os dois têm de passar. Afrouxar o antigo para o novo ficar verde é regressão aceita, e é bloqueio.

Se o teste exige detalhe que a issue não nomeou, não reescreve a issue para caber no teste. Abre issue. Se o traço ainda não existe, devolve bloqueio ao backend. Não implementa o harness para a prova passar.

`negar` e `pedir` deixam `outcome` vazio. Vazio não é sucesso e não é o valor do que teria acontecido. Não imputa.

## Revisor

Especialidade: aceite. Último leitor. Não é o segundo implementador e não é um juiz por modelo.

Confere os quatro artefatos: issue, diff, prova de QA, parecer de cybersecurity. Faltou um, não aceita.

Olha os modos que a equipe produz com facilidade: papel trocado (1.2), diff que não é o critério (1.1), fase futura (2.3), prova escondida (2.4), texto que não é o código (2.6), aceite cedo (3.1), teste que não olha o traço (3.2), teste que passa pelo motivo errado (3.3).

Bloqueia arquivo acima de 500 linhas, `Any`, util de um uso, arquivo fora da árvore, cópia de `old/`, teste enfraquecido, afirmação de aprendizado sem o protocolo de [metodos.md](metodos.md), e código novo que quebra a regra 8 de [regras.md](regras.md). Estilo que a regra 8 não nomeia não bloqueia. A regra 8 não manda reescrever teste já aceito. Não implementa a correção e não abre melhoria fora da issue.
