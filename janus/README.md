# Janus Backend

Este diretório contém o código-fonte do backend do Janus (Python/FastAPI).

## Documentação

A documentação completa do projeto, incluindo arquitetura, configuração e guias de uso, encontra-se no **[README principal](../README.md)** na raiz do repositório.

## Setup Rápido (Backend)

```bash
cd janus
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Para mais detalhes sobre deploy com Docker e variáveis de ambiente, consulte a seção "Ambientes e Deploy" no README principal.
