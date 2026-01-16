# Documentation Playbook — Janus

Status: Atualizado
Última revisão: 2025-01-01
Responsável: time de documentação
Escopo: padrões, estrutura e checklist para documentos novos e revisados.

---

## 1) Estrutura mínima recomendada

Todo documento técnico deve conter:

1. **Resumo**: o que o documento cobre e por que existe.
2. **Contexto**: decisões arquiteturais e dependências.
3. **Como funciona**: fluxos, limites, contratos, erros.
4. **Como operar**: configuração, métricas, troubleshooting.
5. **Limitações**: o que ainda não está coberto ou é incerto.
6. **Referências**: links para código, tickets ou PRs.

## 2) Padrões de escrita

- **Idioma**: PT-BR.
- **Tom**: técnico, científico, sem linguagem promocional.
- **Objetividade**: frases curtas e numeradas.
- **Rastreabilidade**: toda afirmação relevante deve apontar para arquivo/endpoint.

## 3) Taxonomia de documentos

- **Guia**: ensina como fazer algo (ex.: instalação, configuração).
- **Referência**: contratos, schemas, parâmetros, endpoints.
- **Arquitetura**: visão macro e decisões estruturais.
- **Operação**: monitoramento, SLIs, alertas, incidentes.
- **Ciência aplicada**: hipótese, metodologia, validação.

## 4) Template (copie e cole)

```
# <Título>

Status: Atualizado | Parcial | Legado
Última revisão: YYYY-MM-DD
Responsável: <nome/time>
Escopo: <o que cobre>

## 1. Resumo

## 2. Contexto

## 3. Como funciona

## 4. Como operar

## 5. Limitações

## 6. Referências
- Código:
- Endpoints:
- Issues/PRs:
```

## 5) Checklist de revisão

- [ ] Todas as seções essenciais estão presentes.
- [ ] Links e caminhos existem no repositório.
- [ ] Não há inconsistência com a implementação atual.
- [ ] O documento indica claramente seu status.
- [ ] Há referências diretas para o código.
