# Plano de Modernização e Evolução do Frontend Janus V1

Com base na auditoria realizada, este plano visa transformar o frontend atual em uma aplicação de classe mundial, cobrindo as lacunas identificadas e implementando inovações de UI/UX.

## 1. 🏗️ Arquitetura & Infraestrutura (Excelência Técnica)

### 1.1 Padronização e Limpeza
*   **Ação**: Revisar o `GlobalStateStore` e `ConversationStore` para garantir um padrão único de gerenciamento de estado via Signals.
*   **Ação**: Centralizar a configuração de variáveis de ambiente e endpoints, removendo hardcodes residuais.

### 1.2 Testes e Qualidade
*   **Gap Crítico**: Baixa cobertura em páginas e componentes de feature.
*   **Ação**: Configurar **Cypress** para testes E2E (fluxos críticos: Login, Chat, Aprovação HITL).
*   **Ação**: Criar um script de CI para rodar linting e testes unitários antes do commit (Husky).

### 1.3 Performance
*   **Ação**: Implementar **Preloading Strategy** seletivo para rotas críticas (Chat, Dashboard) para acelerar a percepção de performance.
*   **Ação**: Auditar e otimizar o bundle size (budgets no `angular.json`), garantindo que bibliotecas pesadas (ex: markdown parsers) sejam carregadas sob demanda.

## 2. 🎨 UI/UX & Design System (Inovação)

### 2.1 Design System "Janus UI"
*   **Conceito**: Criar uma biblioteca visual coesa inspirada em interfaces futuristas (Cyberpunk/Sci-Fi clean), alinhada com a identidade do Janus.
*   **Ação**: Refatorar componentes `shared/ui-*` para usar **CSS Variables** nativas para temas (Dark/Light/High Contrast).
*   **Novos Componentes**:
    *   `ui-toast`: Sistema de notificações toast empilháveis.
    *   `ui-modal`: Modal acessível e animado.
    *   `ui-skeleton`: Padronizar loading states em todas as telas.

### 2.2 Acessibilidade (a11y)
*   **Ação**: Garantir navegação completa via teclado (Focus Trap em modais, Skip Links).
*   **Ação**: Validar contraste de cores e rótulos ARIA em todos os inputs e botões.

## 3. 🌍 Internacionalização (i18n)

### 3.1 Implementação do Transloco ou ngx-translate
*   **Gap Crítico**: Strings hardcoded em PT-BR.
*   **Ação**: Integrar biblioteca de i18n.
*   **Ação**: Extrair strings para arquivos JSON (`pt-BR.json`, `en-US.json`) e aplicar pipes de tradução em todas as views.

## 4. 🚀 Features Faltantes (Roadmap V1)

### 4.1 Gestão de Ferramentas e Workers
*   **Ação**: Desenvolver as páginas `Tools` e `Workers` (atualmente placeholders ou incompletas) para permitir que o usuário gerencie as capacidades do Janus visualmente.

### 4.2 Monitoramento e Analytics
*   **Ação**: Criar dashboard de **Observabilidade no Frontend** (conectado ao backend) para mostrar:
    *   Custo de tokens em tempo real.
    *   Latência de resposta.
    *   Status de saúde dos agentes.

## Cronograma de Execução (Turno Atual)

Focaremos nas ações de alto impacto e baixo esforço para elevar a qualidade imediatamente:
1.  **Refatoração UI/UX**: Melhorar componentes base (`ui-card`, `ui-button`) e padronizar o tema.
2.  **Internacionalização**: Configurar a infraestrutura base de i18n.
3.  **Testes**: Adicionar testes unitários para componentes críticos sem cobertura.
