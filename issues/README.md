# Issues

Uma issue avança um objetivo. A fase A fecha antes da B. Melhoria opcional fica em `docs/melhorias.md`.

Ordem da fase A: JAN-001, JAN-002 e JAN-003 podem avançar juntas depois que JAN-001 fixar o contrato da API. JAN-004 e JAN-005 leem o traço real. JAN-012 é documentação e critério; não substitui JAN-001 e não implementa runtime. JAN-006 fecha a fase A. JAN-013 registra aprovar e negar sem executar a escrita; não substitui JAN-006 e não abre a fase F. JAN-007 em diante esperam esse aceite.

| ID | Dono | Fase | Objetivo | Estado |
|---|---|---|---|---|
| [JAN-001](JAN-001.md) | dev-backend | A | O1 O2 O7 | aceita |
| [JAN-002](JAN-002.md) | dev-backend | A | O3 O4 | aceita |
| [JAN-003](JAN-003.md) | dev-front | A | O5 | aberta |
| [JAN-013](JAN-013.md) | dev-backend | A | O5 | aberta, depois de JAN-002 |
| [JAN-004](JAN-004.md) | cybersecurity | A | O3 O4 M4 | aberta |
| [JAN-005](JAN-005.md) | qa | A | O6 | aberta |
| [JAN-012](JAN-012.md) | arquiteto | A | protocolo de método | aberta |
| [JAN-006](JAN-006.md) | revisor | A | O1–O7 | aberta |
| [JAN-007](JAN-007.md) | dev-backend | B | O8–O11 | aberta, depois de JAN-006 |
| [JAN-008](JAN-008.md) | dev-backend | C | O12–O16 | aberta, depois de JAN-007 |
| [JAN-009](JAN-009.md) | dev-backend | D | O17–O19 | aberta, depois de JAN-008 |
| [JAN-010](JAN-010.md) | cybersecurity | E | O20 O21 | aberta, depois de JAN-009 |
| [JAN-011](JAN-011.md) | arquiteto | F | O22 O23 | aberta, depois de JAN-010 |

## Definição de pronta

1. O critério desta issue tem teste.
2. QA mostra proposta, decisão e resultado no mesmo run id.
3. Cybersecurity não deixa furo aberto na classe de risco.
4. O revisor aceita.
5. Código novo tem no máximo 500 linhas, não usa `Any`, está na árvore de `docs/regras.md`, e comportamento repetido está em `src/janus/util/`.
6. Problema ou dúvida achados fora desta issue estão em outra issue, não neste diff.
7. A alteração do corte está num commit local. A mensagem cita a issue e o efeito.

Arthur prioriza e aprova efeito irreversível. A equipe não muda essa fila sozinha.
