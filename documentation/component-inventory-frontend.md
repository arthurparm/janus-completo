# Component Inventory - Frontend (`frontend`)

## Resumo

Inventario focado em componentes reutilizaveis e blocos de feature.

- Componentes em `shared/components`: **30** arquivos (TS/HTML/SCSS)
- Features principais: `auth`, `conversations`, `home`, `tools`

## Biblioteca UI Compartilhada

### Base UI (`shared/components/ui`)

- `ui-button`, `ui-card`, `ui-table`, `ui-badge`
- `toast`/`toaster`
- `dialog` (`dialog-container`, `dialog-ref`, `dialog.service`)
- `spinner`, `icon`

### Componentes Funcionais

- `loading`, `loading-dialog`, `skeleton`
- `message-content`, `typing-indicator`
- `confirm-dialog`, `jarvis-avatar`
- `system-status`, `voice-orb`

## Core Layout

- `core/layout/header`
- `core/layout/sidebar`

## Padroes de Componente

- Separacao TS/HTML/SCSS por unidade.
- Servicos de UI para cross-cutting concerns (toast, dialog, markdown, UI service).
- Reuso elevado por `shared` + `core`.

## Oportunidades

- Consolidar naming conventions entre `ui-*` e componentes de dominio.
- Padronizar storybook ou catalogo visual para reduzir regressao em evolucao de UI.

---

_Gerado pelo workflow BMAD `document-project`_
