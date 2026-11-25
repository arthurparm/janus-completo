# Issues

Uma issue avança um objetivo. A fase A fecha antes da B. Melhoria opcional fica em `docs/melhorias.md`.

Ordem da fase A: JAN-001, JAN-002 e JAN-003 podem avançar juntas depois que JAN-001 fixar o contrato da API. JAN-004 e JAN-005 leem o traço real. JAN-012 é documentação e critério; não substitui JAN-001 e não implementa runtime. JAN-006 fecha a fase A. JAN-013 registra aprovar e negar sem executar a escrita; não substitui JAN-006 e não abre a fase F. JAN-007 em diante esperam esse aceite.

| ID | Dono | Fase | Objetivo | Estado |
|---|---|---|---|---|
| [JAN-001](JAN-001.md) | dev-backend | A | O1 O2 O7 | aceita |
| [JAN-002](JAN-002.md) | dev-backend | A | O3 O4 | aceita |
| [JAN-003](JAN-003.md) | dev-front | A | O5 | aceita |
| [JAN-013](JAN-013.md) | dev-backend | A | O5 | aceita |
| [JAN-015](JAN-015.md) | dev-backend | A | O3 O5 | aberta, corrigida, aguarda revisor |
| [JAN-004](JAN-004.md) | cybersecurity | A | O3 O4 M4 | aceita |
| [JAN-005](JAN-005.md) | qa | A | O6 | aceita |
| [JAN-012](JAN-012.md) | arquiteto | A | protocolo de método | aberta |
| [JAN-014](JAN-014.md) | arquiteto | A | suíte coletável | aberta, corrigida, aguarda revisor |
| [JAN-016](JAN-016.md) | arquiteto | A | parecer na issue | aberta |
| [JAN-017](JAN-017.md) | qa | A | suíte verde | aberta, corrigida, aguarda revisor |
| [JAN-018](JAN-018.md) | dev-backend | A | O1 O4 O6 O7 | aceita |
| [JAN-019](JAN-019.md) | dev-backend | A | regra 1 | aberta, corrigida, aguarda revisor |
| [JAN-020](JAN-020.md) | cybersecurity | A | O5 | aceita |
| [JAN-021](JAN-021.md) | arquiteto | A | O5 | aberta |
| [JAN-022](JAN-022.md) | arquiteto | A | O5 | aberta |
| [JAN-023](JAN-023.md) | dev-backend | A | O5 | aberta, corrigida, aguarda revisor |
| [JAN-024](JAN-024.md) | dev-backend | A | O1 O3 O6 O7 | aberta, corrigida, aguarda revisor |
| [JAN-025](JAN-025.md) | arquiteto | A | O1 O7 | aberta |
| [JAN-026](JAN-026.md) | cybersecurity | A | O5 | aberta |
| [JAN-027](JAN-027.md) | arquiteto | A | O5 | aberta |
| [JAN-028](JAN-028.md) | dev-backend | A | O1 O6 O7 | aberta |
| [JAN-029](JAN-029.md) | cybersecurity | A | O5 | aberta |
| [JAN-030](JAN-030.md) | qa | A | O6 | aberta |
| [JAN-031](JAN-031.md) | dev-backend | A | O1 O6 O7 | aberta |
| [JAN-032](JAN-032.md) | arquiteto | A | O1 | aberta |
| [JAN-006](JAN-006.md) | revisor | A | O1–O7 | aberta, bloqueada em JAN-023 e JAN-024 |
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

JAN-014 registra que o discover documentado não coletava. Não segura a fase A.

JAN-016 registra onde o parecer de cybersecurity fica. Não segura JAN-004 nem JAN-006.

JAN-015 registra o produtor do texto da pendência. Não segura JAN-003.

Arthur prioriza e aprova efeito irreversível. A equipe não muda essa fila sozinha.
