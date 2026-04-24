import json
import sys
import os

# Adiciona o diretório backend ao path para podermos importar app.main
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from fastapi.openapi.utils import get_openapi
from app.main import app

def main():
    print("Gerando OpenAPI spec offline...")
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
    )

    with open("outputs/qa/openapi.json", "w") as f:
        json.dump(openapi_schema, f, indent=2)
    print("OpenAPI spec salvo em outputs/qa/openapi.json")

if __name__ == "__main__":
    main()
