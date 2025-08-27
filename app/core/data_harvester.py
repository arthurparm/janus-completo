# app/core/data_harvester.py
import json
import logging

from app.core.filesystem_manager import write_file
from app.core.memory_core import memory_core

logger = logging.getLogger(__name__)

TRAINING_DATA_FILE = "training_data.jsonl"


def harvest_data_for_training(limit: int = 100) -> dict:
    """
    Coleta experiências da memória episódica e as formata num ficheiro
    JSONL, adequado para o fine-tuning de modelos de linguagem.
    """
    logger.info(f"Iniciando a coleta de dados de {limit} experiências para treino.")

    experiences = memory_core.recall(query="experiência do agente", n_results=limit)

    if not experiences:
        summary = "Nenhuma experiência encontrada para a coleta."
        logger.warning(summary)
        return {"message": "Coleta de dados concluída.", "summary": summary}

    training_examples = []
    for exp in experiences:
        if exp.get('content') and exp.get('metadata'):
            prompt = f"Contexto: {json.dumps(exp['metadata'])}"
            completion = exp['content']
            training_examples.append({"prompt": prompt, "completion": completion})

    if not training_examples:
        summary = "Experiências recuperadas não continham dados suficientes para criar exemplos de treino."
        logger.warning(summary)
        return {"message": "Coleta de dados concluída.", "summary": summary}

    jsonl_content = "\n".join(json.dumps(ex) for ex in training_examples)
    write_status = write_file(TRAINING_DATA_FILE, jsonl_content)

    logger.info(write_status)

    summary = f"Coleta de dados concluída. {len(training_examples)} exemplos de treino foram guardados em '{TRAINING_DATA_FILE}'."
    logger.info(summary)

    return {"message": "Coleta de dados bem-sucedida.", "summary": summary}
