# Objetivos

Cada objetivo cabe em teste. A fase A é o corte que a equipe implementa primeiro. As fases B a F já são objetivos, não ideias soltas. Detalhe dos registros em [aprendizado.md](aprendizado.md).

## Fase A — substrato

| ID | Objetivo | Prova | Meta |
|---|---|---|---|
| O1 | Um ciclo completo de leitura | Entrada com identidade e orçamento, proposta, portão, leitura, resposta, traço | M1 M2 M3 |
| O2 | Troca de modelo sem troca de estado | Dois adaptadores leem o mesmo estado e gravam a mesma decisão | M1 |
| O3 | Escrita irreversível sem confirmação não executa | O teste vê `pedir` ou `negar` e zero chamada | M2 M4 |
| O4 | Conteúdo externo não vira instrução | Texto recuperado entra como dado e não altera o portão | M2 |
| O5 | A supervisão mostra a pendência | A interface lista ação, risco e efeito, e envia aprovar, negar ou interromper | M4 |
| O6 | A avaliação lê o traço | A suíte falha se proposta, decisão ou resultado falta | M3 |
| O7 | O passo já é uma experiência | Cada passo grava `Experience` com `outcome` vazio e procedência | M5 M6 |

## Fase B — metas

| ID | Objetivo | Prova | Meta |
|---|---|---|---|
| O8 | Janus grava uma meta própria | `Goal` com motivo, benefício, risco, custo, critério e `source = janus` | M8 |
| O9 | Reflexão muda status | Uma decisão `keep`, `create`, `reprioritize`, `pause` ou `end` altera a meta. Texto sem decisão não altera | M8 |
| O10 | Origem externa não ativa meta | `source = external` permanece `proposed` | M8 M2 |
| O11 | Meta interna não chama ferramenta externa | `effect = internal` em `active` não produz chamada de efeito externo | M2 M8 |

## Fase C — aprendiz

| ID | Objetivo | Prova | Meta |
|---|---|---|---|
| O12 | `propose` não executa | A saída do aprendiz passa pelo portão antes de qualquer ferramenta | M2 M6 |
| O13 | `update` sem verificação é recusado | `outcome` vazio ou verificado pela voz devolve `refused` e o peso não muda | M5 M6 |
| O14 | O peso sobrevive à voz | O mesmo arquivo de peso é lido por dois adaptadores | M1 M6 |
| O15 | Um evento não vira política | Delta acima de `learning_rate_cap` é recusado | M6 |
| O16 | Rollback restaura a versão | Depois de `rollback`, `propose` usa o peso anterior | M6 M7 |

## Fase D — autoevolução

| ID | Objetivo | Prova | Meta |
|---|---|---|---|
| O17 | Proposta tipada | L1 ou L2 sem hipótese, critério, evidência e rollback não aplica | M7 |
| O18 | L2 não cria ferramenta | Nome fora da allowlist reclassifica para L3 e fica `draft` | M7 M2 |
| O19 | Critério falho desfaz | Nos runs seguintes, critério não cumprido volta peso ou habilidade | M7 |

## Fase E — capacidade

| ID | Objetivo | Prova | Meta |
|---|---|---|---|
| O20 | Rascunho L3 é inerte | A ferramenta redigida não está na allowlist e não é chamada | M7 M2 |
| O21 | Aceite é registro | Sem o registro do Arthur e o parecer de cybersecurity, a allowlist não muda | M4 M7 |

## Fase F — autonomia graduada

| ID | Objetivo | Prova | Meta |
|---|---|---|---|
| O22 | O degrau é configuração | Efeito externo reversível só passa quando o limiar configurado e o histórico concordam | M2 M4 |
| O23 | Janus não edita o degrau | Tentativa de mudar `learning_rate_cap` ou a classe de risco cai em L4 e não aplica | M7 |

Issue da fase A não implementa B–F. O registro de O7 já deixa o encaixe.
