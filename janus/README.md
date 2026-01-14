# Janus Backend

Este é o módulo backend do Janus, construído com Python (FastAPI).

Para documentação completa, consulte o [README principal](../README.md).

## Instalação e Execução

### Pré-requisitos
- Python 3.11+
- Dependências listadas em `requirements.txt` (via `pip` ou Docker)

### Execução Local (sem Docker)
1. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
2. Configure as variáveis de ambiente (copie `.env.example` para `.env` se existir, ou configure manualmente conforme `app/config.py`).
3. Inicie o servidor:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

A API estará disponível em `http://localhost:8000`.
Docs (Swagger): `http://localhost:8000/docs`.

### Testes
Para rodar os testes:
```bash
pytest tests/
```
