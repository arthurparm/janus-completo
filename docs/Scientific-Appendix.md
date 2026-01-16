# Apêndice Científico — Janus

Status: Parcial
Última revisão: 2025-01-01
Responsável: time de pesquisa
Escopo: metodologia científica aplicada ao desenvolvimento e validação do Janus.

---

## 1. Objetivo

Formalizar **hipóteses, métodos e validações** usadas na evolução do Janus, garantindo reprodutibilidade e transparência.

## 2. Hipóteses e perguntas de pesquisa

Exemplo de estrutura:
- **Hipótese H1**: o roteamento dinâmico de LLMs reduz custo total mantendo SLA.
- **Hipótese H2**: a memória híbrida melhora retenção de contexto sem aumentar latência média.

Para cada hipótese, registrar:
1. Motivação
2. Métrica alvo
3. Evidências esperadas

## 3. Metodologia

1. **Desenho experimental**
   - Baselines comparáveis.
   - Variáveis controladas.
2. **Dados**
   - Fonte, tamanho, versão e critérios de qualidade.
3. **Execução**
   - Ambiente, configuração e parâmetros.
4. **Coleta de métricas**
   - Latência, custo, precisão, taxa de erro, satisfação.

## 4. Métricas e validação

- **Métricas técnicas**: p95, p99, custo/tarefa, taxa de erro.
- **Métricas cognitivas**: fidelidade de resposta, coerência, alucinação.
- **Métricas operacionais**: sucesso de pipeline, estabilidade, MTTR.

## 5. Reprodutibilidade

- Scripts e seeds versionados.
- Registros de versão de modelos.
- Configurações de serviços externas registradas.

## 6. Limitações e viés

- Dependência de provedores externos.
- Variabilidade de modelos de LLM.
- Viés de dados e falta de cobertura.

## 7. Referências

- Códigos de experimento: `<caminho>`
- Dashboards: `<link>`
- Relatórios: `<link>`
