# Plano de Remediação do Grafo `mypy`

## Objetivo

Congelar a linha de base conhecida do grafo completo de tipos e organizar a redução da dívida técnica por ondas pequenas, auditáveis e de baixo risco operacional.

## Linha de base congelada

- Data de referência da spec: `2026-08-03`
- Baseline operacional aceito para planejamento: `2.094 erros em 250 arquivos`
- Escopo: grafo completo `mypy` do backend
- Observação: os módulos focais alterados recentemente já passaram nos gates locais, mas o grafo completo ainda não está apto para gate global obrigatório

## Comando de revalidação da linha de base

Executar em ambiente Python compatível com `backend/pyproject.toml`:

```powershell
py -3.12 -m mypy "backend/app" --config-file "backend/pyproject.toml" --show-error-codes --pretty | Tee-Object -FilePath "outputs/qa/mypy-full-baseline.txt"
```

Resumo por arquivos com erro:

```powershell
rg -o "^[^:]+\.py" "outputs/qa/mypy-full-baseline.txt" | Sort-Object | Get-Unique | Measure-Object
```

## Agrupamento operacional por ondas

### Wave 0: Congelamento e triagem

Objetivo: impedir drift silencioso enquanto o total global ainda é alto.

- Registrar a baseline acima como referência canônica desta frente.
- Bloquear aumento do total global em branches de remediação.
- Exigir que módulos novos ou alterados mantenham `mypy` limpo no escopo local.

### Wave 1: Superfície de maior retorno operacional

Critério: módulos com maior impacto em autenticação, configuração, migração, observabilidade e tooling.

- `backend/app/config.py`
- `backend/app/core/security/`
- `backend/app/core/infrastructure/`
- `backend/app/services/db_migration_service.py`
- `tooling/`

Foco técnico:

- normalizar `Optional` e `dict[str, Any]` mal delimitados;
- fechar retornos implícitos `None`;
- tipar interfaces de serviços e repositórios usadas em gates operacionais;
- reduzir uso de `Any` em pontos de entrada.

Saída da wave:

- zero regressão no total global;
- redução mensurável do total em arquivos da wave;
- comandos de validação executados e anexados ao pacote de evidências.

### Wave 2: Serviços compartilhados do backend

Critério: domínios usados por múltiplos fluxos e com alta chance de espalhar erros de tipo.

- `backend/app/services/`
- `backend/app/repositories/`
- `backend/app/api/v1/endpoints/`

Foco técnico:

- contratos entre endpoint, service e repository;
- payloads opcionais;
- narrowing de tipos em fluxos assíncronos.

### Wave 3: Borda e contratos secundários

Critério: áreas com menor retorno imediato, mas ainda relevantes para o gate global.

- testes utilitários e scripts de suporte;
- módulos de domínio com baixa frequência de mudança;
- legados com alta densidade de `Any`.

## Matriz de priorização

| Grupo | Severidade operacional | Facilidade de correção | Ação |
|---|---|---:|---|
| Configuração, auth, migração, observabilidade | alta | média | atacar primeiro |
| Serviços/repositórios compartilhados | alta | média | atacar na wave 2 |
| Tooling operacional | média | alta | usar como ganho rápido |
| Testes, legados e utilitários periféricos | baixa a média | variável | atacar por lote após estabilizar núcleo |

## Critérios de aceite por wave

- Nenhum aumento do total global frente à baseline congelada.
- Todos os arquivos tocados na wave passam no recorte local de `mypy`.
- O pacote da wave inclui:
  - comando executado;
  - total global antes/depois;
  - lista de arquivos afetados;
  - riscos remanescentes.

## Comandos mínimos de validação por wave

Recorte local da wave:

```powershell
py -3.12 -m mypy "backend/app/config.py" "backend/app/core/security" "backend/app/core/infrastructure" "backend/app/services/db_migration_service.py" --config-file "backend/pyproject.toml"
```

Revalidação global após uma wave concluída:

```powershell
py -3.12 -m mypy "backend/app" --config-file "backend/pyproject.toml" --show-error-codes | Tee-Object -FilePath "outputs/qa/mypy-after-wave.txt"
```

## Riscos remanescentes

- O grafo completo continua acima do nível aceitável para gate global obrigatório.
- Corrigir o total de uma vez amplia demais o blast radius e aumenta chance de regressão funcional.
- Alguns grupos de erro podem exigir refatoração de contratos, não apenas anotações.
- Enquanto a wave 1 não for executada, a baseline segue apenas congelada e triada, não reduzida.

## Decisão operacional desta entrega

Esta entrega fecha somente:

- congelamento da baseline (`2.094/250`);
- agrupamento por domínio, severidade e facilidade;
- definição das ondas e dos comandos de validação.

Esta entrega não fecha:

- execução da primeira wave;
- revalidação pós-wave com novo total global.
