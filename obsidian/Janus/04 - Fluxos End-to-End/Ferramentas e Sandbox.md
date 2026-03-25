---
tipo: fluxo
dominio: execucao
camada: end-to-end
fonte-de-verdade: codigo
status: ativo
---

# Ferramentas e Sandbox

## Objetivo
Cobrir o plano de execução de ferramentas do Janus.

## Responsabilidades
- Explicar catálogo, criação dinâmica e execução segura.
- Ligar tool executor, pending actions e sandbox.

## Entradas
- Solicitação do usuário.
- Metadados de ferramenta.
- Políticas de risco e permissão.

## Saídas
- Execução ou bloqueio controlado.
- Estatísticas de uso e trilha de aprovação.

## Dependências
- [[02 - Backend/Segurança e Infra]]
- [[02 - Backend/Autonomia e Workers]]

## Sequência
1. Frontend explora ou aciona ferramentas.
2. Backend lista ferramentas e permissões via `/tools`.
3. `ToolService` resolve metadados; `ToolExecutorService` coordena execução.
4. Ações sensíveis podem gerar pending actions e confirmação.
5. O sandbox protege execução Python/OS quando aplicável.

## Arquivos-fonte
- `backend/app/api/v1/endpoints/tools.py`
- `backend/app/services/tool_service.py`
- `backend/app/services/tool_executor_service.py`
- `backend/app/core/tools/*`
- `backend/app/core/infrastructure/python_sandbox.py`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Conversa e Chat]]
- [[04 - Fluxos End-to-End/Autonomia]]

## Riscos/Lacunas
- A superfície de tooling é poderosa e precisa de governança contextual, não só estática.
