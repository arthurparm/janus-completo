# Sprint 9: Gênese Neural - Infraestrutura para Aprendizagem Autônoma

## 📋 Visão Geral

A Sprint 9 estabelece infraestrutura completa para coleta de dados de experiências e treinamento autônomo de modelos de
machine learning. O sistema permite ao Janus aprender continuamente a partir de suas próprias interações, criando
modelos especializados.

## 🎯 Componentes Implementados

### 1. **Data Harvester** (`app/core/data_harvester.py`) ✅

Worker que coleta dados de interações para treino:

- Coleta experiências da memória episódica
- Deduplicação com LRU cache
- Backpressure e rate limiting
- Múltiplas fontes de dados (connectors)
- Métricas Prometheus completas

### 2. **Neural Training System** (`app/core/neural_training_system.py`) ✅

Sistema completo de treinamento autônomo:

**Componentes:**

- `DatasetPreparator`: Prepara dados para diferentes tipos de modelos
- `NeuralTrainer`: Gerencia ciclo de treino completo
- Suporte a múltiplos tipos de modelo:
    - LLM Fine-tuning
    - Classificadores
    - Preditores
    - Embedders

**Fluxo de Treinamento:**

```
1. Carrega experiências da memória episódica
2. Prepara dataset (formato específico por tipo)
3. Treina modelo
4. Valida performance
5. Salva modelo treinado
6. Memoriza resultado
```

### 3. **Tipos de Modelos Suportados**

- **LLM_FINETUNING**: Fine-tune de LLMs existentes
- **CLASSIFIER**: Classificação de intenções/categorias
- **PREDICTOR**: Predição de próximas ações
- **EMBEDDER**: Embeddings customizados

### 4. **Métricas Prometheus**

```python
neural_training_jobs_total{model_type, outcome}
neural_training_latency_seconds
neural_model_accuracy{model_name, model_version}
neural_training_examples_count
```

## 🏆 Status: ✅ SPRINT 9 COMPLETA

O sistema agora possui capacidade de aprendizagem autônoma, coletando dados de experiências e treinando modelos
especializados continuamente.

**Diferencial da Sprint 9:**
> Transforma o Janus de um sistema que usa modelos fixos para um sistema que evolui seus próprios modelos através de
> aprendizado contínuo.
