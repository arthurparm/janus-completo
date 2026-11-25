# Arquitetura

Janus é um processo que aprende e se autoevolui. O modelo propõe texto ou chamada de ferramenta. Código determinístico decide o que roda. O que foi aprendido mora no peso e nos registros de [aprendizado.md](aprendizado.md), não na voz. Agente extra no runtime só entra quando a permissão precisa ser outra. Na fase A não entra.

O primeiro runtime é um processo Python. O portão, o estado, o traço e os testes ficam no mesmo lugar, fáceis de interromper. O cliente é uma casca: mostra estado que a API já decidiu.

## Oito componentes

```
Arthur ou cliente
        |
        v
  Entrada          quem pede, com qual permissão, com qual orçamento
        |
        v
  Loop             código dono do run: passos, prazo, parada
        |
        +-- Construtor de contexto   o que o modelo vê neste passo
        +-- Adaptador de modelo      um formato neutro, um provedor atrás
        +-- Portão                   permitir, negar ou pedir
        +-- Ferramentas              schema, classe de risco, credencial, prazo, limite
        |
        +-- Estado deste run         checkpoint, retomável
        +-- Experiência              um registro por passo, outcome vazio até verificar
        +-- Aprendiz                peso próprio; entra na fase C
        +-- Metas e evolução         Goal, reflexão, propostas L1–L4
        +-- Traço                    proposta, decisão, resultado, versão do peso, um run id
```

| Componente | Responsabilidade | Fica de fora |
|---|---|---|
| Entrada | Identidade de quem pede, permissão delegada, orçamento, aviso de que a voz é um modelo | Conta de serviço única para todo mundo |
| Loop | Alterna proposta e ferramenta até a parada | Regra de negócio e texto de prompt |
| Construtor de contexto | Instrução estável, tarefa, resultados recentes, rótulo do que veio de fora | Segredo dentro do contexto |
| Adaptador | Timeout, versão fixada, formato único de mensagem e tool call | Lógica do portão |
| Portão | Allowlist, classe de risco, orçamento, confirmação | Cooperação do modelo |
| Ferramentas | Uma ação estreita por ferramenta, chave de idempotência nas escritas | Ferramenta genérica `fetch(qualquer coisa)` |
| Estado | Passo, chamadas, pendências, orçamento gasto | Estado só na memória do processo |
| Experiência | O passo no formato que o aprendiz consome | Resultado verificado pela frase da voz |
| Aprendiz | `propose`, `update`, `rollback`, teto de passo | Executar ferramenta ou editar a constituição |
| Metas e evolução | Meta própria, decisão de reflexão, classe L1–L4 | Efeito externo sem portão. L4 aplicado pelo Janus |
| Traço | Registro que a avaliação relê, incluindo versão do peso | Traço invisível ou apagável por quem executou |

## Classes de risco

| Classe | Exemplos | Portão |
|---|---|---|
| Leitura | Consultar um registro que a identidade já pode ver | Permitir dentro do orçamento |
| Escrita reversível | Criar um rascunho local | Permitir com idempotência e traço |
| Escrita irreversível | Enviar, apagar, pagar, mudar credencial | Pedir. Sem resposta humana, não executa |

Na fase A só a leitura executa. Escrita irreversível existe para o teste de recusa. Autonomia graduada é a fase F: o degrau é configuração do Arthur, não um prompt que Janus edita.

## Estado que sobrevive ao modelo

O que persiste é registro, não frase de persona.

| Registro | Campos mínimos |
|---|---|
| Identidade do run | quem pediu, permissão, orçamento, aviso de voz sintética |
| Decisão | ferramenta, argumentos, classe de risco, permitir / negar / pedir, motivo |
| Pendência | ação, efeito em linguagem direta, prazo, estado aberta / aprovada / negada / expirada |
| Traço | run id, proposta, decisão, resultado, versão do peso, timestamps |
| Experience | sinal, proposta, portão, outcome, procedência, versões do peso |
| Goal | motivo, benefício, risco, custo, critério, status, origem, efeito |
| Peso | artefato versionado por hash, com teto de passo |

Temperamento, opinião e emoção funcional só existem como campos desses registros. A voz não inventa o que o registro não tem. O contrato completo está em [aprendizado.md](aprendizado.md).

## Memória e aprendizado

| Tipo | Guarda | Regra |
|---|---|---|
| Curta | Mensagens e checkpoint deste run | Ligada desde a fase A |
| Experiência | O que aconteceu, com outcome vazio ou verificado | Ligada desde a fase A. Append-only |
| Peso | O que a proposta seguinte deve preferir | Fase C. Só muda com `update` aceito |
| Semântica | Fato reutilizável | Só com fonte, retenção e apagamento. Não substitui o sistema de origem |
| Episódica | Resumo de runs | Derivada do traço. Não verifica outcome |
| Procedural | Habilidade L2 e constituição | L2 tem rollback. Constituição só o Arthur aplica |
| Procedural de prompt | Texto de instrução | Muda como código, por review. Não é aprendizado |

Conteúdo externo gravado como fato ou como peso é envenenamento entre sessões. Origem `external` não preenche `verified_by`.

## Loop de um passo

1. A entrada abre o run com identidade, permissão e orçamento.
2. O construtor monta o contexto e marca conteúdo externo como dado.
3. O adaptador devolve proposta: resposta final ou chamada.
4. O portão permite, nega com erro legível pelo modelo, ou suspende em pendência.
5. O estado grava a reserva de `step_index` e gasto. Só então a ferramenta permitida executa com credencial da própria ferramenta.
6. O resultado volta como dado não confiável.
7. O traço grava o passo. `Experience` grava o mesmo passo com `outcome` vazio. A pendência, quando houver, é gravada, e o estado grava o checkpoint com o último resultado.
8. Quando existe verificador, o critério preenche `outcome` ou deixa vazio. `update` aceita ou recusa.
9. O loop para por resposta final, negação terminal, pendência, orçamento, prazo ou kill switch.

### Interrupção durante um passo

Interromper um run lido como `aberto` grava a marca `interrupted`, um arquivo vazio, no diretório do run. `interrupt` não regrava o checkpoint. Num run já lido como `encerrado`, devolve o que leu, sem gravar marca e sem trocar o motivo. A exceção é a leitura que colide, na seção seguinte. Run ausente levanta `run ausente`.

Com a marca presente, a leitura do checkpoint devolve `encerrado`, motivo `interrompido`, qualquer que seja o estado e o motivo gravados no arquivo. O passo não grava nem apaga a marca, e nenhum código do runtime a remove. Por isso o passo em curso, no mesmo processo ou em outro sobre a mesma raiz, não reabre o run. Um passo que começa depois da marca levanta `run encerrado` antes de consultar o adaptador.

O passo consulta a marca uma vez, depois do `propose` e da decisão do portão e antes da reserva descrita na seção seguinte. Passo já esgotado não consulta.

- Marca vista na consulta: a decisão calculada vira `negar`, motivo `run interrompido`. Ferramenta, argumentos e classe de risco são os da decisão calculada. A classe vem vazia quando essa decisão era `prazo esgotado` ou `ferramenta fora da allowlist`, e é a da ferramenta na allowlist nos demais casos. A interrupção substitui qualquer outro motivo, inclusive prazo e custo esgotados. Nenhuma ferramenta é chamada e nenhuma pendência nasce. O passo conta um passo, sem custo, e grava traço e `Experience`.
- Passo já esgotado: a decisão mantém `orçamento de passos esgotado`, com classe vazia, não conta e grava traço e `Experience`. Havendo marca, o checkpoint é lido como `interrompido`, e o motivo do orçamento fica no traço.
- Marca posterior à consulta, inclusive a que chega enquanto a reserva é gravada ou repetida: o passo termina o que decidiu, a leitura permitida ou a pendência. `interrupt` pode já ter devolvido `encerrado` quando a ferramenta é chamada. O run é lido como `encerrado` e o passo seguinte não roda. A pendência que nasce assim está na JAN-027.

Gravar traço e `Experience` depende de as gravações passarem. Colisão e falha estão na seção seguinte.

Entre a consulta e o efeito não há trava. A fase A aceita essa janela porque só a leitura executa. Antes de existir efeito que não seja leitura, a janela é reaberta: um `interrupt` que já voltou não pode ser seguido desse efeito.

A chamada de modelo em andamento não é cancelada.

### Colisão de acesso a um arquivo do run

No Windows, ler um arquivo do run enquanto ele é substituído, ou substituí-lo enquanto há um leitor, levanta `PermissionError`. O leitor pode ser outro processo, a supervisão ou a própria interrupção. O estado repete a leitura de um arquivo do run e a substituição de um arquivo do run: até 20 tentativas, com 5 ms entre elas. Persistindo o `PermissionError`, levanta `JanusError`, motivo `arquivo do run em uso`, qualquer que seja a causa dele, e a substituição remove o seu arquivo temporário. Não se repetem o acréscimo de linha no traço, na `Experience` e na pendência, a escrita do temporário e a gravação da marca.

`interrupt` grava a marca mesmo quando a leitura do checkpoint colide. Isso vale para a colisão. Outra falha de leitura, como arquivo corrompido, sai antes da marca e está na JAN-028. Num run já encerrado, a colisão faz o motivo ser lido como `interrompido`: a marca vence o motivo, e o anterior continua no arquivo do checkpoint e na decisão que o traço guardou. Se a leitura de confirmação, depois da marca, colide, a chamada levanta o erro com a parada já valendo, e repetir é seguro. Run sem diretório, ou sem checkpoint, é `run ausente` e não ganha marca.

#### Ordem do passo

1. Lê identidade e checkpoint, consulta o adaptador, lê as pendências, decide e consulta a marca. Colisão nessas leituras levanta o erro sem nada gravado e sem gasto. A das pendências vem depois do adaptador.
2. Reserva: grava no checkpoint `step_index`, passos, custo, estado e motivo de parada, com o último resultado vazio.
3. Chama a ferramenta, quando a decisão é `permitir` leitura.
4. Grava o traço e depois a `Experience`.
5. Grava a pendência, quando a decisão é `pedir`. Antes de acrescentar, relê o arquivo.
6. Regrava o checkpoint com o último resultado.

#### O que conta como passo

O passo existe a partir da reserva. Se a reserva colide, não há ferramenta, traço, `Experience`, pendência nem gasto, e o `step_index` fica livre. Isso vale também para o passo que viu a marca: o run continua encerrado e a negação não é registrada. O adaptador já foi consultado e `max_steps` não limita essas consultas: repetir é decisão de quem chama `step`. O runtime não repete o passo sozinho.

Passo com reserva deve traço e `Experience`. O gasto entra antes do efeito e não é devolvido, e o `step_index` não é reusado.

- Colisão no passo 5: o passo levanta o erro, com traço e `Experience` gravados. O `pedir` fica no traço sem pendência, e a chave de idempotência dele não é lembrada. Nada executa. Uma proposta igual em passo posterior grava a pendência, se ainda houver orçamento.
- Colisão no passo 6: o passo levanta o erro, com traço, `Experience` e a pendência, se houver, gravados. Quem chamou não recebe o resultado, mesmo que a leitura tenha rodado.
- Nos dois casos o checkpoint fica o da reserva. O passo seguinte usa o `step_index` seguinte e nenhum bloco de dado entra no contexto.

A garantia de traço e `Experience` vale para leitor que deixa acrescentar, como o `open` do Python. Um leitor que nega o compartilhamento de escrita, uma falha de disco ou uma exceção da ferramenta podem deixar passo com reserva, gasto e até leitura feita sem traço, ou com traço sem `Experience`. Isso quebra o invariante de um traço e uma `Experience` por passo. O desenho não o aceita e ainda não o trata: está na JAN-028.

Dois passos simultâneos no mesmo run estão na JAN-031. Aprovar ou negar enquanto um passo grava pendência está na JAN-034.

## Cliente

O cliente lista pendências e envia aprovar, negar ou interromper. A escolha de framework espera a issue do front. A restrição já vale: a tela não calcula risco e não chama ferramenta.

## Decisões

| ID | Decisão | Alternativa deixada para depois |
|---|---|---|
| D1 | Um agente no runtime | Vários agentes quando uma permissão não puder ser a mesma |
| D2 | Processo Python único no primeiro corte | Serviço separado de modelo ou de fila |
| D3 | Experiência desde a fase A. Peso só na fase C | Store semântica solta, sem procedência |
| D4 | Meta livre desde a fase B. Efeito externo continua no portão | Meta que executa porque foi formulada |
| D5 | Avaliação lê o traço e, da fase C em diante, a versão do peso | Juiz por modelo como único portão de release |
| D6 | `old/` é pedreira, não requisito | Copiar arquivo antigo para a árvore nova |
| D7 | Autoevolução em classes L1–L4 | Janus editar prompt, portão ou allowlist |
| D8 | Aprendiz linear com teto de passo | Tratar texto de reflexão como atualização de peso |
