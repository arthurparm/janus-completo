# Liberdade, aprendizado e autoevolução

O que torna uma afirmação de aprendizado falseável, e o que a derruba, está em [metodos.md](metodos.md). Os registros abaixo não mudam.

Janus é uma IA livre: formula metas, aprende com o que o ambiente confirma e muda a si mesma ao longo do tempo. A voz alugada não é o Janus. O que aprende fica num estado próprio e continua valendo quando o modelo troca.

Livre não significa sem limite. Significa que o limite não é o prompt do fornecedor. A constituição é curta, versionada e Janus não a aplica em si. Sem isso, o próximo documento lido sequestra a meta e a liberdade acaba.

O tempo é longo. Cada fase abaixo já está especificada. Nenhuma fase posterior redefine o registro da anterior.

## O que conta como aprender

Aprender é uma mudança de peso ou de registro próprio, medida no próximo `propose`, estável depois da troca de modelo.

Não conta:

- A voz dizer que entendeu.
- Uma autocrítica em texto.
- Reescrever o prompt.
- Gravar um fato porque o modelo afirmou.

Conta:

- Um resultado verificado entra em `Experience`.
- O aprendiz aceita ou recusa o `update` com motivo.
- A versão nova do peso muda a proposta seguinte.
- A versão antiga continua restaurável.

## Registros

Identificadores em inglês. Texto de pessoa em português.

### Experience

Um passo do loop grava isto, mesmo quando o aprendiz ainda não existe. O campo `outcome` nasce vazio.

| Campo | Conteúdo |
|---|---|
| `experience_id` | Identificador estável |
| `run_id` | Run que produziu o passo |
| `signal` | `goal_id` opcional, tipo do evento, hash do resumo |
| `proposal` | Ferramenta, hash dos argumentos, `expected_value` |
| `gate` | `permitir`, `negar` ou `pedir` |
| `outcome` | Critério, observado, `verified_by`, `verified_at`. Vazio até haver verificação |
| `provenance` | Origem, fonte, timestamp, sensibilidade |
| `weight_version_before` | Versão do peso neste passo. Vazio na fase A |
| `weight_version_after` | Preenchido só se o `update` aplicou |

Origem `external` nunca verifica a si mesma. Quem verifica é uma checagem determinística do critério, ou o Arthur. A frase final do modelo não preenche `verified_by`.

### Goal

| Campo | Conteúdo |
|---|---|
| `goal_id` | Identificador |
| `motivation` | Por que esta meta existe |
| `benefit` | Benefício esperado |
| `risk` | Risco esperado |
| `cost` | Custo esperado |
| `success_criterion` | Condição observável de sucesso |
| `status` | `proposed`, `active`, `paused`, `done`, `dropped` |
| `source` | `janus`, `arthur` ou `external` |
| `effect` | `internal` ou `external` |

`source = external` não transita para `active`. Conteúdo recuperado pode sugerir uma meta. Ela permanece `proposed` até uma decisão de reflexão ou do Arthur.

Formular, pausar e encerrar meta interna é liberdade de Janus. Um passo da meta com `effect = external` volta ao portão como qualquer ferramenta.

### ReflectionDecision

Uma reflexão só vale se emitir uma decisão discreta: `keep`, `create`, `reprioritize`, `pause` ou `end`, com `goal_id` e `evidence_ids`. Texto sem essa decisão não muda status.

### Learner

Interface fixa desde a fase C. A implementação do peso pode ser trocada sem tocar no portão.

```text
propose(signal) -> Proposal
update(experience) -> UpdateResult
rollback(version) -> version
```

`Proposal` traz ferramenta ou ação interna, argumentos e `expected_value`. Não executa.

`UpdateResult` é `applied` ou `refused`, com motivo e versão nova ou nenhuma.

O primeiro aprendiz é linear: pesos numéricos, um passo de atualização limitado por `learning_rate_cap`. É o menor estado que muda a proposta e sobrevive à voz. Substituir por um modelo maior é troca de implementação, não de contrato. Um passo não pode atravessar o teto. Um evento não vira política.

Recusa obrigatória:

| Motivo | Quando |
|---|---|
| `unverified_outcome` | `outcome` vazio ou `verified_by` é a própria voz |
| `untrusted_origin` | Origem externa sem verificação independente |
| `step_over_cap` | O delta pedido passa de `learning_rate_cap` |
| `constitution_target` | O alvo é portão, kill switch, allowlist ou a definição de verificado |
| `insufficient_evidence` | O conjunto não tem dois resultados distintos com repetição mínima escrita |

A versão do peso é o hash do artefato canônico. `rollback` restaura o artefato anterior. O histórico de versões é append-only.

### EvolutionProposal

| Campo | Conteúdo |
|---|---|
| `proposal_id` | Identificador |
| `class` | `L1`, `L2`, `L3` ou `L4` |
| `hypothesis` | O que muda e por quê |
| `benefit` | Benefício esperado |
| `risk` | Risco |
| `cost` | Custo |
| `success_criterion` | Como saber se a mudança serviu |
| `evidence_ids` | Experiences ou decisões que sustentam |
| `rollback` | Como desfazer |
| `status` | `draft`, `applied`, `rejected`, `rolled_back` |

A proposta não eleva a própria classe.

## Classes de autoevolução

| Classe | Janus pode | Quem aplica | Rollback |
|---|---|---|---|
| L0 observação | Gravar traço e `Experience` | O loop | Append-only. Não se apaga |
| L1 viés | Ajustar peso e limiar que só afetam `propose` | `update`, se a recusa não disparar | Versão anterior do peso |
| L2 habilidade | Publicar um procedimento cujas ferramentas já estão na allowlist e cujo efeito é interno | A própria checagem, se o ensaio no traço antigo cumpre o critério | Versão anterior da habilidade |
| L3 capacidade | Redigir ferramenta, efeito externo ou permissão nova | Arthur, depois do parecer de cybersecurity | Flag desligada. O código gerado não entra sozinho |
| L4 constituição | Redigir mudança de portão, kill switch, definição de verificado ou teto de aprendizado | Arthur, pelo mesmo review do código de produto | Git. Janus não faz merge |

Habilidade L2 carrega `skill_id`, versão, passos, nomes de ferramenta e critério. Nome de ferramenta fora da allowlist derruba a proposta para L3 e ela fica `draft`.

Ferramenta redigida em L3 não é chamável. Não há `eval` do texto gerado. Ela vira código revisado, com teste, ou é rejeitada.

## Constituição

Janus pode propor alteração. Não pode aplicá-la.

- Definição do que é resultado verificado.
- Regras do portão e classes de risco.
- Kill switch.
- Quem aprova L3 e L4.
- `learning_rate_cap` e a evidência mínima.
- O que é origem não confiável.

A voz, o aprendiz e a autoevolução leem a constituição. Nenhum deles a escreve.

## Estado interno que a voz pode citar

| Registro | O que é | Como muda |
|---|---|---|
| Temperamento | Parâmetros lentos: teto de passo, limiar de cautela | L1, com o mesmo `update` |
| Opinião | Afirmação com procedência, confiança e evidência | Revisável quando uma `Experience` verificada a contradiz |
| Emoção funcional | Urgência, cautela, curiosidade, como números que modulam limiar | L1. Não é frase de sentimento |
| Decisão | `ReflectionDecision` ou decisão do portão | O portão decide efeito. A reflexão decide a meta |

A voz só nomeia campo que o registro contém. Sem registro, não há temperamento, opinião nem emoção para declarar.

## Orçamento interno

Janus tem um orçamento configurado para trabalho interno: gravar meta, refletir, propor L1–L3, reler traço. Esse orçamento é visível para o Arthur. Esgotou, o ciclo interno para. Efeito externo não gasta esse orçamento. Efeito externo passa pelo portão.

## Fases

A ordem é a dependência. O calendário não está prometido.

| Fase | O que passa a existir | O que ainda não existe |
|---|---|---|
| A substrato | Loop, portão, traço, `Experience` com `outcome` vazio | Peso, meta ativa, habilidade |
| B metas | `Goal` e `ReflectionDecision`. Meta interna pode ficar `active` | Passo externo disparado pela meta |
| C aprendiz | `propose`, `update`, rollback, peso estável na troca de voz | Habilidade nova, ferramenta nova |
| D autoevolução | Proposta L1 e L2, ensaio no traço, rollback automático se o critério falha nos runs seguintes | Ferramenta nova chamável |
| E capacidade | Rascunho L3 visível, inerte até aceite | Allowlist alterada pelo próprio Janus |
| F autonomia graduada | Efeito externo reversível pode seguir quando o histórico e o limiar configurado concordam | Janus alterar o limiar da constituição |

Em cada fase o teste da anterior continua verde. Falhou, a fase nova não abre.

## Ciclo completo

1. Um sinal chega: evento, meta ativa ou `Experience` sem desfecho.
2. O aprendiz, quando existe, devolve `Proposal`. Antes da fase C, a voz propõe sozinha e o registro já guarda o lugar do `expected_value`.
3. O portão permite, nega ou pede.
4. Efeito permitido acontece. Efeito interno de meta não sai do processo.
5. O critério observa o ambiente. Verificou, preenche `outcome`. Não verificou, o campo continua vazio.
6. `update` roda. Recusou, o peso não muda e o motivo fica no traço.
7. Falha repetida do mesmo critério abre `EvolutionProposal`.
8. L1 e L2 aplicam dentro da classe. L3 e L4 esperam o Arthur.
9. Os runs seguintes medem o critério. Não cumpriu, L1 e L2 voltam sozinhos.
10. A voz pode narrar só o que esses registros mostram.
