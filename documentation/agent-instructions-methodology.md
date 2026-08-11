# Metodologia de instruções para agentes

## Objetivo

Este documento registra como o Janus projeta e mantém arquivos `AGENTS.md`. É uma metodologia interna derivada de especificações oficiais e evidência empírica; não é um padrão universal publicado.

O objetivo é maximizar aderência com o menor custo de contexto: cada instrução deve mudar uma decisão relevante do agente, no escopo correto, sem repetir aquilo que código, tipos, lint, CI ou documentação já tornam evidente.

## Método MESA

### 1. Mínimo

Inclua somente comportamento estável, acionável e não inferível com segurança a partir do repositório. Exclua tutoriais, inventários extensos, explicações de produto, regras puramente estilísticas já automatizadas e comandos que não se aplicam à subárvore inteira.

Pergunta de admissão: **se esta linha for removida, um agente competente tem chance material de tomar uma decisão errada?** Se não, remova ou mova para documentação.

### 2. Escopo

Mantenha na raiz apenas regras universais. Coloque diferenças reais em arquivos aninhados, próximos ao código governado. Uma regra tem um único proprietário; arquivos filhos complementam ou especializam a raiz, sem copiá-la.

Estrutura do Janus:

```text
AGENTS.md                 regras universais e roteamento
backend/AGENTS.md         FastAPI, domínio, persistência e QA Python
frontend/AGENTS.md        Angular, integração e validação visual
documentation/*.md        explicações, mapas e playbooks sob demanda
```

### 3. Sinal executável

Escreva instruções como decisões observáveis: entrypoint, limite arquitetural, proibição com motivo, comando válido, contrato a testar ou condição de parada. Evite adjetivos sem critério, como “robusto”, “completo” ou “alta qualidade”, desacompanhados de evidência verificável.

Cada regra operacional deve responder ao menos uma pergunta:

- Onde começar?
- Qual limite não pode ser atravessado?
- Qual comportamento deve permanecer equivalente?
- Como provar que a mudança funciona?
- Quando é obrigatório parar e pedir autorização?

### 4. Auditoria

Revise instruções como código:

1. confirme que links, caminhos e comandos existem;
2. procure duplicação e contradição entre raiz e filhos;
3. confirme que regras específicas estão na menor subárvore aplicável;
4. remova fatos voláteis, resultados históricos e regras absorvidas por automação;
5. execute um teste de descoberta a partir da raiz e de cada subdiretório;
6. registre no diff o motivo de cada nova instrução.

## Critérios mensuráveis do Janus

Estes limites são orçamentos internos, não limites da especificação:

- raiz: alvo de até 120 linhas e 8 KiB;
- arquivo aninhado: alvo de até 100 linhas e 8 KiB;
- cadeia raiz + arquivo local: abaixo de 16 KiB;
- zero cópia de configuração de formatter/linter;
- zero comando sem arquivo de configuração, script ou package correspondente;
- zero regra de domínio duplicada entre arquivos de instrução.

Exceder um orçamento exige uma justificativa baseada em risco ou em comportamento não inferível. O limite técnico padrão do Codex para a cadeia descoberta é 32 KiB, mas operar muito abaixo dele reduz truncamento e competição por contexto.

## Base técnica

- A documentação oficial do Codex define descoberta hierárquica, concatenação da raiz até o diretório atual, precedência do arquivo mais próximo e limite combinado padrão de 32 KiB. Ela recomenda regras de revisão concisas e reserva formatação/lint para CI: [Custom instructions with AGENTS.md](https://developers.openai.com/codex/guides/agents-md).
- O guia oficial de introdução ao Codex descreve `AGENTS.md` como local para navegação do repositório, comandos de teste e práticas do projeto; ambientes configurados, testes confiáveis e documentação clara melhoram o desempenho: [Introducing Codex](https://openai.com/index/introducing-codex/).
- Um estudo controlado com repositórios reais encontrou aumento de custo e passos quando arquivos de contexto acrescentavam requisitos desnecessários; a recomendação dos autores é registrar requisitos mínimos, especialmente os fornecidos por mantenedores: [Evaluating AGENTS.md](https://arxiv.org/abs/2602.11988).
- Um estudo de 100 repositórios catalogou como problemas frequentes a repetição de regras de lint, excesso de contexto, vazamento de habilidades e instruções conflitantes: [Configuration Smells in AGENTS.md Files](https://arxiv.org/abs/2606.15828).

## Regra de manutenção

Nova instrução entra no `AGENTS.md` somente quando for recorrente, estável, não inferível, pertencente ao escopo e verificável. Conhecimento explicativo vai para documentação; procedimento especializado vai para tooling/playbook; regra mecânica vai para lint, tipo, teste ou CI.
