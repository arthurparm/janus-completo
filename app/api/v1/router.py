from fastapi import APIRouter
# CORREÇÃO: Garante que o novo endpoint 'knowledge' seja importado
from .endpoints import system_status, knowledge

api_router = APIRouter()

# Roteador existente para o status do sistema
api_router.include_router(system_status.router, prefix="/system")

# CORREÇÃO: Adiciona o novo roteador do grafo de conhecimento
# Esta linha registra as rotas /knowledge/index e /knowledge/files na aplicação
api_router.include_router(knowledge.router, prefix="/knowledge")