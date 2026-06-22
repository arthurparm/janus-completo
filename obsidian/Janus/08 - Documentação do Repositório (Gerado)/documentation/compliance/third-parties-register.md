---
gerado: true
origem: "documentation/compliance/third-parties-register.md"
ultima_geracao: "2026-05-22T18:03:31.345032+00:00"
---

# Registro de Terceiros e Transferências de Dados (Internal-Only)

Classificação: internal-only  
Escopo: provedores habilitáveis via configuração (env) e integrações opcionais.

## Objetivo

Manter inventário rastreável de terceiros que podem processar dados no Janus e documentar transferências nacionais/internacionais.

## Registro (baseline)

| Terceiro | Finalidade | Dados potencialmente processados | Transferência | Observações |
|---|---|---|---|---|
| Provedores LLM (OpenAI/Gemini/DeepSeek/xAI/OpenRouter) | Inferência/geração | Conteúdo de prompts, contexto, metadados de uso | Internacional (depende do provedor/região) | Habilitado via env; revisar ToS/DPA e configurar minimização |
| Google OAuth / APIs Google (quando habilitado) | Autenticação/Produtividade | Identidade, tokens OAuth, dados de calendário/notas | Internacional (Google) | Exige consentimento e proteção de tokens |
| Firebase (quando habilitado) | Auth/infra opcional | Identidade, tokens, metadados | Internacional (Google) | Controlar escopo e retenção |
| Infra (Postgres/Qdrant/Neo4j/RabbitMQ/Redis) | Persistência e mensageria | Dados internos do sistema | Nacional/Interno (depende do deploy) | Operado internamente no ambiente corporativo |

## Revisão periódica

- Periodicidade recomendada: trimestral e a cada nova integração.
- Evidência: PR/commit atualizando este documento + atualização da matriz de rastreabilidade quando houver novos controles.

