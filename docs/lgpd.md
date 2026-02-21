# Relatorio de Conformidade LGPD

**Data:** 2026-03-01
**Responsavel:** Jules (AI Software Engineer)
**Status Geral:** 🟡 Em Adequacao

## 1. Principios Fundamentais

### Finalidade e Necessidade
O Janus coleta dados para:
- Execucao de tarefas autonomas (email, chat).
- Memoria episodica (vetorial) para contexto.
- Memoria semantica (grafo) para conhecimento.

### Minimizaçao
- **Gap:** Logs atuais armazenam conteudo completo de interacoes de email (`productivity_tools.py`), violando o principio de minimizacao.
- **Acao:** Sanitizar logs para remover PII nao essencial para debug.

## 2. Direitos do Titular

| Direito | Implementacao Atual | Status | Gap |
|---|---|---|---|
| **Acesso** | Via API (endpoints de get user/knowledge) | 🟡 Parcial | Nao ha uma "visao unica" exportavel para o usuario final (Takeout). |
| **Retificacao** | Edicao de perfil basico | 🟡 Parcial | Dificil corrigir memorias vetoriais ou nos do grafo incorretos. |
| **Exclusao** | `DataRetentionService.cleanup_user_artifacts` | 🟡 Parcial | Implementacao "best effort". Falhas silenciosas podem deixar residuos no Grafo/Vetor. Trigger manual. |
| **Portabilidade** | Inexistente | 🔴 Falha | Nao ha exportacao de dados em formato aberto (JSON/CSV) para o usuario. |
| **Consentimento** | API `/consents` | 🟡 Parcial | Backend existe, mas nao ha evidencia de UI de "Gestao de Consentimento" ou checagem obrigatoria antes de acoes sensiveis. |

## 3. Seguranca e Boas Praticas

### Retencao de Dados
- Politica de retencao nao esta formalizada em codigo (ex: cron job para limpar dados antigos).
- O servico de retencao depende de eventos ou chamadas explicitas.

### Vazamento de Dados
- Risco de vazamento de PII em logs de aplicacao (`janus.log`).
- Risco de vazamento via `X-User-Id` spoofing (ver `docs/security-review.md`).

## 4. Plano de Adequacao (Roadmap)

### Curto Prazo (P0 - Imediato)
1. **Logs:** Remover log de corpo de email e assunto em `productivity_tools.py`.
2. **Consentimento:** Garantir que ferramentas que enviam dados externos (email, web search) verifiquem consentimento explícito.

### Medio Prazo (P1)
1. **Retencao Automatica:** Criar job agendado (Celery/Arq) para expurgar dados de usuarios inativos ou revogados apos X dias.
2. **Relatorio de Transparencia:** Endpoint que resume quais dados o Janus tem sobre o usuario.

### Longo Prazo (P2)
1. **Data Export:** Funcionalidade de "Download my Data".
2. **Memory Editing:** Interface para usuario visualizar e esquecer memorias especificas (Direito ao Esquecimento Granular).
