# Equipe

Seis papéis, um fluxo, artefatos tipados. A especialização existe para separar permissão e responsabilidade. O runtime do Janus continua sendo um agente que aprende. Esta equipe constrói o produto. Ela não é o produto.

Estratégia de base: papéis com entrada e saída definidas, pessoa accountable no fim, e agentes só onde a fronteira de permissão muda. Fontes em [fontes.md](fontes.md).

## Base técnica

Cada papel é especialista no runtime de IA. Cargo genérico de software não basta. O método, o que entra e o que fica de fora estão em [especialistas.md](especialistas.md). O handoff desta página não muda.

## Papéis

| Papel | Entrada | Saída | Falha se faltar |
|---|---|---|---|
| Arquiteto | Issue e metas | Fronteira, invariante, alternativa rejeitada | Decisão de arquitetura dentro do diff |
| Dev backend | Desenho aceito | Runtime, portão, estado, traço, API, teste do módulo | Nada executa |
| Dev front | Contrato da API | Cliente que mostra o que o portão já decidiu | A tela passa a autorizar sozinha |
| Cybersecurity | Diff e classe de risco | Controles cobertos e furos | Vulnerabilidade entra calada |
| QA | Diff e objetivo | Prova de trajetória | Teste que passa sem verificar o comportamento |
| Revisor | Issue, diff e provas | Aceite ou lista de bloqueios | Escopo cresce no review |

## Fluxo de uma issue

1. A issue liga uma meta, um objetivo e um critério de pronto.
2. O arquiteto confirma que a issue cabe nos invariantes. Se a fronteira mudar, o desenho muda antes do código.
3. Backend e front implementam só o critério. Trabalham em paralelo quando o contrato da API já está na issue.
4. QA prova a trajetória no traço.
5. Cybersecurity verifica o controle da classe de risco.
6. O revisor lê issue, diff e provas. Aceita ou devolve com bloqueio.
7. Arthur prioriza a próxima issue e aprova efeito irreversível.

## Comando

`/ciclo` é um loop. Cada volta segue esta ordem: descobrir a próxima issue elegível, arquiteto, dono da issue, QA, cybersecurity, revisor. Quem altera arquivo do corte cria o commit local no mesmo turno, pela regra 7 de `docs/regras.md`. Aceite grava `Estado: aceita`, commita o que ainda estiver solto desse corte, e a volta seguinte pega a próxima elegível. Bloqueio repete a mesma issue, com o motivo, até o revisor aceitar. A issue pedida em `{"issue":"JAN-001"}` segura o loop nela até o aceite ou até o arquiteto barrar a fronteira. O loop para quando não há issue elegível ou quando o orçamento de agentes não cobre outra volta. `/workflow stop ciclo` interrompe a execução atual.

## Regras de mão

- Um papel não cumpre o trabalho de outro para "adiantar".
- `old/` pode ser lido. O uso segue `docs/regras.md`. Copiar arquivo não entra.
- Prompt não substitui portão, teste nem revisão.
- O revisor é o último leitor. Estilo sem efeito no critério não reabre a issue.
