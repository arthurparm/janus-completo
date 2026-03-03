# Demo Agentic Flow (Fluxo Oficial)

## Objetivo
Demonstrar uma fatia vertical completa e estável do Janus:
- chat com streaming
- resposta com contexto/citações (ou estado explícito sem citações)
- confirmação obrigatória para ação de risco
- aprovação/rejeição com feedback visível na UI

## Persona da demo
- Operador técnico (produto/engenharia)
- Usa a interface web do Janus
- Precisa entender o que o agente está fazendo sem abrir logs

## Fluxo principal congelado
1. Operador abre `/conversations` e inicia uma conversa.
2. Envia uma solicitação com potencial de ação (ex.: deploy/alteração sensível).
3. Janus processa a solicitação e mostra status cognitivo/streaming.
4. Se houver risco, Janus retorna payload estruturado de confirmação e (quando aplicável) `pending_action_id`.
5. UI exibe card de confirmação com motivo e botões `Aprovar` / `Rejeitar`.
6. Operador escolhe aprovar ou rejeitar.
7. UI mostra o resultado da decisão e o estado do chat é atualizado.
8. Resposta exibe citações ou mostra `citation_status` explicando ausência de fonte rastreável.

## Estados visuais esperados
- Conectando stream
- Streaming de resposta
- Baixa confiança (quando aplicável)
- Aguardando confirmação
- Concluído
- Erro (com mensagem legível)

## O que acontece em caso de erro
- Erros HTTP/SSE de chat devem ter código canônico
- Frontend mostra erro legível e estado visual de falha
- O fluxo não depende de inspeção de logs para diagnóstico básico

## Critérios de sucesso
- Usuário consegue completar a demo ponta a ponta sem ambiguidade
- Ações de risco não executam sem confirmação
- Citações têm estado explícito (`present` / `missing_required` / etc.)
- Um teste E2E reproduz o fluxo principal

## Fora de escopo
- Redesign completo de todas as telas
- Generalização de confirmação para todos os subsistemas
- Cobertura E2E de todas as features de chat/memória/autonomia
- Quebra de compatibilidade do SSE/REST atuais

## Caminho de confirmação adotado
- Demo principal usa **SQL pending actions** (`/api/v1/pending_actions/action/{id}/approve|reject`)
- Fluxo LangGraph por `thread_id` permanece suportado, mas não é o caminho oficial da demo

