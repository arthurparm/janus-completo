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
5. Ferramenta permitida executa com credencial da própria ferramenta.
6. O resultado volta como dado não confiável.
7. O estado grava checkpoint. O traço grava o passo. `Experience` grava o mesmo passo com `outcome` vazio.
8. Quando existe verificador, o critério preenche `outcome` ou deixa vazio. `update` aceita ou recusa.
9. O loop para por resposta final, negação terminal, pendência, orçamento, prazo ou kill switch.

### Interrupção durante um passo

Interromper grava a marca `interrupted` no diretório do run. O passo não escreve essa marca, e a leitura do checkpoint com ela devolve `encerrado`, motivo `interrompido`. Por isso o passo em curso, no mesmo processo ou em outro sobre a mesma raiz, não reabre o run.

O passo consulta a marca depois do `propose` e antes de qualquer efeito:

- Marca presente: a decisão é `negar`, motivo `run interrompido`, com a classe de risco que a proposta tinha. Nenhuma ferramenta é chamada e nenhuma pendência nasce. O passo grava traço e `Experience` e conta um passo, sem custo. Passo já esgotado mantém o motivo do orçamento e não conta.
- Marca posterior à consulta: o passo termina o que decidiu, inclusive a leitura permitida ou a pendência. O run fica `encerrado` e o passo seguinte não roda.

A chamada de modelo em andamento não é cancelada.

### Colisão de acesso a um arquivo do run

No Windows, ler um arquivo do run enquanto ele é substituído, ou substituí-lo enquanto há um leitor, levanta `PermissionError`. O leitor pode ser outro processo, a supervisão ou a própria interrupção. O estado repete a leitura ou a substituição até 20 vezes, com 5 ms entre elas. Persistindo, levanta `JanusError`, motivo `arquivo do run em uso`, e remove o arquivo temporário da substituição.

`interrupt` não depende de ler o checkpoint. Se a primeira leitura colide, ele grava a marca mesmo assim. Num run já encerrado, esse caso faz o motivo ser lido como `interrompido`. Se a leitura de confirmação, depois da marca, colide, a chamada levanta o erro com a parada já valendo, e repetir é seguro. Run sem diretório continua `run ausente` e não ganha marca.

O passo grava o checkpoint duas vezes:

1. Depois de decidir e antes de qualquer efeito, a reserva: `step_index`, gasto e estado do run, sem o último resultado. Se a reserva colide, nenhuma ferramenta roda, não há traço, `Experience` nem pendência, e o passo não conta. O adaptador já foi consultado.
2. Depois do traço, da `Experience` e da pendência, o último resultado. Se essa gravação ou a leitura da pendência colide, o passo levanta o erro e a reserva fica: o gasto conta e o passo seguinte usa o `step_index` seguinte, sem o resultado no contexto. Colisão na leitura da pendência deixa o `pedir` no traço sem pendência gravada.

Dois passos simultâneos no mesmo run não são tratados aqui.

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
