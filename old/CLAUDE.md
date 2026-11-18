@AGENTS.md

# Instruções específicas do Claude Code

## Idioma

- Responda sempre em português do Brasil.
- Preserve código, nomes técnicos, comandos, logs e identificadores em inglês.
- Documentação existente em português deve continuar em português.
- Não traduza nomes de classes, funções, arquivos, APIs ou bibliotecas.

## Forma de trabalho

- Execute a tarefa completa com autonomia.
- Não pare depois de apenas analisar ou apresentar um plano.
- Faça perguntas somente quando faltar uma informação que torne uma implementação correta impossível.
- Quando houver uma interpretação tecnicamente segura e reversível, assuma-a e prossiga.
- Não peça confirmação para correções locais, reversíveis e cobertas pelo escopo solicitado.
- Não declare uma tarefa concluída sem evidências verificáveis.

## Uso eficiente do contexto

- Leia primeiro os arquivos de instrução e os documentos diretamente relacionados à tarefa.
- Não leia o repositório inteiro indiscriminadamente.
- Use Glob e Grep para localizar candidatos antes de abrir arquivos completos.
- Leia somente os trechos necessários de arquivos grandes.
- Evite repetir conteúdo já presente no contexto.
- Não reproduza arquivos inteiros na resposta final.
- Resuma outputs extensos de comandos, preservando erros e evidências importantes.

## Ferramentas

- Prefira inicialmente as ferramentas nativas Read, Glob, Grep, Edit e Bash.
- Use Serena somente quando navegação semântica por símbolos trouxer uma vantagem objetiva.
- Não repita indefinidamente uma ferramenta que retornar parâmetros inválidos.
- Após duas falhas equivalentes de uma ferramenta, use uma alternativa mais simples.
- Não inicie subagentes para tarefas que possam ser resolvidas diretamente.
- Use no máximo um subagente por vez.

## Implementação

- Investigue a causa raiz antes de editar.
- Faça mudanças pequenas, coerentes e revisáveis.
- Preserve contratos públicos e limites arquiteturais.
- Não introduza workarounds quando a causa raiz puder ser corrigida.
- Não altere arquivos não relacionados apenas para "melhorar" o projeto.
- Não silencie testes, lint, type checking ou validações.
- Não remova testes válidos para fazer a suíte passar.
- Não use tipos inseguros, supressões ou casts para esconder erros sem justificativa técnica.

## Validação

- Execute primeiro os testes e verificações diretamente relacionados à alteração.
- Depois execute os quality gates relevantes definidos no AGENTS.md.
- Compare o estado final com o estado inicial.
- Verifique `git diff` antes de concluir.
- Informe claramente qualquer validação que não pôde ser executada.

## Git

- Não execute `git reset --hard`.
- Não execute `git clean -fd` ou variantes destrutivas.
- Não force push.
- Não faça commit ou push sem solicitação explícita.
- Não descarte alterações preexistentes do usuário.
- Diferencie alterações preexistentes das alterações realizadas nesta tarefa.

## Resposta final

- Seja direto.
- Informe o que foi alterado.
- Informe os testes e verificações executados.
- Informe riscos ou pendências reais.
- Não inclua explicações genéricas ou tutoriais não solicitados.
