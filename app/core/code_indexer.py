import os
import logging

from app.db.graph import graph_db

logger = logging.getLogger(__name__)

# O diretório a ser escaneado dentro do container
CODEBASE_DIR = "/app"

def index_codebase() -> dict:
    """
    Varre o diretório da aplicação, encontra arquivos .py e os adiciona ao grafo.
    """
    logger.info(f"Iniciando varredura da base de código em '{CODEBASE_DIR}'...")
    file_count = 0
    for root, _, files in os.walk(CODEBASE_DIR):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                try:
                    # Usa MERGE para evitar criar nós duplicados
                    graph_db.query(
                        "MERGE (f:File {path: $path})",
                        params={"path": file_path}
                    )
                    file_count += 1
                except Exception as e:
                    logger.error(f"Falha ao indexar o arquivo {file_path}: {e}")

    summary = f"Varredura concluída. {file_count} arquivos .py foram indexados/atualizados no grafo."
    logger.info(summary)
    return {"message": "Indexação da base de código concluída.", "files_indexed": file_count}
