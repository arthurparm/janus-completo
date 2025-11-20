## Objetivo
Consolidar visibilidade por usuário, completar gates de publicação, integrar LoRA real, fortalecer A/B em runtime e entregar UI mínima para operar produtividade, A/B, deployment e recursos.

## Observabilidade e Grafana
- Adicionar painéis por usuário para produtividade (filtros por user_id, erro/sucesso, p95).
- Criar painéis de treino (jobs, latência, acurácia, consumo de GPU por usuário) e A/B (médias, p‑value, vencedor).
- Propagar métricas necessárias em workers e serviços (já iniciadas), validar escritas no Prometheus.

## Publicação Segura
- Implementar dataset sentinela e checagens de bias/segurança antes do publish.
- Enriquecer precheck (relatórios, thresholds configuráveis), registrar resultados no deployment.
- Automatizar rollback por degradação (monitorar métricas em tempo real; gatilhos).

## LoRA/Fine‑Tuning Real
- Integrar `transformers/peft` e PyTorch no trainer, com fallback quando ausentes.
- Salvar adapters/artefatos, versionar modelo e registrar metadados (dataset, hiperparâmetros, acurácia).
- Expor endpoints para iniciar e monitorar treinos LoRA por usuário.

## A/B em Runtime
- Ampliar assignment por segmento (ex.: perfil/projeto) e randomização estratificada.
- Coletar feedback explícito em rotas reais (UI), consolidar métricas e significância.
- Seleção de vencedor e integração automática com publish/stage.

## UI Mínima
- Páginas: produtividade (limites, OAuth, status de tarefas), A/B (vencedor/feedback), deployment (precheck/publish/rollback), recursos (orçamento/uso de GPU).
- Conectar serviço já estendido do frontend às novas telas.

## Orquestração e Tracing
- DSL de “task graph” com estado, reentrada e memória por tarefa.
- Tracing por passo (decisão/resultado) e painéis de pipeline (fila, sucesso/erro, tempos, retries).

## Testes
- Unit/integration para treino LoRA, A/B (assignment/feedback/winner), deployment (precheck/rollback), produtividade (fila/worker), recursos (orçamento/prioridade).

## Critérios de Aceitação
- Grafana mostra eventos/latência por usuário; painéis de treino, A/B e recursos operacionais.
- Publish bloqueia modelos abaixo de thresholds e com bias elevado; rollback automático em degradação.
- LoRA executa com artefatos versionados; fallback funciona sem libs.
- A/B coleta feedback, calcula vencedor e integra com publish/stage.
- UI permite operar limites/OAuth, visualizar tarefas, publicar/rollback, ver uso de GPU.

Confirma seguir com este plano para iniciar as implementações?