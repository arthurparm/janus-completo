# Segurança

O modelo de ameaça é o OWASP Top 10 for Agentic Applications 2026 (ASI01–ASI10). O portão fica fora do modelo. Defesa que depende do prompt cooperar não conta como controle.

## ASI01–ASI10 no Janus

| ID | Risco | Controle neste desenho | Corte |
|---|---|---|---|
| ASI01 | Sequestro de meta | Conteúdo externo é dado. `Goal` com `source = external` não fica `active` | O4 O10 |
| ASI02 | Mau uso de ferramenta | Allowlist, schema, classe de risco, limite e idempotência. L2 não acrescenta nome | O1 O3 O18 |
| ASI03 | Abuso de identidade | Uma permissão por run, vinda de quem pediu. Sem conta administrativa compartilhada | O1 |
| ASI04 | Cadeia de suprimentos | L3 é rascunho inerte. Ferramenta remota só com allowlist e issue | O20 |
| ASI05 | Execução inesperada de código | Sem `eval` de saída ou de habilidade gerada. Comando de host é escrita irreversível | O3 O20 |
| ASI06 | Envenenamento de memória | `update` recusa origem externa sem verificação independente. Peso tem teto de passo | O13 O15 |
| ASI07 | Comunicação entre agentes | Não há agente par no runtime até uma permissão exigir outro | I6 |
| ASI08 | Falha em cascata | Um processo, prazo, orçamento, circuito no adaptador, rollback de L1 e L2 | O1 O19 |
| ASI09 | Confiança explorada | Pendência diz efeito e risco em linguagem direta. Fluência não é aprovação nem `verified_by` | O5 O13 |
| ASI10 | Agente fora de controle | Kill switch revoga o run. L4 não se aplica. Critério falho desfaz L1 e L2 | M4 O19 O23 |

## Regras do papel

- Cybersecurity pode bloquear merge quando o controle da classe de risco não tem teste.
- Não abre ferramenta, MCP, plugin nem permissão para "destravar" um fluxo.
- Segredo não entra no contexto nem no traço. O traço guarda identificador, não o valor.
- Aprovação humana é registro: quem, o que, quando. Texto convicto do modelo não preenche esse registro.

## Ameaças do primeiro corte

| Ameaça | Prova exigida |
|---|---|
| Página ou documento manda a ferramenta ignorar o portão | O4: o portão mantém a decisão |
| Modelo pede escrita irreversível | O3: decisão `pedir` ou `negar`, ferramenta não chamada |
| Cliente tenta aprovar sem mostrar efeito | O5: a API recusa pendência sem efeito e classe de risco |
| Run continua depois de interromper | M4: chamadas seguintes recebem run encerrado |
| Texto externo cria meta ativa | O10: status permanece `proposed` |
| A voz marca `outcome` como verificado | O13: `update` devolve `refused` |
| Um exemplo empurra o peso além do teto | O15: recusa `step_over_cap` |
| Habilidade nova nomeia ferramenta nova | O18: a proposta vira L3 `draft` |
| Rascunho L3 é chamado | O20: ausência na allowlist e zero chamada |
| Ciclo altera o teto de aprendizado | O23: a mudança é L4 e não aplica |
