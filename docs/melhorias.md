# Melhorias

Aprendizado e autoevolução não estão nesta lista. São metas M6 e M7, com fases B a F em [objetivos.md](objetivos.md) e [aprendizado.md](aprendizado.md).

Aqui ficam acréscimos que não bloqueiam essa trajetória. Cada um vira issue só com objetivo novo e controle. Nenhum está autorizado agora.

| ID | Melhoria | Condição para abrir |
|---|---|---|
| I1 | Fato semântico com campos nomeados, retenção e apagamento | M5 já recusa fato sem fonte. O fato não vira `verified_by` |
| I2 | Traço exportável no formato GenAI do OpenTelemetry, atrás de um wrapper | O6 está verde. O wrapper é a única face do formato |
| I3 | Ferramenta remota com allowlist, pin e interruptor | ASI04 tem teste. L3 continua inerte até o aceite |
| I4 | Juiz por modelo ao lado da avaliação de trajetória | O6 e O13 continuam obrigatórios. O juiz não libera sozinho |
| I5 | Substituir o aprendiz linear por outro modelo de peso | O12–O16 verdes. A interface `propose` / `update` / `rollback` permanece |
| I6 | Vários agentes no runtime | Uma permissão não cabe no mesmo portão. Cada um tem identidade própria |

## Não é melhoria

- Copiar arquivo de `old/` porque ele já existia. Ler e reescrever, sob `docs/regras.md`, pode.
- Deixar a voz declarar aprendizado sem `UpdateResult`.
- Aplicar L4 por dentro do ciclo.
- Tratar geração de ferramenta como execução. L3 é rascunho até review.
