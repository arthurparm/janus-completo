# app/api/v1/endpoints/learning.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core import data_harvester, neural_trainer

router = APIRouter()

class LearningResponse(BaseModel):
    message: str
    summary: str

@router.post(
    "/harvest",
    response_model=LearningResponse,
    summary="Inicia a coleta de dados de experiência para treino",
    tags=["Neural Learning"]
)
def trigger_harvesting():
    """
    Aciona o 'data_harvester' para recolher experiências da memória
    e prepará-las num ficheiro de dados para treino.
    """
    try:
        result = data_harvester.harvest_data_for_training()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/train",
    response_model=LearningResponse,
    summary="Inicia o processo de treino de um novo modelo neural",
    tags=["Neural Learning"]
)
def trigger_training():
    """
    Aciona o 'neural_trainer' para iniciar um processo de treino (simulado)
    utilizando os dados previamente coletados.
    """
    try:
        result = neural_trainer.start_training_process()
        if "Falha" in result["message"]:
            raise HTTPException(status_code=404, detail=result["summary"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))