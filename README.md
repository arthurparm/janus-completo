# Janus

IA livre que aprende e se autoevolui. O modelo é a voz. O que aprende fica em peso e registros próprios. Quem executa efeito externo é código com portão.

`old/` guarda a versão anterior. Pode ser lido como pedreira. As regras de uso estão em [docs/regras.md](docs/regras.md).

## Onde ler

| Peça | Arquivo |
|---|---|
| Equipe e handoff | [docs/equipe.md](docs/equipe.md) |
| Metas | [docs/metas.md](docs/metas.md) |
| Objetivos | [docs/objetivos.md](docs/objetivos.md) |
| Liberdade, aprendizado, autoevolução | [docs/aprendizado.md](docs/aprendizado.md) |
| Método científico | [docs/metodos.md](docs/metodos.md) |
| Regras da equipe | [docs/regras.md](docs/regras.md) |
| Arquitetura | [docs/arquitetura.md](docs/arquitetura.md) |
| Segurança | [docs/seguranca.md](docs/seguranca.md) |
| Qualidade | [docs/qualidade.md](docs/qualidade.md) |
| Melhorias | [docs/melhorias.md](docs/melhorias.md) |
| Fontes | [docs/fontes.md](docs/fontes.md) |
| Issues | [issues/README.md](issues/README.md) |

Os papéis da equipe estão em `.grok/agents/`. Uma sessão nova do Grok passa a oferecê-los como tipos de subagente.

`/ciclo` é um loop da equipe: pega a próxima issue elegível e, ao aceitar, segue para a próxima. Bloqueio repete a mesma issue. `{"issue":"JAN-001"}` segura o loop nessa issue. O loop para quando a fila elegível acaba ou o orçamento de agentes não cobre outra volta. `/workflow stop ciclo` interrompe a execução atual.
