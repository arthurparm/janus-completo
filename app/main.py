from fastapi import FastAPI
from app.config import settings
from app.api.v1.router import api_router

# Inicializa a aplicação FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Janus: Uma IA arquiteta de software, modular e autônoma."
)

# Inclui o roteador da API v1 com um prefixo global
app.include_router(api_router, prefix="/api/v1")

@app.get("/", include_in_schema=False)
def read_root():
    """Redireciona para a documentação da API."""
    return {"message": f"Welcome to {settings.APP_NAME}. Docs available at /docs"}
