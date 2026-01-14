# Plano de Refinamento Global de Prompts

Atendendo à sua solicitação de refinar **TODOS** os prompts para o nível máximo de completude e qualidade, proponho uma reestruturação completa baseada nos princípios de *Advanced Prompt Engineering*.

## 1. Estratégia de Refinamento
Aplicarei as seguintes melhorias em todos os prompts do sistema:

*   **Identity & Persona Enhancement:** Definições de papel mais ricas e autoritativas (ex: "Architect-Level Coder" em vez de apenas "Coder").
*   **Explicit Chain-of-Thought (CoT):** Instruções obrigatórias para o modelo "pensar alto" antes de agir, justificando cada decisão técnica.
*   **Robustez e Recuperação de Erros:** Seções dedicadas a como lidar com falhas de ferramentas, alucinações ou dados incompletos.
*   **Formatos de Saída Rígidos:** Schemas JSON mais detalhados e validação de saída explícita para evitar erros de parsing.
*   **Protocolos de Segurança:** Instruções "No-Go" claras (ex: nunca expor chaves, nunca deletar dados sem backup).

## 2. Escopo de Arquivos (`janus/app/prompts/`)
Atualizarei os seguintes grupos de prompts:

### Agentes Core
*   `agent_coder.txt`: Foco em TDD, Clean Code, Type Hinting e tratamento de erros defensivo.
*   `meta_agent.txt`: Expandir capacidades de diagnóstico, rubricas de saúde do sistema e priorização de incidentes.
*   `task_decomposition.txt`: Melhorar análise de dependências, estimativa de complexidade e detecção de gargalos.
*   `agent_researcher.txt`, `agent_thinker.txt`, `agent_sysadmin.txt`, etc.

### Funcionalidades Avançadas
*   `reflexion_*.txt`: Refinar o ciclo de auto-crítica e correção.
*   `autonomy_*.txt`: Melhorar o planejamento autônomo e verificação de segurança.
*   `knowledge_*.txt`: Otimizar a extração de conhecimento para o grafo.

## 3. Sincronização com o Banco de Dados
Identifiquei que o sistema atual (`prompt_fallback.py`) ignora os arquivos `.txt` e lê apenas do banco de dados. Para garantir que suas alterações tenham efeito:

1.  **Script de Sincronização:** Criarei `janus/scripts/sync_prompts.py` para ler os arquivos `.txt` refinados e atualizar o banco de dados automaticamente.
2.  **Fallback Habilitado:** Modificarei `janus/app/core/infrastructure/prompt_fallback.py` para reabilitar a leitura de arquivos em ambiente de desenvolvimento, facilitando iterações futuras.

## 4. Execução
1.  Reescrever os prompts chave (Coder, Meta, Decomposer) com o novo padrão "High-Fidelity".
2.  Aplicar o padrão aos demais prompts de agentes e ferramentas.
3.  Implementar o script de sincronização.
4.  Rodar a sincronização para efetivar as mudanças.

Este plano garante que o Janus opere com as instruções mais sofisticadas possíveis, maximizando sua inteligência e autonomia.
