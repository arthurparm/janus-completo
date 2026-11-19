# Regras da equipe

Valem para todo papel. O revisor recusa o diff que as quebra.

## `old/` é pedreira

Pode ler `old/` para achar comportamento, falha, nome ou ideia. A issue cita o caminho como evidência.

`old/` não é especificação. Não se copia arquivo para a árvore nova. O que for aproveitado é reescrito e passa nas regras abaixo. Documentação antiga não vira requisito. Segredo não se lê nem se traz.

## 1. Quinhentas linhas e util compartilhado

Arquivo de código que a equipe escreve, implementação ou teste, tem no máximo 500 linhas. A contagem é a do arquivo. Passou, divide por responsabilidade.

Comportamento usado em dois ou mais arquivos vai para um util. Util com um único uso não se cria.

`old/` não entra nessa conta: é arquivo, e não se reescreve para caber no limite. Documento de desenho que passar de 500 linhas também se divide.

## 2. Sem `Any`

É proibido `any`, `Any`, `as any` e `typing.Any`. Também é proibido o comentário que existe só para esconder esse tipo.

O tipo é explícito. O que ainda não tem forma vira um tipo nomeado ou uma issue. Não vira `Any`.

## 3. Problema fora do contexto vira issue

Problema achado fora da issue aberta não entra no mesmo diff e não fica no silêncio. Se outra issue já o cobre, registra-se nela. Se não cobre, abre-se issue com dono, fase e critério de pronto.

O diff atual continua só no critério da issue em que a equipe está.

## 4. Dúvida vira issue. O código da issue é o mais completo que o critério permite

Dúvida que trava uma decisão vira issue antes de virar código. Dentro da issue, o código cobre o caminho, o erro e a borda que o critério nomeia. O que não couber não fica como `TODO` solto: vira issue.

## 5. Explorar e misturar pesquisa é liberado

Ler, comparar e misturar ideias é permitido. Vale pesquisa, vale `old/`, vale cruzar as duas. O lugar disso é o desenho e a issue, com hipótese e critério.

Misturar ideia não autoriza implementar fase futura dentro da fase atual. Ideia sem critério não é comportamento entregue.

## 6. Estrutura de arquivos organizada

Código novo só entra nesta árvore. Arquivo fora dela é bloqueio. Pasta nova na raiz só nasce se o arquiteto a incluir aqui antes.

```
pyproject.toml        manifesto do pacote, na raiz, não é módulo
docs/                 desenho, método e regras
issues/               uma issue por arquivo
.grok/agents/         papéis da equipe
.grok/workflows/      comandos
src/janus/            runtime, um arquivo por componente
src/janus/tools/      uma ferramenta por arquivo
src/janus/util/       só comportamento usado por dois ou mais módulos
tests/janus/          o mesmo caminho relativo de src/janus
tests/janus/support.py  fixture de teste usada por dois ou mais módulos; não é teste
client/conversa/      aviso de que a voz é um modelo
client/supervisao/    pendência, aprovar, negar, interromper
```

| Componente | Arquivo |
|---|---|
| Entrada | `src/janus/entry.py` |
| Loop | `src/janus/loop.py` |
| Construtor de contexto | `src/janus/context.py` |
| Adaptador | `src/janus/adapter.py` |
| Portão | `src/janus/gate.py` |
| Estado | `src/janus/state.py` |
| Traço | `src/janus/trace.py` |
| Experiência | `src/janus/experience.py` |
| Meta, reflexão | `src/janus/goals.py` |
| Aprendiz | `src/janus/learner.py` |
| Autoevolução | `src/janus/evolution.py` |
| API que o cliente chama | `src/janus/api.py` |

`src/janus/__init__.py` só reexporta. Lógica não mora nele. `src/janus/__main__.py` só chama `main` de `entry.py`. `src/janus/util/` não é gaveta: o nome do arquivo é o comportamento, e um util de um único uso não existe. `codec.py` é o texto compartilhado. `pairs.py` é o par de argumentos da proposta e da decisão.

Teste de `src/janus/gate.py` fica em `tests/janus/test_gate.py`. O cliente não contém portão, peso nem ferramenta. A raiz do repositório não recebe módulo solto.

## 7. Quem altera o corte commita

Alteração de arquivo neste repositório fecha no mesmo turno com um commit local. A mensagem cita a issue e o efeito. O commit contém só os arquivos desse corte. Segredo fica de fora. O passo termina nesse commit.

## 8. Organização e nome

Vale para arquivo e método que o diff cria. Não reescreve teste nem módulo já aceito para trocar nome. Renomear o que já passa só entra se uma issue pedir isso. Esta regra não é essa issue.

O nome diz o que o trecho é. Módulo, função e método em `lower_with_under`. Classe em `CapWords`. Constante de módulo em `CAPS_WITH_UNDER`. Nome interno leva `_` na frente. Arquivo `.py` não leva hífen e não leva id de issue.

Estado mutável de módulo não entra. Constante pode. Importar o módulo não abre run, não chama ferramenta e não escreve estado.

### Teste

O runner é o `unittest` da biblioteca padrão. A suíte roda com a raiz do repositório no topo da importação:

```
python -m unittest discover -s tests -t .
```

`PYTHONPATH` aponta para `src`. Sem `-t .`, `tests/janus` esconde `src/janus` e a suíte deixa de provar o runtime. O arquivo de teste casa com `test*.py`. Arquivo que não é teste não começa com `test`.

Teste de módulo espelha o fonte: `src/janus/gate.py` fica em `tests/janus/test_gate.py`. Trajetória que cruza módulos leva o comportamento no nome, como `tests/janus/test_read_cycle.py`. Quando a trajetória é de uma issue, o id fica numa linha no topo do arquivo. Não fica no nome do arquivo.

Uma classe de teste por arquivo. Um método prova uma condição: estado inicial, ato e resultado esperado. O nome é `test_<condição>_<resultado>`. Vários asserts do mesmo ato e do mesmo resultado ficam juntos. Condições independentes não dividem método, e o nome não as junta com `and`. A mesma decisão com entradas diferentes usa `subTest`. O rótulo do `subTest` diz a entrada.

A ordem no método é preparar, agir, verificar. Helper de um arquivo fica nesse arquivo, com `_`. Helper usado por dois ou mais módulos de teste fica em `tests/janus/support.py`. Teste não importa outro teste. Cada teste monta o próprio estado e não depende da ordem da suíte. Sem rede e sem `sleep`. Timeout de processo local é limite, não espera.

O revisor bloqueia código novo que quebre esta regra. Não bloqueia estilo que ela não nomeia. Não pede renomear o que já estava aceito. Afrouxar assert para o nome caber continua bloqueio.

### O que não entra

- Teto de 80 colunas e `pylint` como portão. O Google Python Style Guide os usa. Aqui o teto continua o arquivo de 500 linhas.
- Teto duro de função. O mesmo guia pede para pensar em quebrar uma função perto de 40 linhas e não fixa limite. Não criamos o segundo teto.
- Um assert por método. A condição é uma. Os asserts dessa condição ficam.
- Trocar o runner para pytest. O que se aproveita de lá é o layout: testes fora do pacote, pacote em `src/`.
- Forma de import do guia do Google (`import pacote` em vez de `from pacote import nome`). O código já aceito não se reescreve por isso.
- As nove características da ISO/IEC 25010 como checklist de review. Modularidade e testabilidade são o motivo desta organização, não um processo novo.
- "Inspirar confiança" ou "apto para produção" como aceite. Suíte verde não afirma que o runtime aprende.

As fontes estão em [fontes.md](fontes.md), na seção Qualidade de organização.
