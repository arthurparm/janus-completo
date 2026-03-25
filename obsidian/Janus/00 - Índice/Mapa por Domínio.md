---
tipo: indice
dominio: sistema
camada: navegacao
fonte-de-verdade: codigo
status: ativo
---

# Mapa por Domínio

## Objetivo
Quebrar o sistema em bounded contexts úteis para leitura e manutenção.

## Responsabilidades
- Evitar leitura por arquivo.
- Direcionar a análise por responsabilidade operacional.

## Entradas
- Módulos em `backend/app`.
- Features em `frontend/src/app`.

## Saídas
- Navegação temática do vault.

## Dependências
- [[00 - Índice/Home]]
- [[02 - Backend/API por Bounded Context]]
- [[03 - Frontend/Features e Experiência]]

## Domínios
- Composição e boot: [[02 - Backend/Kernel e Startup]]
- Chat e interação: [[04 - Fluxos End-to-End/Conversa e Chat]]
- Autonomia e execução: [[02 - Backend/Autonomia e Workers]]
- Conhecimento, memória e RAG: [[02 - Backend/Memória Conhecimento e RAG]]
- Observabilidade e saúde: [[04 - Fluxos End-to-End/Observabilidade]]
- Segurança, auth e guardrails: [[02 - Backend/Segurança e Infra]], [[04 - Fluxos End-to-End/Login e Identidade]]
- UI, navegação e integração: [[03 - Frontend/Shell e Navegação]], [[03 - Frontend/Serviços de Integração]]
- Operação e runtime: [[05 - Infra e Operação/PC1 PC2 e Docker]]

## Arquivos-fonte
- `backend/app/api/v1/router.py`
- `backend/app/services/*.py`
- `backend/app/core/*`
- `frontend/src/app/features/*`

## Fluxos relacionados
- [[00 - Índice/Mapa por Fluxos Críticos]]

## Riscos/Lacunas
- Alguns domínios se sobrepõem porque o kernel centraliza muitas dependências.
