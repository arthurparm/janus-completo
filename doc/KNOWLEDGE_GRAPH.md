# Esquema do Grafo de Conhecimento (Janus-KG)

Este documento define a estrutura de dados do Grafo de Conhecimento do Janus, que reside na Memória Semântica (
implementada com Neo4j). O objetivo deste grafo é armazenar conhecimento abstrato, generalizável e **canonizado**.

## Princípios de Design

1. **Abstração:** O grafo armazena padrões, fatos validados, e workflows, não detalhes de interações individuais.
2. **Conectividade:** O valor do grafo está nas relações. O esquema é projetado para revelar conexões entre tarefas,
   habilidades e aprendizados.
3. **Canonização:** Todas as entidades são normalizadas para uma forma canônica para garantir consistência e evitar
   duplicatas.
4. **Evolução:** Este esquema é um ponto de partida e será estendido à medida que o Janus desenvolve novas capacidades.

---

## Tipos de Nós (Nodes)

Os nós são as entidades primárias no grafo.

- `Entity`: Representa um conceito, pessoa, local, organização ou qualquer substantivo nomeado.
- `Skill`: Representa uma ferramenta ou capacidade que um agente pode executar.
- `Task`: Representa um objetivo ou um tipo de problema de forma abstrata.
- `Workflow`: Representa um plano de ação bem-sucedido e reutilizável para resolver uma `Task`.
- `Step`: Um passo individual e ordenado dentro de um `Workflow`.
- `Reflection`: Representa um aprendizado explícito, geralmente derivado da análise de uma falha.

---

## Tipos de Relacionamentos (Relationships)

**Apenas os seguintes tipos de relacionamento são permitidos no grafo.**

### Relacionamentos Estruturais e de Habilidade

- `HAS_PROPERTY`: Conecta uma `Entity` a outra que a descreve.
- `HAS_METADATA`: Conecta uma entidade aos seus metadados ou atributos.
- `IS_A_TYPE_OF`: Relacionamento de classificação (ex: `(Itanhaém) -[:IS_A_TYPE_OF]-> (Cidade)`).
- `IS_SYNONYM_OF`: Conecta uma entidade não-canônica à sua forma canônica.
- `ACHIEVES`: Conecta um `Workflow` à `Task` que ele é capaz de resolver.
- `HAS_STEP`: Conecta um `Workflow` aos seus `Step`s constituintes, de forma ordenada.
- `USES_SKILL`: Conecta um `Step` de um workflow à `Skill` que ele utiliza.
- `LEARNED_FROM`: Conecta um `Workflow` ou `Skill` a uma `Reflection`.

### Relacionamentos Semânticos e de Processo

- `RECEIVES_TASK`: Indica que um agente ou componente recebe uma tarefa.
- `AIMS_TO_DETECT`: Descreve o objetivo de uma análise ou monitoramento.
- `INVOLVES_DATA`: Conecta um processo a os dados que ele manipula.
- `PROCESSES`: Indica que uma entidade processa ou transforma outra.
- `CONFIGURED_WITH`: Descreve a configuração de um componente.
- `REPORTS`: Indica que um componente reporta um status ou resultado.
- `ORIGINATES_FROM`: Mostra a origem de um evento, dado ou erro.
- `PERFORMS_WITH_STATUS`: Descreve o resultado de uma ação.
- `CREATES`: Indica que uma entidade produz ou cria outra.
- `EXAMINES`: Descreve uma ação de análise ou inspeção.
- `IDENTIFIES`: Indica a descoberta ou identificação de uma entidade ou padrão.
- `PRODUCES`: Similar a `CREATES`, indica a saída ou resultado de um processo.

### Relacionamentos de Análise e Benefício

- `BENEFITS`: Descreve o benefício ou vantagem de uma ação ou entidade.
- `EMBODIES`: Indica que uma entidade representa ou encarna um conceito (ex:
  `(Workflow) -[:EMBODIES]-> (Princípio SOLID)`).
- `RECOMMENDS_AS_SOLUTION`: Conecta uma `Reflection` a uma `Skill` ou `Workflow` como uma solução sugerida.
- `IDENTIFIES_AS_ISSUE`: Conecta uma `Reflection` a uma `Entity` que foi identificada como um problema.

---

## Exemplo de Consulta (Cypher)

**Pergunta:** "Qual foi a causa raiz de uma falha recente e qual a solução recomendada?"

```cypher
MATCH (reflect:Reflection)-[:IDENTIFIES_AS_ISSUE]->(issue:Entity)
OPTIONAL MATCH (reflect)-[:RECOMMENDS_AS_SOLUTION]->(solution)
RETURN reflect.insight, issue.name, solution.name
ORDER BY reflect.createdAt DESC
LIMIT 5
```
