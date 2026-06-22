---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/code_analysis_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# code_analysis_service

## Arquivos-fonte
- `backend/app/services/code_analysis_service.py`

## Fluxos de uso (chamadores)
- `backend/app/repositories/knowledge_repository.py`
- `backend/app/services/knowledge_service.py`

## Símbolos
- class: `CodeParser`
  - Um NodeVisitor que extrai funções, classes e chamadas de um arquivo Python.
- method: `CodeParser.__init__(self, file_path: str)`
- method: `CodeParser._qualify_name(self, name: str)` -> `str`
- method: `CodeParser._attribute_to_name(self, node: ast.AST)` -> `str | None`
- method: `CodeParser._visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef)`
- method: `CodeParser.visit_ClassDef(self, node: ast.ClassDef)`
- method: `CodeParser.visit_FunctionDef(self, node: ast.FunctionDef)`
- method: `CodeParser.visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef)`
- method: `CodeParser.visit_Call(self, node: ast.Call)`
- class: `CodeAnalysisService`
  - Serviço responsável por analisar arquivos de código-fonte.
Sua única responsabilidade é entender e extrair informações do código.
- method: `CodeAnalysisService.parse_python_file(self, file_path: str)` -> `CodeParser | None`
  - Lê e analisa um único arquivo Python, retornando o objeto parser.
- method: `CodeAnalysisService.find_python_files(self, directory: str)` -> `list[str]`
  - Encontra todos os arquivos .py em um diretório.

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
