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
