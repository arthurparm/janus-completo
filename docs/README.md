# Documentação Janus — Índice Profissional

> **Objetivo**: consolidar uma documentação organizada, rastreável e científica, reduzindo a distância entre código e documentação.
> Este índice define uma taxonomia clara, estados de atualização e padrões de escrita.

## 1) Como navegar

### 1.1 Trilhas principais
- **Visão geral e onboarding**
  - `docs/Project-Structure.md`
  - `docs/Architecture.md`
  - `docs/Usage.md`

- **Configuração e operação**
  - `docs/Configuration.md`
  - `docs/Troubleshooting.md`
  - `docker-compose.yml`

- **Referência técnica**
  - `docs/Examples.md`
  - `docs/Release-Notes-1.0.0.md`

- **Documentação científica (nova trilha)**
  - `docs/Scientific-Appendix.md`

### 1.2 Documentos legados
Os manuais abaixo existem, mas estão **marcados como legados** e precisam ser revisados antes de uso:
- `docs/Janus-Manual.md`
- `docs/Janus-Manual-v2.md`
- `docs/Janus-Architecture-Report-2026.md`
- `docs/Janus-Roadmap-Review-2026.md`

## 2) Princípios de documentação

1. **Rastreabilidade**: todo bloco técnico deve apontar para código real (arquivo, função, ou endpoint).
2. **Estado explícito**: cada documento deve declarar data de revisão e status (Atualizado, Parcial, Legado).
3. **Separação de camadas**: conceitos, arquitetura, operação e referência não devem se misturar.
4. **Reprodutibilidade**: fluxos e experimentos devem ser reproduzíveis e versionados.

## 3) Estado e atualização

Para cada documento novo ou revisado, incluir um bloco como este no topo:

```
Status: Atualizado | Parcial | Legado
Última revisão: YYYY-MM-DD
Responsável: <nome/time>
Escopo: <o que cobre>
```

## 4) Padrão editorial

- **Tom**: profissional, técnico e objetivo.
- **Formato**: Markdown com seções numeradas e índice inicial.
- **Métrica de qualidade**: cada seção deve responder às perguntas **o que**, **por que**, **como**, **quando** e **limitações**.

## 5) Próximos passos sugeridos

1. **Atualizar o conteúdo crítico** em `Architecture`, `Configuration`, `Usage` com referências reais do código.
2. **Migrar o conteúdo de manuais legados** para documentos menores e rastreáveis.
3. **Criar páginas de ciência aplicada**, com metodologia e validação (ver `Scientific-Appendix.md`).

---

Para orientar a escrita e revisão, use o playbook em `docs/Documentation-Playbook.md`.
